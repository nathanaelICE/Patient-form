from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Patient
from schemas import PatientCreate, PatientRead

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(patient_in: PatientCreate, session: Session = Depends(get_session)):
    patient = Patient(**patient_in.model_dump())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.get("", response_model=list[PatientRead])
def list_patients(session: Session = Depends(get_session)):
    patients = session.exec(select(Patient).order_by(Patient.name)).all()
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
