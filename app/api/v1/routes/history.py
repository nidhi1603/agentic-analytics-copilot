from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.observability import get_investigation_history


router = APIRouter(tags=["history"])


@router.get("/history")
def history(
    limit: int = Query(25, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    return {
        "role": current_user.role,
        **get_investigation_history(limit=limit),
    }
