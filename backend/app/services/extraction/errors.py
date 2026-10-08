from enum import StrEnum


class ExtractionErrorCode(StrEnum):
    NOT_CONFIGURED = "extraction_not_configured"
    TIMEOUT = "extraction_timeout"
    RATE_LIMITED = "extraction_rate_limited"
    PROVIDER_UNAVAILABLE = "extraction_provider_unavailable"
    INVALID_RESPONSE = "extraction_invalid_response"
    UNSUPPORTED_DOCUMENT = "unsupported_document"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    VIRUS_DETECTED = "virus_detected"
    INTERNAL_ERROR = "extraction_failed"


class ExtractionError(Exception):
    def __init__(self, code: ExtractionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
