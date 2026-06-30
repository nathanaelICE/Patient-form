# OCR-Assisted Patient Registration — Design

**Date:** 2026-06-30
**Status:** Approved (brainstorming complete)

## Goal

Let clinic staff register a patient by uploading a photo/scan of a paper
patient form. A vision LLM (Claude vision) reads the form and returns the
fields as structured JSON; the frontend pre-fills the registration form;
staff review, correct, and save. OCR speeds up data entry but a human always
confirms before anything is written to the database.

## Approach

- **Engine:** Claude vision via the Anthropic API. The form image is sent with
  a structured-output (tool) schema describing the target fields. Claude
  returns the field values plus a per-field confidence. No model training, no
  training dataset, and no per-layout templating are required.
- **Why not Tesseract/PaddleOCR:** traditional OCR is strong on clean printed
  text but weak on handwriting and requires layout/templating work. Patient
  forms are often handwritten and semi-structured, so a vision LLM is the
  better fit.
- **Dataset:** none needed for training. A small set of real sample form
  photos is kept only as a manual accuracy test set.

## Schema changes — `Patient` model

All new columns are **nullable/optional** so existing records and partially
filled forms remain valid.

| Field | Type | Notes |
|-------|------|-------|
| `national_id` (NIK) | `str?` | Indexed. If present, validated as 16 digits. |
| `place_of_birth` | `str?` | |
| `marital_status` | `str?` | Enum: `single` / `married` / `divorced` / `widowed`. |
| `occupation` | `str?` | Free text. |
| `religion` | `str?` | Free text. |
| `nationality` | `str?` | Defaults to `Indonesian`. |
| `blood_type` | `str?` | Enum: `A` / `B` / `AB` / `O`, optional `+`/`-`. |
| `allergies` | `str?` | Free text. |
| `known_conditions` | `str?` | Free text. |

- Added to `PatientCreate`, `PatientRead`, and `PatientUpdate` in `schemas.py`,
  with field validators mirroring the existing style (strip blanks → `None`,
  enum normalization to lowercase, NIK digit check).
- The live database is Postgres (Neon). Because `create_all` does not alter
  existing tables, a migration script (`ALTER TABLE patient ADD COLUMN ...`
  for each new column, plus an index on `national_id`) upgrades the live DB
  cleanly. Document running it as a deploy step.

## OCR flow — new components

### Backend
- New router `routers/ocr.py` with `POST /ocr/extract`.
  - **Auth:** admin-only, consistent with all other routes in this app.
  - **Input:** multipart image upload (JPEG/PNG/WebP/PDF-page).
  - **Behavior:** calls Claude vision with the structured schema; returns
    `{ "fields": { ...patient fields... }, "confidence": { field: 0.0–1.0 } }`.
  - **Does not write to the database.** Extraction and persistence are separate.
- A thin `ocr_service` module wraps the Anthropic client so it can be mocked in
  tests and swapped later. Reads `ANTHROPIC_API_KEY` from the environment.

### Frontend (React SPA)
- An **"Upload form"** button on the patient registration screen.
- On upload: call `/ocr/extract`, then pre-fill the registration form fields
  with the returned values. Low-confidence fields are visually highlighted so
  staff know what to double-check.
- Staff edit as needed and save through the **existing** `POST /patients` path.
  The OCR step never bypasses the normal create/validation flow.

### Image storage
- **None in v1.** The uploaded image is processed in memory and discarded.
  Keeps the feature simple and privacy-friendly. Image storage / audit trail
  can be added later if required.

## Error handling

- Unsupported or unreadable image → `400` with a clear message.
- Claude API failure or timeout → `502`; the frontend tells staff to fill the
  form manually. The registration form remains fully usable without OCR.
- Missing `ANTHROPIC_API_KEY` → the feature is disabled gracefully and the
  "Upload form" button is hidden (a capability/health flag the frontend reads).

## Testing

- **Unit:** validators for each new field (NIK digits, enum normalization,
  blank → `None`), mirroring existing tests in `tests/`.
- **Endpoint:** `/ocr/extract` tested with a **mocked** Anthropic client — no
  real API calls in CI. Assert image-in → structured-JSON-out, the auth gate,
  and each error path (bad image, API failure, missing key).
- **Manual:** accuracy spot-check against the sample form images.

## Out of scope (v1)

- Training or fine-tuning any model.
- Storing uploaded images / audit trail.
- ID-card (KTP) layout-specific parsing.
- Contact fields (address, email, emergency contact) — not requested.

## Environment / config additions

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Auth for Claude vision. Without it, OCR is disabled. |

Optional: `OCR_MODEL` to pin the vision model id. Default to `claude-opus-4-8`
(the current most-capable model; per the `claude-api` skill, default to Opus
unless a model is explicitly chosen). All Claude 4.x models accept image input,
so `OCR_MODEL=claude-sonnet-4-6` is a valid lower-cost option for form reading
if cost matters more than accuracy.
