from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaxComputation


class TaxComputationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: UUID,
        financial_year: str,
        rules_version: str,
        computation_type: str,
        result: dict[str, object],
    ) -> TaxComputation:
        computation = TaxComputation(
            user_id=user_id,
            financial_year=financial_year,
            rules_version=rules_version,
            computation_type=computation_type,
            result=result,
        )
        self.session.add(computation)
        await self.session.commit()
        await self.session.refresh(computation)
        return computation
