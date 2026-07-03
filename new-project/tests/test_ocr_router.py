import io
from unittest.mock import patch
import routers.ocr as ocr_router
import ocr_service
from models import OcrJob


def _png_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"0" * 32


def _png():
    return ("f.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")


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


# --- Job endpoints ---

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
