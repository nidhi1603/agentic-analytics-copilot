from typing import Literal

from pydantic import BaseModel, Field


AllowedRole = Literal["operations_analyst", "regional_manager", "exec_viewer"]


class AskRequest(BaseModel):
    question: str = Field(min_length=5, description="Business investigation question")
    role: AllowedRole = Field(
        default="operations_analyst",
        description="Role requesting the investigation",
    )


class Citation(BaseModel):
    source_type: str
    source_path: str
    title: str
    snippet: str


class AskResponse(BaseModel):
    request_id: str
    latency_ms: int
    role: str
    answer: str
    confidence: str
    confidence_breakdown: list[str]
    needs_analyst_review: bool
    analyst_review_reason: str | None = None
    likely_causes: list[str]
    recommended_next_steps: list[str]
    citations: list[Citation]
    trace: list[str]
    evidence_summary: str
    blocked_sources: list[str]
    data_as_of: str | None = None
    freshness_status: str
    completeness_status: str
