from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions.openai_embedding_function import (
    OpenAIEmbeddingFunction,
)

try:
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional until dependencies are installed
    BM25Okapi = None  # type: ignore[assignment]

from app.core.config import get_settings
from app.retrieval.models import DocumentChunk
from app.retrieval.reranker import rerank_results


class SimpleBM25Fallback:
    def __init__(self, corpus: list[list[str]]) -> None:
        self.corpus = corpus

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        query_terms = set(query_tokens)
        scores: list[float] = []
        for doc_tokens in self.corpus:
            doc_terms = set(doc_tokens)
            overlap = len(query_terms & doc_terms)
            scores.append(float(overlap))
        return scores


def get_chroma_client() -> chromadb.PersistentClient:
    chroma_path = Path(get_settings().chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_path))


def get_collection() -> Collection:
    settings = get_settings()
    client = get_chroma_client()
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    embedding_function = OpenAIEmbeddingFunction(
        api_key_env_var="OPENAI_API_KEY",
        model_name=settings.openai_embedding_model,
    )

    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        embedding_function=embedding_function,
    )


def index_chunks(chunks: list[DocumentChunk]) -> int:
    collection = get_collection()
    if not chunks:
        return 0

    collection.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.content for chunk in chunks],
        metadatas=[
            {
                "source_path": chunk.source_path,
                "title": chunk.title,
                "doc_group": chunk.doc_group,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ],
    )
    get_bm25_index.cache_clear()
    return len(chunks)


@lru_cache
def get_bm25_index() -> tuple[object | None, list[dict]]:
    collection = get_collection()
    dataset = collection.get(include=["documents", "metadatas"])
    documents = dataset.get("documents", [])
    metadatas = dataset.get("metadatas", [])
    ids = dataset.get("ids", [])

    corpus: list[dict] = []
    tokenized_documents: list[list[str]] = []
    for doc_id, document, metadata in zip(ids, documents, metadatas):
        if not document or not metadata:
            continue
        tokenized = tokenize_text(document)
        corpus.append(
            {
                "id": doc_id,
                "content": document,
                "metadata": metadata,
            }
        )
        tokenized_documents.append(tokenized)

    if not corpus:
        return None, []

    if BM25Okapi is None:
        return SimpleBM25Fallback(tokenized_documents), corpus

    return BM25Okapi(tokenized_documents), corpus


def tokenize_text(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9_]+", text.lower()) if token]


def reciprocal_rank_fusion(*rankings: list[str], k: int) -> dict[str, float]:
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (k + rank)
    return fused


def query_chunks(query_text: str, limit: int = 5) -> list[dict]:
    settings = get_settings()
    collection = get_collection()
    vector_results = collection.query(
        query_texts=[query_text],
        n_results=max(limit, settings.hybrid_search_vector_candidates),
    )

    vector_documents = vector_results.get("documents", [[]])[0]
    vector_metadatas = vector_results.get("metadatas", [[]])[0]
    vector_distances = vector_results.get("distances", [[]])[0]
    vector_ids = vector_results.get("ids", [[]])[0]

    vector_lookup: dict[str, dict] = {}
    vector_ranking: list[str] = []
    for rank, (doc_id, document, metadata, distance) in enumerate(
        zip(vector_ids, vector_documents, vector_metadatas, vector_distances),
        start=1,
    ):
        vector_ranking.append(doc_id)
        vector_lookup[doc_id] = {
            "id": doc_id,
            "content": document,
            "metadata": metadata,
            "distance": distance,
            "vector_rank": rank,
        }

    bm25, corpus = get_bm25_index()
    keyword_lookup: dict[str, dict] = {}
    keyword_ranking: list[str] = []
    if bm25 is not None and corpus:
        tokenized_query = tokenize_text(query_text)
        scores = bm25.get_scores(tokenized_query)
        ranked = sorted(
            zip(corpus, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )[: settings.hybrid_search_keyword_candidates]
        for rank, (item, score) in enumerate(ranked, start=1):
            keyword_ranking.append(item["id"])
            keyword_lookup[item["id"]] = {
                "id": item["id"],
                "content": item["content"],
                "metadata": item["metadata"],
                "keyword_rank": rank,
                "keyword_score": float(score),
            }

    fused_scores = reciprocal_rank_fusion(
        vector_ranking,
        keyword_ranking,
        k=settings.hybrid_search_rrf_k,
    )

    combined_ids = list(fused_scores.keys())
    hybrid_results: list[dict] = []
    for item_id in combined_ids:
        vector_item = vector_lookup.get(item_id, {})
        keyword_item = keyword_lookup.get(item_id, {})
        base_item = vector_item or keyword_item
        hybrid_results.append(
            {
                "id": item_id,
                "content": base_item["content"],
                "metadata": base_item["metadata"],
                "distance": vector_item.get("distance"),
                "vector_rank": vector_item.get("vector_rank"),
                "keyword_rank": keyword_item.get("keyword_rank"),
                "hybrid_score": fused_scores[item_id],
            }
        )

    hybrid_results.sort(key=lambda item: item["hybrid_score"], reverse=True)
    reranked = rerank_results(
        query_text=query_text,
        results=hybrid_results[: max(limit, settings.retrieval_final_limit) * 4],
        limit=limit,
    )
    return reranked[:limit]
