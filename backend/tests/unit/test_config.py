import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_blank_optional_environment_values_are_treated_as_unconfigured() -> None:
    settings = Settings(
        firebase_api_key="",
        firebase_auth_domain="",
        firebase_storage_bucket="",
        tax_rules_file="",
    )

    assert settings.firebase_api_key is None
    assert settings.firebase_auth_domain is None
    assert settings.firebase_storage_bucket is None
    assert settings.tax_rules_file is None


def test_missing_firebase_api_key_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Settings(firebase_api_key="short")