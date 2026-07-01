import json
from unittest.mock import patch, MagicMock
import pytest
import ocr_service


def _fake_response(payload: dict):
    """Build a fake Gemini response whose `.text` is JSON."""
    resp = MagicMock()
    resp.text = json.dumps(payload)
    return resp


def test_ocr_available_reflects_env(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert ocr_service.ocr_available() is True
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert ocr_service.ocr_available() is False


def test_extract_returns_fields_and_confidence():
    payload = {
        "fields": {f: None for f in ocr_service.PATIENT_FIELDS},
        "confidence": {f: 0.0 for f in ocr_service.PATIENT_FIELDS},
    }
    payload["fields"]["name"] = "Budi Santoso"
    payload["confidence"]["name"] = 0.97

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = _fake_response(payload)

    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        result = ocr_service.extract_patient_fields(b"\xff\xd8fakejpeg", "image/jpeg")

    assert result["fields"]["name"] == "Budi Santoso"
    assert result["confidence"]["name"] == 0.97
    # the image was sent as an inline-data part with the right mime type
    sent = fake_client.models.generate_content.call_args.kwargs
    assert sent["model"]  # a model id was passed
    image_part = sent["contents"][0]
    assert image_part.inline_data.mime_type == "image/jpeg"


def test_extract_raises_ocrerror_on_sdk_failure():
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("boom")
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRError):
            ocr_service.extract_patient_fields(b"x", "image/png")


def test_extract_raises_ocrerror_on_bad_json():
    resp = MagicMock()
    resp.text = "this is not json"
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = resp
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRError):
            ocr_service.extract_patient_fields(b"x", "image/png")
