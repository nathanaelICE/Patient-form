# OCR-Assisted Patient Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin upload a photo of a paper patient form; Claude vision extracts the fields as JSON; the React form pre-fills them; staff review, correct, and save through the existing create flow.

**Architecture:** A new `routers/ocr.py` endpoint accepts an image, calls a thin `ocr_service.py` wrapper around the Anthropic SDK (Claude vision + JSON-schema structured output), and returns `{fields, confidence}` without writing to the DB. The `Patient` model and Pydantic schemas gain nine new optional columns. The React `PatientForm` renders the new fields; `PatientNewPage` adds an "Upload form" button that calls the endpoint and pre-fills the form.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, Pydantic v2, `anthropic` SDK; React 18 + TypeScript, Vite, Vitest, @testing-library/react, TanStack Query; Postgres (Neon) in prod, SQLite in tests.

## Global Constraints

- Backend tests run with `cd new-project && uv run pytest`. Frontend tests run with `cd new-project/frontend && npm test`.
- All new API routes are prefixed `/api/...` and gated by `Depends(get_admin)`, matching `routers/patients.py`.
- New `Patient` columns are **all nullable/optional** — existing rows and partial forms must stay valid.
- The OCR service must read `ANTHROPIC_API_KEY` from the environment and be patchable in tests — **no real API calls in CI**.
- Default vision model is `claude-opus-4-8`, overridable via the `OCR_MODEL` env var (per the `claude-api` skill: default to Opus unless a model is explicitly chosen).
- Tests use SQLite via the existing `tests/conftest.py` fixtures (`session`, `client`, `admin_client`); `SQLModel.metadata.create_all` creates the new columns automatically, so the Postgres migration script is **not** exercised by tests.
- Follow existing code style: SQLModel `Field(...)`, Pydantic `field_validator`, FastAPI `APIRouter`. Match `schemas.py` validator patterns (strip blanks → `None`, enum-normalize to lowercase).

---

### Task 1: Expand the `Patient` model and add the Postgres migration

**Files:**
- Modify: `new-project/models.py` (the `Patient` class, lines 12-19)
- Create: `new-project/scripts/migrate_add_patient_fields.py`
- Test: `new-project/tests/test_patient_model_fields.py`

**Interfaces:**
- Produces: `Patient` gains these optional columns (all `Optional[str]`, default `None`): `national_id` (indexed), `place_of_birth`, `marital_status`, `occupation`, `religion`, `nationality`, `blood_type`, `allergies`, `known_conditions`. Later tasks (schemas, OCR) rely on exactly these names.

- [ ] **Step 1: Write the failing test**

Create `new-project/tests/test_patient_model_fields.py`:

```python
from datetime import date
from sqlmodel import Session
from models import Patient


def test_patient_has_new_optional_fields(session: Session):
    patient = Patient(
        name="Budi Santoso",
        date_of_birth=date(1990, 5, 15),
        gender="male",
        national_id="3201234567890001",
        place_of_birth="Jakarta",
        marital_status="married",
        occupation="Teacher",
        religion="Islam",
        nationality="Indonesian",
        blood_type="O+",
        allergies="Penicillin",
        known_conditions="Hypertension",
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    assert patient.id is not None
    assert patient.national_id == "3201234567890001"
    assert patient.blood_type == "O+"


def test_patient_new_fields_default_to_none(session: Session):
    patient = Patient(name="Siti", date_of_birth=date(1985, 3, 20), gender="female")
    session.add(patient)
    session.commit()
    session.refresh(patient)
    assert patient.national_id is None
    assert patient.allergies is None
    assert patient.nationality is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd new-project && uv run pytest tests/test_patient_model_fields.py -v`
Expected: FAIL — `TypeError` / unexpected keyword argument `national_id` (column does not exist yet).

- [ ] **Step 3: Add the columns to the model**

In `new-project/models.py`, replace the `Patient` class body so it reads:

```python
class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    national_id: Optional[str] = Field(default=None, index=True)
    place_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    religion: Optional[str] = None
    nationality: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    known_conditions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd new-project && uv run pytest tests/test_patient_model_fields.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Create the Postgres migration script**

Create `new-project/scripts/migrate_add_patient_fields.py` (run once against the live Neon DB; idempotent via `IF NOT EXISTS`):

```python
"""Add OCR-related columns to the patient table on the live Postgres DB.

Run once after deploying the model change:
    cd new-project && uv run python -m scripts.migrate_add_patient_fields

SQLModel.create_all() does NOT alter existing tables, so production needs this.
Tests use a fresh SQLite schema and do not run it.
"""
from sqlalchemy import text
from database import engine

COLUMNS = [
    "national_id VARCHAR",
    "place_of_birth VARCHAR",
    "marital_status VARCHAR",
    "occupation VARCHAR",
    "religion VARCHAR",
    "nationality VARCHAR",
    "blood_type VARCHAR",
    "allergies VARCHAR",
    "known_conditions VARCHAR",
]


def main() -> None:
    with engine.begin() as conn:
        for col in COLUMNS:
            conn.execute(text(f"ALTER TABLE patient ADD COLUMN IF NOT EXISTS {col}"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_patient_national_id ON patient (national_id)")
        )
    print("Migration complete: patient table now has OCR columns.")


if __name__ == "__main__":
    main()
```

Also create an empty `new-project/scripts/__init__.py` so `uv run python -m scripts.migrate_add_patient_fields` resolves.

- [ ] **Step 6: Commit**

```bash
git add new-project/models.py new-project/scripts/ new-project/tests/test_patient_model_fields.py
git commit -m "feat(patients): add OCR-related optional columns to Patient model + migration"
```

---

### Task 2: Extend the Pydantic schemas with the new fields and validators

**Files:**
- Modify: `new-project/schemas.py` (`PatientCreate` lines 11-51, `PatientRead` lines 54-62, `PatientUpdate` lines 65-107; add new constants near line 7)
- Test: `new-project/tests/test_patient_schema_fields.py`

**Interfaces:**
- Consumes: the `Patient` columns from Task 1.
- Produces: `PatientCreate` / `PatientRead` / `PatientUpdate` accept and expose all nine new fields. `PatientCreate.national_id` is validated as 16 digits when present; `marital_status` and `blood_type` are normalized/validated against fixed sets; blank optional strings normalize to `None`.

- [ ] **Step 1: Write the failing test**

Create `new-project/tests/test_patient_schema_fields.py`:

```python
import pytest
from datetime import date
from schemas import PatientCreate


def test_create_accepts_all_new_fields():
    p = PatientCreate(
        name="Budi",
        date_of_birth=date(1990, 5, 15),
        gender="male",
        national_id="3201234567890001",
        place_of_birth="Jakarta",
        marital_status="Married",
        occupation="Teacher",
        religion="Islam",
        nationality="Indonesian",
        blood_type="o+",
        allergies="Penicillin",
        known_conditions="Hypertension",
    )
    assert p.marital_status == "married"   # normalized to lowercase
    assert p.blood_type == "O+"            # normalized to uppercase
    assert p.national_id == "3201234567890001"


def test_national_id_must_be_16_digits():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", national_id="123")


def test_invalid_marital_status_rejected():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", marital_status="single-ish")


def test_invalid_blood_type_rejected():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", blood_type="Z+")


def test_blank_optional_strings_become_none():
    p = PatientCreate(
        name="X", date_of_birth=date(2000, 1, 1), gender="male",
        occupation="   ", allergies="", national_id=None,
    )
    assert p.occupation is None
    assert p.allergies is None
    assert p.national_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd new-project && uv run pytest tests/test_patient_schema_fields.py -v`
Expected: FAIL — `PatientCreate` has no field `national_id` (Pydantic raises on unexpected kwargs only if extra=forbid; otherwise the assertions on normalized values fail). Either way: FAIL.

- [ ] **Step 3: Add constants and fields to the schemas**

In `new-project/schemas.py`, add these constants right after the existing `PHONE_RE` line (line 8):

```python
VALID_MARITAL = {"single", "married", "divorced", "widowed"}
VALID_BLOOD = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "A", "B", "AB", "O"}
NIK_RE = re.compile(r"^\d{16}$")
```

Add these reusable validator helpers as module-level functions (place them after the constants):

```python
def _normalize_optional_str(v):
    if v is None:
        return None
    v = v.strip()
    return v or None


def _validate_national_id(v):
    v = _normalize_optional_str(v)
    if v is not None and not NIK_RE.match(v):
        raise ValueError("national ID must be 16 digits")
    return v


def _validate_marital_status(v):
    v = _normalize_optional_str(v)
    if v is None:
        return None
    v = v.lower()
    if v not in VALID_MARITAL:
        raise ValueError(f"must be one of: {', '.join(sorted(VALID_MARITAL))}")
    return v


def _validate_blood_type(v):
    v = _normalize_optional_str(v)
    if v is None:
        return None
    v = v.upper()
    if v not in VALID_BLOOD:
        raise ValueError(f"must be one of: {', '.join(sorted(VALID_BLOOD))}")
    return v
```

In `PatientCreate`, add the new fields after `phone` (line 15) and the validators after the existing `phone_format` validator (line 51):

```python
    national_id: Optional[str] = None
    place_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    religion: Optional[str] = None
    nationality: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    known_conditions: Optional[str] = None

    @field_validator('national_id')
    @classmethod
    def national_id_valid(cls, v):
        return _validate_national_id(v)

    @field_validator('marital_status')
    @classmethod
    def marital_status_valid(cls, v):
        return _validate_marital_status(v)

    @field_validator('blood_type')
    @classmethod
    def blood_type_valid(cls, v):
        return _validate_blood_type(v)

    @field_validator('place_of_birth', 'occupation', 'religion', 'nationality', 'allergies', 'known_conditions')
    @classmethod
    def optional_strings_clean(cls, v):
        return _normalize_optional_str(v)
```

In `PatientRead`, add the nine fields after `phone` (line 61) so they are serialized back to the client:

```python
    national_id: Optional[str] = None
    place_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    religion: Optional[str] = None
    nationality: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    known_conditions: Optional[str] = None
```

In `PatientUpdate`, add the same nine optional fields after `phone` (line 69) and reuse the same validators:

```python
    national_id: Optional[str] = None
    place_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    religion: Optional[str] = None
    nationality: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    known_conditions: Optional[str] = None

    @field_validator('national_id')
    @classmethod
    def national_id_valid(cls, v):
        return _validate_national_id(v)

    @field_validator('marital_status')
    @classmethod
    def marital_status_valid(cls, v):
        return _validate_marital_status(v)

    @field_validator('blood_type')
    @classmethod
    def blood_type_valid(cls, v):
        return _validate_blood_type(v)

    @field_validator('place_of_birth', 'occupation', 'religion', 'nationality', 'allergies', 'known_conditions')
    @classmethod
    def optional_strings_clean(cls, v):
        return _normalize_optional_str(v)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd new-project && uv run pytest tests/test_patient_schema_fields.py tests/test_patients.py -v`
Expected: PASS (new schema tests pass; existing patient endpoint tests still pass because new fields are optional).

- [ ] **Step 5: Add an endpoint round-trip test for a new field**

Append to `new-project/tests/test_patients.py`:

```python
def test_create_patient_with_ocr_fields(admin_client):
    response = admin_client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "national_id": "3201234567890001",
        "blood_type": "o+",
        "marital_status": "Married",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["national_id"] == "3201234567890001"
    assert data["blood_type"] == "O+"
    assert data["marital_status"] == "married"


def test_create_patient_rejects_bad_national_id(admin_client):
    response = admin_client.post("/api/patients", json={
        "name": "X", "date_of_birth": "2000-01-01", "gender": "male",
        "national_id": "not-16-digits",
    })
    assert response.status_code == 422
```

Run: `cd new-project && uv run pytest tests/test_patients.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add new-project/schemas.py new-project/tests/test_patient_schema_fields.py new-project/tests/test_patients.py
git commit -m "feat(patients): extend schemas with OCR fields and validators"
```

---

### Task 3: Build the OCR service wrapper around the Anthropic SDK

**Files:**
- Modify: `new-project/pyproject.toml` (add `anthropic` dependency)
- Create: `new-project/ocr_service.py`
- Test: `new-project/tests/test_ocr_service.py`

**Interfaces:**
- Produces:
  - `ocr_service.ocr_available() -> bool` — `True` iff `ANTHROPIC_API_KEY` is set and non-empty.
  - `ocr_service.extract_patient_fields(image_bytes: bytes, media_type: str) -> dict` — returns `{"fields": {<field>: str|None}, "confidence": {<field>: float}}`. Raises `ocr_service.OCRError` on any SDK/parse failure.
  - `ocr_service.OCRError` — exception class.
  - `ocr_service.PATIENT_FIELDS: list[str]` — the field names the model is asked to fill.
  - Internal `ocr_service._get_client()` returns an `anthropic.Anthropic()` — tests patch this.

- [ ] **Step 1: Add the dependency**

In `new-project/pyproject.toml`, add `"anthropic>=0.49.0",` to the `dependencies` list (keep alphabetical-ish ordering; placing it first is fine). Then install:

Run: `cd new-project && (uv add anthropic 2>/dev/null || pip install "anthropic>=0.49.0")`
Expected: `anthropic` installs into the active environment.

- [ ] **Step 2: Write the failing test**

Create `new-project/tests/test_ocr_service.py`:

```python
import json
from unittest.mock import patch, MagicMock
import pytest
import ocr_service


def _fake_response(payload: dict):
    """Build a fake Anthropic Message whose first content block is JSON text."""
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_ocr_available_reflects_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert ocr_service.ocr_available() is True
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ocr_service.ocr_available() is False


def test_extract_returns_fields_and_confidence():
    payload = {
        "fields": {f: None for f in ocr_service.PATIENT_FIELDS},
        "confidence": {f: 0.0 for f in ocr_service.PATIENT_FIELDS},
    }
    payload["fields"]["name"] = "Budi Santoso"
    payload["confidence"]["name"] = 0.97

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response(payload)

    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        result = ocr_service.extract_patient_fields(b"\xff\xd8fakejpeg", "image/jpeg")

    assert result["fields"]["name"] == "Budi Santoso"
    assert result["confidence"]["name"] == 0.97
    # the image was sent as a base64 block
    sent = fake_client.messages.create.call_args.kwargs
    assert sent["model"]  # a model id was passed
    image_block = sent["messages"][0]["content"][0]
    assert image_block["type"] == "image"
    assert image_block["source"]["media_type"] == "image/jpeg"


def test_extract_raises_ocrerror_on_sdk_failure():
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("boom")
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRError):
            ocr_service.extract_patient_fields(b"x", "image/png")


def test_extract_raises_ocrerror_on_bad_json():
    block = MagicMock()
    block.type = "text"
    block.text = "this is not json"
    resp = MagicMock()
    resp.content = [block]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = resp
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRError):
            ocr_service.extract_patient_fields(b"x", "image/png")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd new-project && uv run pytest tests/test_ocr_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ocr_service'`.

- [ ] **Step 4: Write the OCR service**

Create `new-project/ocr_service.py`:

```python
"""Claude-vision wrapper that reads a patient-form image into structured fields.

Does no database work. Returns a dict of extracted field values plus a per-field
confidence score. Designed to be patched in tests (`_get_client`) so CI makes no
real API calls.
"""
import os
import re
import json
import base64
from typing import Optional

import anthropic

# Default to the most capable model; override with OCR_MODEL (e.g. claude-sonnet-4-6
# for lower cost). Per the claude-api guidance, default to Opus unless explicitly changed.
DEFAULT_MODEL = "claude-opus-4-8"

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


def ocr_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _model() -> str:
    return os.environ.get("OCR_MODEL", DEFAULT_MODEL)


def _extract_json(text: str) -> dict:
    match = _JSON_RE.search(text)
    if not match:
        raise OCRError("no JSON object found in model response")
    return json.loads(match.group(0))


def _empty(value: dict) -> dict:
    return {f: value for f in PATIENT_FIELDS}


def extract_patient_fields(image_bytes: bytes, media_type: str) -> dict:
    """Send the image to Claude vision and return {fields, confidence}."""
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    try:
        client = _get_client()
        response = client.messages.create(
            model=_model(),
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
        )
    except Exception as exc:  # SDK/network error
        raise OCRError(f"vision request failed: {exc}") from exc

    text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd new-project && uv run pytest tests/test_ocr_service.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add new-project/pyproject.toml new-project/uv.lock new-project/ocr_service.py new-project/tests/test_ocr_service.py
git commit -m "feat(ocr): add Claude-vision service that extracts patient fields from an image"
```

---

### Task 4: Add the `/api/ocr` endpoints and register the router

**Files:**
- Create: `new-project/routers/ocr.py`
- Modify: `new-project/main.py` (import + `include_router`, lines 9 and 42-44)
- Test: `new-project/tests/test_ocr_router.py`

**Interfaces:**
- Consumes: `ocr_service.ocr_available`, `ocr_service.extract_patient_fields`, `ocr_service.OCRError`, `deps.get_admin`.
- Produces:
  - `GET /api/ocr/status` (admin-only) → `{"available": bool}`.
  - `POST /api/ocr/extract` (admin-only, multipart field `file`) → `{"fields": {...}, "confidence": {...}}`. 503 if OCR not configured, 400 on bad/empty/unsupported image, 502 on extraction failure.

- [ ] **Step 1: Write the failing test**

Create `new-project/tests/test_ocr_router.py`:

```python
import io
from unittest.mock import patch
import routers.ocr as ocr_router


def _png_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"0" * 32


def test_extract_requires_auth(client):
    resp = client.post("/api/ocr/extract", files={"file": ("f.png", _png_bytes(), "image/png")})
    assert resp.status_code == 401


def test_status_reports_availability(admin_client):
    with patch.object(ocr_router.ocr_service, "ocr_available", return_value=True):
        resp = admin_client.get("/api/ocr/status")
    assert resp.status_code == 200
    assert resp.json() == {"available": True}


def test_extract_returns_fields(admin_client):
    fake_result = {
        "fields": {"name": "Budi"}, "confidence": {"name": 0.9},
    }
    with patch.object(ocr_router.ocr_service, "ocr_available", return_value=True), \
         patch.object(ocr_router.ocr_service, "extract_patient_fields", return_value=fake_result):
        resp = admin_client.post(
            "/api/ocr/extract",
            files={"file": ("form.png", _png_bytes(), "image/png")},
        )
    assert resp.status_code == 200
    assert resp.json()["fields"]["name"] == "Budi"


def test_extract_503_when_not_configured(admin_client):
    with patch.object(ocr_router.ocr_service, "ocr_available", return_value=False):
        resp = admin_client.post(
            "/api/ocr/extract",
            files={"file": ("form.png", _png_bytes(), "image/png")},
        )
    assert resp.status_code == 503


def test_extract_400_on_unsupported_type(admin_client):
    with patch.object(ocr_router.ocr_service, "ocr_available", return_value=True):
        resp = admin_client.post(
            "/api/ocr/extract",
            files={"file": ("form.txt", b"hello", "text/plain")},
        )
    assert resp.status_code == 400


def test_extract_502_on_ocr_error(admin_client):
    from ocr_service import OCRError
    with patch.object(ocr_router.ocr_service, "ocr_available", return_value=True), \
         patch.object(ocr_router.ocr_service, "extract_patient_fields", side_effect=OCRError("boom")):
        resp = admin_client.post(
            "/api/ocr/extract",
            files={"file": ("form.png", _png_bytes(), "image/png")},
        )
    assert resp.status_code == 502
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd new-project && uv run pytest tests/test_ocr_router.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routers.ocr'`.

- [ ] **Step 3: Write the router**

Create `new-project/routers/ocr.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from deps import get_admin
from models import AdminUser
import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/status")
def ocr_status(_: AdminUser = Depends(get_admin)):
    return {"available": ocr_service.ocr_available()}


@router.post("/extract")
async def extract(file: UploadFile = File(...), _: AdminUser = Depends(get_admin)):
    if not ocr_service.ocr_available():
        raise HTTPException(status_code=503, detail="OCR is not configured")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        return ocr_service.extract_patient_fields(data, file.content_type)
    except ocr_service.OCRError:
        raise HTTPException(status_code=502, detail="OCR extraction failed")
```

- [ ] **Step 4: Register the router in `main.py`**

In `new-project/main.py`, change the import on line 9 from:

```python
from routers import patients, visits, auth as auth_router
```
to:
```python
from routers import patients, visits, auth as auth_router, ocr as ocr_router
```

And after line 44 (`app.include_router(auth_router.router)`), add:

```python
app.include_router(ocr_router.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd new-project && uv run pytest tests/test_ocr_router.py -v`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add new-project/routers/ocr.py new-project/main.py new-project/tests/test_ocr_router.py
git commit -m "feat(ocr): add admin-only /api/ocr/extract and /api/ocr/status endpoints"
```

---

### Task 5: Add the new fields to the React form and types

**Files:**
- Modify: `new-project/frontend/src/api/types.ts` (`Patient` lines 3-10, `PatientCreate` lines 11-16)
- Modify: `new-project/frontend/src/components/PatientForm.tsx` (whole file)
- Test: `new-project/frontend/src/components/PatientForm.test.tsx` (create)

**Interfaces:**
- Consumes: nothing from prior frontend tasks.
- Produces: `PatientCreate` TS type includes the nine optional string fields; `PatientForm` renders inputs for them, seeds them from `initial`, and includes them in the `onSubmit` payload. `PatientForm` accepts an optional `lowConfidence?: Record<string, number>` prop and adds a `field-low-confidence` CSS class to fields whose confidence < 0.6 (used by Task 6).

- [ ] **Step 1: Write the failing test**

Create `new-project/frontend/src/components/PatientForm.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import PatientForm from './PatientForm'

function renderForm(props = {}) {
  const onSubmit = vi.fn()
  render(
    <MemoryRouter>
      <PatientForm
        title="Register Patient"
        submitLabel="Create"
        pending={false}
        fieldErrors={{}}
        cancelTo="/patients"
        onSubmit={onSubmit}
        {...props}
      />
    </MemoryRouter>,
  )
  return { onSubmit }
}

describe('PatientForm new fields', () => {
  it('renders the OCR fields', () => {
    renderForm()
    expect(screen.getByLabelText(/National ID/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Blood Type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Occupation/i)).toBeInTheDocument()
  })

  it('seeds fields from initial and submits them', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderForm({
      initial: {
        name: 'Budi',
        date_of_birth: '1990-05-15',
        gender: 'male',
        national_id: '3201234567890001',
        occupation: 'Teacher',
      },
    })
    await user.click(screen.getByRole('button', { name: 'Create' }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Budi',
        national_id: '3201234567890001',
        occupation: 'Teacher',
      }),
    )
  })

  it('marks low-confidence fields', () => {
    renderForm({
      initial: { name: 'Budi', date_of_birth: '1990-05-15', gender: 'male', occupation: 'Teacher' },
      lowConfidence: { occupation: 0.3 },
    })
    expect(screen.getByLabelText(/Occupation/i).closest('.form-group')).toHaveClass('field-low-confidence')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd new-project/frontend && npm test -- PatientForm`
Expected: FAIL — the OCR fields aren't rendered / `lowConfidence` prop doesn't exist.

- [ ] **Step 3: Extend the TS types**

In `new-project/frontend/src/api/types.ts`, replace the `Patient` and `PatientCreate` interfaces (lines 3-16) with:

```typescript
export interface Patient {
  id: number
  name: string
  date_of_birth: string // ISO date
  gender: Gender
  phone: string | null
  national_id: string | null
  place_of_birth: string | null
  marital_status: string | null
  occupation: string | null
  religion: string | null
  nationality: string | null
  blood_type: string | null
  allergies: string | null
  known_conditions: string | null
  created_at: string
}
export interface PatientCreate {
  name: string
  date_of_birth: string
  gender: Gender
  phone?: string | null
  national_id?: string | null
  place_of_birth?: string | null
  marital_status?: string | null
  occupation?: string | null
  religion?: string | null
  nationality?: string | null
  blood_type?: string | null
  allergies?: string | null
  known_conditions?: string | null
}
```

- [ ] **Step 4: Rewrite `PatientForm.tsx` to render and submit the new fields**

Replace the entire contents of `new-project/frontend/src/components/PatientForm.tsx` with:

```tsx
import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import FormField from './FormField'
import type { PatientCreate, Gender } from '../api/types'

interface Props {
  title: string
  initial?: Partial<PatientCreate>
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  cancelTo: string
  onSubmit: (data: PatientCreate) => void
  lowConfidence?: Record<string, number>
}

const LOW_CONF = 0.6

export default function PatientForm({
  title, initial, submitLabel, pending, fieldErrors, cancelTo, onSubmit, lowConfidence,
}: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [dob, setDob] = useState(initial?.date_of_birth ?? '')
  const [gender, setGender] = useState<Gender>((initial?.gender as Gender) ?? 'male')
  const [phone, setPhone] = useState(initial?.phone ?? '')
  const [nationalId, setNationalId] = useState(initial?.national_id ?? '')
  const [placeOfBirth, setPlaceOfBirth] = useState(initial?.place_of_birth ?? '')
  const [maritalStatus, setMaritalStatus] = useState(initial?.marital_status ?? '')
  const [occupation, setOccupation] = useState(initial?.occupation ?? '')
  const [religion, setReligion] = useState(initial?.religion ?? '')
  const [nationality, setNationality] = useState(initial?.nationality ?? '')
  const [bloodType, setBloodType] = useState(initial?.blood_type ?? '')
  const [allergies, setAllergies] = useState(initial?.allergies ?? '')
  const [knownConditions, setKnownConditions] = useState(initial?.known_conditions ?? '')

  function lowConf(field: string): boolean {
    const c = lowConfidence?.[field]
    return c !== undefined && c < LOW_CONF
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    onSubmit({
      name,
      date_of_birth: dob,
      gender,
      phone: phone || null,
      national_id: nationalId || null,
      place_of_birth: placeOfBirth || null,
      marital_status: maritalStatus || null,
      occupation: occupation || null,
      religion: religion || null,
      nationality: nationality || null,
      blood_type: bloodType || null,
      allergies: allergies || null,
      known_conditions: knownConditions || null,
    })
  }

  return (
    <form className="card form-card" onSubmit={submit}>
      <h2>{title}</h2>
      <FormField label="Name" name="name" required error={fieldErrors.name} className={lowConf('name') ? 'field-low-confidence' : undefined}>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" />
      </FormField>
      <FormField label="Date of Birth" name="date_of_birth" required error={fieldErrors.date_of_birth} className={lowConf('date_of_birth') ? 'field-low-confidence' : undefined}>
        <input id="date_of_birth" type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
      </FormField>
      <FormField label="Gender" name="gender" required error={fieldErrors.gender} className={lowConf('gender') ? 'field-low-confidence' : undefined}>
        <select id="gender" value={gender} onChange={(e) => setGender(e.target.value as Gender)}>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </FormField>
      <FormField label="Phone" name="phone" optional error={fieldErrors.phone} className={lowConf('phone') ? 'field-low-confidence' : undefined}>
        <input id="phone" value={phone ?? ''} onChange={(e) => setPhone(e.target.value)} placeholder="e.g. 08123456789" />
      </FormField>
      <FormField label="National ID (NIK)" name="national_id" optional error={fieldErrors.national_id} className={lowConf('national_id') ? 'field-low-confidence' : undefined}>
        <input id="national_id" value={nationalId ?? ''} onChange={(e) => setNationalId(e.target.value)} placeholder="16-digit NIK" />
      </FormField>
      <FormField label="Place of Birth" name="place_of_birth" optional error={fieldErrors.place_of_birth} className={lowConf('place_of_birth') ? 'field-low-confidence' : undefined}>
        <input id="place_of_birth" value={placeOfBirth ?? ''} onChange={(e) => setPlaceOfBirth(e.target.value)} />
      </FormField>
      <FormField label="Marital Status" name="marital_status" optional error={fieldErrors.marital_status} className={lowConf('marital_status') ? 'field-low-confidence' : undefined}>
        <select id="marital_status" value={maritalStatus ?? ''} onChange={(e) => setMaritalStatus(e.target.value)}>
          <option value="">—</option>
          <option value="single">Single</option>
          <option value="married">Married</option>
          <option value="divorced">Divorced</option>
          <option value="widowed">Widowed</option>
        </select>
      </FormField>
      <FormField label="Occupation" name="occupation" optional error={fieldErrors.occupation} className={lowConf('occupation') ? 'field-low-confidence' : undefined}>
        <input id="occupation" value={occupation ?? ''} onChange={(e) => setOccupation(e.target.value)} />
      </FormField>
      <FormField label="Religion" name="religion" optional error={fieldErrors.religion} className={lowConf('religion') ? 'field-low-confidence' : undefined}>
        <input id="religion" value={religion ?? ''} onChange={(e) => setReligion(e.target.value)} />
      </FormField>
      <FormField label="Nationality" name="nationality" optional error={fieldErrors.nationality} className={lowConf('nationality') ? 'field-low-confidence' : undefined}>
        <input id="nationality" value={nationality ?? ''} onChange={(e) => setNationality(e.target.value)} placeholder="e.g. Indonesian" />
      </FormField>
      <FormField label="Blood Type" name="blood_type" optional error={fieldErrors.blood_type} className={lowConf('blood_type') ? 'field-low-confidence' : undefined}>
        <select id="blood_type" value={bloodType ?? ''} onChange={(e) => setBloodType(e.target.value)}>
          <option value="">—</option>
          {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
      </FormField>
      <FormField label="Allergies" name="allergies" optional error={fieldErrors.allergies} className={lowConf('allergies') ? 'field-low-confidence' : undefined}>
        <input id="allergies" value={allergies ?? ''} onChange={(e) => setAllergies(e.target.value)} />
      </FormField>
      <FormField label="Known Conditions" name="known_conditions" optional error={fieldErrors.known_conditions} className={lowConf('known_conditions') ? 'field-low-confidence' : undefined}>
        <input id="known_conditions" value={knownConditions ?? ''} onChange={(e) => setKnownConditions(e.target.value)} />
      </FormField>
      <div className="modal-actions">
        <button type="submit" className="btn btn-primary" disabled={pending}>{submitLabel}</button>
        <Link to={cancelTo} className="btn btn-secondary">Cancel</Link>
      </div>
    </form>
  )
}
```

- [ ] **Step 5: Add `className` support to `FormField`**

`new-project/frontend/src/components/FormField.tsx` renders its wrapper with class `form-group`. Add an optional `className?: string` prop and append it to that wrapper so `field-low-confidence` is applied. Replace the file with:

```tsx
import { ReactNode } from 'react'
interface Props {
  label: string
  name: string
  error?: string
  required?: boolean
  optional?: boolean
  className?: string
  children: ReactNode
}
export default function FormField({ label, name, error, required, optional, className, children }: Props) {
  return (
    <div className={`form-group${className ? ` ${className}` : ''}`}>
      <label htmlFor={name}>
        {label} {required && <span className="required">*</span>}
        {optional && <span className="optional">(optional)</span>}
      </label>
      {children}
      {error && <span className="form-error">{error}</span>}
    </div>
  )
}
```

The base class stays `form-group` (the test calls `.closest('.form-group')`); the conditional `field-low-confidence` is appended.

Add a style rule to `new-project/frontend/src/styles.css`:

```css
.field-low-confidence input,
.field-low-confidence select {
  border-color: #e0a106;
  background: #fff8e1;
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd new-project/frontend && npm test -- PatientForm`
Expected: PASS (3 passed).

- [ ] **Step 7: Type-check and run the full frontend suite**

Run: `cd new-project/frontend && npm run build && npm test`
Expected: build succeeds (TS types align), all tests pass. If `PatientForm` is used in `PatientEditPage`/`PatientNewPage` without the new optional props, that's fine — they're optional.

- [ ] **Step 8: Commit**

```bash
git add new-project/frontend/src/api/types.ts new-project/frontend/src/components/PatientForm.tsx new-project/frontend/src/components/FormField.tsx new-project/frontend/src/components/PatientForm.test.tsx new-project/frontend/src/styles.css
git commit -m "feat(frontend): render OCR patient fields and low-confidence highlighting"
```

---

### Task 6: Wire the OCR upload button into the registration page

**Files:**
- Create: `new-project/frontend/src/api/ocr.ts`
- Modify: `new-project/frontend/src/pages/PatientNewPage.tsx` (whole file)
- Test: `new-project/frontend/src/pages/PatientNewPage.test.tsx` (create)

**Interfaces:**
- Consumes: `PatientForm` (`initial`, `lowConfidence` props from Task 5); `/api/ocr/status` and `/api/ocr/extract` from Task 4; `useCreatePatient` from `api/patients`.
- Produces: an "Upload form" file input on the registration page that calls `/api/ocr/extract`, then re-renders `PatientForm` pre-filled with the extracted fields and low-confidence highlighting. The button is hidden when `/api/ocr/status` reports `available: false`.

- [ ] **Step 1: Write the API helper**

Create `new-project/frontend/src/api/ocr.ts`:

```typescript
import { ApiError } from './client'
import type { PatientCreate } from './types'

export interface OcrResult {
  fields: Partial<PatientCreate>
  confidence: Record<string, number>
}

export async function getOcrStatus(): Promise<boolean> {
  const res = await fetch('/api/ocr/status', { credentials: 'include' })
  if (!res.ok) return false
  const body = await res.json()
  return Boolean(body.available)
}

export async function extractPatientForm(file: File): Promise<OcrResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/ocr/extract', {
    method: 'POST',
    credentials: 'include',
    body: form, // do NOT set Content-Type; the browser sets the multipart boundary
  })
  let parsed: unknown = null
  try {
    parsed = await res.json()
  } catch {
    parsed = null
  }
  if (!res.ok) throw new ApiError(res.status, parsed)
  return parsed as OcrResult
}
```

- [ ] **Step 2: Write the failing test**

Create `new-project/frontend/src/pages/PatientNewPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PatientNewPage from './PatientNewPage'

const mockFetch = vi.fn()

beforeEach(() => {
  mockFetch.mockReset()
  vi.stubGlobal('fetch', mockFetch)
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PatientNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) } as Response)
}

describe('PatientNewPage OCR', () => {
  it('shows the upload control when OCR is available', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: true })
      return jsonResponse({})
    })
    renderPage()
    expect(await screen.findByLabelText(/Upload form/i)).toBeInTheDocument()
  })

  it('hides the upload control when OCR is unavailable', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: false })
      return jsonResponse({})
    })
    renderPage()
    // status resolves, then the control is absent
    await waitFor(() => expect(mockFetch).toHaveBeenCalled())
    expect(screen.queryByLabelText(/Upload form/i)).not.toBeInTheDocument()
  })

  it('pre-fills the form from an extracted result', async () => {
    const user = userEvent.setup()
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: true })
      if (url.includes('/api/ocr/extract')) {
        return jsonResponse({
          fields: { name: 'Budi Santoso', occupation: 'Teacher' },
          confidence: { name: 0.95, occupation: 0.3 },
        })
      }
      return jsonResponse({})
    })
    renderPage()
    const input = await screen.findByLabelText(/Upload form/i)
    const file = new File([new Uint8Array([1, 2, 3])], 'form.png', { type: 'image/png' })
    await user.upload(input, file)
    await waitFor(() =>
      expect((screen.getByLabelText(/^Name/i) as HTMLInputElement).value).toBe('Budi Santoso'),
    )
    expect((screen.getByLabelText(/Occupation/i) as HTMLInputElement).value).toBe('Teacher')
  })
})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd new-project/frontend && npm test -- PatientNewPage`
Expected: FAIL — there is no "Upload form" control yet.

- [ ] **Step 4: Rewrite `PatientNewPage.tsx`**

Replace the entire contents of `new-project/frontend/src/pages/PatientNewPage.tsx` with:

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreatePatient } from '../api/patients'
import { ApiError } from '../api/client'
import { getOcrStatus, extractPatientForm } from '../api/ocr'
import PatientForm from '../components/PatientForm'
import ErrorBanner from '../components/ErrorBanner'
import type { PatientCreate } from '../api/types'

export default function PatientNewPage() {
  const create = useCreatePatient()
  const navigate = useNavigate()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<unknown>(null)

  const [ocrAvailable, setOcrAvailable] = useState(false)
  const [ocrPending, setOcrPending] = useState(false)
  const [initial, setInitial] = useState<Partial<PatientCreate> | undefined>(undefined)
  const [confidence, setConfidence] = useState<Record<string, number> | undefined>(undefined)
  // Bump to force PatientForm to remount with new `initial` after an extraction.
  const [formKey, setFormKey] = useState(0)

  useEffect(() => {
    getOcrStatus().then(setOcrAvailable).catch(() => setOcrAvailable(false))
  }, [])

  async function onUpload(file: File) {
    setOcrPending(true)
    setError(null)
    try {
      const result = await extractPatientForm(file)
      setInitial(result.fields)
      setConfidence(result.confidence)
      setFormKey((k) => k + 1)
    } catch (e) {
      setError(e)
    } finally {
      setOcrPending(false)
    }
  }

  return (
    <section>
      <ErrorBanner error={error} />
      {ocrAvailable && (
        <div className="card form-card ocr-upload">
          <label htmlFor="ocr-upload">Upload form (scan or photo) to auto-fill</label>
          <input
            id="ocr-upload"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={ocrPending}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onUpload(f)
            }}
          />
          {ocrPending && <span className="ocr-status">Reading form…</span>}
        </div>
      )}
      <PatientForm
        key={formKey}
        title="Register Patient"
        submitLabel="Create"
        pending={create.isPending}
        fieldErrors={fieldErrors}
        cancelTo="/patients"
        initial={initial}
        lowConfidence={confidence}
        onSubmit={async (data) => {
          setFieldErrors({}); setError(null)
          try {
            const p = await create.mutateAsync(data)
            navigate(`/patients/${p.id}`)
          } catch (e) {
            if (e instanceof ApiError && e.status === 422) setFieldErrors(e.fieldErrors())
            else setError(e)
          }
        }}
      />
    </section>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd new-project/frontend && npm test -- PatientNewPage`
Expected: PASS (3 passed).

- [ ] **Step 6: Run the full frontend + backend suites**

Run: `cd new-project/frontend && npm run build && npm test`
Expected: build + all frontend tests pass.

Run: `cd new-project && uv run pytest`
Expected: all backend tests pass.

- [ ] **Step 7: Commit**

```bash
git add new-project/frontend/src/api/ocr.ts new-project/frontend/src/pages/PatientNewPage.tsx new-project/frontend/src/pages/PatientNewPage.test.tsx
git commit -m "feat(frontend): add OCR upload to registration page with form pre-fill"
```

---

### Task 7: Document the feature and the deploy step

**Files:**
- Modify: `new-project/README.md` (Required environment variables table; add an OCR + migration section)

**Interfaces:** none (docs only).

- [ ] **Step 1: Add `ANTHROPIC_API_KEY` to the env var table**

In `new-project/README.md`, add a row to the "Required environment variables" table:

```
| `ANTHROPIC_API_KEY` | Enables OCR form-scanning (Claude vision). If unset, the OCR upload button is hidden and the form works manually. |
| `OCR_MODEL` | Optional. Vision model id (default `claude-opus-4-8`; `claude-sonnet-4-6` is a lower-cost option). |
```

- [ ] **Step 2: Add an OCR + migration section**

Append to `new-project/README.md`:

```markdown
## OCR form scanning

Admins can upload a photo/scan of a paper patient form on the registration
page; Claude vision extracts the fields and pre-fills the form for review
before saving. Set `ANTHROPIC_API_KEY` to enable it; without it the feature is
hidden and registration works manually.

## Database migration (new patient columns)

The OCR feature adds optional columns to the `patient` table. `create_all` does
not alter existing tables, so run this once against the live Postgres DB after
deploying:

\`\`\`bash
cd new-project && uv run python -m scripts.migrate_add_patient_fields
\`\`\`
```

- [ ] **Step 3: Commit**

```bash
git add new-project/README.md
git commit -m "docs: document OCR form scanning and the patient-columns migration"
```

---

## Self-Review

**Spec coverage:**
- Engine = Claude vision → Task 3 (`ocr_service.py`). ✅
- Nine new columns → Task 1 (model) + Task 2 (schemas) + Task 5 (TS types/form). ✅
- Postgres migration (not `create_all`) → Task 1 Step 5. ✅
- `POST /ocr/extract` admin-only, no DB write → Task 4. ✅
- Capability flag / button hidden without key → `/api/ocr/status` (Task 4) + `getOcrStatus` (Task 6). ✅
- Frontend pre-fill + low-confidence highlight + staff-review-then-save through existing `POST /patients` → Task 5 + Task 6. ✅
- No image storage → endpoint reads bytes in-memory, never persists (Task 4). ✅
- Error handling: 400 bad image, 502 API failure, 503 missing key → Task 4 tests. ✅
- Testing: validator units (Task 2), mocked-client OCR service (Task 3), mocked endpoint (Task 4), frontend component + page tests (Tasks 5-6). ✅

**Type consistency:** `PATIENT_FIELDS` field names match the `Patient` columns and the TS `PatientCreate` keys exactly (`national_id`, `place_of_birth`, `marital_status`, `occupation`, `religion`, `nationality`, `blood_type`, `allergies`, `known_conditions`). `ocr_service.extract_patient_fields` returns `{fields, confidence}`; the router returns it verbatim; `OcrResult` in `api/ocr.ts` matches that shape; `PatientNewPage` passes `result.fields` → `initial` and `result.confidence` → `lowConfidence`, both accepted by `PatientForm` (Task 5). Route prefix `/api/ocr` is consistent across router, tests, and frontend.

**Placeholder scan:** No TBD/TODO; every code step has complete code. The only "adapt to the actual file" note is Task 5 Step 5 (`FormField` className) because that file wasn't quoted in full — the required change (add `className` prop, keep base `field` class) is stated explicitly.

**Verified against the codebase:** `FormField.tsx` wraps with class `form-group` (confirmed by reading the file); Task 5 Step 5 gives the exact rewrite and the test uses `.closest('.form-group')`. Backend test command is `uv run pytest` and the migration runs via `uv run python -m scripts.migrate_add_patient_fields`, matching `CLAUDE.md`.
