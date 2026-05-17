"""End-to-end RAG evaluation: LangGraph (retrieve → grade → generate) + RAGAS.

Produces the same aggregate metrics as `/evaluate`, plus a **relevancy_score**
that summarizes answer fit, retrieval precision, and faithfulness to context.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.services import evaluator
from backend.services.rag_graph import run_rag_trace

logger = logging.getLogger(__name__)


async def run_pipeline_evaluation(
    namespace: str,
    questions: List[str],
    ground_truths: List[str],
    session_id: str,
) -> Dict[str, Any]:
    """For each question, run live RAG against `namespace`, then score with RAGAS."""
    answers: List[str] = []
    contexts: List[List[str]] = []
    traces: List[Dict[str, Any]] = []

    for q in questions:
        trace = await run_rag_trace(
            question=q,
            chat_history=[],
            namespace=namespace,
            session_id=session_id,
        )
        traces.append(trace)
        answers.append(trace.get("answer") or "")
        ctx = trace.get("contexts") or []
        if not ctx:
            ctx = [
                "(no passages retained after retrieval grading — evaluating "
                "faithfulness/relevancy against this placeholder)"
            ]
        contexts.append(ctx)

    gt = ground_truths if ground_truths else []

    ragas_payload = await evaluator.run_evaluation(
        questions=questions,
        answers=answers,
        contexts=contexts,
        ground_truths=gt,
    )

    per_sample = ragas_payload.get("per_sample") or []
    per_question: List[Dict[str, Any]] = []
    for i, q in enumerate(questions):
        row_scores: Dict[str, float] = {}
        row_rel = 0.0
        if i < len(per_sample):
            row_scores = per_sample[i].get("scores") or {}
            row_rel = float(per_sample[i].get("relevancy_score") or 0.0)

        tr = traces[i] if i < len(traces) else {}
        gt_val = gt[i] if i < len(gt) else None

        per_question.append(
            {
                "question": q,
                "answer": answers[i] if i < len(answers) else "",
                "ground_truth": gt_val,
                "contexts_used": len(tr.get("contexts") or []),
                "retrieved_count": int(tr.get("retrieved_count") or 0),
                "relevant_count_after_grader": int(tr.get("relevant_count") or 0),
                "scores": row_scores,
                "relevancy_score": row_rel,
            }
        )

    logger.info(
        "pipeline eval ns=%s questions=%d relevancy=%.4f",
        namespace,
        len(questions),
        ragas_payload.get("relevancy_score") or 0.0,
    )

    return {
        "namespace": namespace,
        "relevancy_score": ragas_payload["relevancy_score"],
        "aggregate_scores": ragas_payload["scores"],
        "relevancy_breakdown": ragas_payload["relevancy_breakdown"],
        "metrics_used": ragas_payload["metrics_used"],
        "sample_count": ragas_payload["sample_count"],
        "per_question": per_question,
        "per_sample": per_sample,
    }
