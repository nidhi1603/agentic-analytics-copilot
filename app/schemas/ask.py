from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=5, description="Business investigation question")


class Citation(BaseModel):
    source_type: str
    source_path: str
    title: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    confidence: str
    needs_analyst_review: bool
    likely_causes: list[str]
    recommended_next_steps: list[str]
    citations: list[Citation]
    trace: list[str]
    evidence_summary: str

