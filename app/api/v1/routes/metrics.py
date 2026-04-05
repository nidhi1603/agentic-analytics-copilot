from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.services.metrics_service import get_dashboard_for_role


router = APIRouter(tags=["metrics"])


@router.get("/metrics/dashboard")
def get_metrics_dashboard(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    return get_dashboard_for_role(current_user.role)
