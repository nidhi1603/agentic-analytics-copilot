from contextlib import asynccontextmanager

from app.api.routes.ask import router as ask_router
from app.api.routes.debug import router as debug_router
from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.bootstrap import initialize_database


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for an agentic analytics copilot",
    lifespan=lifespan,
)

app.include_router(ask_router)
app.include_router(debug_router)
app.include_router(health_router)
