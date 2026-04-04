from app.services.retrieval_service import retrieve_documents
from app.retrieval.vector_store import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_rewards_documents_present_in_multiple_rankings() -> None:
    fused = reciprocal_rank_fusion(
        ["doc_a", "doc_b", "doc_c"],
        ["doc_b", "doc_a", "doc_d"],
        k=60,
    )

    assert fused["doc_b"] > fused["doc_c"]
    assert fused["doc_a"] > fused["doc_d"]


def test_retrieve_documents_maps_hybrid_and_rerank_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.retrieval_service.query_chunks",
        lambda query_text, limit: [
            {
                "content": "Escalation policy chunk",
                "metadata": {
                    "source_path": "data/docs/policies/escalation_policy.md",
                    "title": "Escalation policy",
                    "doc_group": "policies",
                },
                "distance": 0.12,
                "vector_rank": 2,
                "keyword_rank": 1,
                "rerank_score": 0.91,
                "hybrid_score": 0.032,
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.retrieval_service.is_resource_allowed",
        lambda role, resource_type, resource_name: (True, None),
    )

    documents, blocked_sources, allowed_sources = retrieve_documents(
        query_text="What does escalation policy say?",
        role="exec_viewer",
        limit=4,
    )

    assert blocked_sources == []
    assert allowed_sources == ["document:policies"]
    assert documents[0].vector_rank == 2
    assert documents[0].keyword_rank == 1
    assert documents[0].rerank_score == 0.91
