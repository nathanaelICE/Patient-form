# Batch Async OCR — Design

**Date:** 2026-07-03
**Status:** Approved (pending spec review)

## Problem

Today OCR is synchronous and single-document: the admin uploads one image on the
Register Patient form, waits, reviews the auto-filled fields, and submits to create the
patient. We want to:

- Upload **multiple documents at once**.
- Process them **asynchronously** on the backend so the admin can navigate away and use
  other features while they run.
- Show progress on the **Patients page**: N documents produce N placeholder rows labelled
  "Processing…". When a document finishes and is readable, its row becomes a real patient.
  When a document can't be read, its row moves to the **bottom** labelled **ERROR**.

## Decisions (from brainstorming)

- **Auto-create.** A successfully-read document becomes a real `Patient` automatically, with
  no human review step.
- **Partial reads are ERRORs.** A patient requires `name`, `date_of_birth`, and `gender`
  (non-null). If OCR succeeds technically but any required field is missing or invalid, the
  job becomes an ERROR row (no placeholder/junk patients).
- **Error-row actions:** Retry (re-run OCR on the stored image), Dismiss (delete the row),
  and Manual entry (open a prefilled Register form and create by hand).
- **Engine:** DB-backed job queue + in-process asyncio worker (Approach A). Fits the
  single-process / single-service deployment.

## Architecture

### Engine (Approach A)

A new `OcrJob` DB table is the queue. On app startup, `main.py` launches a single
background asyncio worker task that:

1. Requeues orphans: any job left in `processing` (from a prior crash/restart) → `pending`.
2. Loops: claim the oldest `pending` job → mark `processing` → run OCR → resolve to a
   Patient or an error → repeat. A bounded number of jobs process concurrently (semaphore).

The Gemini SDK call is blocking, so it runs in a threadpool (`anyio.to_thread` /
`run_in_executor`) to avoid blocking the event loop.

### Data model — `OcrJob` (new table in `models.py`)

| column | type | notes |
|---|---|---|
| `id` | int PK | |
| `filename` | str | original upload name, for display |
| `media_type` | str | e.g. `image/png` |
| `image` | bytes (bytea) | original bytes, retained so Retry works |
| `status` | str | `pending` / `processing` / `error` (a `done` job is deleted) |
| `error_message` | str? | human-readable failure reason for the ERROR row |
| `extracted_fields` | JSON? | partial OCR result, used to prefill Manual entry |
| `created_at` | datetime | ordering |
| `updated_at` | datetime | |

Rationale for a separate table: during processing there is no valid patient (required
fields may be unknown), so we cannot represent in-flight/errored work as `Patient` rows.

### Lifecycle

```
upload (N files) ──> N × OcrJob(status=pending)
worker claims job  ──> status=processing
  OCR ok AND name/DOB/gender valid ──> create Patient, DELETE job   (row becomes a real patient)
  OCR fails OR required field missing/invalid ──> status=error, set error_message
retry (error only) ──> status=pending  (worker picks it up again)
dismiss ──> DELETE job
manual entry ──> open prefilled Register form; on successful create, DELETE job
```

Validation reuses the existing `schemas.py` patient-create validation (the single source of
truth), so auto-create and manual create apply identical rules.

### Endpoints (all admin-gated, in `routers/ocr.py`)

| method | path | purpose |
|---|---|---|
| `POST` | `/api/ocr/jobs` | multipart, **multiple** files; creates one `pending` job per file; returns the created jobs |
| `GET` | `/api/ocr/jobs` | list non-done jobs (processing + error), for the polling hook |
| `POST` | `/api/ocr/jobs/{id}/retry` | error → pending |
| `DELETE` | `/api/ocr/jobs/{id}` | dismiss (delete) a job |

The existing `POST /api/ocr/extract` (synchronous single-image) and `GET /api/ocr/status`
remain — `extract` is no longer the primary path but is kept available; `status` still gates
whether OCR UI is shown. Upload endpoints reuse the existing `ALLOWED_TYPES` guard.

### Frontend

- **New API module** `src/api/ocrJobs.ts`: `uploadOcrJobs(files)`, `listOcrJobs()`,
  `retryOcrJob(id)`, `dismissOcrJob(id)` + a `useOcrJobs` React Query hook that polls
  `GET /api/ocr/jobs` on an interval **while any job is `processing`** (stops polling when
  idle). Completion is detected when a processing job disappears → invalidate the patients
  query so the new patient appears.
- **Batch upload control on the Patients page** (`PatientListPage`): an `<input type="file"
  multiple>` shown to admins when OCR is available. Selecting files calls `uploadOcrJobs`.
- **Merged table rendering** in `PatientListPage`:
  - **Processing pseudo-rows at the top** — "Processing…", filename shown, no patient data.
  - Real patients in the middle (unchanged).
  - **ERROR pseudo-rows at the bottom** — "ERROR" + `error_message`, with **Retry**,
    **Dismiss**, and **Manual entry** buttons.
  - Manual entry navigates to `/patients/new` prefilled from the job's `extracted_fields`
    (carried via router state); on successful create the page dismisses the job.

## Error handling

- Unsupported media type / empty file at upload → 400 (no job created).
- OCR service unavailable (`ocr_available()` false) → 503 on upload; UI hidden via `status`.
- Worker OCR exception → job `error`, message "could not read document".
- Required-field validation failure → job `error`, message names the missing/invalid field.
- Worker isolates per-job failures: one bad job never stops the loop.
- Restart mid-processing → orphaned `processing` jobs requeued to `pending` on startup.

## Testing

**Backend** (patch `ocr_service.extract_patient_fields`):
- Upload creates N pending jobs; rejects bad media type / empty file.
- Worker success path: valid fields → Patient created, job deleted.
- Worker error paths: OCR raises → error; missing/invalid required field → error with message.
- Retry resets error → pending; dismiss deletes; `GET /api/ocr/jobs` omits done.
- Startup requeue of orphaned `processing` jobs.

**Frontend** (vitest + jsdom):
- Table renders processing rows at top, error rows at bottom, patients in the middle.
- Error-row actions call the right endpoints; polling hook starts/stops correctly.
- Manual-entry navigation carries prefill data.

## Out of scope (YAGNI)

- External queue / multi-replica workers.
- Per-field confidence review UI for auto-created patients (auto-create is trusted; edit later).
- Progress percentage per document (binary processing/done/error is enough).
