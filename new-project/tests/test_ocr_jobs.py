from datetime import datetime
from models import OcrJob
from schemas import OcrJobRead


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
