from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.middleware import usage_snapshot
from app.models import User
from app.schemas.health import HealthResponse, UsageMetricsResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="fintax-ai")


@router.get("/metrics/usage", response_model=UsageMetricsResponse)
async def usage_metrics(
    _user: User = Depends(get_current_user),
) -> UsageMetricsResponse:
    return UsageMetricsResponse(process_scope="single-process", request_counts=usage_snapshot())
