from fastapi.testclient import TestClient

from app.core.auth import create_demo_token
from app.main import app


client = TestClient(app)


def _auth_headers(role: str = "operations_analyst") -> dict[str, str]:
    token = create_demo_token(role=role)  # type: ignore[arg-type]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_is_versioned() -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "agentic-analytics-copilot"


def test_ask_requires_bearer_token() -> None:
    response = client.post("/v1/ask", json={"question": "Why did Region 3 drop?"})

    assert response.status_code == 401


def test_ask_accepts_valid_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.ask.run_question_workflow",
        lambda question, role: type(
            "Response",
            (),
                {
                    "request_id": "req_test",
                    "latency_ms": 42,
                    "cache_status": "miss",
                    "role": role,
                    "answer": f"handled {question}",
                "confidence": "high",
                "confidence_breakdown": ["Structured evidence available."],
                "needs_analyst_review": False,
                "analyst_review_reason": None,
                "likely_causes": [],
                "recommended_next_steps": [],
                "suggested_follow_up_questions": ["What incident details support this drop?"],
                "citations": [],
                "trace": [],
                "evidence_summary": "",
                "blocked_sources": [],
                "data_as_of": None,
                "freshness_status": "fresh",
                "completeness_status": "complete",
            },
        )(),
    )

    response = client.post(
        "/v1/ask",
        json={"question": "Why did Region 3 drop?"},
        headers=_auth_headers("exec_viewer"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "exec_viewer"
    assert body["request_id"] == "req_test"


def test_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setitem(app.state.__dict__, "_rate_buckets", {})
    monkeypatch.setattr(
        "app.api.v1.routes.ask.run_question_workflow",
        lambda question, role: type(
            "Response",
            (),
                {
                    "request_id": "req_ok",
                    "latency_ms": 1,
                    "cache_status": "miss",
                    "role": role,
                    "answer": "ok",
                "confidence": "high",
                "confidence_breakdown": [],
                "needs_analyst_review": False,
                "analyst_review_reason": None,
                "likely_causes": [],
                "recommended_next_steps": [],
                "suggested_follow_up_questions": [],
                "citations": [],
                "trace": [],
                "evidence_summary": "",
                "blocked_sources": [],
                "data_as_of": None,
                "freshness_status": "fresh",
                "completeness_status": "complete",
            },
        )(),
    )

    headers = _auth_headers("operations_analyst")
    for _ in range(10):
        response = client.post(
            "/v1/ask",
            json={"question": "Why did Region 3 drop?"},
            headers=headers,
        )
        assert response.status_code == 200

    blocked = client.post(
        "/v1/ask",
        json={"question": "Why did Region 3 drop?"},
        headers=headers,
    )

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_debug_metrics_endpoint_returns_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.debug.get_metrics_summary",
        lambda limit=20: {
            "summary": {"requests": 3, "avg_latency_ms": 120.0},
            "recent_requests": [{"request_id": "req_1"}],
        },
    )

    response = client.get("/v1/debug/metrics", headers=_auth_headers("regional_manager"))

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "regional_manager"
    assert body["summary"]["requests"] == 3


def test_metrics_dashboard_endpoint_returns_role_scoped_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.metrics.get_dashboard_for_role",
        lambda role: {
            "role": role,
            "role_label": "Regional manager view",
            "assigned_region": "Region 3",
            "alerts": [{"level": "red", "title": "Threshold breached"}],
            "sections": [{"title": "My region performance (Region 3)", "metrics": []}],
            "restricted": ["Raw shipment logs are not visible to this role."],
        },
    )

    response = client.get(
        "/v1/metrics/dashboard",
        headers=_auth_headers("regional_manager"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "regional_manager"
    assert body["assigned_region"] == "Region 3"
    assert body["alerts"][0]["level"] == "red"


def test_history_endpoint_returns_recent_investigations(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.history.get_investigation_history",
        lambda limit=25: {
            "count": 1,
            "items": [
                {
                    "request_id": "req_hist_1",
                    "created_at": "2026-04-05T00:00:00+00:00",
                    "role": "operations_analyst",
                    "question": "Why did Region 3 drop?",
                    "answer": "Carrier capacity shortage caused the drop.",
                    "confidence": "high",
                    "needs_analyst_review": False,
                    "analyst_review_reason": None,
                    "cache_status": "miss",
                    "freshness_status": "fresh",
                    "completeness_status": "complete",
                    "blocked_sources_count": 0,
                    "citations_count": 2,
                }
            ],
        },
    )

    response = client.get("/v1/history", headers=_auth_headers("operations_analyst"))

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "operations_analyst"
    assert body["count"] == 1
    assert body["items"][0]["request_id"] == "req_hist_1"


def test_stream_endpoint_returns_sse(monkeypatch) -> None:
    monkeypatch.setitem(app.state.__dict__, "_rate_buckets", {})

    async def fake_run_question_workflow_async(question: str, role: str):
        return type(
            "Response",
            (),
            {
                "request_id": "req_stream",
                "latency_ms": 12,
                "cache_status": "miss",
                "role": role,
                "answer": f"streamed {question}",
                "confidence": "medium",
                "confidence_breakdown": ["Testing stream path."],
                "needs_analyst_review": False,
                "analyst_review_reason": None,
                "likely_causes": [],
                "recommended_next_steps": [],
                "suggested_follow_up_questions": ["What runbook applies here?"],
                "citations": [],
                "trace": [],
                "evidence_summary": "",
                "blocked_sources": [],
                "data_as_of": None,
                "freshness_status": "unknown",
                "completeness_status": "unknown",
                "model_dump": lambda self=None: {
                    "request_id": "req_stream",
                    "latency_ms": 12,
                    "cache_status": "miss",
                    "role": role,
                    "answer": f"streamed {question}",
                    "confidence": "medium",
                    "confidence_breakdown": ["Testing stream path."],
                    "needs_analyst_review": False,
                    "analyst_review_reason": None,
                    "likely_causes": [],
                    "recommended_next_steps": [],
                    "suggested_follow_up_questions": ["What runbook applies here?"],
                    "citations": [],
                    "trace": [],
                    "evidence_summary": "",
                    "blocked_sources": [],
                    "data_as_of": None,
                    "freshness_status": "unknown",
                    "completeness_status": "unknown",
                },
            },
        )()

    monkeypatch.setattr(
        "app.api.v1.routes.ask.run_question_workflow_async",
        fake_run_question_workflow_async,
    )

    response = client.post(
        "/v1/ask/stream",
        json={"question": "Why did Region 3 drop?"},
        headers=_auth_headers("operations_analyst"),
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "event: status" in body
    assert "event: answer_chunk" in body
    assert "event: complete" in body
