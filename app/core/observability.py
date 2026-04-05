from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def _ensure_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def get_observability_connection() -> sqlite3.Connection:
    settings = get_settings()
    db_path = settings.observability_db_path
    _ensure_parent_dir(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_observability_store() -> None:
    with get_observability_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS request_metrics (
                request_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL,
                question TEXT NOT NULL,
                confidence TEXT NOT NULL,
                cache_status TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                llm_latency_ms INTEGER NOT NULL,
                freshness_status TEXT NOT NULL,
                completeness_status TEXT NOT NULL,
                blocked_sources_count INTEGER NOT NULL,
                trace_steps INTEGER NOT NULL,
                citations_count INTEGER NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost_usd REAL NOT NULL,
                llm_model TEXT NOT NULL,
                provider TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS investigation_history (
                request_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                confidence TEXT NOT NULL,
                needs_analyst_review INTEGER NOT NULL,
                analyst_review_reason TEXT,
                cache_status TEXT NOT NULL,
                freshness_status TEXT NOT NULL,
                completeness_status TEXT NOT NULL,
                blocked_sources_count INTEGER NOT NULL,
                citations_count INTEGER NOT NULL
            )
            """
        )


def estimate_openai_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    pricing_per_million = {
        "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    }
    pricing = pricing_per_million.get(model)
    if pricing is None:
        return 0.0

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def record_request_metric(
    *,
    request_id: str,
    role: str,
    question: str,
    confidence: str,
    cache_status: str,
    latency_ms: int,
    freshness_status: str,
    completeness_status: str,
    blocked_sources_count: int,
    trace_steps: int,
    citations_count: int,
    llm_observability: dict[str, Any] | None,
) -> None:
    initialize_observability_store()
    llm_meta = llm_observability or {}
    payload = {
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "question": question,
        "confidence": confidence,
        "cache_status": cache_status,
        "latency_ms": latency_ms,
        "llm_latency_ms": int(llm_meta.get("llm_latency_ms", 0)),
        "freshness_status": freshness_status,
        "completeness_status": completeness_status,
        "blocked_sources_count": blocked_sources_count,
        "trace_steps": trace_steps,
        "citations_count": citations_count,
        "prompt_tokens": int(llm_meta.get("prompt_tokens", 0)),
        "completion_tokens": int(llm_meta.get("completion_tokens", 0)),
        "total_tokens": int(llm_meta.get("total_tokens", 0)),
        "estimated_cost_usd": float(llm_meta.get("estimated_cost_usd", 0.0)),
        "llm_model": str(llm_meta.get("model", "fallback")),
        "provider": str(llm_meta.get("provider", "fallback")),
        "metadata_json": json.dumps(llm_meta, ensure_ascii=True),
    }
    with get_observability_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO request_metrics (
                request_id,
                created_at,
                role,
                question,
                confidence,
                cache_status,
                latency_ms,
                llm_latency_ms,
                freshness_status,
                completeness_status,
                blocked_sources_count,
                trace_steps,
                citations_count,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost_usd,
                llm_model,
                provider,
                metadata_json
            ) VALUES (
                :request_id,
                :created_at,
                :role,
                :question,
                :confidence,
                :cache_status,
                :latency_ms,
                :llm_latency_ms,
                :freshness_status,
                :completeness_status,
                :blocked_sources_count,
                :trace_steps,
                :citations_count,
                :prompt_tokens,
                :completion_tokens,
                :total_tokens,
                :estimated_cost_usd,
                :llm_model,
                :provider,
                :metadata_json
            )
            """,
            payload,
        )


def record_investigation_history(
    *,
    request_id: str,
    role: str,
    question: str,
    answer: str,
    confidence: str,
    needs_analyst_review: bool,
    analyst_review_reason: str | None,
    cache_status: str,
    freshness_status: str,
    completeness_status: str,
    blocked_sources_count: int,
    citations_count: int,
) -> None:
    initialize_observability_store()
    payload = {
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "needs_analyst_review": 1 if needs_analyst_review else 0,
        "analyst_review_reason": analyst_review_reason,
        "cache_status": cache_status,
        "freshness_status": freshness_status,
        "completeness_status": completeness_status,
        "blocked_sources_count": blocked_sources_count,
        "citations_count": citations_count,
    }
    with get_observability_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO investigation_history (
                request_id,
                created_at,
                role,
                question,
                answer,
                confidence,
                needs_analyst_review,
                analyst_review_reason,
                cache_status,
                freshness_status,
                completeness_status,
                blocked_sources_count,
                citations_count
            ) VALUES (
                :request_id,
                :created_at,
                :role,
                :question,
                :answer,
                :confidence,
                :needs_analyst_review,
                :analyst_review_reason,
                :cache_status,
                :freshness_status,
                :completeness_status,
                :blocked_sources_count,
                :citations_count
            )
            """,
            payload,
        )


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def get_metrics_summary(limit: int = 20) -> dict[str, Any]:
    with get_observability_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM request_metrics
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        all_rows = connection.execute(
            """
            SELECT *
            FROM request_metrics
            ORDER BY created_at DESC
            """
        ).fetchall()

    if not all_rows:
        return {
            "summary": {
                "requests": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "cache_hit_rate": 0.0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_cost_usd": 0.0,
            },
            "recent_requests": [],
        }

    latencies = [int(row["latency_ms"]) for row in all_rows]
    cache_hits = sum(1 for row in all_rows if row["cache_status"] == "hit")
    total_tokens = sum(int(row["total_tokens"]) for row in all_rows)
    total_cost = round(sum(float(row["estimated_cost_usd"]) for row in all_rows), 6)

    recent_requests = [
        {
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "role": row["role"],
            "question": row["question"],
            "confidence": row["confidence"],
            "cache_status": row["cache_status"],
            "latency_ms": int(row["latency_ms"]),
            "llm_latency_ms": int(row["llm_latency_ms"]),
            "total_tokens": int(row["total_tokens"]),
            "estimated_cost_usd": round(float(row["estimated_cost_usd"]), 6),
            "freshness_status": row["freshness_status"],
            "completeness_status": row["completeness_status"],
            "blocked_sources_count": int(row["blocked_sources_count"]),
            "trace_steps": int(row["trace_steps"]),
            "citations_count": int(row["citations_count"]),
            "llm_model": row["llm_model"],
            "provider": row["provider"],
        }
        for row in rows
    ]

    return {
        "summary": {
            "requests": len(all_rows),
            "avg_latency_ms": round(mean(latencies), 1),
            "p50_latency_ms": _percentile(latencies, 0.5),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "cache_hit_rate": round(cache_hits / len(all_rows), 2),
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_cost_usd": round(total_cost / len(all_rows), 6),
        },
        "recent_requests": recent_requests,
    }


def get_investigation_history(limit: int = 25) -> dict[str, Any]:
    with get_observability_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM investigation_history
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "count": len(rows),
        "items": [
            {
                "request_id": row["request_id"],
                "created_at": row["created_at"],
                "role": row["role"],
                "question": row["question"],
                "answer": row["answer"],
                "confidence": row["confidence"],
                "needs_analyst_review": bool(row["needs_analyst_review"]),
                "analyst_review_reason": row["analyst_review_reason"],
                "cache_status": row["cache_status"],
                "freshness_status": row["freshness_status"],
                "completeness_status": row["completeness_status"],
                "blocked_sources_count": int(row["blocked_sources_count"]),
                "citations_count": int(row["citations_count"]),
            }
            for row in rows
        ],
    }


_langfuse_client = None
_langfuse_init_attempted = False


def get_langfuse_client():
    global _langfuse_client, _langfuse_init_attempted
    if _langfuse_client is not None or _langfuse_init_attempted:
        return _langfuse_client

    _langfuse_init_attempted = True
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:
        logger.warning("langfuse_unavailable error=%s", exc)
        _langfuse_client = None
    return _langfuse_client


def log_langfuse_generation(
    *,
    request_id: str | None,
    role: str | None,
    question: str | None,
    prompt: str,
    model: str,
    usage: dict[str, Any],
    output: str,
) -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        trace = client.trace(
            id=request_id,
            name="agentic_analytics_request",
            user_id=role or "unknown",
            input=question,
            metadata={
                "request_id": request_id,
                "role": role,
            },
        )
        trace.generation(
            name="answer_synthesis",
            model=model,
            input=prompt,
            output=output,
            usage={
                "input": int(usage.get("prompt_tokens", 0)),
                "output": int(usage.get("completion_tokens", 0)),
                "total": int(usage.get("total_tokens", 0)),
            },
            metadata=usage,
        )
        client.flush()
    except Exception as exc:
        logger.warning("langfuse_logging_failed request_id=%s error=%s", request_id, exc)
