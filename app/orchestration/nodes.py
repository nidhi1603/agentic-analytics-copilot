from app.llm.client import synthesize_answer
from app.orchestration.router import classify_route, extract_metric_name, extract_region
from app.orchestration.state import WorkflowState
from app.services.answer_service import apply_confidence_guardrails, build_citations
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
    route = classify_route(question)
    region = extract_region(question)
    metric_name = extract_metric_name(question)

    trace = list(state.get("trace", []))
    trace.append(
        f"classify_request: route={route}, region={region or 'unknown'}, metric={metric_name or 'unknown'}"
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
    region = state.get("region")
    metric_name = state.get("metric_name")
    trace = list(state.get("trace", []))

    kpi_summary = tool_get_kpi_summary(region=region, metric_name=metric_name, limit=5)
    anomaly_report = tool_get_anomaly_report(region=region, metric_name=metric_name)
    incidents = tool_get_incidents(region=region, limit=5)
    failure_breakdown = tool_get_failure_breakdown(region=region)
    metric_definition = (
        tool_get_metric_definition(metric_name) if metric_name is not None else None
    )

    trace.append(
        "gather_structured_evidence: "
        f"kpis={len(kpi_summary)}, anomalies={len(anomaly_report)}, "
        f"incidents={len(incidents)}, failures={len(failure_breakdown)}"
    )

    return {
        "kpi_summary": kpi_summary,
        "anomaly_report": anomaly_report,
        "incidents": incidents,
        "failure_breakdown": failure_breakdown,
        "metric_definition": metric_definition,
        "trace": trace,
    }


def gather_document_evidence_node(state: WorkflowState) -> WorkflowState:
    question = state["question"]
    metric_name = state.get("metric_name")
    trace = list(state.get("trace", []))

    query_text = question
    if metric_name:
        query_text = f"{question}\nRelated metric: {metric_name}"

    documents = tool_retrieve_documents(query_text=query_text, limit=4)
    trace.append(f"gather_document_evidence: documents={len(documents)}")

    return {
        "documents": documents,
        "trace": trace,
    }


def prepare_investigation_context_node(state: WorkflowState) -> WorkflowState:
    trace = list(state.get("trace", []))
    route = state["route"]
    region = state.get("region") or "unspecified region"
    metric_name = state.get("metric_name") or "unspecified metric"

    summary_lines = [
        f"Question route: {route}",
        f"Region: {region}",
        f"Metric: {metric_name}",
        f"KPI rows retrieved: {len(state.get('kpi_summary', []))}",
        f"Anomalies retrieved: {len(state.get('anomaly_report', []))}",
        f"Incidents retrieved: {len(state.get('incidents', []))}",
        f"Failure patterns retrieved: {len(state.get('failure_breakdown', []))}",
        f"Documents retrieved: {len(state.get('documents', []))}",
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
    }


def should_collect_structured(state: WorkflowState) -> str:
    return "gather_structured_evidence" if state.get("requires_structured") else "skip_structured"


def should_collect_documents(state: WorkflowState) -> str:
    return "gather_document_evidence" if state.get("requires_documents") else "prepare_investigation_context"
