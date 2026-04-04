from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.routes.ask import router as ask_router
from app.api.v1.routes.debug import router as debug_router
from app.api.v1.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.observability import initialize_observability_store
from app.db.bootstrap import initialize_database


settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    initialize_database()
    initialize_observability_store()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for an agentic analytics copilot",
    lifespan=lifespan,
)


@app.middleware("http")
async def apply_rate_limit(request, call_next):
    if request.url.path.startswith("/v1/ask") or request.url.path.startswith("/v1/debug"):
        forwarded_for = request.headers.get("x-forwarded-for")
        client_host = request.client.host if request.client else "unknown"
        key = request.headers.get("authorization") or forwarded_for or client_host
        bucket = getattr(app.state, "_rate_buckets", {})
        app.state._rate_buckets = bucket
        from time import time

        now = int(time())
        window = now // 60
        window_key = f"{key}:{window}"
        count = bucket.get(window_key, 0) + 1
        bucket[window_key] = count
        request.state.rate_limited = count > settings.rate_limit_per_minute
        if request.state.rate_limited:
            retry_after = 60 - (now % 60)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={"Retry-After": str(retry_after)},
            )

    return await call_next(request)


app.include_router(ask_router, prefix="/v1")
app.include_router(debug_router, prefix="/v1")
app.include_router(health_router, prefix="/v1")
