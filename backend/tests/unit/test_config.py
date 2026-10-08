import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_blank_optional_environment_values_are_treated_as_unconfigured() -> None:
    settings = Settings(
        supabase_url="",
        supabase_anon_key="",
        supabase_jwt_secret="",
        tax_rules_file="",
    )

    assert settings.supabase_url is None
    assert settings.supabase_anon_key is None
    assert settings.supabase_jwt_secret is None
    assert settings.tax_rules_file is None


def test_legacy_hmac_secret_must_have_sufficient_entropy_length() -> None:
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(supabase_jwt_secret=SecretStr("too-short"))
