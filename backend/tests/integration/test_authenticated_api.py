import json
import struct
import zlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.dependencies import (
    get_extraction_job,
    get_privacy_service,
    get_storage,
    require_configured_rules,
)
from app.core import auth as auth_module
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.main import app
from app.models import (
    Base,
    ChatMessage,
    ChatSession,
    Document,
    ExtractionResult,
    TaxComputation,
    User,
)
from app.schemas.tax import TaxComparisonResult, TaxpayerProfile
from app.services.chat.service import ChatService
from app.services.extraction.gemini import GeminiExtractor
from app.services.extraction.jobs import ExtractionJob
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.privacy import PrivacyService
from app.services.tax_engine.rules import RulesetVersion
from tests.unit.tax_engine_fixtures import build_test_rules

TEST_JWT_SECRET = "test-only-secret-key-that-is-never-used-outside-tests"
FIREBASE_PROJECT_ID = "fintax-cbad3"
FIXTURE_DIRECTORY = Path(__file__).parents[1] / "fixtures" / "documents"
FORM16_FIXTURE = json.loads(
    (FIXTURE_DIRECTORY / "synthetic_form16_extraction.json").read_text(encoding="utf-8")
)


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_paths: list[str] = []

    async def upload(self, object_path: str, content: bytes, mime_type: str) -> None:
        self.objects[object_path] = content
        self.upload_paths.append(object_path)

    async def create_signed_url(self, object_path: str) -> str:
        return f"https://firebasestorage.googleapis.com/v0/b/fintax-cbad3.appspot.com/o"

    async def download(self, object_path: str) -> bytes:
        return self.objects[object_path]

    async def delete(self, object_path: str) -> None:
        self.objects.pop(object_path, None)


class CleanTestScanner:
    async def scan(self, document_id: UUID, content: bytes) -> str:
        return "clean"


def _png_chunk(name: bytes, data: bytes) -> bytes:
    body = name + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def synthetic_png() -> bytes:
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x20\x40\x60"))
        + _png_chunk(b"IEND", b"")
    )


@pytest_asyncio.fixture
async def api_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    def select_test_rules(financial_year: str) -> RulesetVersion:
        rules = build_test_rules()
        if financial_year not in {rules.financial_year, "2025-26"}:
            raise ValueError("Test API requests must use a fixture financial year.")
        return rules.model_copy(update={"financial_year": financial_year})

    app.dependency_overrides[get_db_session] = test_session
    test_settings = Settings(
        database_url="sqlite+aiosqlite://",
        firebase_project_id=FIREBASE_PROJECT_ID,
        firebase_api_key=TEST_JWT_SECRET,
        firebase_test_mode=True,
        google_api_key=None,
    )
    storage = InMemoryStorage()
    extraction_job = ExtractionJob(
        factory,
        storage,  # type: ignore[arg-type]
        ExtractionOrchestrator(test_settings, storage),  # type: ignore[arg-type]
        CleanTestScanner(),
    )

    async def mock_gemini_extract(
        self: GeminiExtractor,
        *,
        document_type: str,
        mime_type: str,
        schema: type[BaseModel],
        pages: object = None,
        document_bytes: bytes | None = None,
    ) -> BaseModel:
        assert document_type == "form16"
        assert mime_type == "image/png"
        assert pages is None
        assert document_bytes == synthetic_png()
        return schema.model_validate(FORM16_FIXTURE)

    monkeypatch.setattr(GeminiExtractor, "extract", mock_gemini_extract)
    # Monkeypatch Firebase auth to accept test JWT tokens
    import app.core.auth as auth_module
    original_verify = auth_module._verify_firebase_token
    def test_verify_firebase_token(token, settings):
        try:
            import jwt
            decoded = jwt.decode(
                token,
                TEST_JWT_SECRET,
                algorithms=['HS256'],
                audience=f'https://{FIREBASE_PROJECT_ID}.firebaseapp.com/auth/v1',
            )
            return decoded, ['HS256']
        except Exception:
            return original_verify(token, settings)
    auth_module._verify_firebase_token = test_verify_firebase_token
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_storage] = lambda: storage  # type: ignore[assignment]
    app.dependency_overrides[get_extraction_job] = lambda: extraction_job
    app.dependency_overrides[require_configured_rules] = lambda: select_test_rules
    app.state.test_session_factory = factory
    app.state.test_storage = storage
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    del app.state.test_session_factory
    del app.state.test_storage
    await engine.dispose()


def make_token(user_id: UUID, **overrides: object) -> str:
    claims: dict[str, object] = {
        "sub": str(user_id),
        "aud": "authenticated",
        "role": "authenticated",
        "iss": f"https://{FIREBASE_PROJECT_ID}.firebaseapp.com/auth/v1",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "email": f"{user_id.hex}@example.test",
    }
    claims.update(overrides)
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def profile_payload() -> dict[str, object]:
    return {
        "salary_components": {
            "basic_salary": "10000",
            "dearness_allowance": "0",
            "hra_received": "0",
            "other_allowances": "0",
        },
        "hra_inputs": {"rent_paid": "0"},
        "other_income": "0",
        "deductions_claimed": {
            "section_80c": "0",
            "section_80d": "0",
            "section_80ccd_1b": "0",
            "section_80e": "0",
            "section_24b": "0",
        },
        "age_bracket": "below_60",
        "city_type": "non_metro",
    }


@pytest.mark.asyncio
async def test_auth_protects_profile_and_creates_profile_from_supabase_subject(
    api_client: AsyncClient,
) -> None:
    health = await api_client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in health.headers["content-security-policy"]

    unauthenticated = await api_client.get("/api/v1/me")
    assert unauthenticated.status_code == 401

    user_id = uuid4()
    response = await api_client.get(
        "/api/v1/me",
        headers={**auth(make_token(user_id)), "X-Request-ID": "test-request-42"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-42"
    assert response.json()["id"] == str(user_id)
    metrics = await api_client.get("/api/v1/metrics/usage", headers=auth(make_token(user_id)))
    assert metrics.status_code == 200
    assert metrics.json()["process_scope"] == "single-process"
    assert any(key.startswith("health_check:") for key in metrics.json()["request_counts"])


@pytest.mark.asyncio
async def test_jwt_signature_issuer_audience_and_expiry_are_verified(
    api_client: AsyncClient,
) -> None:
    user_id = uuid4()
    wrong_issuer = make_token(user_id, iss="https://attacker.invalid/auth/v1")
    expired = make_token(user_id, exp=datetime.now(UTC) - timedelta(minutes=1))
    bad_signature = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "role": "authenticated",
            "iss": f"https://{FIREBASE_PROJECT_ID}.firebaseapp.com/auth/v1",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "wrong-test-secret-is-long-enough-for-testing",
        algorithm="HS256",
    )
    for token in (wrong_issuer, expired, bad_signature):
        response = await api_client.get("/api/v1/me", headers=auth(token))
        assert response.status_code == 401
    wrong_role = make_token(user_id, role="anon")
    assert (await api_client.get("/api/v1/me", headers=auth(wrong_role))).status_code == 401
    valid = await api_client.get("/api/v1/me", headers=auth(make_token(user_id)))
    assert valid.status_code == 200


@pytest.mark.asyncio
async def test_asymmetric_supabase_jwks_signature_is_verified(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    kid = "test-jwks-key"
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})

    async def return_test_key(_settings: Settings) -> list[dict[str, object]]:
        return [jwk]

    monkeypatch.setattr(auth_module, "_get_jwks", return_test_key)
    user_id = uuid4()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "role": "authenticated",
            "iss": f"https://{FIREBASE_PROJECT_ID}.firebaseapp.com/auth/v1",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    response = await api_client.get("/api/v1/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)


@pytest.mark.asyncio
async def test_documents_are_private_and_soft_deleted(api_client: AsyncClient) -> None:
    owner_id, other_user_id = uuid4(), uuid4()
    created = await api_client.post(
        "/api/v1/documents",
        headers=auth(make_token(owner_id)),
        files={
            "file": ("synthetic-form16.png", synthetic_png(), "image/png"),
        },
        data={"document_type": "form16", "auto_delete_after_30_days": "true"},
    )
    assert created.status_code == 202
    document_id = created.json()["id"]
    assert created.json()["status"] == "pending"
    assert created.json()["signed_url"].startswith("https://")
    assert "public" not in created.json()
    assert created.json()["auto_delete_at"] is not None
    assert "ABCDE1234F" not in created.json()["file_name"]

    async with app.state.test_session_factory() as session:
        document = await session.get(Document, UUID(document_id))
        assert document is not None
        assert document.storage_path.startswith(f"{owner_id}/")
        assert document.status == "extracted"
        assert document.auto_delete_at is not None
        extraction = await session.execute(
            select(ExtractionResult).where(ExtractionResult.document_id == document.id)
        )
        extracted = extraction.scalar_one()
        assert extracted.payload["gross_salary"]["value"] == "12345"

    owner_list = await api_client.get("/api/v1/documents", headers=auth(make_token(owner_id)))
    other_list = await api_client.get("/api/v1/documents", headers=auth(make_token(other_user_id)))
    assert [item["id"] for item in owner_list.json()] == [document_id]
    assert other_list.json() == []
    assert owner_list.json()[0]["status"] == "extracted"

    result = await api_client.get(
        f"/api/v1/documents/{document_id}/extraction",
        headers=auth(make_token(owner_id)),
    )
    assert result.status_code == 200
    extraction_id = result.json()["extraction_id"]
    assert extraction_id
    assert result.json()["extraction"]["gross_salary"] == {
        "value": "12345",
        "confidence": "0.97",
        "source_page": 1,
    }
    hidden_result = await api_client.get(
        f"/api/v1/documents/{document_id}/extraction",
        headers=auth(make_token(other_user_id)),
    )
    assert hidden_result.status_code == 404

    validation = await api_client.get(
        f"/api/v1/extractions/{extraction_id}/validation",
        headers=auth(make_token(owner_id)),
    )
    assert validation.status_code == 200
    assert validation.json()["preview_url"].startswith("https://")
    assert {issue["field"] for issue in validation.json()["issues"]} >= {
        "employee_name",
        "employee_pan",
    }
    assert (
        await api_client.get(
            f"/api/v1/extractions/{extraction_id}/validation",
            headers=auth(make_token(other_user_id)),
        )
    ).status_code == 404

    profile = {
        "employment_type": "employee",
        "consent_given": True,
        "financial_year": "2025-26",
        "salary_components": {
            "basic_salary": "12345",
            "dearness_allowance": "0",
            "hra_received": "0",
            "other_allowances": "0",
        },
        "hra_inputs": {"rent_paid": "0"},
        "other_income": "0",
        "deductions_claimed": {
            "section_80c": "0",
            "section_80d": "0",
            "section_80ccd_1b": "0",
            "section_80e": "0",
            "section_24b": "0",
        },
        "age_bracket": "below_60",
        "city_type": "non_metro",
        "planning_eligibility": {
            "health_insurance_eligible": False,
            "eligible_health_insurance_premium": "0",
            "education_loan_eligible": False,
            "eligible_education_loan_interest": "0",
            "home_loan_eligible": False,
            "eligible_home_loan_interest": "0",
        },
    }
    confirmed = await api_client.put(
        f"/api/v1/extractions/{extraction_id}/confirm",
        headers=auth(make_token(owner_id)),
        json={
            "field_values": {
                "employee_name": "Synthetic Employee",
                "employee_pan": "ABCDE1234F",
            },
            "profile": profile,
            "consent_given": True,
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["fields"]["employee_name"]["value"] == "Synthetic Employee"
    assert confirmed.json()["fields"]["employee_pan"]["value"] == "AB*******F"
    assert confirmed.json()["profile"]["employment_type"] == "employee"
    confirmed_user = await api_client.get(
        "/api/v1/me",
        headers=auth(make_token(owner_id)),
    )
    assert confirmed_user.json()["confirmed_profile"]["financial_year"] == "2025-26"
    async with app.state.test_session_factory() as session:
        saved_result = await session.get(ExtractionResult, UUID(extraction_id))
        assert saved_result is not None
        assert saved_result.confirmed_profile["consent_given"] is True
        assert saved_result.payload["employee_name"]["value"] == "Synthetic Employee"
        assert saved_result.payload["employee_pan"]["value"] == "AB*******F"

    profile["salary_components"]["basic_salary"] = 12.5
    invalid_profile = await api_client.put(
        f"/api/v1/extractions/{extraction_id}/confirm",
        headers=auth(make_token(owner_id)),
        json={
            "field_values": {},
            "profile": profile,
            "consent_given": True,
        },
    )
    assert invalid_profile.status_code == 422

    forbidden_delete = await api_client.delete(
        f"/api/v1/documents/{document_id}", headers=auth(make_token(other_user_id))
    )
    assert forbidden_delete.status_code == 404
    deleted = await api_client.delete(
        f"/api/v1/documents/{document_id}", headers=auth(make_token(owner_id))
    )
    assert deleted.status_code == 204
    remaining = await api_client.get("/api/v1/documents", headers=auth(make_token(owner_id)))
    assert remaining.json() == []
    assert not app.state.test_storage.objects


@pytest.mark.asyncio
async def test_manual_profile_requires_explicit_consent_and_persists(
    api_client: AsyncClient,
) -> None:
    user_id = uuid4()
    profile = {
        "employment_type": "business_freelancer",
        "consent_given": True,
        "financial_year": "2025-26",
        "salary_components": {
            "basic_salary": "0",
            "dearness_allowance": "0",
            "hra_received": "0",
            "other_allowances": "0",
        },
        "hra_inputs": {"rent_paid": "0"},
        "other_income": "50000",
        "deductions_claimed": {
            "section_80c": "0",
            "section_80d": "0",
            "section_80ccd_1b": "0",
            "section_80e": "0",
            "section_24b": "0",
        },
        "age_bracket": "below_60",
        "city_type": "non_metro",
        "planning_eligibility": {
            "health_insurance_eligible": False,
            "eligible_health_insurance_premium": "0",
            "education_loan_eligible": False,
            "eligible_education_loan_interest": "0",
            "home_loan_eligible": False,
            "eligible_home_loan_interest": "0",
        },
    }
    headers = auth(make_token(user_id))
    rejected = await api_client.put(
        "/api/v1/me/confirmed-profile",
        headers=headers,
        json={**profile, "consent_given": False},
    )
    assert rejected.status_code == 422
    saved = await api_client.put(
        "/api/v1/me/confirmed-profile",
        headers=headers,
        json=profile,
    )
    assert saved.status_code == 200
    assert saved.json()["employment_type"] == "business_freelancer"
    me = await api_client.get("/api/v1/me", headers=headers)
    assert me.json()["confirmed_profile"]["employment_type"] == "business_freelancer"
    async with app.state.test_session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        assert user.confirmed_profile["other_income"] == "50000"


@pytest.mark.asyncio
async def test_delete_my_data_requires_confirmation_and_removes_local_records(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def skip_external_auth_delete(self: PrivacyService, user_id: UUID) -> None:
        assert user_id

    async def privacy_service(
        session: AsyncSession = Depends(get_db_session),
    ) -> AsyncIterator[PrivacyService]:
        yield PrivacyService(
            session,
            Settings(
                database_url="sqlite+aiosqlite://",
                firebase_project_id=FIREBASE_PROJECT_ID,
            ),
            app.state.test_storage,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(PrivacyService, "_delete_firebase_identity", skip_external_auth_delete)
    app.dependency_overrides[get_privacy_service] = privacy_service
    user_id = uuid4()
    headers = auth(make_token(user_id))
    rejected = await api_client.request("DELETE", "/api/v1/me/data", headers=headers, json={})
    assert rejected.status_code == 422

    deleted = await api_client.request(
        "DELETE",
        "/api/v1/me/data",
        headers=headers,
        json={"confirmation": "DELETE"},
    )
    assert deleted.status_code == 204
    async with app.state.test_session_factory() as session:
        assert await session.get(User, user_id) is None
    app.dependency_overrides.pop(get_privacy_service)


@pytest.mark.asyncio
async def test_upload_rejects_bad_magic_type_and_size(api_client: AsyncClient) -> None:
    headers = auth(make_token(uuid4()))
    bad_signature = await api_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("not-a-pdf.pdf", b"<html>not a PDF</html>", "application/pdf")},
        data={"document_type": "form16"},
    )
    assert bad_signature.status_code == 415

    mismatched_extension = await api_client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("image.pdf", synthetic_png(), "image/png")},
        data={"document_type": "form16"},
    )
    assert mismatched_extension.status_code == 415

    too_large = await api_client.post(
        "/api/v1/documents",
        headers=headers,
        files={
            "file": (
                "large.pdf",
                b"%PDF-" + b"0" * (10 * 1024 * 1024),
                "application/pdf",
            )
        },
        data={"document_type": "form16"},
    )
    assert too_large.status_code == 413


@pytest.mark.asyncio
async def test_failed_document_extraction_can_be_retried(api_client: AsyncClient) -> None:
    user_id = uuid4()
    response = await api_client.post(
        "/api/v1/documents",
        headers=auth(make_token(user_id)),
        files={"file": ("synthetic.png", synthetic_png(), "image/png")},
        data={"document_type": "form16"},
    )
    document_id = UUID(response.json()["id"])
    async with app.state.test_session_factory() as session:
        document = await session.get(Document, document_id)
        assert document is not None
        document.status = "failed"
        document.extraction_error_code = "extraction_failed"
        await session.commit()

    retried = await api_client.post(
        f"/api/v1/documents/{document_id}/retry",
        headers=auth(make_token(user_id)),
    )
    assert retried.status_code == 202
    assert retried.json()["status"] == "pending"
    status_response = await api_client.get(
        f"/api/v1/documents/{document_id}/extraction",
        headers=auth(make_token(user_id)),
    )
    assert status_response.json()["status"] == "extracted"


@pytest.mark.asyncio
async def test_document_upload_rejects_oversized_request(api_client: AsyncClient) -> None:
    user_id = uuid4()
    response = await api_client.post(
        "/api/v1/documents",
        headers=auth(make_token(user_id)),
        content=b"x" * (get_settings().max_upload_size_bytes + 64 * 1024 + 1),
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Document exceeds the upload size limit."


@pytest.mark.asyncio
async def test_tax_compute_and_compare_use_engine_and_persist_trace(
    api_client: AsyncClient,
) -> None:
    user_id = uuid4()
    headers = auth(make_token(user_id))
    compute = await api_client.post(
        "/api/v1/tax/compute",
        headers=headers,
        json={"financial_year": "Synthetic FY", "regime": "old", "profile": profile_payload()},
    )
    assert compute.status_code == 200
    compute_result = compute.json()["result"]
    assert compute_result["regime"] == "old"
    assert compute_result["trace"]

    compare = await api_client.post(
        "/api/v1/tax/compare",
        headers=headers,
        json={"financial_year": "Synthetic FY", "profile": profile_payload()},
    )
    assert compare.status_code == 200
    compare_result = compare.json()["result"]
    assert compare_result["old_regime"]["trace"]
    assert compare_result["new_regime"]["trace"]

    async with app.state.test_session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        computations = await session.execute(
            select(func.count())
            .select_from(TaxComputation)
            .where(TaxComputation.user_id == user_id)
        )
        assert computations.scalar_one() == 2
        saved = await session.get(TaxComputation, UUID(compute.json()["id"]))
        assert saved is not None
        assert saved.result["trace"] == compute_result["trace"]


@pytest.mark.asyncio
async def test_invalid_tax_input_is_rejected_without_echoing_sensitive_values(
    api_client: AsyncClient,
) -> None:
    secret_value = "987654321"
    response = await api_client.post(
        "/api/v1/tax/compute",
        headers=auth(make_token(uuid4())),
        json={
            "financial_year": "Synthetic FY",
            "regime": "old",
            "profile": {**profile_payload(), "other_income": secret_value},
            "unexpected": "should fail validation",
        },
    )
    assert response.status_code == 422
    assert secret_value not in response.text


@pytest.mark.asyncio
async def test_tax_endpoints_fail_closed_when_verified_rules_are_not_available(
    api_client: AsyncClient,
) -> None:
    app.dependency_overrides.pop(require_configured_rules)
    response = await api_client.post(
        "/api/v1/tax/compute",
        headers=auth(make_token(uuid4())),
        json={"financial_year": "2025-26", "regime": "old", "profile": profile_payload()},
    )
    assert response.status_code == 503
    assert "Verified tax rules" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tax_compare_cache_reuses_result_but_persists_each_request(
    api_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import tax as tax_service_module

    calls = 0
    original_compare = tax_service_module.compare_regimes

    def counted_compare(profile: TaxpayerProfile, rules: RulesetVersion) -> TaxComparisonResult:
        nonlocal calls
        calls += 1
        return original_compare(profile, rules)

    monkeypatch.setattr(tax_service_module, "compare_regimes", counted_compare)
    user_id = uuid4()
    headers = auth(make_token(user_id))
    request = {"financial_year": "Synthetic FY", "profile": profile_payload()}
    first = await api_client.post("/api/v1/tax/compare", headers=headers, json=request)
    second = await api_client.post("/api/v1/tax/compare", headers=headers, json=request)

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["result"] == second.json()["result"]
    assert calls == 1

    async with app.state.test_session_factory() as session:
        computations = await session.execute(
            select(func.count())
            .select_from(TaxComputation)
            .where(TaxComputation.user_id == user_id)
        )
        assert computations.scalar_one() == 2


@pytest.mark.asyncio
async def test_chat_sse_persists_history_and_enforces_session_ownership(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_respond(self: ChatService, session_id: UUID, question: str) -> ChatMessage:
        assert question == "Explain my saved result."
        await self.repository.add_message(session_id, "user", question)
        return await self.repository.add_message(
            session_id,
            "assistant",
            "I'm not sure I can verify that from the available tools.",
        )

    monkeypatch.setattr(ChatService, "respond", mock_respond)
    owner_id = uuid4()
    owner_headers = auth(make_token(owner_id))
    created = await api_client.post(
        "/api/v1/chat/sessions",
        headers=owner_headers,
        json={"title": "My tax question"},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    response = await api_client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        headers=owner_headers,
        json={"content": "Explain my saved result."},
    )
    assert response.status_code == 200
    assert "event: delta" in response.text
    assert "event: citations" in response.text
    assert "event: done" in response.text

    history = await api_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers=owner_headers,
    )
    assert history.status_code == 200
    assert [message["role"] for message in history.json()["messages"]] == [
        "user",
        "assistant",
    ]
    forbidden = await api_client.get(
        f"/api/v1/chat/sessions/{session_id}",
        headers=auth(make_token(uuid4())),
    )
    assert forbidden.status_code == 404

    async with app.state.test_session_factory() as session:
        persisted = await session.get(ChatSession, UUID(session_id))
        assert persisted is not None
        assert persisted.user_id == owner_id
        messages = list(
            (
                await session.scalars(
                    select(ChatMessage).where(ChatMessage.chat_session_id == UUID(session_id))
                )
            ).all()
        )
        assert len(messages) == 2


@pytest.mark.asyncio
async def test_simulator_returns_exact_engine_before_and_after_results(
    api_client: AsyncClient,
) -> None:
    unauthenticated = await api_client.post("/api/v1/tax/simulate", json={})
    assert unauthenticated.status_code == 401

    profile = profile_payload()
    profile["salary_components"] = {
        "basic_salary": "10000",
        "dearness_allowance": "0",
        "hra_received": "0",
        "other_allowances": "0",
    }
    profile["other_income"] = "50000"
    response = await api_client.post(
        "/api/v1/tax/simulate",
        headers=auth(make_token(uuid4())),
        json={
            "financial_year": "Synthetic FY",
            "profile": profile,
            "change": {"kind": "deduction", "section": "80C", "amount": "50"},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["before"]["old_regime"]["trace"]
    assert result["after"]["old_regime"]["trace"]
    assert result["tax_saved"] == str(
        min(
            Decimal(result["before"]["old_regime"]["total_tax"]),
            Decimal(result["before"]["new_regime"]["total_tax"]),
        )
        - min(
            Decimal(result["after"]["old_regime"]["total_tax"]),
            Decimal(result["after"]["new_regime"]["total_tax"]),
        )
    )


@pytest.mark.asyncio
async def test_suggestions_are_persisted_and_plan_state_is_user_scoped(
    api_client: AsyncClient,
) -> None:
    owner_id = uuid4()
    profile = {
        **profile_payload(),
        "employment_type": "employee",
        "consent_given": True,
        "financial_year": "2025-26",
        "planning_eligibility": {
            "health_insurance_eligible": True,
            "eligible_health_insurance_premium": "100",
            "education_loan_eligible": True,
            "eligible_education_loan_interest": "100",
            "home_loan_eligible": True,
            "eligible_home_loan_interest": "100",
        },
    }
    profile["salary_components"] = {
        "basic_salary": "10000",
        "dearness_allowance": "0",
        "hra_received": "1000",
        "other_allowances": "0",
    }
    profile["hra_inputs"] = {"rent_paid": "1000"}
    profile["other_income"] = "50000"
    response = await api_client.post(
        "/api/v1/tax/suggestions",
        headers=auth(make_token(owner_id)),
        json={"financial_year": "2025-26", "profile": profile},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["suggestions"]
    assert any(item["key"] == "HRA" for item in payload["suggestions"])
    planned_item = payload["suggestions"][0]
    plan_url = f"/api/v1/tax/suggestions/{planned_item['id']}/plan"

    other_user = await api_client.put(
        plan_url,
        headers=auth(make_token(uuid4())),
        json={"planned_to_do": True},
    )
    assert other_user.status_code == 404

    planned = await api_client.put(
        plan_url,
        headers=auth(make_token(owner_id)),
        json={"planned_to_do": True},
    )
    assert planned.status_code == 200
    assert planned.json()["planned_to_do"] is True

    regenerated = await api_client.post(
        "/api/v1/tax/suggestions",
        headers=auth(make_token(owner_id)),
        json={"financial_year": "2025-26", "profile": profile},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["planned_count"] == 1
    matching = next(
        item for item in regenerated.json()["suggestions"] if item["key"] == planned_item["key"]
    )
    assert matching["planned_to_do"] is True
