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
