import asyncio
import ocr_service
from models import OcrJob, Patient
from sqlmodel import select
import main


def test_worker_tick_processes_pending(session, monkeypatch):
    # Both the listing session and each per-job session resolve to the test session
    # (StaticPool in-memory DB), so the whole tick operates on one database.
    monkeypatch.setattr(main, "_worker_session", lambda: session)
    monkeypatch.setattr(
        ocr_service, "extract_patient_fields",
        lambda img, mt: {"fields": {f: None for f in ocr_service.PATIENT_FIELDS} |
                         {"name": "Ana", "date_of_birth": "1990-01-01", "gender": "female"},
                         "confidence": {}},
    )
    session.add(OcrJob(filename="a.png", media_type="image/png", image=b"x"))
    session.commit()

    asyncio.run(main._process_pending_once())

    assert session.exec(select(Patient)).all()[0].name == "Ana"
    assert session.exec(select(OcrJob)).all() == []
