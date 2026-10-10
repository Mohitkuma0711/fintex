import asyncio
import os
from io import BytesIO
from uuid import UUID, uuid4

import structlog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.models import Document, ExtractionResult, User
from app.schemas.extraction import Form16Extraction
from app.services.storage.supabase_storage import SupabaseStorage

logger = structlog.get_logger(__name__)


def _synthetic_pdf() -> bytes:
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=A4)
    page.setFont("Helvetica-Bold", 18)
    page.drawString(48, 790, "SYNTHETIC DEMO DOCUMENT")
    page.setFont("Helvetica", 12)
    page.drawString(48, 758, "NOT A VALID FORM 16 — fabricated values for product demonstration.")
    page.drawString(48, 728, "Employee: Synthetic Demo User")
    page.drawString(48, 708, "Employer: Example Employer")
    page.drawString(48, 688, "Assessment year: 2025-26")
    page.drawString(48, 668, "Gross salary: INR 100000")
    page.drawString(48, 648, "Tax deducted: INR 0")
    page.save()
    return output.getvalue()


def _synthetic_extraction() -> dict[str, object]:
    payload = Form16Extraction.model_validate(
        {
            "employee_name": {"value": "Synthetic Demo User", "confidence": "1", "source_page": 1},
            "employee_pan": {"value": None, "confidence": "1", "source_page": 1},
            "employer_name": {"value": "Example Employer", "confidence": "1", "source_page": 1},
            "employer_tan": {"value": None, "confidence": "1", "source_page": 1},
            "assessment_year": {"value": "2025-26", "confidence": "1", "source_page": 1},
            "gross_salary": {"value": "100000", "confidence": "1", "source_page": 1},
            "exempt_allowances": {"value": "0", "confidence": "1", "source_page": 1},
            "perquisites": {"value": "0", "confidence": "1", "source_page": 1},
            "profits_in_lieu_of_salary": {"value": "0", "confidence": "1", "source_page": 1},
            "deductions_under_chapter_vi_a": {
                "value": "0",
                "confidence": "1",
                "source_page": 1,
            },
            "section_80c": {"value": "0", "confidence": "1", "source_page": 1},
            "deduction_items": [],
            "taxable_income": {"value": "100000", "confidence": "1", "source_page": 1},
            "total_tax_deducted": {"value": "0", "confidence": "1", "source_page": 1},
        }
    )
    return payload.model_dump(mode="json")


async def seed_demo() -> UUID:
    demo_user_value = os.environ.get("DEMO_USER_ID")
    if not demo_user_value:
        raise RuntimeError("Set DEMO_USER_ID to the UUID of a pre-created demo user.")
    user_id = UUID(demo_user_value)
    settings = get_settings()
    storage = SupabaseStorage(settings)
    document_id = uuid4()
    extraction_id = uuid4()
    object_path = f"{user_id}/demo/{document_id}.pdf"
    pdf_content = _synthetic_pdf()
    uploaded = False

    await storage.upload(object_path, pdf_content, "application/pdf")
    uploaded = True
    try:
        async with SessionFactory() as session:
            async with session.begin():
                user = await session.scalar(select(User).where(User.id == user_id))
                if user is None:
                    user = User(
                        id=user_id,
                        email=os.environ.get("DEMO_USER_EMAIL"),
                        display_name="Synthetic Demo User",
                    )
                    session.add(user)
                else:
                    user.display_name = "Synthetic Demo User"

                document = Document(
                    id=document_id,
                    user_id=user_id,
                    file_name="SYNTHETIC-NOT-TAX-FORM.pdf",
                    storage_path=object_path,
                    content_type="application/pdf",
                    size_bytes=len(pdf_content),
                    status="extracted",
                    document_type="form16",
                    scan_status="not_scanned",
                )
                extraction = ExtractionResult(
                    id=extraction_id,
                    document_id=document_id,
                    extraction_type="form16",
                    model_version="synthetic-seed",
                    prompt_version="synthetic-seed",
                    payload=_synthetic_extraction(),
                )
                session.add_all([document, extraction])
    except Exception:
        if uploaded:
            try:
                await storage.delete(object_path)
            except Exception as cleanup_error:
                logger.error(
                    "demo_seed_storage_cleanup_failed",
                    error_type=type(cleanup_error).__name__,
                )
        raise

    print(f"Synthetic demo document seeded: {document_id}")
    return document_id


def main() -> None:
    document_id = asyncio.run(seed_demo())
    print(
        "After signing in, open "
        f"/review?documentId={document_id} to inspect the synthetic extraction."
    )


if __name__ == "__main__":
    main()
