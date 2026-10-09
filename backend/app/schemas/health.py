from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    service: str


class UsageMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_scope: str
    request_counts: dict[str, int]
