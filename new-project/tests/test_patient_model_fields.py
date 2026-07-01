from datetime import date
from sqlmodel import Session
from models import Patient


def test_patient_has_new_optional_fields(session: Session):
    patient = Patient(
        name="Budi Santoso",
        date_of_birth=date(1990, 5, 15),
        gender="male",
        national_id="3201234567890001",
        place_of_birth="Jakarta",
        marital_status="married",
        occupation="Teacher",
        religion="Islam",
        nationality="Indonesian",
        blood_type="O+",
        allergies="Penicillin",
        known_conditions="Hypertension",
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    assert patient.id is not None
    assert patient.national_id == "3201234567890001"
    assert patient.blood_type == "O+"


def test_patient_new_fields_default_to_none(session: Session):
    patient = Patient(name="Siti", date_of_birth=date(1985, 3, 20), gender="female")
    session.add(patient)
    session.commit()
    session.refresh(patient)
    assert patient.national_id is None
    assert patient.allergies is None
    assert patient.nationality is None
