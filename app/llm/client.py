import json

from openai import OpenAI

from app.core.config import get_settings
from app.llm.prompts import build_investigation_prompt
from app.orchestration.state import WorkflowState
from app.schemas.answer import SynthesizedAnswer


def synthesize_answer(state: WorkflowState) -> SynthesizedAnswer:
    settings = get_settings()
    if not settings.openai_api_key:
        return fallback_synthesized_answer(state)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = build_investigation_prompt(state)

    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a grounded enterprise analytics assistant.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    return SynthesizedAnswer.model_validate(parsed)


def fallback_synthesized_answer(state: WorkflowState) -> SynthesizedAnswer:
    anomaly_report = state.get("anomaly_report", [])
    incidents = state.get("incidents", [])
    failure_breakdown = state.get("failure_breakdown", [])
    documents = state.get("documents", [])

    likely_causes: list[str] = []
    if failure_breakdown:
        likely_causes.append(
            f"Top shipment issue observed: {failure_breakdown[0].failure_reason}"
        )
    if incidents:
        likely_causes.append(f"Operational incident observed: {incidents[0].incident_type}")

    recommended_next_steps = [
        "Review the top failure reasons and confirm whether they explain the KPI movement.",
        "Validate the explanation against incident logs and runbook guidance.",
    ]

    if not anomaly_report and not documents:
        return SynthesizedAnswer(
            answer="The system could not find enough evidence to explain the issue confidently.",
            likely_causes=[],
            recommended_next_steps=["Escalate to an analyst for manual investigation."],
            confidence="low",
            confidence_breakdown=["Both structured and document evidence were unavailable in the fallback path."],
            needs_analyst_review=True,
            analyst_review_reason="Evidence was missing across both structured and document sources.",
        )

    return SynthesizedAnswer(
        answer=(
            "Based on the retrieved KPI, incident, and document evidence, the issue appears linked "
            "to the dominant operational patterns surfaced in the investigation context."
        ),
        likely_causes=likely_causes,
        recommended_next_steps=recommended_next_steps,
        confidence="medium",
        confidence_breakdown=[
            "Fallback synthesis was used instead of the primary LLM response path.",
            "Evidence was present, but the conservative fallback keeps confidence below auto-approval.",
        ],
        needs_analyst_review=True,
        analyst_review_reason="This fallback path is conservative and keeps an analyst in the loop.",
    )
