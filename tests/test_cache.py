from pathlib import Path

from app.core.cache import cosine_similarity, load_cached_response, save_cached_response
from app.schemas.ask import AskResponse


def test_cosine_similarity_detects_identical_vectors() -> None:
    score = cosine_similarity([1.0, 0.0], [1.0, 0.0])

    assert score == 1.0


def test_semantic_cache_round_trip(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.core.cache.embed_query_text", lambda question: [1.0, 0.0, 0.0])
    monkeypatch.setattr(
        "app.core.cache.get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "semantic_cache_path": str(tmp_path / "semantic_cache.sqlite"),
                "semantic_cache_similarity_threshold": 0.95,
                "openai_api_key": None,
                "openai_embedding_model": "text-embedding-3-small",
            },
        )(),
    )

    response = AskResponse(
        request_id="req_a",
        latency_ms=12,
        cache_status="miss",
        role="operations_analyst",
        answer="cached answer",
        confidence="high",
        confidence_breakdown=["Structured evidence available."],
        needs_analyst_review=False,
        analyst_review_reason=None,
        likely_causes=[],
        recommended_next_steps=[],
        citations=[],
        trace=[],
        evidence_summary="",
        blocked_sources=[],
        data_as_of=None,
        freshness_status="fresh",
        completeness_status="complete",
    )

    save_cached_response("Why did Region 3 drop?", "operations_analyst", response)
    cached = load_cached_response("Why did Region 3 drop?", "operations_analyst")

    assert cached is not None
    assert cached.answer == "cached answer"
    assert cached.cache_status == "hit"
