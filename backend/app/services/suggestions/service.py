from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import User
from app.repositories.suggestions import SuggestionRepository
from app.repositories.tax_computations import TaxComputationRepository
from app.schemas.api import TaxSuggestionsResponse
from app.schemas.suggestions import SuggestionResponse
from app.schemas.tax import ConfirmedTaxpayerProfile
from app.services.suggestions.engine import build_suggestion_drafts, savings_potential
from app.services.suggestions.explainer import explain_suggestion
from app.services.tax_engine.compare import compare_regimes
from app.services.tax_engine.rules import RulesetVersion


class SuggestionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.suggestion_repository = SuggestionRepository(session)
        self.computation_repository = TaxComputationRepository(session)

    async def generate(
        self,
        user: User,
        financial_year: str,
        confirmed_profile: ConfirmedTaxpayerProfile,
        rules: RulesetVersion,
    ) -> TaxSuggestionsResponse:
        rules.require_ready()
        rules.require_suggestion_terms_ready()
        profile = confirmed_profile.to_taxpayer_profile()
        baseline = compare_regimes(profile, rules)
        computation = await self.computation_repository.add(
            user_id=user.id,
            financial_year=financial_year,
            rules_version=rules.version,
            computation_type="suggestions",
            result=baseline.model_dump(mode="json"),
        )
        drafts = build_suggestion_drafts(confirmed_profile, rules)
        suggestions: list[SuggestionResponse] = []
        for draft in drafts:
            explained = await explain_suggestion(draft, self.settings)
            row = await self.suggestion_repository.save_or_update(
                user_id=user.id,
                tax_computation_id=computation.id,
                financial_year=financial_year,
                rules_version=rules.version,
                key=explained.key,
                title=explained.title,
                detail=explained.model_dump(mode="json"),
            )
            suggestions.append(
                SuggestionResponse.model_validate(
                    {
                        **row.detail,
                        "id": row.id,
                        "planned_to_do": row.planned_to_do,
                    }
                )
            )
        await self.session.commit()
        return TaxSuggestionsResponse(
            financial_year=financial_year,
            rules_version=rules.version,
            suggestions=suggestions,
            savings_potential=savings_potential(drafts),
            planned_count=sum(item.planned_to_do for item in suggestions),
        )

    async def set_planned(
        self,
        suggestion_id: UUID,
        user_id: UUID,
        planned_to_do: bool,
    ) -> SuggestionResponse | None:
        row = await self.suggestion_repository.get_for_user(suggestion_id, user_id)
        if row is None:
            return None
        row.planned_to_do = planned_to_do
        await self.session.commit()
        await self.session.refresh(row)
        return SuggestionResponse.model_validate(
            {
                **row.detail,
                "id": row.id,
                "planned_to_do": row.planned_to_do,
            }
        )
