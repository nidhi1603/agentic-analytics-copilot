from app.orchestration.state import WorkflowState
from app.schemas.answer import SynthesizedAnswer
from app.schemas.ask import Citation


def build_citations(state: WorkflowState) -> list[Citation]:
    citations: list[Citation] = []

    for incident in state.get("incidents", [])[:2]:
        citations.append(
            Citation(
                source_type="structured",
                source_path="incident_log",
                title=f"Incident {incident.incident_id}",
                snippet=incident.summary,
            )
        )

    for document in state.get("documents", [])[:3]:
        citations.append(
            Citation(
                source_type="document",
                source_path=document.source_path,
                title=document.title,
                snippet=document.content[:220],
            )
        )

    return citations


def apply_confidence_guardrails(
    state: WorkflowState, synthesized: SynthesizedAnswer
) -> SynthesizedAnswer:
    anomaly_count = len(state.get("anomaly_report", []))
    document_count = len(state.get("documents", []))
    incident_count = len(state.get("incidents", []))

    if anomaly_count == 0 and document_count == 0:
        return synthesized.model_copy(
            update={
                "confidence": "low",
                "needs_analyst_review": True,
                "recommended_next_steps": ["Escalate to analyst review due to missing evidence."],
            }
        )

    if anomaly_count > 0 and incident_count > 0 and document_count > 0:
        if synthesized.confidence == "low":
            return synthesized.model_copy(
                update={"confidence": "medium", "needs_analyst_review": True}
            )
        return synthesized

    return synthesized.model_copy(update={"needs_analyst_review": True})

