"""POST /evaluate — RAGAS metrics; POST /evaluate/pipeline — live RAG + RAGAS + relevancy."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.models.evaluate import (
    EvaluateRequest,
    EvaluateResponse,
    PipelineEvaluateRequest,
    PipelineEvaluateResponse,
)
from backend.services import evaluator
from backend.services.evaluation_pipeline import run_pipeline_evaluation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("", response_model=EvaluateResponse)
async def evaluate_batch(req: EvaluateRequest) -> EvaluateResponse:
    try:
        result = await evaluator.run_evaluation(
            questions=req.questions,
            answers=req.answers,
            contexts=req.contexts,
            ground_truths=req.ground_truths,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ragas failure")
        raise HTTPException(status_code=500, detail=f"ragas error: {exc}") from exc

    return EvaluateResponse(**result)


@router.post("/pipeline", response_model=PipelineEvaluateResponse)
async def evaluate_pipeline(req: PipelineEvaluateRequest) -> PipelineEvaluateResponse:
    """Run retrieval → grading → generation per question, then RAGAS + relevancy_score."""
    try:
        result = await run_pipeline_evaluation(
            namespace=req.namespace,
            questions=req.questions,
            ground_truths=req.ground_truths,
            session_id=req.session_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("pipeline eval failure")
        raise HTTPException(
            status_code=500, detail=f"pipeline evaluation error: {exc}"
        ) from exc

    return PipelineEvaluateResponse(**result)
