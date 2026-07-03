# Batch Async OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an admin upload multiple patient-form images at once, have the backend OCR them asynchronously, and show each document on the Patients page as a "Processing…" row that becomes a real patient on success or an "ERROR" row (moved to the bottom, with Retry/Dismiss/Manual-entry) on failure.

**Architecture:** A new `OcrJob` DB table is a queue. An in-process asyncio worker started in `main.py` polls for `pending` jobs, runs the blocking Gemini call in a threadpool, and either auto-creates a `Patient` (deleting the job) or marks the job `error`. The single-document synchronous OCR path is unchanged. The React Patients page polls a jobs endpoint every 2s while any job is in flight and renders the merged table.

**Tech Stack:** FastAPI + SQLModel (SQLite in tests, Postgres in prod), Python 3.12 / `uv`, React + TypeScript, React Query, Vitest, Pytest.

## Global Constraints

- Backend deps managed with `uv`; run tests with `uv run pytest`. Frontend from `frontend/`: `npm test`.
- All OCR endpoints are admin-gated via `Depends(get_admin)`.
- Patients are soft-deleted; every `Patient` query filters `deleted_at == None`. (Not directly touched here, but keep it in mind if you read patient rows.)
- Validation lives in `schemas.py`, not `models.py`. Auto-create MUST reuse `PatientCreate` so rules match manual creation exactly.
- Never send raw image bytes to the frontend. The `OcrJob` read schema excludes `image`.
- A finished (successful) job is **deleted**, not kept — the created `Patient` is its only trace. Only `pending`/`processing`/`error` jobs exist as rows.
- `ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}` (already defined in `routers/ocr.py`) is the single allow-list for uploads.
- Poll interval is exactly **2000 ms**, and polling stops when no job is `pending`/`processing`.
- The async worker is NOT started in tests (conftest builds `TestClient(app)` without a `with` block, so startup events don't fire). Tests exercise the worker's per-job logic directly via `process_job(session, job_id)`.

---

### Task 1: `OcrJob` model + table registration

**Files:**
- Modify: `models.py` (add `OcrJob` at end)
- Modify: `database.py:16-18` (import `OcrJob` in `create_db_and_tables`)
- Test: `tests/test_ocr_jobs.py` (new)

**Interfaces:**
- Produces: `OcrJob` SQLModel table with columns `id: int`, `filename: str`, `media_type: str`, `image: bytes`, `status: str` (default `"pending"`), `error_message: Optional[str]`, `extracted_fields: Optional[dict]` (JSON column), `created_at: datetime`, `updated_at: datetime`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ocr_jobs.py
from datetime import datetime
from models import OcrJob


def test_ocr_job_defaults(session):
    job = OcrJob(filename="form.png", media_type="image/png", image=b"\x89PNG")
    session.add(job)
    session.commit()
    session.refresh(job)
    assert job.id is not None
    assert job.status == "pending"
    assert job.error_message is None
    assert job.extracted_fields is None
    assert isinstance(job.created_at, datetime)
    assert isinstance(job.updated_at, datetime)


def test_ocr_job_stores_extracted_fields_json(session):
    job = OcrJob(
        filename="f.png", media_type="image/png", image=b"x",
        status="error", error_message="bad",
        extracted_fields={"name": "Ana", "gender": None},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    assert job.extracted_fields == {"name": "Ana", "gender": None}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ocr_jobs.py -v`
Expected: FAIL with `ImportError: cannot import name 'OcrJob' from 'models'`

- [ ] **Step 3: Add the model**

Append to `models.py`:

```python
from typing import Any
from sqlalchemy import Column, JSON, LargeBinary


class OcrJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    media_type: str
    image: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    status: str = Field(default="pending")  # pending | processing | error
    error_message: Optional[str] = None
    extracted_fields: Optional[dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

(Move the `from typing import Optional` line already at the top to also import nothing new; add the `Any` import where shown or fold into the existing typing import.)

- [ ] **Step 4: Register the table for prod DB creation**

In `database.py`, update the import inside `create_db_and_tables`:

```python
def create_db_and_tables():
    from models import Patient, Visit, Claim, AdminUser, OcrJob  # noqa: F401
    SQLModel.metadata.create_all(engine)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ocr_jobs.py -v`
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add models.py database.py tests/test_ocr_jobs.py
git commit -m "feat: add OcrJob queue table"
```

---

### Task 2: `OcrJobRead` schema

**Files:**
- Modify: `schemas.py` (add `OcrJobRead` near the other Read models)
- Test: `tests/test_ocr_jobs.py`

**Interfaces:**
- Produces: `OcrJobRead` Pydantic model (`from_attributes=True`) with fields `id, filename, status, error_message, extracted_fields, created_at`. **No `image`, no `media_type`, no `updated_at`.**

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_ocr_jobs.py
from schemas import OcrJobRead


def test_ocr_job_read_excludes_image(session):
    job = OcrJob(filename="f.png", media_type="image/png", image=b"secret")
    session.add(job)
    session.commit()
    session.refresh(job)
    out = OcrJobRead.model_validate(job).model_dump()
    assert set(out) == {"id", "filename", "status", "error_message", "extracted_fields", "created_at"}
    assert "image" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ocr_jobs.py::test_ocr_job_read_excludes_image -v`
Expected: FAIL with `ImportError: cannot import name 'OcrJobRead'`

- [ ] **Step 3: Add the schema**

In `schemas.py`, after `PatientRead` (around line 173), add:

```python
class OcrJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    error_message: Optional[str] = None
    extracted_fields: Optional[dict] = None
    created_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ocr_jobs.py::test_ocr_job_read_excludes_image -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add schemas.py tests/test_ocr_jobs.py
git commit -m "feat: add OcrJobRead schema (excludes image bytes)"
```

---

### Task 3: `ocr_jobs` service — per-job processing + orphan requeue

This is the core logic and the most heavily tested task. The async loop (Task 5) is a thin wrapper over `process_job`.

**Files:**
- Create: `ocr_jobs.py`
- Test: `tests/test_ocr_jobs.py`

**Interfaces:**
- Consumes: `ocr_service.extract_patient_fields(image_bytes, media_type) -> {"fields": {...}, "confidence": {...}}` and `ocr_service.OCRError`; `schemas.PatientCreate`; `models.OcrJob`, `models.Patient`.
- Produces:
  - `process_job(session: Session, job_id: int) -> None` — claims one job, runs OCR, and either creates a `Patient` + deletes the job, or sets the job to `error` with a message. Idempotent-safe: no-op if the job is missing or already `error`.
  - `requeue_orphans(session: Session) -> int` — sets every `processing` job back to `pending`; returns the count changed.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_ocr_jobs.py
import ocr_jobs
import ocr_service
from sqlmodel import select
from models import Patient


def _make_job(session, **over):
    job = OcrJob(filename="f.png", media_type="image/png", image=b"img")
    for k, v in over.items():
        setattr(job, k, v)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _fields(**over):
    base = {f: None for f in ocr_service.PATIENT_FIELDS}
    base.update(over)
    return {"fields": base, "confidence": {}}


def test_process_job_success_creates_patient_and_deletes_job(session, monkeypatch):
    job = _make_job(session)
    monkeypatch.setattr(
        ocr_service, "extract_patient_fields",
        lambda img, mt: _fields(name="Ana Lestari", date_of_birth="1990-05-01", gender="female"),
    )
    ocr_jobs.process_job(session, job.id)

    assert session.get(OcrJob, job.id) is None
    patients = session.exec(select(Patient)).all()
    assert len(patients) == 1
    assert patients[0].name == "Ana Lestari"
    assert patients[0].gender == "female"


def test_process_job_ocr_failure_marks_error(session, monkeypatch):
    job = _make_job(session)
    def boom(img, mt):
        raise ocr_service.OCRError("vision down")
    monkeypatch.setattr(ocr_service, "extract_patient_fields", boom)

    ocr_jobs.process_job(session, job.id)

    refreshed = session.get(OcrJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "error"
    assert refreshed.error_message == "could not read document"


def test_process_job_missing_required_field_marks_error(session, monkeypatch):
    job = _make_job(session)
    # gender missing/unreadable -> validation fails -> error, not a junk patient
    monkeypatch.setattr(
        ocr_service, "extract_patient_fields",
        lambda img, mt: _fields(name="Budi", date_of_birth="1985-02-02", gender=None),
    )
    ocr_jobs.process_job(session, job.id)

    refreshed = session.get(OcrJob, job.id)
    assert refreshed.status == "error"
    assert "gender" in refreshed.error_message
    assert session.exec(select(Patient)).all() == []
    # partial fields retained for manual-entry prefill
    assert refreshed.extracted_fields["name"] == "Budi"


def test_process_job_ignores_already_errored_job(session, monkeypatch):
    job = _make_job(session, status="error", error_message="prior")
    called = {"n": 0}
    monkeypatch.setattr(ocr_service, "extract_patient_fields",
                        lambda img, mt: called.__setitem__("n", called["n"] + 1) or _fields())
    ocr_jobs.process_job(session, job.id)
    assert called["n"] == 0  # not reprocessed


def test_requeue_orphans_resets_processing(session):
    a = _make_job(session, status="processing")
    b = _make_job(session, status="pending")
    n = ocr_jobs.requeue_orphans(session)
    assert n == 1
    assert session.get(OcrJob, a.id).status == "pending"
    assert session.get(OcrJob, b.id).status == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ocr_jobs.py -v -k process_job or requeue`
Expected: FAIL with `ModuleNotFoundError: No module named 'ocr_jobs'`

- [ ] **Step 3: Implement the service**

Create `ocr_jobs.py`:

```python
"""Async-worker business logic for OCR jobs.

`process_job` handles a single job end-to-end and is fully synchronous so it can
be unit-tested with the in-memory test session and driven from a threadpool by
the worker loop. The loop itself lives in `main.py` startup.
"""
from datetime import datetime

from pydantic import ValidationError
from sqlmodel import Session, select

import ocr_service
from models import OcrJob, Patient
from schemas import PatientCreate


def _touch(job: OcrJob) -> None:
    job.updated_at = datetime.utcnow()


def _fail(session: Session, job: OcrJob, message: str) -> None:
    job.status = "error"
    job.error_message = message
    _touch(job)
    session.add(job)
    session.commit()


def _first_error_field_message(exc: ValidationError) -> str:
    err = exc.errors()[0]
    loc = err.get("loc") or ()
    field = loc[-1] if loc else "field"
    return f"{field}: {err.get('msg', 'invalid')}"


def process_job(session: Session, job_id: int) -> None:
    job = session.get(OcrJob, job_id)
    if job is None or job.status == "error":
        return

    job.status = "processing"
    _touch(job)
    session.add(job)
    session.commit()

    try:
        result = ocr_service.extract_patient_fields(job.image, job.media_type)
    except ocr_service.OCRError:
        _fail(session, job, "could not read document")
        return

    fields = result.get("fields") or {}
    job.extracted_fields = fields  # retained for manual-entry prefill

    present = {k: v for k, v in fields.items() if v is not None}
    try:
        patient_in = PatientCreate(**present)
    except ValidationError as exc:
        _fail(session, job, _first_error_field_message(exc))
        return

    patient = Patient(**patient_in.model_dump())
    session.add(patient)
    session.delete(job)
    session.commit()


def requeue_orphans(session: Session) -> int:
    stuck = session.exec(select(OcrJob).where(OcrJob.status == "processing")).all()
    for job in stuck:
        job.status = "pending"
        _touch(job)
        session.add(job)
    session.commit()
    return len(stuck)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ocr_jobs.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add ocr_jobs.py tests/test_ocr_jobs.py
git commit -m "feat: OCR job processing + orphan requeue logic"
```

---

### Task 4: Job endpoints — upload (multiple), list, retry, dismiss

**Files:**
- Modify: `routers/ocr.py`
- Test: `tests/test_ocr_router.py` (new)

**Interfaces:**
- Consumes: `models.OcrJob`, `schemas.OcrJobRead`, `ocr_service.ocr_available`, `ocr_service.ALLOWED_TYPES` (already `ALLOWED_TYPES` in this module), `get_session`, `get_admin`.
- Produces these routes (all under existing `prefix="/api/ocr"`):
  - `POST /api/ocr/jobs` — body: multipart `files` (one or more). 503 if OCR unavailable; 400 if any file has an unsupported type or is empty (no jobs created); else creates one `pending` job per file and returns `list[OcrJobRead]` with 201.
  - `GET /api/ocr/jobs` — returns `list[OcrJobRead]`, ordered `created_at` ascending. (Only pending/processing/error rows exist.)
  - `POST /api/ocr/jobs/{job_id}/retry` — 404 if missing; 409 if status != `error`; else set `pending`, clear `error_message`, return `OcrJobRead`.
  - `DELETE /api/ocr/jobs/{job_id}` — 404 if missing; else delete, 204.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_router.py
import io
import ocr_service
from models import OcrJob


def _png():
    return ("f.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")


def test_upload_requires_admin(client):
    resp = client.post("/api/ocr/jobs", files={"files": _png()})
    assert resp.status_code == 401


def test_upload_creates_pending_jobs(admin_client, monkeypatch):
    monkeypatch.setattr(ocr_service, "ocr_available", lambda: True)
    resp = admin_client.post(
        "/api/ocr/jobs",
        files=[("files", _png()), ("files", ("g.png", io.BytesIO(b"\x89PNG2"), "image/png"))],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 2
    assert all(j["status"] == "pending" for j in body)
    assert "image" not in body[0]


def test_upload_rejects_bad_type_without_creating(admin_client, session, monkeypatch):
    from sqlmodel import select
    monkeypatch.setattr(ocr_service, "ocr_available", lambda: True)
    resp = admin_client.post(
        "/api/ocr/jobs",
        files=[("files", _png()), ("files", ("bad.txt", io.BytesIO(b"hi"), "text/plain"))],
    )
    assert resp.status_code == 400
    assert session.exec(select(OcrJob)).all() == []


def test_upload_503_when_unavailable(admin_client, monkeypatch):
    monkeypatch.setattr(ocr_service, "ocr_available", lambda: False)
    resp = admin_client.post("/api/ocr/jobs", files={"files": _png()})
    assert resp.status_code == 503


def test_list_jobs_returns_rows(admin_client, session):
    session.add(OcrJob(filename="a.png", media_type="image/png", image=b"x"))
    session.add(OcrJob(filename="b.png", media_type="image/png", image=b"y", status="error", error_message="nope"))
    session.commit()
    resp = admin_client.get("/api/ocr/jobs")
    assert resp.status_code == 200
    names = [j["filename"] for j in resp.json()]
    assert names == ["a.png", "b.png"]


def test_retry_resets_error_job(admin_client, session):
    job = OcrJob(filename="a.png", media_type="image/png", image=b"x", status="error", error_message="nope")
    session.add(job); session.commit(); session.refresh(job)
    resp = admin_client.post(f"/api/ocr/jobs/{job.id}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["error_message"] is None


def test_retry_conflict_when_not_error(admin_client, session):
    job = OcrJob(filename="a.png", media_type="image/png", image=b"x", status="pending")
    session.add(job); session.commit(); session.refresh(job)
    resp = admin_client.post(f"/api/ocr/jobs/{job.id}/retry")
    assert resp.status_code == 409


def test_dismiss_deletes_job(admin_client, session):
    job = OcrJob(filename="a.png", media_type="image/png", image=b"x", status="error")
    session.add(job); session.commit(); session.refresh(job)
    resp = admin_client.delete(f"/api/ocr/jobs/{job.id}")
    assert resp.status_code == 204
    assert session.get(OcrJob, job.id) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ocr_router.py -v`
Expected: FAIL — `POST /api/ocr/jobs` returns 404/405 (route not defined)

- [ ] **Step 3: Implement the endpoints**

Rewrite `routers/ocr.py` to add the job routes (keep the existing `status` and `extract` routes intact):

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select

from deps import get_admin
from database import get_session
from models import AdminUser, OcrJob
from schemas import OcrJobRead
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


@router.post("/jobs", response_model=List[OcrJobRead], status_code=201)
async def create_jobs(
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    if not ocr_service.ocr_available():
        raise HTTPException(status_code=503, detail="OCR is not configured")
    # Read + validate all first so a single bad file creates no jobs.
    staged = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {f.filename}")
        data = await f.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"Empty file: {f.filename}")
        staged.append((f.filename or "upload", f.content_type, data))

    jobs = [OcrJob(filename=name, media_type=mt, image=data) for name, mt, data in staged]
    for job in jobs:
        session.add(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return jobs


@router.get("/jobs", response_model=List[OcrJobRead])
def list_jobs(session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    return session.exec(select(OcrJob).order_by(OcrJob.created_at)).all()


@router.post("/jobs/{job_id}/retry", response_model=OcrJobRead)
def retry_job(job_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    job = session.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "error":
        raise HTTPException(status_code=409, detail="Only errored jobs can be retried")
    job.status = "pending"
    job.error_message = None
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def dismiss_job(job_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    job = session.get(OcrJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(job)
    session.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ocr_router.py -v`
Expected: PASS (all)

- [ ] **Step 5: Run the full backend suite (no regressions)**

Run: `uv run pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add routers/ocr.py tests/test_ocr_router.py
git commit -m "feat: OCR job endpoints (batch upload, list, retry, dismiss)"
```

---

### Task 5: Start the async worker on app startup

**Files:**
- Modify: `main.py:35-39` (replace the sync startup with async startup that launches the worker; add shutdown to cancel it)
- Test: covered indirectly — the worker loop itself is not unit-tested (per Global Constraints); `process_job`/`requeue_orphans` are already covered in Task 3. Add one focused test that the loop function drains a pending job when run once.

**Interfaces:**
- Consumes: `ocr_jobs.process_job`, `ocr_jobs.requeue_orphans`, `database.engine`, `database.create_db_and_tables`, `database.seed_admin`.
- Produces: `async def _ocr_worker_loop(stop: asyncio.Event)` in `main.py` that, per tick, requeues nothing (requeue is startup-only) and processes all currently `pending` jobs via `anyio.to_thread.run_sync`, sleeping `POLL_SECONDS` between ticks. A module-level `POLL_SECONDS = 1.0`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ocr_worker.py
import asyncio
import ocr_service
from models import OcrJob, Patient
from sqlmodel import select
import main


def test_worker_tick_processes_pending(session, monkeypatch):
    # _process_pending_once is called directly with the test session below.
    monkeypatch.setattr(
        ocr_service, "extract_patient_fields",
        lambda img, mt: {"fields": {f: None for f in ocr_service.PATIENT_FIELDS} |
                         {"name": "Ana", "date_of_birth": "1990-01-01", "gender": "female"},
                         "confidence": {}},
    )
    session.add(OcrJob(filename="a.png", media_type="image/png", image=b"x"))
    session.commit()

    asyncio.run(main._process_pending_once(session))

    assert session.exec(select(Patient)).all()[0].name == "Ana"
    assert session.exec(select(OcrJob)).all() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ocr_worker.py -v`
Expected: FAIL with `AttributeError: module 'main' has no attribute '_process_pending_once'`

- [ ] **Step 3: Implement the worker in `main.py`**

Add imports at the top of `main.py`:

```python
import asyncio
import anyio
from sqlmodel import select
from database import create_db_and_tables, seed_admin, engine
from models import OcrJob
import ocr_jobs
```

Add module-level constants + helpers (after `DIST_DIR`):

```python
POLL_SECONDS = 1.0


def _worker_session() -> Session:
    return Session(engine)


async def _process_pending_once(session: Session) -> None:
    job_ids = [j.id for j in session.exec(select(OcrJob).where(OcrJob.status == "pending")).all()]
    for job_id in job_ids:
        await anyio.to_thread.run_sync(ocr_jobs.process_job, session, job_id)


async def _ocr_worker_loop(stop: asyncio.Event) -> None:
    with _worker_session() as session:
        ocr_jobs.requeue_orphans(session)
    while not stop.is_set():
        try:
            with _worker_session() as session:
                await _process_pending_once(session)
        except Exception:
            # Never let a transient DB/OCR error kill the loop.
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
```

Replace the existing sync `@app.on_event("startup")` block (lines 35-39) with:

```python
@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin(session)
    app.state.ocr_stop = asyncio.Event()
    app.state.ocr_worker = asyncio.create_task(_ocr_worker_loop(app.state.ocr_stop))


@app.on_event("shutdown")
async def on_shutdown():
    stop = getattr(app.state, "ocr_stop", None)
    worker = getattr(app.state, "ocr_worker", None)
    if stop is not None:
        stop.set()
    if worker is not None:
        try:
            await worker
        except Exception:
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ocr_worker.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite**

Run: `uv run pytest`
Expected: PASS (startup worker does not run under the non-context `TestClient`, so existing tests are unaffected)

- [ ] **Step 6: Confirm `anyio` is available**

`anyio` ships as a FastAPI/Starlette dependency, so no new dep is expected. Verify:

Run: `uv run python -c "import anyio; print(anyio.__version__)"`
Expected: prints a version (no ImportError). If it errors, run `uv add anyio` and commit `pyproject.toml`/`uv.lock`.

- [ ] **Step 7: Commit**

```bash
git add main.py tests/test_ocr_worker.py
git commit -m "feat: start async OCR worker on app startup"
```

---

### Task 6: Frontend API module + hooks for OCR jobs

**Files:**
- Create: `frontend/src/api/ocrJobs.ts`
- Modify: `frontend/src/api/types.ts` (add `OcrJob` type)
- Test: `frontend/src/api/ocrJobs.test.tsx` (new)

**Interfaces:**
- Produces:
  - `type OcrJobStatus = 'pending' | 'processing' | 'error'`
  - `interface OcrJob { id: number; filename: string; status: OcrJobStatus; error_message: string | null; extracted_fields: Partial<PatientCreate> | null; created_at: string }`
  - `useOcrJobs()` — React Query `['ocrJobs']`, `refetchInterval` = 2000 while any job is `pending`/`processing`, else `false`.
  - `useUploadOcrJobs()` — mutation, `FormData` with repeated `files`, invalidates `['ocrJobs']`.
  - `useRetryOcrJob()` / `useDismissOcrJob()` — mutations invalidating `['ocrJobs']` and `['patients']`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/api/ocrJobs.test.tsx
import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import { useOcrJobs } from './ocrJobs'

afterEach(() => vi.restoreAllMocks())

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useOcrJobs', () => {
  it('fetches the job list', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => [{ id: 1, filename: 'a.png', status: 'processing', error_message: null, extracted_fields: null, created_at: '2026-07-03T00:00:00' }],
    } as Response))
    const { result } = renderHook(() => useOcrJobs(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.data?.[0].filename).toBe('a.png'))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- ocrJobs`
Expected: FAIL — cannot resolve `./ocrJobs`

- [ ] **Step 3: Add the `OcrJob` type**

Append to `frontend/src/api/types.ts`:

```typescript
export type OcrJobStatus = 'pending' | 'processing' | 'error'
export interface OcrJob {
  id: number
  filename: string
  status: OcrJobStatus
  error_message: string | null
  extracted_fields: Partial<PatientCreate> | null
  created_at: string
}
```

- [ ] **Step 4: Implement the API module**

Create `frontend/src/api/ocrJobs.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, ApiError } from './client'
import type { OcrJob } from './types'

function isActive(jobs: OcrJob[] | undefined): boolean {
  return !!jobs?.some((j) => j.status === 'pending' || j.status === 'processing')
}

export function useOcrJobs() {
  return useQuery({
    queryKey: ['ocrJobs'],
    queryFn: () => apiFetch<OcrJob[]>('/api/ocr/jobs'),
    refetchInterval: (query) => (isActive(query.state.data as OcrJob[] | undefined) ? 2000 : false),
  })
}

export function useUploadOcrJobs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData()
      for (const f of files) form.append('files', f)
      const res = await fetch('/api/ocr/jobs', { method: 'POST', credentials: 'include', body: form })
      let parsed: unknown = null
      try { parsed = await res.json() } catch { parsed = null }
      if (!res.ok) throw new ApiError(res.status, parsed)
      return parsed as OcrJob[]
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ocrJobs'] }),
  })
}

export function useRetryOcrJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<OcrJob>(`/api/ocr/jobs/${id}/retry`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ocrJobs'] }),
  })
}

export function useDismissOcrJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/ocr/jobs/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ocrJobs'] })
      qc.invalidateQueries({ queryKey: ['patients'] })
    },
  })
}
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `frontend/`): `npm test -- ocrJobs`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/ocrJobs.ts frontend/src/api/types.ts frontend/src/api/ocrJobs.test.tsx
git commit -m "feat: frontend OCR jobs api module and hooks"
```

---

### Task 7: Patients page — batch upload + merged Processing/ERROR rows

**Files:**
- Modify: `frontend/src/pages/PatientListPage.tsx`
- Modify: `frontend/src/pages/PatientListPage.test.tsx`

**Interfaces:**
- Consumes: `useOcrJobs`, `useUploadOcrJobs`, `useRetryOcrJob`, `useDismissOcrJob` (Task 6); `getOcrStatus` from `../api/ocr`; existing `usePatients`, `useDeletePatient`, `useAuth`.
- Produces: a Patients table that renders, in order — (1) `pending`/`processing` jobs as pseudo-rows showing the filename + "Processing…", (2) the real patients, (3) `error` jobs as pseudo-rows at the bottom showing "ERROR" + message with Retry / Dismiss / Manual-entry controls. Upload `<input type="file" multiple>` is shown to admins when OCR is available.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/pages/PatientListPage.test.tsx`:

```tsx
import { fireEvent } from '@testing-library/react'

it('renders processing rows at top and error rows at bottom', async () => {
  const fetchMock = vi.fn((url: string) => {
    if (url.includes('/api/ocr/status')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ available: true }) } as Response)
    if (url.includes('/api/ocr/jobs')) return Promise.resolve({ ok: true, status: 200, json: async () => [
      { id: 10, filename: 'scan1.png', status: 'processing', error_message: null, extracted_fields: null, created_at: '2026-07-03T00:00:00' },
      { id: 11, filename: 'scan2.png', status: 'error', error_message: 'could not read document', extracted_fields: null, created_at: '2026-07-03T00:00:01' },
    ] } as Response)
    return Promise.resolve({ ok: true, status: 200, json: async () => [
      { id: 1, name: 'Ana', date_of_birth: '1990-01-01', gender: 'female', phone: null, created_at: '2026-01-01T00:00:00' },
    ] } as Response)
  })
  vi.stubGlobal('fetch', fetchMock)

  renderWithProviders(
    <AuthContext.Provider value={{ isAdmin: true, isLoading: false }}>
      <PatientListPage />
    </AuthContext.Provider>,
    { route: '/patients' },
  )

  await waitFor(() => expect(screen.getByText('scan1.png')).toBeInTheDocument())
  expect(screen.getByText(/Processing/i)).toBeInTheDocument()
  expect(screen.getByText('ERROR')).toBeInTheDocument()

  const rows = screen.getAllByRole('row').map((r) => r.textContent || '')
  const processingIdx = rows.findIndex((t) => t.includes('scan1.png'))
  const patientIdx = rows.findIndex((t) => t.includes('Ana'))
  const errorIdx = rows.findIndex((t) => t.includes('scan2.png'))
  expect(processingIdx).toBeLessThan(patientIdx)
  expect(patientIdx).toBeLessThan(errorIdx)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- PatientListPage`
Expected: FAIL — no `scan1.png` / `ERROR` text

- [ ] **Step 3: Implement the page**

Rewrite `frontend/src/pages/PatientListPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { usePatients, useDeletePatient } from '../api/patients'
import { useOcrJobs, useUploadOcrJobs, useRetryOcrJob, useDismissOcrJob } from '../api/ocrJobs'
import { getOcrStatus } from '../api/ocr'
import { useAuth } from '../auth/AuthContext'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorBanner from '../components/ErrorBanner'

export default function PatientListPage() {
  const { data: patients, isLoading, error } = usePatients()
  const del = useDeletePatient()
  const { isAdmin } = useAuth()
  const navigate = useNavigate()
  const [toDelete, setToDelete] = useState<number | null>(null)

  const [ocrAvailable, setOcrAvailable] = useState(false)
  useEffect(() => {
    if (isAdmin) getOcrStatus().then(setOcrAvailable).catch(() => setOcrAvailable(false))
  }, [isAdmin])

  const jobs = useOcrJobs()
  const upload = useUploadOcrJobs()
  const retry = useRetryOcrJob()
  const dismiss = useDismissOcrJob()

  const allJobs = jobs.data ?? []
  const processing = allJobs.filter((j) => j.status === 'pending' || j.status === 'processing')
  const errored = allJobs.filter((j) => j.status === 'error')
  const colSpan = isAdmin ? 6 : 5

  if (isLoading) return <p>Loading…</p>
  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">Patients</h2>
        {isAdmin && <Link className="btn btn-primary" to="/patients/new">+ Register Patient</Link>}
      </div>
      <ErrorBanner error={error} />
      {isAdmin && ocrAvailable && (
        <div className="card form-card ocr-upload">
          <label htmlFor="ocr-batch">Upload one or more forms to auto-register patients</label>
          <input
            id="ocr-batch"
            type="file"
            multiple
            accept="image/png,image/jpeg,image/webp"
            disabled={upload.isPending}
            onChange={(e) => {
              const files = Array.from(e.target.files ?? [])
              if (files.length) upload.mutate(files)
              e.target.value = ''
            }}
          />
          {upload.isPending && <span className="ocr-status">Uploading…</span>}
          <ErrorBanner error={upload.error} />
        </div>
      )}
      <div className="table-wrapper">
        <table className="patient-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Gender</th>
              <th>Phone</th>
              <th>Date of Birth</th>
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {processing.map((j) => (
              <tr key={`job-${j.id}`} className="ocr-row ocr-row-processing">
                <td>—</td>
                <td>{j.filename}</td>
                <td colSpan={colSpan - 2}>Processing…</td>
              </tr>
            ))}
            {(patients ?? []).map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td><Link to={`/patients/${p.id}`}>{p.name}</Link></td>
                <td>{p.gender}</td>
                <td>{p.phone || '-'}</td>
                <td>{p.date_of_birth}</td>
                {isAdmin && (
                  <td className="actions-cell">
                    <Link to={`/patients/${p.id}/edit`} className="btn btn-secondary btn-icon" title="Edit">✎</Link>
                    <button className="btn btn-danger btn-icon" title="Delete" onClick={() => setToDelete(p.id)}>🗑</button>
                  </td>
                )}
              </tr>
            ))}
            {errored.map((j) => (
              <tr key={`job-${j.id}`} className="ocr-row ocr-row-error">
                <td><strong>ERROR</strong></td>
                <td>{j.filename}</td>
                <td colSpan={colSpan - 3}>{j.error_message || 'could not read document'}</td>
                <td className="actions-cell">
                  <button className="btn btn-secondary" onClick={() => retry.mutate(j.id)}>Retry</button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate('/patients/new', { state: { prefill: j.extracted_fields ?? {}, jobId: j.id } })}
                  >Manual entry</button>
                  <button className="btn btn-danger" onClick={() => dismiss.mutate(j.id)}>Dismiss</button>
                </td>
              </tr>
            ))}
            {(patients?.length ?? 0) === 0 && allJobs.length === 0 && (
              <tr><td colSpan={colSpan} className="empty-state">No patients registered yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <ConfirmDialog
        open={toDelete !== null}
        title="Delete patient"
        message="This soft-deletes the patient. Continue?"
        onCancel={() => setToDelete(null)}
        onConfirm={() => { if (toDelete !== null) del.mutate(toDelete); setToDelete(null) }}
      />
    </section>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `frontend/`): `npm test -- PatientListPage`
Expected: PASS (both the original "renders fetched patients" test and the new ordering test)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PatientListPage.tsx frontend/src/pages/PatientListPage.test.tsx
git commit -m "feat: patients page batch upload + processing/error OCR rows"
```

---

### Task 8: Manual-entry prefill + job dismissal on create

**Files:**
- Modify: `frontend/src/pages/PatientNewPage.tsx`
- Modify: `frontend/src/pages/PatientNewPage.test.tsx`

**Interfaces:**
- Consumes: router location `state` shaped `{ prefill?: Partial<PatientCreate>; jobId?: number }` (set by Task 7's "Manual entry" button); `useDismissOcrJob` (Task 6).
- Produces: when navigated to with `state.prefill`, the Register form is pre-populated from it; on a successful create, if `state.jobId` is present the corresponding OCR job is dismissed and the user is sent to the new patient.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/pages/PatientNewPage.test.tsx` (create the file if it lacks a render helper; use `renderWithProviders` with a route that carries state via `MemoryRouter`). Because `renderWithProviders` only takes a `route` string, add a variant test using `MemoryRouter` with `initialEntries` carrying `state`:

```tsx
import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import PatientNewPage from './PatientNewPage'

afterEach(() => vi.restoreAllMocks())

it('prefills the form from router state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ available: false }) } as Response))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[{ pathname: '/patients/new', state: { prefill: { name: 'Budi Santoso' }, jobId: 5 } }]}>
        <PatientNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  await waitFor(() => expect((screen.getByLabelText(/name/i) as HTMLInputElement).value).toBe('Budi Santoso'))
})
```

(Import `render` from `@testing-library/react`.)

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `npm test -- PatientNewPage`
Expected: FAIL — the name field is empty (prefill not wired)

- [ ] **Step 3: Wire prefill + dismissal into `PatientNewPage`**

Modify `frontend/src/pages/PatientNewPage.tsx`:

Add imports and read location state:

```tsx
import { useLocation, useNavigate } from 'react-router-dom'
import { useDismissOcrJob } from '../api/ocrJobs'
import type { PatientCreate } from '../api/types'
```

Inside the component, near the top:

```tsx
const location = useLocation()
const navState = (location.state ?? {}) as { prefill?: Partial<PatientCreate>; jobId?: number }
const dismissJob = useDismissOcrJob()
```

Initialize `initial` from the prefill (replace the `useState<Partial<PatientCreate> | undefined>(undefined)` initializer):

```tsx
const [initial, setInitial] = useState<Partial<PatientCreate> | undefined>(navState.prefill)
```

In the `onSubmit` success branch, after `const p = await create.mutateAsync(data)` and before `navigate`, dismiss the source job if present:

```tsx
const p = await create.mutateAsync(data)
if (navState.jobId != null) {
  try { await dismissJob.mutateAsync(navState.jobId) } catch { /* job already gone is fine */ }
}
navigate(`/patients/${p.id}`)
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `frontend/`): `npm test -- PatientNewPage`
Expected: PASS

- [ ] **Step 5: Run the full frontend suite + type-check**

Run (from `frontend/`): `npm test` then `npm run build`
Expected: all tests PASS; `tsc -b` reports no type errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PatientNewPage.tsx frontend/src/pages/PatientNewPage.test.tsx
git commit -m "feat: manual-entry prefill and job dismissal from error rows"
```

---

## Final Verification

- [ ] **Backend:** `uv run pytest` → all pass.
- [ ] **Frontend:** from `frontend/`, `npm test` and `npm run build` → all pass, no type errors.
- [ ] **Manual smoke (optional, needs `GEMINI_API_KEY` + `DATABASE_URL`):** run the API, log in, upload 2+ images on the Patients page, confirm two "Processing…" rows appear, then one becomes a patient and (with a deliberately unreadable image) one drops to an ERROR row at the bottom; exercise Retry, Manual entry, and Dismiss.

## Notes for the implementer

- **Why `process_job` is sync and session-injected:** the worker loop drives it through `anyio.to_thread.run_sync` with a per-tick `Session(engine)`, while tests call it directly with the in-memory session. Keep it synchronous.
- **Ordering rule:** processing/pending rows render before patients; error rows render after. This satisfies "processing rows appear as new rows" and "errored rows move toward the bottom."
- **Do not** delete or alter `POST /api/ocr/extract` or `GET /api/ocr/status` — the single-form OCR path and the availability probe both still use them.
- **Concurrency:** the worker processes pending jobs sequentially per tick. That's intentional and simplest; do not add a thread pool / semaphore unless a later requirement demands it (YAGNI).
