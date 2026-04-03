from app.services.workflow_service import run_question_workflow


def test_run_question_workflow_returns_safe_fallback_on_exception(monkeypatch) -> None:
    def fake_run_investigation_workflow(_question: str, _role: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.services.workflow_service.run_investigation_workflow",
        fake_run_investigation_workflow,
    )

    response = run_question_workflow("Why did Region 3 drop?", "operations_analyst")

    assert response.confidence == "low"
    assert response.needs_analyst_review is True
    assert response.trace == ["workflow_failed"]
    assert response.role == "operations_analyst"
