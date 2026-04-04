from langgraph.graph import END, START, StateGraph

from app.orchestration.nodes import (
    classify_request_node,
    gather_document_evidence_node,
    gather_structured_evidence_node,
    prepare_investigation_context_node,
    should_collect_documents,
    should_collect_structured,
    synthesize_answer_node,
)
from app.orchestration.state import WorkflowState


def build_investigation_graph():
    graph = StateGraph(WorkflowState)

    graph.add_node("classify_request", classify_request_node)
    graph.add_node("gather_structured_evidence", gather_structured_evidence_node)
    graph.add_node("skip_structured", lambda state: {"trace": list(state.get("trace", []))})
    graph.add_node("gather_document_evidence", gather_document_evidence_node)
    graph.add_node("prepare_investigation_context", prepare_investigation_context_node)
    graph.add_node("synthesize_answer", synthesize_answer_node)

    graph.add_edge(START, "classify_request")
    graph.add_conditional_edges(
        "classify_request",
        should_collect_structured,
        {
            "gather_structured_evidence": "gather_structured_evidence",
            "skip_structured": "skip_structured",
        },
    )
    graph.add_conditional_edges(
        "gather_structured_evidence",
        should_collect_documents,
        {
            "gather_document_evidence": "gather_document_evidence",
            "prepare_investigation_context": "prepare_investigation_context",
        },
    )
    graph.add_conditional_edges(
        "skip_structured",
        should_collect_documents,
        {
            "gather_document_evidence": "gather_document_evidence",
            "prepare_investigation_context": "prepare_investigation_context",
        },
    )
    graph.add_edge("gather_document_evidence", "prepare_investigation_context")
    graph.add_edge("prepare_investigation_context", "synthesize_answer")
    graph.add_edge("synthesize_answer", END)

    return graph.compile()


def run_investigation_workflow(question: str, role: str, request_id: str | None = None) -> WorkflowState:
    graph = build_investigation_graph()
    return graph.invoke(
        {
            "request_id": request_id,
            "question": question,
            "role": role,
            "trace": [],
            "blocked_sources": [],
            "allowed_sources": [],
        }
    )
