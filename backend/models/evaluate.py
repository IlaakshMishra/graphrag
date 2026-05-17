"""RAGAS evaluation schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class EvaluateRequest(BaseModel):
    questions: List[str] = Field(..., min_length=1)
    answers: List[str] = Field(..., min_length=1)
    contexts: List[List[str]] = Field(
        ...,
        min_length=1,
        description="Retrieved chunks (texts) per question",
    )
    ground_truths: List[str] = Field(
        default_factory=list,
        description="Optional reference answers; required for context_recall",
    )

    @model_validator(mode="after")
    def _equal_lengths(self):
        n = len(self.questions)
        if not (len(self.answers) == len(self.contexts) == n):
            raise ValueError(
                "questions, answers, contexts must all have the same length"
            )
        if self.ground_truths and len(self.ground_truths) != n:
            raise ValueError("ground_truths length must match questions length")
        return self


class PerSampleEval(BaseModel):
    index: int
    scores: Dict[str, float] = Field(default_factory=dict)
    relevancy_score: float = 0.0


class EvaluateResponse(BaseModel):
    scores: Dict[str, float]
    sample_count: int
    metrics_used: List[str]
    relevancy_score: float = Field(
        ...,
        description=(
            "Composite 0–1 score: weighted blend of answer_relevancy, "
            "context_precision, and faithfulness"
        ),
    )
    relevancy_breakdown: Dict[str, Any] = Field(default_factory=dict)
    per_sample: List[PerSampleEval] = Field(default_factory=list)


class PipelineEvaluateRequest(BaseModel):
    """Run live RAG against a Pinecone namespace, then RAGAS."""

    namespace: str = Field(..., min_length=1)
    questions: List[str] = Field(..., min_length=1)
    ground_truths: List[str] = Field(
        default_factory=list,
        description="Optional reference answers per question (enables context_recall)",
    )
    session_id: str = Field(
        "eval-pipeline",
        min_length=1,
        description="Stable id for logging / future chat threading",
    )

    @model_validator(mode="after")
    def _gt_len(self):
        if self.ground_truths and len(self.ground_truths) != len(self.questions):
            raise ValueError("ground_truths length must match questions length")
        return self


class PipelineQuestionResult(BaseModel):
    question: str
    answer: str
    ground_truth: Optional[str] = None
    contexts_used: int = 0
    retrieved_count: int = 0
    relevant_count_after_grader: int = 0
    scores: Dict[str, float] = Field(default_factory=dict)
    relevancy_score: float = 0.0


class PipelineEvaluateResponse(BaseModel):
    namespace: str
    relevancy_score: float
    aggregate_scores: Dict[str, float]
    relevancy_breakdown: Dict[str, Any]
    metrics_used: List[str]
    sample_count: int
    per_question: List[PipelineQuestionResult]
    per_sample: List[PerSampleEval] = Field(
        default_factory=list,
        description="Raw RAGAS rows aligned with question order",
    )
