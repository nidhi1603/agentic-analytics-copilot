from fastapi import APIRouter, Query

from app.orchestration.graph import run_investigation_workflow


router = APIRouter(tags=["debug"])


@router.get("/debug/trace")
def debug_trace(question: str = Query(..., min_length=5)) -> dict:
    state = run_investigation_workflow(question)
    synthesized = state.get("synthesized_answer")

    return {
        "question": question,
        "route": state.get("route"),
        "trace": state.get("trace", []),
        "evidence_summary": state.get("evidence_summary", ""),
        "confidence": synthesized.confidence if synthesized else None,
        "needs_analyst_review": (
            synthesized.needs_analyst_review if synthesized else True
        ),
    }

