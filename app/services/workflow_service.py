import asyncio
from time import perf_counter
from uuid import uuid4

from app.core.cache import load_cached_response, save_cached_response
from app.core.logging import get_logger
from app.core.observability import record_investigation_history, record_request_metric
from app.orchestration.graph import run_investigation_workflow
from app.schemas.ask import AskResponse


logger = get_logger(__name__)


def _invoke_workflow(question: str, role: str, request_id: str):
    try:
        return run_investigation_workflow(question, role, request_id=request_id)
    except TypeError:
        return run_investigation_workflow(question, role)


def run_question_workflow(question: str, role: str) -> AskResponse:
    request_id = f"req_{uuid4().hex[:12]}"
    started_at = perf_counter()
    logger.info("workflow_started request_id=%s role=%s question=%s", request_id, role, question)
    cached_response = load_cached_response(question, role)
    if cached_response is not None:
        latency_ms = int((perf_counter() - started_at) * 1000)
        response = cached_response.model_copy(
            update={
                "request_id": request_id,
                "latency_ms": latency_ms,
                "cache_status": "hit",
            }
        )
        logger.info(
            "workflow_cache_hit request_id=%s role=%s latency_ms=%s",
            request_id,
            role,
            latency_ms,
        )
        record_request_metric(
            request_id=request_id,
            role=role,
            question=question,
            confidence=response.confidence,
            cache_status=response.cache_status,
            latency_ms=latency_ms,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=len(response.blocked_sources),
            trace_steps=len(response.trace),
            citations_count=len(response.citations),
            llm_observability={
                "provider": "semantic_cache",
                "model": "semantic_cache",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "llm_latency_ms": 0,
            },
        )
        record_investigation_history(
            request_id=request_id,
            role=role,
            question=question,
            answer=response.answer,
            confidence=response.confidence,
            needs_analyst_review=response.needs_analyst_review,
            analyst_review_reason=response.analyst_review_reason,
            cache_status=response.cache_status,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=len(response.blocked_sources),
            citations_count=len(response.citations),
        )
        return response
    try:
        state = _invoke_workflow(question, role, request_id)
        synthesized = state["synthesized_answer"]
        latency_ms = int((perf_counter() - started_at) * 1000)
        response = AskResponse(
            request_id=request_id,
            latency_ms=latency_ms,
            cache_status="miss",
            role=role,
            answer=synthesized.answer,
            confidence=synthesized.confidence,
            confidence_breakdown=synthesized.confidence_breakdown,
            needs_analyst_review=synthesized.needs_analyst_review,
            analyst_review_reason=synthesized.analyst_review_reason,
            likely_causes=synthesized.likely_causes,
            recommended_next_steps=synthesized.recommended_next_steps,
            citations=state.get("citations", []),
            trace=state.get("trace", []),
            evidence_summary=state.get("evidence_summary", ""),
            blocked_sources=state.get("blocked_sources", []),
            data_as_of=state.get("data_as_of"),
            freshness_status=state.get("freshness_status", "unknown"),
            completeness_status=state.get("completeness_status", "unknown"),
        )
        save_cached_response(question, role, response)
        record_request_metric(
            request_id=request_id,
            role=role,
            question=question,
            confidence=response.confidence,
            cache_status=response.cache_status,
            latency_ms=latency_ms,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=len(response.blocked_sources),
            trace_steps=len(response.trace),
            citations_count=len(response.citations),
            llm_observability=state.get("llm_observability"),
        )
        record_investigation_history(
            request_id=request_id,
            role=role,
            question=question,
            answer=response.answer,
            confidence=response.confidence,
            needs_analyst_review=response.needs_analyst_review,
            analyst_review_reason=response.analyst_review_reason,
            cache_status=response.cache_status,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=len(response.blocked_sources),
            citations_count=len(response.citations),
        )
        logger.info(
            "workflow_completed request_id=%s role=%s confidence=%s needs_review=%s trace_steps=%s blocked_sources=%s latency_ms=%s cache_status=%s",
            request_id,
            role,
            response.confidence,
            response.needs_analyst_review,
            len(response.trace),
            len(response.blocked_sources),
            latency_ms,
            response.cache_status,
        )
        return response
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        logger.exception("workflow_failed request_id=%s error=%s", request_id, exc)
        response = AskResponse(
            request_id=request_id,
            latency_ms=latency_ms,
            cache_status="miss",
            role=role,
            answer="The system could not complete the investigation safely.",
            confidence="low",
            confidence_breakdown=[
                "The workflow failed before a complete evidence package could be assembled.",
                "The system cannot support a confident automated answer without trusted evidence.",
            ],
            needs_analyst_review=True,
            analyst_review_reason="The workflow failed before it could assemble a trusted evidence package.",
            likely_causes=[],
            recommended_next_steps=[
                "Retry the request after checking service dependencies.",
                "Escalate to analyst review if the issue persists.",
            ],
            citations=[],
            trace=["workflow_failed"],
            evidence_summary="Workflow failed before a complete evidence package could be prepared.",
            blocked_sources=[],
            data_as_of=None,
            freshness_status="unknown",
            completeness_status="unknown",
        )
        record_request_metric(
            request_id=request_id,
            role=role,
            question=question,
            confidence=response.confidence,
            cache_status=response.cache_status,
            latency_ms=latency_ms,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=0,
            trace_steps=len(response.trace),
            citations_count=0,
            llm_observability={
                "provider": "workflow_failure",
                "model": "workflow_failure",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "llm_latency_ms": 0,
                "error": str(exc),
            },
        )
        record_investigation_history(
            request_id=request_id,
            role=role,
            question=question,
            answer=response.answer,
            confidence=response.confidence,
            needs_analyst_review=response.needs_analyst_review,
            analyst_review_reason=response.analyst_review_reason,
            cache_status=response.cache_status,
            freshness_status=response.freshness_status,
            completeness_status=response.completeness_status,
            blocked_sources_count=0,
            citations_count=0,
        )
        return response


async def run_question_workflow_async(question: str, role: str) -> AskResponse:
    return await asyncio.to_thread(run_question_workflow, question, role)
