from app.retrieval.vector_store import query_chunks
from app.schemas.tools import RetrievedDocument


def retrieve_documents(query_text: str, limit: int = 4) -> list[RetrievedDocument]:
    results = query_chunks(query_text=query_text, limit=limit)

    return [
        RetrievedDocument(
            content=item["content"],
            source_path=item["metadata"]["source_path"],
            title=item["metadata"]["title"],
            doc_group=item["metadata"]["doc_group"],
            distance=item.get("distance"),
        )
        for item in results
    ]

