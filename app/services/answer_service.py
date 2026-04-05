from app.orchestration.state import WorkflowState
from app.schemas.answer import SynthesizedAnswer
from app.schemas.ask import Citation


def build_citations(state: WorkflowState) -> list[Citation]:
    citations: list[Citation] = []

    for kpi in (state.get("anomaly_report") or state.get("kpi_summary", []))[:2]:
        citations.append(
            Citation(
                source_type="structured",
                source_path="daily_kpis",
                title=f"{kpi.metric_name} in {kpi.region} on {kpi.metric_date}",
                snippet=(
                    f"value={kpi.metric_value}, target={kpi.metric_target}, "
                    f"freshness={kpi.freshness_status}, completeness={kpi.completeness_pct}"
                ),
            )
        )

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
    blocked_count = len(state.get("blocked_sources", []))
    freshness_status = state.get("freshness_status", "unknown")
    completeness_status = state.get("completeness_status", "unknown")

    if blocked_count > 0 and anomaly_count == 0 and document_count == 0:
        updated = synthesized.model_copy(
            update={
                "confidence": "low",
                "needs_analyst_review": True,
                "analyst_review_reason": "Required sources were restricted by role-based access policy.",
                "recommended_next_steps": [
                    "Escalate to a role with broader access or request analyst review."
                ],
            }
        )
        return updated.model_copy(
            update={
                "confidence_breakdown": build_confidence_breakdown(state, updated),
                "suggested_follow_up_questions": build_follow_up_questions(state, updated),
            }
        )

    if anomaly_count == 0 and document_count == 0:
        updated = synthesized.model_copy(
            update={
                "confidence": "low",
                "needs_analyst_review": True,
                "analyst_review_reason": "The system could not retrieve enough evidence to support a grounded answer.",
                "recommended_next_steps": ["Escalate to analyst review due to missing evidence."],
            }
        )
        return updated.model_copy(
            update={
                "confidence_breakdown": build_confidence_breakdown(state, updated),
                "suggested_follow_up_questions": build_follow_up_questions(state, updated),
            }
        )

    if freshness_status in {"stale", "lagging"} or completeness_status in {"partial", "low"}:
        updated = synthesized.model_copy(
            update={
                "confidence": "medium" if synthesized.confidence == "high" else "low",
                "needs_analyst_review": True,
                "analyst_review_reason": (
                    "Data freshness or completeness is below the trusted threshold for full automation."
                ),
            }
        )
        return updated.model_copy(
            update={
                "confidence_breakdown": build_confidence_breakdown(state, updated),
                "suggested_follow_up_questions": build_follow_up_questions(state, updated),
            }
        )

    if anomaly_count > 0 and incident_count > 0 and document_count > 0:
        if synthesized.confidence == "low":
            updated = synthesized.model_copy(
                update={
                    "confidence": "medium",
                    "needs_analyst_review": True,
                    "analyst_review_reason": "Evidence is present but confidence remains below the auto-approval threshold.",
                }
            )
            return updated.model_copy(
                update={
                    "confidence_breakdown": build_confidence_breakdown(state, updated),
                    "suggested_follow_up_questions": build_follow_up_questions(state, updated),
                }
            )
        return synthesized.model_copy(
            update={
                "confidence_breakdown": build_confidence_breakdown(state, synthesized),
                "suggested_follow_up_questions": build_follow_up_questions(state, synthesized),
            }
        )

    updated = synthesized.model_copy(
        update={
            "needs_analyst_review": True,
            "analyst_review_reason": synthesized.analyst_review_reason
            or "The evidence package is incomplete, so analyst review is recommended.",
        }
    )
    return updated.model_copy(
        update={
            "confidence_breakdown": build_confidence_breakdown(state, updated),
            "suggested_follow_up_questions": build_follow_up_questions(state, updated),
        }
    )


def build_confidence_breakdown(
    state: WorkflowState, synthesized: SynthesizedAnswer
) -> list[str]:
    breakdown: list[str] = []
    anomaly_count = len(state.get("anomaly_report", []))
    kpi_count = len(state.get("kpi_summary", []))
    document_count = len(state.get("documents", []))
    incident_count = len(state.get("incidents", []))
    blocked_count = len(state.get("blocked_sources", []))
    freshness_status = state.get("freshness_status", "unknown")
    completeness_status = state.get("completeness_status", "unknown")

    if anomaly_count > 0 or kpi_count > 0:
        breakdown.append(
            f"Structured KPI evidence available ({max(anomaly_count, kpi_count)} row(s))."
        )
    else:
        breakdown.append("No structured KPI evidence was available for this answer.")

    if incident_count > 0:
        breakdown.append(f"Incident context was retrieved from {incident_count} record(s).")

    if document_count > 0:
        breakdown.append(f"Document retrieval returned {document_count} supporting chunk(s).")
    else:
        breakdown.append("No supporting documents were retrieved for this question.")

    if blocked_count > 0:
        breakdown.append(
            f"{blocked_count} source(s) were blocked by role-based access policy, reducing confidence."
        )

    if freshness_status != "unknown":
        breakdown.append(f"Data freshness status is {freshness_status}.")

    if completeness_status != "unknown":
        breakdown.append(f"Data completeness status is {completeness_status}.")

    if synthesized.needs_analyst_review and synthesized.analyst_review_reason:
        breakdown.append(f"Analyst review triggered: {synthesized.analyst_review_reason}")

    if synthesized.confidence == "high" and anomaly_count > 0 and document_count > 0:
        breakdown.append("Structured and document evidence both support the current conclusion.")

    return breakdown


def build_follow_up_questions(
    state: WorkflowState, synthesized: SynthesizedAnswer
) -> list[str]:
    suggestions: list[str] = []
    region = state.get("region") or "the impacted region"
    metric_name = (state.get("metric_name") or "this KPI").replace("_", " ")
    role = state.get("role", "operations_analyst")
    route = state.get("route", "structured_only")

    if state.get("incidents"):
        suggestions.append(f"What incident details support the {metric_name} issue in {region}?")

    if state.get("documents"):
        suggestions.append(f"What do the runbook or policy documents recommend we do next for {region}?")
    else:
        suggestions.append(f"Which internal policy or SOP should we consult next for {region}?")

    if state.get("anomaly_report") or state.get("kpi_summary"):
        suggestions.append(f"How has {metric_name} trended over the last 3 days in {region}?")

    freshness_status = state.get("freshness_status", "unknown")
    completeness_status = state.get("completeness_status", "unknown")
    if freshness_status in {"stale", "lagging"} or completeness_status in {"partial", "low"}:
        suggestions.append(f"When will fresher or more complete data be available for {region}?")

    blocked_sources = state.get("blocked_sources", [])
    if blocked_sources:
        if role == "exec_viewer":
            suggestions.append("What analyst briefing should I request to review the restricted operational detail?")
        elif role == "regional_manager":
            suggestions.append(f"What analyst-only evidence is missing for {region}, and who should review it?")
        else:
            suggestions.append("Which restricted sources would improve confidence if an authorized reviewer checked them?")

    if synthesized.needs_analyst_review:
        suggestions.append("What should an analyst verify first before acting on this conclusion?")

    if route == "documents_only":
        suggestions.append(f"Can we validate this document guidance against KPI evidence for {region}?")
    elif route == "structured_only":
        suggestions.append(f"What document or runbook context should we use to interpret the {metric_name} movement?")

    deduped: list[str] = []
    seen = set()
    for suggestion in suggestions:
        normalized = suggestion.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(suggestion)

    return deduped[:4]
