import asyncio
import json
from pathlib import Path

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.services.suggestions.engine import SuggestionDraft

logger = structlog.get_logger(__name__)
PROMPT_PATH = Path(__file__).parent / "prompts" / "explanation_v1.txt"


class SuggestionExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(min_length=1, max_length=1000)


class SuggestionExplanationError(RuntimeError):
    """Raised when a configured Gemini suggestion explanation cannot be produced."""


async def explain_suggestion(
    draft: SuggestionDraft,
    settings: Settings,
) -> SuggestionDraft:
    api_key = settings.google_api_key or settings.gemini_api_key
    if api_key is None:
        return draft
    try:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except OSError as error:
        logger.error("suggestion_explanation_prompt_unavailable")
        raise SuggestionExplanationError("Suggestion explanation prompt is unavailable.") from error

    engine_facts = {
        "title": draft.title,
        "amount_to_invest": str(draft.amount_to_invest),
        "tax_saved": str(draft.tax_saved),
        "net_benefit_tax_only": str(draft.net_benefit),
        "eligible_regime": draft.eligible_regime,
        "lock_in_period": draft.lock_in_period,
        "liquidity_note": draft.liquidity_note,
        "rule_reference": draft.rule_reference,
        "tax_engine_explanation": draft.explanation,
    }
    client = genai.Client(
        api_key=api_key.get_secret_value(),
        http_options=types.HttpOptions(
            timeout=settings.gemini_timeout_seconds * 1000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    try:
        async with client.aio as async_client:
            async with asyncio.timeout(settings.gemini_timeout_seconds):
                response = await async_client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[prompt, json.dumps(engine_facts, separators=(",", ":"))],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=SuggestionExplanation.model_json_schema(),
                    ),
                )
        if not response.text:
            raise SuggestionExplanationError("Gemini returned no suggestion explanation.")
        explanation = SuggestionExplanation.model_validate_json(response.text)
    except (TimeoutError, genai_errors.APIError, ValidationError, ValueError, TypeError) as error:
        logger.warning("suggestion_explanation_failed", error_type=type(error).__name__)
        raise SuggestionExplanationError(
            "Suggestion explanations are temporarily unavailable."
        ) from error
    return draft.model_copy(
        update={"explanation": explanation.explanation, "explanation_source": "gemini"}
    )
