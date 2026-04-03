from app.orchestration.state import WorkflowState


def build_investigation_prompt(state: WorkflowState) -> str:
    lines: list[str] = [
        "You are an internal analytics copilot for enterprise operations.",
        "Answer only from the evidence provided below.",
        "Do not invent causes, metrics, incidents, or recommendations.",
        "If evidence is incomplete or conflicting, lower confidence and require analyst review.",
        "",
        f"User question: {state['question']}",
        "",
        "Evidence summary:",
        state.get("evidence_summary", "No evidence summary available."),
        "",
        "Structured evidence:",
    ]

    for kpi in state.get("anomaly_report", []):
        lines.append(
            f"- KPI anomaly | date={kpi.metric_date} | region={kpi.region} | "
            f"metric={kpi.metric_name} | value={kpi.metric_value} | target={kpi.metric_target} | "
            f"severity={kpi.anomaly_severity} | notes={kpi.notes}"
        )

    for incident in state.get("incidents", []):
        lines.append(
            f"- Incident | date={incident.incident_date} | region={incident.region} | "
            f"type={incident.incident_type} | severity={incident.severity} | status={incident.status} | "
            f"summary={incident.summary}"
        )

    for failure in state.get("failure_breakdown", []):
        lines.append(
            f"- Failure pattern | reason={failure.failure_reason} | count={failure.event_count}"
        )

    metric_definition = state.get("metric_definition")
    if metric_definition is not None:
        lines.append(
            f"- Metric definition | metric={metric_definition.metric_name} | "
            f"definition={metric_definition.metric_definition} | "
            f"hint={metric_definition.investigation_hint}"
        )

    lines.append("")
    lines.append("Document evidence:")

    for document in state.get("documents", []):
        lines.append(
            f"- Doc | title={document.title} | group={document.doc_group} | "
            f"source={document.source_path} | content={document.content}"
        )

    lines.append("")
    lines.append(
        "Return a grounded JSON object with: answer, likely_causes, recommended_next_steps, confidence, needs_analyst_review."
    )

    return "\n".join(lines)

