import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_blank_optional_environment_values_are_treated_as_unconfigured() -> None:
    settings = Settings(
        supabase_url="",
        supabase_anon_key="",
        supabase_jwt_secret="",
        supabase_service_role_key="",
        tax_rules_file="",
    )

    assert settings.supabase_url is None
    assert settings.supabase_anon_key is None
    assert settings.supabase_jwt_secret is None
    assert settings.supabase_service_role_key is None
    assert settings.tax_rules_file is None


def test_short_supabase_jwt_secret_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Settings(supabase_jwt_secret="too-short-secret")