from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path

from openai import OpenAI

from app.core.config import get_settings
from app.schemas.ask import AskResponse


def get_cache_connection() -> sqlite3.Connection:
    settings = get_settings()
    cache_path = Path(settings.semantic_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(cache_path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS semantic_cache (
            cache_key TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            question TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    return connection


def embed_query_text(question: str) -> list[float]:
    settings = get_settings()
    if settings.openai_api_key:
        try:
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(
                model=settings.openai_embedding_model,
                input=question,
            )
            return list(response.data[0].embedding)
        except Exception:
            return fallback_embedding(question)

    return fallback_embedding(question)


def fallback_embedding(question: str, dims: int = 128) -> list[float]:
    vector = [0.0] * dims
    for token in question.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = digest[0] % dims
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[bucket] += sign
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def load_cached_response(question: str, role: str) -> AskResponse | None:
    settings = get_settings()
    query_embedding = embed_query_text(question)
    connection = get_cache_connection()
    try:
        rows = connection.execute(
            """
            SELECT embedding_json, response_json
            FROM semantic_cache
            WHERE role = ?
            ORDER BY created_at DESC
            LIMIT 25
            """,
            (role,),
        ).fetchall()
    finally:
        connection.close()

    for embedding_json, response_json in rows:
        cached_embedding = json.loads(embedding_json)
        similarity = cosine_similarity(query_embedding, cached_embedding)
        if similarity >= settings.semantic_cache_similarity_threshold:
            cached = AskResponse.model_validate_json(response_json)
            return cached.model_copy(update={"cache_status": "hit"})

    return None


def save_cached_response(question: str, role: str, response: AskResponse) -> None:
    cache_key = hashlib.sha256(f"{role}:{question}".encode("utf-8")).hexdigest()
    embedding = embed_query_text(question)
    connection = get_cache_connection()
    try:
        connection.execute(
            """
            INSERT OR REPLACE INTO semantic_cache(cache_key, role, question, embedding_json, response_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                role,
                question,
                json.dumps(embedding),
                response.model_dump_json(),
            ),
        )
        connection.commit()
    finally:
        connection.close()
