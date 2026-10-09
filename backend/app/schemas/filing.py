from pydantic import BaseModel, ConfigDict


class FilingGuidanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    likely_forms: list[str]
    guidance: str
    schedules_to_review: list[str]
    documents_to_prepare: list[str]
    prefilled_summary: dict[str, object] | None
    official_source: str
    disclaimer: str
