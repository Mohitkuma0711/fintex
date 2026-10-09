import re

_PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)


def mask_pan(value: str | None) -> str | None:
    if not value:
        return value
    normalized = value.strip().upper()
    if re.fullmatch(r"[A-Z]{2}\*{7}[A-Z]", normalized):
        return normalized
    if not _PAN_PATTERN.fullmatch(value.strip()):
        return "[MASKED]"
    return f"{normalized[:2]}*******{normalized[-1]}"


def mask_pans_in_text(value: str) -> str:
    return _PAN_PATTERN.sub(lambda match: mask_pan(match.group()) or "[MASKED]", value)


def redact_pans_in_text(value: str) -> str:
    return _PAN_PATTERN.sub("[REDACTED]", value)
