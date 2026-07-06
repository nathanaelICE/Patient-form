from datetime import datetime
from models import OcrJob
from schemas import OcrJobRead
import ocr_jobs
import ocr_service
from sqlmodel import select
from models import Patient


def test_ocr_job_read_excludes_image(session):
    job = OcrJob(filename="f.png", media_type="image/png", image=b"secret")
    session.add(job)
    session.commit()
    session.refresh(job)
    out = OcrJobRead.model_validate(job).model_dump()
    assert set(out) == {"id", "filename", "status", "error_message", "extracted_fields", "created_at"}
    assert "image" not in out


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
    # the real cause is surfaced, not a generic message
    assert "vision down" in refreshed.error_message


def test_process_job_rate_limit_records_message(session, monkeypatch):
    job = _make_job(session)

    def boom(img, mt):
        raise ocr_service.OCRRateLimitError("rate limited after 3 attempts: 429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(ocr_service, "extract_patient_fields", boom)
    ocr_jobs.process_job(session, job.id)

    refreshed = session.get(OcrJob, job.id)
    assert refreshed.status == "error"
    assert "rate limit" in refreshed.error_message.lower()


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
