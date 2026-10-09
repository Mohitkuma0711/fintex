from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import register_exception_handlers
from app.core.firebase import initialize_firebase
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    UploadSizeLimitMiddleware,
    UsageMetricsMiddleware,
)
from app.core.rate_limit import limiter

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


def _scrub_sentry_event(event: dict, _hint: dict) -> dict:
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("headers", None)
        request.pop("cookies", None)
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = url.split("?", maxsplit=1)[0]
    event.pop("user", None)
    return event


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        send_default_pii=False,
        traces_sample_rate=0,
        before_send=_scrub_sentry_event,
    )


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator[None, None]:
    if not settings.firebase_test_mode:
        try:
            initialize_firebase(settings)
        except Exception as error:
            logger.warning("firebase_initialization_failed", error_type=type(error).__name__)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "FinTax AI API. Tax results are produced only by the deterministic, "
        "versioned-rules engine and include calculation traces."
    ),
    contact={"name": "FinTax AI"},
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(UploadSizeLimitMiddleware, max_bytes=settings.max_upload_size_bytes)
app.add_middleware(UsageMetricsMiddleware)
app.add_middleware(
    SecurityHeadersMiddleware,
    production=settings.app_env.lower() in {"production", "prod"},
)
app.add_middleware(RequestIdMiddleware)
register_exception_handlers(app)
app.include_router(v1_router, prefix=settings.api_v1_prefix)
