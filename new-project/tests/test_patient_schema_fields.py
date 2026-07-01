import pytest
from datetime import date
from schemas import PatientCreate


def test_create_accepts_all_new_fields():
    p = PatientCreate(
        name="Budi",
        date_of_birth=date(1990, 5, 15),
        gender="male",
        national_id="3201234567890001",
        place_of_birth="Jakarta",
        marital_status="Married",
        occupation="Teacher",
        religion="Islam",
        nationality="Indonesian",
        blood_type="o+",
        allergies="Penicillin",
        known_conditions="Hypertension",
    )
    assert p.marital_status == "married"   # normalized to lowercase
    assert p.blood_type == "O+"            # normalized to uppercase
    assert p.national_id == "3201234567890001"


def test_national_id_must_be_16_digits():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", national_id="123")


def test_invalid_marital_status_rejected():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", marital_status="single-ish")


def test_invalid_blood_type_rejected():
    with pytest.raises(ValueError):
        PatientCreate(name="X", date_of_birth=date(2000, 1, 1), gender="male", blood_type="Z+")


def test_blank_optional_strings_become_none():
    p = PatientCreate(
        name="X", date_of_birth=date(2000, 1, 1), gender="male",
        occupation="   ", allergies="", national_id=None,
    )
    assert p.occupation is None
    assert p.allergies is None
    assert p.national_id is None
