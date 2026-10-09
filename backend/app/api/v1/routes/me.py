from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.v1.dependencies import get_privacy_service, get_user_service
from app.core.auth import get_current_user
from app.models import User
from app.schemas.api import DeleteMyDataRequest, UpdateUserRequest, UserResponse
from app.schemas.tax import ConfirmedTaxpayerProfile
from app.services.privacy import PrivacyService
from app.services.users import UserService

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the authenticated user's profile",
)
async def update_me(
    request: UpdateUserRequest,
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> User:
    return await service.update_profile(user, request)


@router.put(
    "/me/confirmed-profile",
    response_model=ConfirmedTaxpayerProfile,
    summary="Save a manually entered, consented taxpayer profile",
)
async def confirm_manual_profile(
    request: ConfirmedTaxpayerProfile,
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> ConfirmedTaxpayerProfile:
    updated = await service.confirm_profile(user, request)
    return ConfirmedTaxpayerProfile.model_validate(updated.confirmed_profile)


@router.delete("/me/data", status_code=status.HTTP_204_NO_CONTENT, summary="Delete my FinTax data")
async def delete_my_data(
    request: DeleteMyDataRequest,
    user: User = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
) -> Response:
    if request.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Explicit deletion confirmation is required.",
        )
    await service.delete_user_data(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
