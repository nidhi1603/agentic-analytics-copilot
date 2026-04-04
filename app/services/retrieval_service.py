from app.services.policy_service import is_resource_allowed
from app.retrieval.vector_store import query_chunks
from app.schemas.tools import RetrievedDocument


def retrieve_documents(
    query_text: str,
    role: str,
    limit: int = 4,
) -> tuple[list[RetrievedDocument], list[str], list[str]]:
    results = query_chunks(query_text=query_text, limit=limit)

    documents: list[RetrievedDocument] = []
    blocked_sources: list[str] = []
    allowed_sources: list[str] = []

    for item in results:
        doc_group = item["metadata"]["doc_group"]
        allowed, reason = is_resource_allowed(
            role=role,
            resource_type="document",
            resource_name=doc_group,
        )
        source_label = f"document:{doc_group}"
        if not allowed:
            blocked_sources.append(f"{source_label} ({reason})")
            continue

        allowed_sources.append(source_label)
        documents.append(
            RetrievedDocument(
                content=item["content"],
                source_path=item["metadata"]["source_path"],
                title=item["metadata"]["title"],
                doc_group=doc_group,
                distance=item.get("distance"),
                vector_rank=item.get("vector_rank"),
                keyword_rank=item.get("keyword_rank"),
                rerank_score=item.get("rerank_score"),
                hybrid_score=item.get("hybrid_score"),
            )
        )

    return documents, blocked_sources, allowed_sources
