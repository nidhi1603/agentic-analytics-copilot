from app.core.logging import get_logger
from app.orchestration.graph import run_investigation_workflow
from app.schemas.ask import AskResponse


logger = get_logger(__name__)


def run_question_workflow(question: str) -> AskResponse:
    logger.info("workflow_started question=%s", question)
    try:
        state = run_investigation_workflow(question)
        synthesized = state["synthesized_answer"]
        response = AskResponse(
            answer=synthesized.answer,
            confidence=synthesized.confidence,
            needs_analyst_review=synthesized.needs_analyst_review,
            likely_causes=synthesized.likely_causes,
            recommended_next_steps=synthesized.recommended_next_steps,
            citations=state.get("citations", []),
            trace=state.get("trace", []),
            evidence_summary=state.get("evidence_summary", ""),
        )
        logger.info(
            "workflow_completed confidence=%s needs_review=%s trace_steps=%s",
            response.confidence,
            response.needs_analyst_review,
            len(response.trace),
        )
        return response
    except Exception as exc:
        logger.exception("workflow_failed error=%s", exc)
        return AskResponse(
            answer="The system could not complete the investigation safely.",
            confidence="low",
            needs_analyst_review=True,
            likely_causes=[],
            recommended_next_steps=[
                "Retry the request after checking service dependencies.",
                "Escalate to analyst review if the issue persists.",
            ],
            citations=[],
            trace=["workflow_failed"],
            evidence_summary="Workflow failed before a complete evidence package could be prepared.",
        )

