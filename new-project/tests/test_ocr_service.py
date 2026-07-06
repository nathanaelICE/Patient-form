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


def test_is_rate_limit_classifies_errors():
    class Coded(Exception):
        code = 429

    assert ocr_service._is_rate_limit(Coded("nope")) is True
    assert ocr_service._is_rate_limit(RuntimeError("429 RESOURCE_EXHAUSTED: quota")) is True
    assert ocr_service._is_rate_limit(RuntimeError("please slow down, rate limit")) is True
    assert ocr_service._is_rate_limit(RuntimeError("could not parse json")) is False


def _valid_payload():
    payload = {
        "fields": {f: None for f in ocr_service.PATIENT_FIELDS},
        "confidence": {f: 0.0 for f in ocr_service.PATIENT_FIELDS},
    }
    payload["fields"]["name"] = "Budi"
    return payload


def test_extract_retries_on_rate_limit_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return _fake_response(_valid_payload())

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = flaky
    monkeypatch.setattr(ocr_service.time, "sleep", lambda _s: None)
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        result = ocr_service.extract_patient_fields(b"x", "image/png")

    assert calls["n"] == 3
    assert result["fields"]["name"] == "Budi"


def test_extract_raises_ratelimit_after_max_attempts(monkeypatch):
    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr(ocr_service.time, "sleep", lambda _s: None)
    monkeypatch.setattr(ocr_service, "RATE_LIMIT_MAX_ATTEMPTS", 3)
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRRateLimitError):
            ocr_service.extract_patient_fields(b"x", "image/png")


def test_extract_does_not_retry_non_rate_limit(monkeypatch):
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("boom")

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = boom
    monkeypatch.setattr(ocr_service.time, "sleep", lambda _s: None)
    with patch.object(ocr_service, "_get_client", return_value=fake_client):
        with pytest.raises(ocr_service.OCRError):
            ocr_service.extract_patient_fields(b"x", "image/png")
    assert calls["n"] == 1  # no retries for non-rate-limit errors
