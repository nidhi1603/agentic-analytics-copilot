from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings

try:
    from sentence_transformers import CrossEncoder
except Exception:  # pragma: no cover - optional runtime dependency during local install
    CrossEncoder = None  # type: ignore[assignment]


@lru_cache
def get_reranker() -> Any | None:
    if CrossEncoder is None:
        return None

    settings = get_settings()
    return CrossEncoder(settings.reranker_model_name)


def rerank_results(query_text: str, results: list[dict], limit: int = 5) -> list[dict]:
    reranker = get_reranker()
    if reranker is None or not results:
        return results[:limit]

    pairs = [(query_text, item["content"]) for item in results]
    scores = reranker.predict(pairs)

    rescored: list[dict] = []
    for item, score in zip(results, scores):
        rescored.append({**item, "rerank_score": float(score)})

    rescored.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
    return rescored[:limit]
