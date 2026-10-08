import hashlib
import json
import threading
import time
from collections import OrderedDict
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaxComputation, User
from app.repositories.tax_computations import TaxComputationRepository
from app.schemas.api import TaxCompareRequest, TaxComputeRequest, TaxSimulationRequest
from app.schemas.tax import TaxComparisonResult, TaxResult
from app.services.suggestions.engine import apply_simulation_change, tax_difference
from app.services.tax_engine.compare import compare_regimes
from app.services.tax_engine.new_regime import calculate_new_regime
from app.services.tax_engine.old_regime import calculate_old_regime
from app.services.tax_engine.rules import RulesetVersion

_COMPARE_CACHE_TTL_SECONDS = 300
_COMPARE_CACHE_MAX_ENTRIES = 128
_compare_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_compare_cache_lock = threading.Lock()


def _comparison_cache_key(user_id: UUID, request: TaxCompareRequest, rules: RulesetVersion) -> str:
    cache_input = {
        "user_id": str(user_id),
        "act": rules.act,
        "financial_year": rules.financial_year,
        "rules_version": rules.version,
        "profile": request.profile.model_dump(mode="json"),
    }
    canonical_input = json.dumps(cache_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_input.encode("utf-8")).hexdigest()


def _cached_comparison(cache_key: str) -> TaxComparisonResult | None:
    now = time.monotonic()
    with _compare_cache_lock:
        cached = _compare_cache.get(cache_key)
        if cached is None:
            return None
        expires_at, serialized_result = cached
        if expires_at <= now:
            del _compare_cache[cache_key]
            return None
        _compare_cache.move_to_end(cache_key)
        return TaxComparisonResult.model_validate_json(serialized_result)


def _cache_comparison(cache_key: str, result: TaxComparisonResult) -> None:
    with _compare_cache_lock:
        _compare_cache[cache_key] = (
            time.monotonic() + _COMPARE_CACHE_TTL_SECONDS,
            result.model_dump_json(),
        )
        _compare_cache.move_to_end(cache_key)
        while len(_compare_cache) > _COMPARE_CACHE_MAX_ENTRIES:
            _compare_cache.popitem(last=False)


class TaxService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = TaxComputationRepository(session)

    async def compute(
        self, user: User, request: TaxComputeRequest, rules: RulesetVersion
    ) -> tuple[TaxComputation, TaxResult]:
        result = (
            calculate_old_regime(request.profile, rules)
            if request.regime == "old"
            else calculate_new_regime(request.profile, rules)
        )
        record = await self.repository.add(
            user_id=user.id,
            financial_year=request.financial_year,
            rules_version=result.rules_version,
            computation_type=request.regime,
            result=result.model_dump(mode="json"),
        )
        return record, result

    async def compare(
        self, user: User, request: TaxCompareRequest, rules: RulesetVersion
    ) -> tuple[TaxComputation, TaxComparisonResult]:
        cache_key = _comparison_cache_key(user.id, request, rules)
        result = _cached_comparison(cache_key)
        if result is None:
            result = compare_regimes(request.profile, rules)
            _cache_comparison(cache_key, result)
        record = await self.repository.add(
            user_id=user.id,
            financial_year=request.financial_year,
            rules_version=result.old_regime.rules_version,
            computation_type="compare",
            result=result.model_dump(mode="json"),
        )
        return record, result

    @staticmethod
    def simulate(
        request: TaxSimulationRequest,
        rules: RulesetVersion,
    ) -> tuple[TaxComparisonResult, TaxComparisonResult, Decimal]:
        before = compare_regimes(request.profile, rules)
        after_profile = apply_simulation_change(
            request.profile,
            kind=request.change.kind,
            amount=request.change.amount,
            section=request.change.section,
        )
        after = compare_regimes(after_profile, rules)
        return before, after, tax_difference(before, after)
