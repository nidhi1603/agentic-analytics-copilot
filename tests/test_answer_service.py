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
    assert any("No structured KPI evidence" in item for item in result.confidence_breakdown)
    assert result.suggested_follow_up_questions


def test_apply_confidence_guardrails_marks_restricted_access_low_confidence() -> None:
    synthesized = SynthesizedAnswer(
        answer="Restricted access.",
        likely_causes=[],
        recommended_next_steps=[],
        confidence="medium",
        needs_analyst_review=False,
    )

    result = apply_confidence_guardrails(
        {
            "anomaly_report": [],
            "documents": [],
            "incidents": [],
            "blocked_sources": ["document:incident_notes (restricted)"],
        },
        synthesized,
    )

    assert result.confidence == "low"
    assert result.needs_analyst_review is True
    assert "restricted" in (result.analyst_review_reason or "").lower()
    assert any("blocked by role-based access policy" in item for item in result.confidence_breakdown)
    assert any("authorized" in item.lower() or "restricted" in item.lower() for item in result.suggested_follow_up_questions)
