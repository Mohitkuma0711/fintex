from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware, UploadSizeLimitMiddleware
from app.core.rate_limit import limiter

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator[None, None]:
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
app.add_middleware(RequestIdMiddleware)
register_exception_handlers(app)
app.include_router(v1_router, prefix=settings.api_v1_prefix)
