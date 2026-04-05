from types import SimpleNamespace

from app.llm.client import synthesize_answer_with_metadata


def test_synthesize_answer_with_metadata_falls_back_when_llm_call_fails(monkeypatch) -> None:
    class FailingCompletions:
        @staticmethod
        def create(**_kwargs):
            raise RuntimeError("network down")

    class FailingChat:
        completions = FailingCompletions()

    class FailingClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.chat = FailingChat()

    monkeypatch.setattr(
        "app.llm.client.get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openai_chat_model="gpt-4o-mini",
        ),
    )
    monkeypatch.setattr("app.llm.client.OpenAI", FailingClient)
    monkeypatch.setattr("app.llm.client.build_investigation_prompt", lambda state: "prompt")

    synthesized, observability = synthesize_answer_with_metadata(
        {
            "anomaly_report": [
                SimpleNamespace(
                    metric_name="delivery_success_rate",
                    region="Region 3",
                    metric_date="2026-03-31",
                    metric_value=62.0,
                    metric_target=70.0,
                    freshness_status="fresh",
                    completeness_pct=1.0,
                    data_as_of="2026-03-31T00:00:00Z",
                )
            ],
            "documents": [],
            "incidents": [],
            "failure_breakdown": [],
        }
    )

    assert synthesized.confidence == "medium"
    assert synthesized.needs_analyst_review is True
    assert observability["provider"] == "fallback"
    assert observability["fallback_reason"] == "llm_error:RuntimeError"
