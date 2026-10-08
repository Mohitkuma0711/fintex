from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import (
    get_suggestion_service,
    get_tax_service,
    require_configured_rules,
)
from app.core.auth import get_current_user
from app.models import TaxComputation, User
from app.schemas.api import (
    SuggestionPlanRequest,
    SuggestionPlanResponse,
    TaxCompareRequest,
    TaxCompareResponse,
    TaxComputeRequest,
    TaxComputeResponse,
    TaxSimulationRequest,
    TaxSimulationResponse,
    TaxSuggestionsRequest,
    TaxSuggestionsResponse,
)
from app.schemas.tax import TaxComparisonResult
from app.services.suggestions.explainer import SuggestionExplanationError
from app.services.suggestions.service import SuggestionService
from app.services.tax import TaxService
from app.services.tax_engine.rules import RuleConfigurationError, RulesetVersion

router = APIRouter(prefix="/tax", tags=["tax"])


@router.post(
    "/compute",
    response_model=TaxComputeResponse,
    summary="Calculate tax using the selected verified ruleset",
    description=(
        "Uses the deterministic tax engine. The calculation is not performed by an LLM. "
        "Requests fail closed when verified rules are unavailable."
    ),
)
async def compute_tax(
    request: TaxComputeRequest,
    user: User = Depends(get_current_user),
    service: TaxService = Depends(get_tax_service),
    select_rules: Callable[[str], RulesetVersion] = Depends(require_configured_rules),
) -> TaxComputeResponse:
    rules: RulesetVersion = select_rules(request.financial_year)
    record, result = await service.compute(user, request, rules)
    return TaxComputeResponse(id=record.id, result=result)


@router.post(
    "/compare",
    response_model=TaxCompareResponse,
    summary="Compare old and new regimes using the selected verified ruleset",
    description="Returns a trace for each regime and persists the comparison.",
)
async def compare_tax(
    request: TaxCompareRequest,
    user: User = Depends(get_current_user),
    service: TaxService = Depends(get_tax_service),
    select_rules: Callable[[str], RulesetVersion] = Depends(require_configured_rules),
) -> TaxCompareResponse:
    rules: RulesetVersion = select_rules(request.financial_year)
    record: TaxComputation
    result: TaxComparisonResult
    record, result = await service.compare(user, request, rules)
    return TaxCompareResponse(id=record.id, result=result)


@router.post(
    "/simulate",
    response_model=TaxSimulationResponse,
    summary="Run a what-if tax scenario",
    description="Re-runs both deterministic regime calculations with one changed input.",
)
async def simulate_tax(
    request: TaxSimulationRequest,
    user: User = Depends(get_current_user),
    select_rules: Callable[[str], RulesetVersion] = Depends(require_configured_rules),
) -> TaxSimulationResponse:
    if user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is unavailable.")
    rules = select_rules(request.financial_year)
    before, after, tax_saved = TaxService.simulate(request, rules)
    before_result = before.old_regime if before.recommended_regime == "old" else before.new_regime
    after_result = after.old_regime if after.recommended_regime == "old" else after.new_regime
    return TaxSimulationResponse(
        financial_year=rules.financial_year,
        rules_version=rules.version,
        before=before,
        after=after,
        tax_saved=tax_saved,
        recommended_regime_changed=before.recommended_regime != after.recommended_regime,
        trace_before=before_result.trace,
        trace_after=after_result.trace,
    )


@router.post(
    "/suggestions",
    response_model=TaxSuggestionsResponse,
    summary="Generate personalized, engine-tested tax suggestions",
)
async def get_tax_suggestions(
    request: TaxSuggestionsRequest,
    user: User = Depends(get_current_user),
    service: SuggestionService = Depends(get_suggestion_service),
    select_rules: Callable[[str], RulesetVersion] = Depends(require_configured_rules),
) -> TaxSuggestionsResponse:
    rules = select_rules(request.financial_year)
    try:
        return await service.generate(user, request.financial_year, request.profile, rules)
    except RuleConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Verified suggestion terms are not available for the requested financial year."
            ),
        ) from error
    except SuggestionExplanationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error


@router.put(
    "/suggestions/{suggestion_id}/plan",
    response_model=SuggestionPlanResponse,
    summary="Mark a suggestion as planned or unplanned",
)
async def update_suggestion_plan(
    suggestion_id: UUID,
    request: SuggestionPlanRequest,
    user: User = Depends(get_current_user),
    service: SuggestionService = Depends(get_suggestion_service),
) -> SuggestionPlanResponse:
    suggestion = await service.set_planned(suggestion_id, user.id, request.planned_to_do)
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found.",
        )
    return SuggestionPlanResponse(
        id=suggestion.id,
        key=suggestion.key,
        planned_to_do=suggestion.planned_to_do,
    )
