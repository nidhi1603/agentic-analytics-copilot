from app.schemas.answer import SynthesizedAnswer
from app.services.answer_service import apply_confidence_guardrails


def test_apply_confidence_guardrails_marks_missing_evidence_low_confidence() -> None:
    synthesized = SynthesizedAnswer(
        answer="Insufficient evidence.",
        likely_causes=[],
        recommended_next_steps=[],
        confidence="medium",
        needs_analyst_review=False,
    )

    result = apply_confidence_guardrails(
        {"anomaly_report": [], "documents": [], "incidents": []},
        synthesized,
    )

    assert result.confidence == "low"
    assert result.needs_analyst_review is True

