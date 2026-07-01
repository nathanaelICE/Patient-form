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
