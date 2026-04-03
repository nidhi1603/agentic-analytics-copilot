from fastapi import APIRouter

from app.core.config import get_settings
from app.db.duckdb_client import get_duckdb_path
from app.schemas.health import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.app_env,
        database_path=str(get_duckdb_path()),
    )

