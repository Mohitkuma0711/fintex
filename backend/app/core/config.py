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
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_jwt_secret: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_storage_bucket: str = "fintax-private"
    storage_signed_url_ttl_seconds: int = 900
    max_upload_size_bytes: int = 10 * 1024 * 1024
    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = 45
    gemini_max_attempts: int = 3
    extraction_max_pdf_pages: int = 50
    validation_low_confidence_threshold: Decimal = Decimal("0.8")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    tax_rules_file: Path | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator(
        "supabase_url",
        "supabase_anon_key",
        "supabase_jwt_secret",
        "supabase_service_role_key",
        "google_api_key",
        "tax_rules_file",
        mode="before",
    )
    @classmethod
    def blank_auth_values_are_unset(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("supabase_jwt_secret")
    @classmethod
    def require_strong_legacy_jwt_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError("SUPABASE_JWT_SECRET must be at least 32 characters.")
        return value

    @field_validator("storage_signed_url_ttl_seconds")
    @classmethod
    def validate_signed_url_ttl(cls, value: int) -> int:
        if not 60 <= value <= 3600:
            raise ValueError("Signed URL lifetime must be between 60 and 3600 seconds.")
        return value

    @field_validator("supabase_storage_bucket")
    @classmethod
    def validate_storage_bucket_name(cls, value: str) -> str:
        if not value or "/" in value or value.strip() != value:
            raise ValueError("SUPABASE_STORAGE_BUCKET must be a non-empty bucket name.")
        return value

    @field_validator("max_upload_size_bytes")
    @classmethod
    def validate_upload_limit(cls, value: int) -> int:
        if not 1 <= value <= 50 * 1024 * 1024:
            raise ValueError("Upload size limit must be between 1 byte and 50 MiB.")
        return value

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
