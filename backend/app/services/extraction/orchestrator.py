import re
from decimal import Decimal

from pydantic import BaseModel

from app.core.config import Settings
from app.schemas.extraction import ExtractedField, Form16Extraction, SalarySlipExtraction
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode
from app.services.extraction.gemini import GeminiExtractor, extraction_schema, prompt_for_document
from app.services.extraction.strategy import select_extraction_input
from app.services.storage.supabase_storage import SupabaseStorage


class ExtractionOrchestrator:
    def __init__(self, settings: Settings, storage: SupabaseStorage) -> None:
        self.settings = settings
        self.storage = storage
        self.gemini = GeminiExtractor(settings)

    async def extract(
        self,
        *,
        object_path: str,
        mime_type: str,
        document_type: str,
        content: bytes | None = None,
    ) -> tuple[BaseModel, str]:
        try:
            schema = extraction_schema(document_type)
            _prompt, prompt_version = prompt_for_document(document_type)
        except ExtractionError:
            raise
        document_content = (
            content if content is not None else await self.storage.download(object_path)
        )
        source = select_extraction_input(
            document_content,
            mime_type,
            self.settings.extraction_max_pdf_pages,
        )
        try:
            result = await self.gemini.extract(
                document_type=document_type,
                mime_type=source.mime_type,
                schema=schema,
                pages=source.pages,
                document_bytes=source.document_bytes,
            )
        except ExtractionError as error:
            if source.pages and error.code in {
                ExtractionErrorCode.RATE_LIMITED,
                ExtractionErrorCode.PROVIDER_UNAVAILABLE,
                ExtractionErrorCode.TIMEOUT,
            }:
                result = self._extract_text_without_ai(document_type, source.pages)
            else:
                raise
        return result, prompt_version

    @staticmethod
    def _extract_text_without_ai(
        document_type: str, pages: list[tuple[int, str]]
    ) -> Form16Extraction | SalarySlipExtraction:
        """Recover literal label/value pairs when the AI provider is throttled."""
        text = "\n".join(f"page {page}: {value}" for page, value in pages)

        def field(*labels: str, amount: bool = False) -> ExtractedField:
            escaped_labels = "|".join(re.escape(label) for label in labels)
            pattern = rf"(?im)(?:^|\n)\s*(?:{escaped_labels})\s*[:\-]?\s+([^\n]+)"
            match = re.search(pattern, text)
            value = match.group(1).strip()[:500] if match else None
            if amount and value:
                amounts = re.findall(r"\d[\d,]*(?:\.\d{1,2})?", value)
                value = amounts[-1].replace(",", "") if amounts else None
            page_match = re.search(
                r"page\s+(\d+):[^\n]*" + (re.escape(value) if value else r"$"),
                text,
                re.I,
            )
            return ExtractedField(
                value=value,
                confidence=Decimal("0.9") if value else Decimal("0"),
                source_page=int(page_match.group(1)) if page_match else None,
            )

        if document_type == "salary_slip":
            return SalarySlipExtraction(
                employee_name=field("Employee Name", "Name"),
                employee_id=field("Employee ID", "Employee Code"),
                employer_name=field("Employer Name", "Company Name"),
                pay_period=field("Pay Period", "Salary Month"),
                basic_salary=field("Basic Salary", "Basic"),
                dearness_allowance=field("Dearness Allowance", "DA"),
                hra=field("HRA", "House Rent Allowance"),
                other_earnings=field("Other Earnings", "Other Allowances"),
                gross_pay=field("Gross Pay", "Gross Salary"),
                deductions=field("Deductions", "Total Deductions"),
                net_pay=field("Net Pay", "Net Salary"),
            )
        return Form16Extraction(
            employee_name=field("Employee Name"),
            employee_pan=field("PAN", "PAN of the employee"),
            employer_name=field("Employer Name"),
            employer_tan=field("Employer TAN", "TAN"),
            assessment_year=field("Assessment Year", "Assessment / financial period"),
            gross_salary=field("Gross Salary", "Gross total income", amount=True),
            exempt_allowances=field(
                "Less: exempt allowances",
                "Exempt Allowances",
                "Allowances exempt",
                "exempt allowances",
                amount=True,
            ),
            perquisites=field("Perquisites"),
            profits_in_lieu_of_salary=field("Profits in lieu of salary"),
            deductions_under_chapter_vi_a=field(
                "Deductions under Chapter VI-A", "Chapter VI-A deductions", amount=True
            ),
            taxable_income=field(
                "Taxable Income", "Income chargeable under salaries", amount=True
            ),
            total_tax_deducted=field(
                "Total Tax Deducted", "TDS deducted", "Tax deducted", amount=True
            ),
        )
