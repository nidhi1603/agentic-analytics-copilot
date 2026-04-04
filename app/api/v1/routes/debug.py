from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.observability import get_metrics_summary
from app.orchestration.graph import run_investigation_workflow


router = APIRouter(tags=["debug"])


@router.get("/debug/trace")
def debug_trace(
    question: str = Query(..., min_length=5),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    state = run_investigation_workflow(question, current_user.role)
    synthesized = state.get("synthesized_answer")

    return {
        "question": question,
        "role": current_user.role,
        "route": state.get("route"),
        "trace": state.get("trace", []),
        "evidence_summary": state.get("evidence_summary", ""),
        "confidence": synthesized.confidence if synthesized else None,
        "needs_analyst_review": (
            synthesized.needs_analyst_review if synthesized else True
        ),
        "blocked_sources": state.get("blocked_sources", []),
    }


@router.get("/debug/metrics")
def debug_metrics(
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    return {
        "role": current_user.role,
        **get_metrics_summary(limit=limit),
    }
