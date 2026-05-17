"""RAGAS evaluation runner.

Compatible with RAGAS 0.2.x. We expose four canonical metrics and let
the API layer stay thin.

Notes
-----
* In RAGAS 0.2, `evaluate(...)` no longer auto-wraps raw LangChain LLMs;
  the explicit `LangchainLLMWrapper` / `LangchainEmbeddingsWrapper` is
  required.
* We use `result.to_pandas()` for score extraction — it works across
  RAGAS 0.1 and 0.2 and naturally handles per-sample NaNs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Composite relevancy index (0–1): answer ↔ question, retrieval quality, grounding.
# Weights renormalize automatically if a metric is absent (e.g. missing API fields).
_RELEVANCY_WEIGHTS: Dict[str, float] = {
    "answer_relevancy": 0.45,
    "context_precision": 0.35,
    "faithfulness": 0.20,
}


def compute_relevancy_score(
    scores: Dict[str, float],
) -> tuple[float, Dict[str, float], Dict[str, float]]:
    """Return (relevancy_score, normalized_weights_used, component_scores_used)."""
    import math

    components: Dict[str, float] = {}
    weight_sum = 0.0
    weighted = 0.0
    for key, w in _RELEVANCY_WEIGHTS.items():
        raw = scores.get(key)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isnan(v):
            continue
        components[key] = v
        weighted += w * v
        weight_sum += w

    if weight_sum <= 0:
        ar = scores.get("answer_relevancy")
        if ar is not None:
            try:
                fv = float(ar)
                if not math.isnan(fv):
                    return fv, {"answer_relevancy": 1.0}, {"answer_relevancy": fv}
            except (TypeError, ValueError):
                pass
        return 0.0, {}, {}

    relevancy = weighted / weight_sum
    norm_weights = {k: _RELEVANCY_WEIGHTS[k] / weight_sum for k in components}
    return relevancy, norm_weights, components


def _per_sample_rows(result, metrics) -> List[Dict[str, Any]]:
    """Build per-question scores + relevancy when RAGAS returns a DataFrame."""
    import math

    rows_out: List[Dict[str, Any]] = []
    try:
        df = result.to_pandas()
    except Exception:  # noqa: BLE001
        return rows_out

    if df is None or len(df) == 0:
        return rows_out

    for i in range(len(df)):
        row = df.iloc[i]
        sample_scores: Dict[str, float] = {}
        for m in metrics:
            name = getattr(m, "name", None) or m.__class__.__name__
            if name not in df.columns:
                continue
            v = row[name]
            try:
                if hasattr(v, "item"):
                    v = v.item()
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    continue
                sample_scores[name] = float(v)
            except (TypeError, ValueError):
                continue
        rel, _, _ = compute_relevancy_score(sample_scores)
        rows_out.append(
            {
                "index": i,
                "scores": sample_scores,
                "relevancy_score": rel,
            }
        )
    return rows_out


def _build_dataset(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: List[str],
) -> Dataset:
    payload: Dict[str, List[Any]] = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
    }
    if ground_truths:
        # RAGAS 0.2 prefers `reference`; legacy `ground_truth` still works
        payload["reference"] = ground_truths
        payload["ground_truth"] = ground_truths
    return Dataset.from_dict(payload)


def _select_metrics(has_ground_truth: bool):
    from ragas.metrics import (  # local import keeps cold-start cheap
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    metrics = [faithfulness, answer_relevancy, context_precision]
    if has_ground_truth:
        metrics.append(context_recall)
    return metrics


def _extract_scores(result, metrics) -> Dict[str, float]:
    """Pull mean per-metric scores out of a RAGAS result, version-agnostic."""
    out: Dict[str, float] = {}

    df = None
    try:
        df = result.to_pandas()
    except Exception:  # noqa: BLE001
        df = None

    if df is not None:
        for m in metrics:
            name = getattr(m, "name", None) or m.__class__.__name__
            if name in df.columns:
                col = df[name].dropna()
                if not col.empty:
                    out[name] = float(col.mean())

    if not out and hasattr(result, "scores"):
        # ragas 0.2 fallback: result.scores is List[Dict[str, float]]
        scores_list = result.scores or []
        if scores_list and isinstance(scores_list, list):
            sums: Dict[str, float] = {}
            counts: Dict[str, int] = {}
            for sample in scores_list:
                if not isinstance(sample, dict):
                    continue
                for k, v in sample.items():
                    try:
                        f = float(v)
                    except (TypeError, ValueError):
                        continue
                    if f != f:  # NaN
                        continue
                    sums[k] = sums.get(k, 0.0) + f
                    counts[k] = counts.get(k, 0) + 1
            out = {k: sums[k] / counts[k] for k in sums if counts[k] > 0}

    if not out:
        # ragas 0.1 fallback: result is dict-like
        try:
            for k, v in dict(result).items():
                f = float(v)
                if f == f:
                    out[str(k)] = f
        except Exception:  # noqa: BLE001
            pass

    return out


def _run_sync(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: List[str],
) -> Dict[str, Any]:
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    cfg = get_settings()
    has_gt = bool(ground_truths and any(g.strip() for g in ground_truths))
    metrics = _select_metrics(has_gt)

    base_llm = ChatOpenAI(
        model=cfg.OPENAI_CHAT_MODEL,
        api_key=cfg.OPENAI_API_KEY,
        temperature=0.0,
    )
    base_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=cfg.OPENAI_API_KEY,
    )
    llm = LangchainLLMWrapper(base_llm)
    embeddings = LangchainEmbeddingsWrapper(base_embeddings)

    dataset = _build_dataset(
        questions, answers, contexts, ground_truths if has_gt else []
    )

    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
        show_progress=False,
    )

    scores = _extract_scores(result, metrics)
    relevancy, norm_weights, components = compute_relevancy_score(scores)
    per_sample = _per_sample_rows(result, metrics)

    return {
        "scores": scores,
        "sample_count": len(questions),
        "metrics_used": [getattr(m, "name", m.__class__.__name__) for m in metrics],
        "relevancy_score": relevancy,
        "relevancy_breakdown": {
            "components": components,
            "weights_applied": norm_weights,
            "description": (
                "Weighted blend of answer_relevancy (Q↔A fit), "
                "context_precision (retrieval usefulness vs question), "
                "and faithfulness (answer grounded in retrieved context)."
            ),
        },
        "per_sample": per_sample,
    }


async def run_evaluation(
    questions: List[str],
    answers: List[str],
    contexts: List[List[str]],
    ground_truths: List[str],
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _run_sync, questions, answers, contexts, ground_truths
    )
