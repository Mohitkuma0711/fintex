from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Suggestion


class SuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_or_update(
        self,
        *,
        user_id: UUID,
        tax_computation_id: UUID,
        financial_year: str,
        rules_version: str,
        key: str,
        title: str,
        detail: dict[str, object],
    ) -> Suggestion:
        statement = select(Suggestion).where(
            Suggestion.user_id == user_id,
            Suggestion.financial_year == financial_year,
            Suggestion.rules_version == rules_version,
            Suggestion.suggestion_key == key,
            Suggestion.deleted_at.is_(None),
        )
        suggestion = (await self.session.execute(statement)).scalar_one_or_none()
        if suggestion is None:
            suggestion = Suggestion(
                user_id=user_id,
                tax_computation_id=tax_computation_id,
                financial_year=financial_year,
                rules_version=rules_version,
                suggestion_key=key,
                planned_to_do=False,
                title=title,
                detail=detail,
            )
            self.session.add(suggestion)
        else:
            suggestion.tax_computation_id = tax_computation_id
            suggestion.title = title
            suggestion.detail = detail
        await self.session.flush()
        return suggestion

    async def get_for_user(self, suggestion_id: UUID, user_id: UUID) -> Suggestion | None:
        statement = select(Suggestion).where(
            Suggestion.id == suggestion_id,
            Suggestion.user_id == user_id,
            Suggestion.deleted_at.is_(None),
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
