from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db_session
from app.models import User
from app.schemas.filing import FilingGuidanceResponse
from app.schemas.tax import ConfirmedTaxpayerProfile
from app.services.reports.service import ReportService, filing_guidance

router = APIRouter(tags=["reports"])


@router.get(
    "/reports/latest.pdf",
    responses={200: {"content": {"application/pdf": {}}}, 404: {"description": "No comparison"}},
    summary="Download the latest saved tax comparison report",
)
async def download_latest_report(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    pdf = await ReportService(session).build_pdf(user.id)
    if pdf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculate a tax comparison before downloading a report.",
        )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="fintax-tax-summary.pdf"'},
    )


@router.get(
    "/filing-guidance",
    response_model=FilingGuidanceResponse,
    summary="Get non-binding income-tax return form guidance and a filing checklist",
)
async def get_filing_guidance(
    user: User = Depends(get_current_user),
) -> FilingGuidanceResponse:
    profile: ConfirmedTaxpayerProfile | None = None
    if user.confirmed_profile is not None:
        try:
            profile = ConfirmedTaxpayerProfile.model_validate(user.confirmed_profile)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The saved profile needs review before filing guidance is available.",
            ) from error
    return FilingGuidanceResponse.model_validate(filing_guidance(profile))
