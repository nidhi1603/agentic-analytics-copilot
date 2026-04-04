from time import perf_counter
from uuid import uuid4

from app.core.cache import load_cached_response, save_cached_response
from app.core.logging import get_logger
from app.orchestration.graph import run_investigation_workflow
from app.schemas.ask import AskResponse


logger = get_logger(__name__)


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
        return response
    try:
        state = run_investigation_workflow(question, role)
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
        return AskResponse(
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
