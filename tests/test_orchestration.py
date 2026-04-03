from app.orchestration.nodes import prepare_investigation_context_node


def test_prepare_investigation_context_summarizes_state() -> None:
    result = prepare_investigation_context_node(
        {
            "question": "Why did delivery success rate drop in Region 3?",
            "role": "operations_analyst",
            "route": "hybrid",
            "region": "Region 3",
            "metric_name": "delivery_success_rate",
            "kpi_summary": [],
            "anomaly_report": [],
            "incidents": [],
            "failure_breakdown": [],
            "documents": [],
            "metric_definition": None,
            "trace": [],
            "blocked_sources": [],
            "freshness_status": "fresh",
            "completeness_status": "complete",
        }
    )

    assert "Region: Region 3" in result["evidence_summary"]
    assert "Metric: delivery_success_rate" in result["evidence_summary"]


def test_synthesize_answer_node_can_be_added_later_without_state_loss() -> None:
    result = prepare_investigation_context_node(
        {
            "question": "What does the SOP say for Region 3?",
            "role": "operations_analyst",
            "route": "documents_only",
            "region": "Region 3",
            "metric_name": None,
            "documents": [],
            "trace": ["classify_request"],
            "blocked_sources": [],
            "freshness_status": "unknown",
            "completeness_status": "unknown",
        }
    )

    assert "Documents retrieved: 0" in result["evidence_summary"]
    assert "Role: operations_analyst" in result["evidence_summary"]
