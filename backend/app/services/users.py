from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import sync_user_document
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.api import UpdateUserRequest
from app.schemas.tax import ConfirmedTaxpayerProfile


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = UserRepository(session)

    async def update_profile(self, user: User, changes: UpdateUserRequest) -> User:
        updated = await self.repository.update(user, changes.model_dump(exclude_unset=True))
        sync_user_document(
            user_id=str(updated.id),
            email=updated.email,
            display_name=updated.display_name,
            preferred_financial_year=updated.preferred_financial_year,
            confirmed_profile=updated.confirmed_profile,
        )
        return updated

    async def confirm_profile(self, user: User, profile: ConfirmedTaxpayerProfile) -> User:
        updated = await self.repository.update(
            user,
            {
                "confirmed_profile": profile.model_dump(mode="json"),
                "profile_confirmed_at": datetime.now(UTC),
            },
        )
        sync_user_document(
            user_id=str(updated.id),
            email=updated.email,
            display_name=updated.display_name,
            preferred_financial_year=updated.preferred_financial_year,
            confirmed_profile=updated.confirmed_profile,
        )
        return updated
