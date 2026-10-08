import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.extraction.errors import ExtractionError

logger = structlog.get_logger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ExtractionError)
    async def extraction_error(request: Request, error: ExtractionError) -> JSONResponse:
        status_code = 503 if error.code.value != "unsupported_document" else 415
        return JSONResponse(
            status_code=status_code,
            content={
                "detail": str(error),
                "code": error.code.value,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        detail = error.detail if isinstance(error.detail, str) else "Request failed."
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": detail, "request_id": _request_id(request)},
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(item["loc"]), "type": item["type"], "msg": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": details, "request_id": _request_id(request)},
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_error(request: Request, error: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded.", "request_id": _request_id(request)},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _error: Exception) -> JSONResponse:
        logger.error("unhandled_request_error", error_type=type(_error).__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred.", "request_id": _request_id(request)},
        )
