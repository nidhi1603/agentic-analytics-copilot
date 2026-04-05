from pydantic import BaseModel, Field


class SynthesizedAnswer(BaseModel):
    answer: str = Field(description="Grounded answer based only on provided evidence")
    likely_causes: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    suggested_follow_up_questions: list[str] = Field(default_factory=list)
    confidence: str = Field(description="One of high, medium, or low")
    confidence_breakdown: list[str] = Field(
        default_factory=list,
        description="Short reasons that explain the current confidence level",
    )
    needs_analyst_review: bool = Field(
        description="True when evidence is insufficient or conflicting"
    )
    analyst_review_reason: str | None = Field(
        default=None,
        description="Short explanation for why analyst review is required",
    )
