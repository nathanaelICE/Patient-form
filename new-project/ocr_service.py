"""Gemini-vision wrapper that reads a patient-form image into structured fields.

Does no database work. Returns a dict of extracted field values plus a per-field
confidence score. Designed to be patched in tests (`_get_client`) so CI makes no
real API calls.
"""
import os
import re
import json
import time
import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Default to a cheap, capable vision model; override with OCR_MODEL (e.g.
# gemini-2.5-pro for higher accuracy, gemini-2.5-flash-lite for lowest cost).
DEFAULT_MODEL = "gemini-2.5-flash"

# Retry policy for transient rate-limit (HTTP 429 / RESOURCE_EXHAUSTED) errors.
# Free-tier Gemini has a low requests-per-minute ceiling, so a burst batch can
# trip it; back off and retry rather than failing the job outright.
RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get("OCR_RATELIMIT_RETRIES", "4"))
RATE_LIMIT_BASE_DELAY = float(os.environ.get("OCR_RATELIMIT_BASE_DELAY", "2.0"))

PATIENT_FIELDS = [
    "name", "date_of_birth", "gender", "phone",
    "national_id", "place_of_birth", "marital_status",
    "occupation", "religion", "nationality",
    "blood_type", "allergies", "known_conditions",
]

_PROMPT = (
    "You are reading a scanned or photographed patient registration form. "
    "Extract the following fields. Return ONLY a JSON object, no prose, with two "
    "top-level keys:\n"
    '  "fields": an object with these keys, each a string or null if absent:\n'
    f"    {', '.join(PATIENT_FIELDS)}\n"
    '  "confidence": an object with the same keys, each a number 0.0-1.0 for how '
    "sure you are of that field.\n"
    "Rules: date_of_birth must be ISO format YYYY-MM-DD. gender must be one of "
    "male/female/other. national_id is the 16-digit NIK if present. Use null "
    "(not empty string) for any field you cannot read."
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class OCRError(Exception):
    """Raised when the vision call or its parsing fails."""


class OCRRateLimitError(OCRError):
    """Raised when the vision API keeps returning a rate-limit/quota error."""


def _is_rate_limit(exc: Exception) -> bool:
    """Best-effort detection of a 429 / quota-exhausted error from the SDK."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 429:
        return True
    text = str(exc).lower()
    markers = ("429", "resource_exhausted", "quota", "rate limit", "too many requests")
    return any(m in text for m in markers)


def ocr_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def _get_client() -> "genai.Client":
    # Reads GEMINI_API_KEY / GOOGLE_API_KEY from the environment.
    return genai.Client()


def _model() -> str:
    return os.environ.get("OCR_MODEL", DEFAULT_MODEL)


def _extract_json(text: str) -> dict:
    match = _JSON_RE.search(text or "")
    if not match:
        raise OCRError("no JSON object found in model response")
    return json.loads(match.group(0))


def extract_patient_fields(image_bytes: bytes, media_type: str) -> dict:
    """Send the image to Gemini vision and return {fields, confidence}."""
    client = _get_client()
    attempt = 0
    while True:
        try:
            response = client.models.generate_content(
                model=_model(),
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=media_type),
                    _PROMPT,
                ],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            break
        except Exception as exc:  # SDK/network error
            if _is_rate_limit(exc):
                attempt += 1
                if attempt >= RATE_LIMIT_MAX_ATTEMPTS:
                    raise OCRRateLimitError(
                        f"rate limited after {attempt} attempts: {exc}"
                    ) from exc
                delay = RATE_LIMIT_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "OCR rate-limited (attempt %d/%d); backing off %.1fs: %s",
                    attempt, RATE_LIMIT_MAX_ATTEMPTS, delay, exc,
                )
                time.sleep(delay)
                continue
            raise OCRError(f"vision request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise OCRError("model returned no text content")

    try:
        parsed = _extract_json(text)
    except (ValueError, OCRError) as exc:
        raise OCRError(f"could not parse model JSON: {exc}") from exc

    raw_fields = parsed.get("fields") or {}
    raw_conf = parsed.get("confidence") or {}
    # Normalize: only known fields, missing keys default to null / 0.0
    fields = {f: (raw_fields.get(f) if isinstance(raw_fields, dict) else None) for f in PATIENT_FIELDS}
    confidence = {f: (raw_conf.get(f, 0.0) if isinstance(raw_conf, dict) else 0.0) for f in PATIENT_FIELDS}
    return {"fields": fields, "confidence": confidence}
