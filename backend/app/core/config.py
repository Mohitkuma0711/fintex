from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinTax AI API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://fintax:fintax@localhost:5432/fintax"
    firebase_project_id: str | None = None
    firebase_service_account_path: str | None = None
    firebase_api_key: str | None = None
    firebase_auth_domain: str | None = None
    firebase_storage_bucket: str | None = None
    firebase_app_id: str | None = None
    firebase_message_sender_id: str | None = None
    firebase_measurement_id: str | None = None
    storage_signed_url_ttl_seconds: int = 300
    max_upload_size_bytes: int = 10 * 1024 * 1024
    storage_backend: str = "firebase"
    local_storage_dir: Path = Path(".local_storage")
    public_base_url: str = "http://localhost:8000"
    google_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    firebase_test_mode: bool = False
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = 45
    gemini_max_attempts: int = 3
    extraction_max_pdf_pages: int = 50
    validation_low_confidence_threshold: Decimal = Decimal("0.8")
    knowledge_base_dir: Path = Path("app/knowledge_base/official")
    rag_index_dir: Path = Path("app/knowledge_base/.index")
    gemini_embedding_model: str = "gemini-embedding-001"
    rag_top_k: int = 5
    rag_similarity_threshold: Decimal = Decimal("0.45")
    chat_max_tool_calls: int = 6
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    tax_rules_file: Path | None = None
    log_level: str = "INFO"
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator(
        "firebase_api_key",
        "firebase_service_account_path",
        "firebase_auth_domain",
        "firebase_storage_bucket",
        "firebase_app_id",
        "firebase_message_sender_id",
        "firebase_measurement_id",
        "google_api_key",
        "gemini_api_key",
        "tax_rules_file",
        mode="before",
    )
    @classmethod
    def blank_auth_values_are_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("firebase_api_key")
    @classmethod
    def require_valid_firebase_api_key(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 10:
            raise ValueError("Firebase API key must be at least 10 characters.")
        return value

    @field_validator("storage_signed_url_ttl_seconds")
    @classmethod
    def validate_signed_url_ttl(cls, value: int) -> int:
        if not 60 <= value <= 900:
            raise ValueError("Signed URL lifetime must be between 60 and 900 seconds.")
        return value

    @field_validator("max_upload_size_bytes")
    @classmethod
    def validate_upload_limit(cls, value: int) -> int:
        if not 1 <= value <= 50 * 1024 * 1024:
            raise ValueError("Upload size limit must be between 1 byte and 50 MiB.")
        return value

    @field_validator("storage_backend")
    @classmethod
    def validate_storage_backend(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"firebase", "local"}:
            raise ValueError("Storage backend must be 'firebase' or 'local'.")
        return normalized

    @field_validator("public_base_url")
    @classmethod
    def validate_public_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("Public base URL must start with http:// or https://.")
        return normalized

    @field_validator("gemini_timeout_seconds", "gemini_max_attempts", "extraction_max_pdf_pages")
    @classmethod
    def validate_extraction_limits(cls, value: int, info) -> int:
        if value < 1:
            raise ValueError(f"{info.field_name} must be at least 1.")
        return value

    @field_validator("validation_low_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, value: Decimal) -> Decimal:
        if not Decimal("0") <= value <= Decimal("1"):
            raise ValueError("Validation confidence threshold must be between 0 and 1.")
        return value

    @field_validator("rag_top_k", "chat_max_tool_calls")
    @classmethod
    def validate_chat_limits(cls, value: int, info) -> int:
        if value < 1:
            raise ValueError(f"{info.field_name} must be at least 1.")
        return value

    @field_validator("rag_similarity_threshold")
    @classmethod
    def validate_similarity_threshold(cls, value: Decimal) -> Decimal:
        if not Decimal("-1") <= value <= Decimal("1"):
            raise ValueError("RAG similarity threshold must be between -1 and 1.")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, value: list[str], info) -> list[str]:
        if not value or any(origin == "*" for origin in value):
            raise ValueError("CORS origins must be an explicit, non-empty allowlist.")
        app_env = str(info.data.get("app_env", "development")).lower()
        if app_env in {"production", "prod"} and any(
            not origin.startswith("https://") for origin in value
        ):
            raise ValueError("Production CORS origins must use HTTPS.")
        return value

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
