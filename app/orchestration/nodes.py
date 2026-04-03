from app.llm.client import synthesize_answer
from app.orchestration.router import classify_route, extract_metric_name, extract_region
from app.orchestration.state import WorkflowState
from app.services.answer_service import apply_confidence_guardrails, build_citations
from app.services.policy_service import is_resource_allowed
from app.tools.operations_tools import (
    tool_get_anomaly_report,
    tool_get_failure_breakdown,
    tool_get_incidents,
    tool_get_kpi_summary,
    tool_get_metric_definition,
    tool_retrieve_documents,
)


def classify_request_node(state: WorkflowState) -> WorkflowState:
    question = state["question"]
    role = state["role"]
    route = classify_route(question)
    region = extract_region(question)
    metric_name = extract_metric_name(question)

    trace = list(state.get("trace", []))
    trace.append(
        f"classify_request: role={role}, route={route}, region={region or 'unknown'}, metric={metric_name or 'unknown'}"
    )

    return {
        "route": route,
        "region": region,
        "metric_name": metric_name,
        "requires_structured": route in {"structured_only", "hybrid"},
        "requires_documents": route in {"documents_only", "hybrid"},
        "trace": trace,
    }


def gather_structured_evidence_node(state: WorkflowState) -> WorkflowState:
    role = state["role"]
    region = state.get("region")
    metric_name = state.get("metric_name")
    trace = list(state.get("trace", []))
    blocked_sources = list(state.get("blocked_sources", []))
    allowed_sources = list(state.get("allowed_sources", []))

    kpi_summary = []
    anomaly_report = []
    incidents = []
    failure_breakdown = []
    metric_definition = None

    daily_allowed, daily_reason = is_resource_allowed(role, "structured", "daily_kpis")
    if daily_allowed:
        allowed_sources.append("structured:daily_kpis")
        kpi_summary = tool_get_kpi_summary(region=region, metric_name=metric_name, limit=5)
        anomaly_report = tool_get_anomaly_report(region=region, metric_name=metric_name)
    else:
        blocked_sources.append(f"structured:daily_kpis ({daily_reason})")

    incident_allowed, incident_reason = is_resource_allowed(role, "structured", "incident_log")
    if incident_allowed:
        allowed_sources.append("structured:incident_log")
        incidents = tool_get_incidents(region=region, limit=5)
    else:
        blocked_sources.append(f"structured:incident_log ({incident_reason})")

    shipment_allowed, shipment_reason = is_resource_allowed(role, "structured", "shipment_events")
    if shipment_allowed:
        allowed_sources.append("structured:shipment_events")
        failure_breakdown = tool_get_failure_breakdown(region=region)
    else:
        blocked_sources.append(f"structured:shipment_events ({shipment_reason})")

    metric_allowed, metric_reason = is_resource_allowed(role, "structured", "metric_definitions")
    if metric_allowed and metric_name is not None:
        allowed_sources.append("structured:metric_definitions")
        metric_definition = tool_get_metric_definition(metric_name)
    elif not metric_allowed:
        blocked_sources.append(f"structured:metric_definitions ({metric_reason})")

    freshness_status, data_as_of, completeness_status = summarize_data_health(
        anomaly_report or kpi_summary
    )

    trace.append(
        "gather_structured_evidence: "
        f"kpis={len(kpi_summary)}, anomalies={len(anomaly_report)}, "
        f"incidents={len(incidents)}, failures={len(failure_breakdown)}, "
        f"blocked={len(blocked_sources)}"
    )

    return {
        "kpi_summary": kpi_summary,
        "anomaly_report": anomaly_report,
        "incidents": incidents,
        "failure_breakdown": failure_breakdown,
        "metric_definition": metric_definition,
        "trace": trace,
        "blocked_sources": blocked_sources,
        "allowed_sources": allowed_sources,
        "freshness_status": freshness_status,
        "data_as_of": data_as_of,
        "completeness_status": completeness_status,
    }


def gather_document_evidence_node(state: WorkflowState) -> WorkflowState:
    question = state["question"]
    role = state["role"]
    metric_name = state.get("metric_name")
    trace = list(state.get("trace", []))
    blocked_sources = list(state.get("blocked_sources", []))
    allowed_sources = list(state.get("allowed_sources", []))

    query_text = question
    if metric_name:
        query_text = f"{question}\nRelated metric: {metric_name}"

    documents, blocked_documents, allowed_documents = tool_retrieve_documents(
        query_text=query_text,
        role=role,
        limit=4,
    )
    blocked_sources.extend(blocked_documents)
    allowed_sources.extend(allowed_documents)
    trace.append(
        f"gather_document_evidence: documents={len(documents)}, blocked={len(blocked_documents)}"
    )

    return {
        "documents": documents,
        "trace": trace,
        "blocked_sources": blocked_sources,
        "allowed_sources": allowed_sources,
    }


def prepare_investigation_context_node(state: WorkflowState) -> WorkflowState:
    trace = list(state.get("trace", []))
    route = state["route"]
    region = state.get("region") or "unspecified region"
    metric_name = state.get("metric_name") or "unspecified metric"

    summary_lines = [
        f"Role: {state['role']}",
        f"Question route: {route}",
        f"Region: {region}",
        f"Metric: {metric_name}",
        f"KPI rows retrieved: {len(state.get('kpi_summary', []))}",
        f"Anomalies retrieved: {len(state.get('anomaly_report', []))}",
        f"Incidents retrieved: {len(state.get('incidents', []))}",
        f"Failure patterns retrieved: {len(state.get('failure_breakdown', []))}",
        f"Documents retrieved: {len(state.get('documents', []))}",
        f"Blocked sources: {len(state.get('blocked_sources', []))}",
        f"Freshness status: {state.get('freshness_status', 'unknown')}",
        f"Completeness status: {state.get('completeness_status', 'unknown')}",
    ]

    if state.get("metric_definition") is not None:
        summary_lines.append("Metric definition available: yes")
    else:
        summary_lines.append("Metric definition available: no")

    trace.append("prepare_investigation_context: packaged evidence summary")

    return {
        "evidence_summary": "\n".join(summary_lines),
        "trace": trace,
    }


def synthesize_answer_node(state: WorkflowState) -> WorkflowState:
    trace = list(state.get("trace", []))
    synthesized = synthesize_answer(state)
    guarded = apply_confidence_guardrails(state, synthesized)
    citations = build_citations(state)

    trace.append(
        "synthesize_answer: "
        f"confidence={guarded.confidence}, needs_review={guarded.needs_analyst_review}, "
        f"citations={len(citations)}"
    )

    return {
        "synthesized_answer": guarded,
        "citations": citations,
        "trace": trace,
        "analyst_review_reason": guarded.analyst_review_reason,
    }


def should_collect_structured(state: WorkflowState) -> str:
    return "gather_structured_evidence" if state.get("requires_structured") else "skip_structured"


def should_collect_documents(state: WorkflowState) -> str:
    return "gather_document_evidence" if state.get("requires_documents") else "prepare_investigation_context"


def summarize_data_health(
    anomaly_report,
) -> tuple[str, str | None, str]:
    if not anomaly_report:
        return "unknown", None, "unknown"

    statuses = {item.freshness_status for item in anomaly_report}
    if "stale" in statuses:
        freshness_status = "stale"
    elif "lagging" in statuses:
        freshness_status = "lagging"
    else:
        freshness_status = "fresh"

    latest_data_as_of = max(item.data_as_of for item in anomaly_report)
    min_completeness = min(item.completeness_pct for item in anomaly_report)
    if min_completeness >= 0.95:
        completeness_status = "complete"
    elif min_completeness >= 0.8:
        completeness_status = "partial"
    else:
        completeness_status = "low"

    return freshness_status, latest_data_as_of, completeness_status
