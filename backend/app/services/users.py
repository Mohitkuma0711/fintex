from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.users import UserRepository
from app.schemas.api import UpdateUserRequest
from app.schemas.tax import ConfirmedTaxpayerProfile


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = UserRepository(session)

    async def update_profile(self, user: User, changes: UpdateUserRequest) -> User:
        return await self.repository.update(user, changes.model_dump(exclude_unset=True))

    async def confirm_profile(self, user: User, profile: ConfirmedTaxpayerProfile) -> User:
        return await self.repository.update(
            user,
            {
                "confirmed_profile": profile.model_dump(mode="json"),
                "profile_confirmed_at": datetime.now(UTC),
            },
        )
