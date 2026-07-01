import pytest
from pydantic import ValidationError
from schemas import ClaimCreate, PatientCreate


def _valid_claim():
    return dict(
        claim_date="2026-06-01",
        claim_amount=1200.50,
        claim_type="outpatient",
        claim_submission_method="online",
    )


def test_claim_defaults_status_pending():
    c = ClaimCreate(**_valid_claim())
    assert c.claim_status == "pending"


def test_claim_lowercases_enums():
    c = ClaimCreate(**{**_valid_claim(), "claim_type": "Inpatient", "claim_submission_method": "PAPER"})
    assert c.claim_type == "inpatient"
    assert c.claim_submission_method == "paper"


def test_claim_rejects_bad_type():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_type": "spaceflight"})


def test_claim_rejects_bad_status():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_status": "maybe"})


def test_claim_rejects_negative_amount():
    with pytest.raises(ValidationError):
        ClaimCreate(**{**_valid_claim(), "claim_amount": -5})


def test_claim_blank_codes_become_none():
    c = ClaimCreate(**{**_valid_claim(), "diagnosis_code": "  ", "provider_id": ""})
    assert c.diagnosis_code is None
    assert c.provider_id is None


def test_patient_employment_validated_and_income_nonnegative():
    p = PatientCreate(name="A", date_of_birth="2000-01-01", gender="male",
                      employment_status="Student", income=50000)
    assert p.employment_status == "student"
    with pytest.raises(ValidationError):
        PatientCreate(name="A", date_of_birth="2000-01-01", gender="male", income=-1)
    with pytest.raises(ValidationError):
        PatientCreate(name="A", date_of_birth="2000-01-01", gender="male",
                      employment_status="freelancer")
