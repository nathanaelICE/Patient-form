from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, AdminUser
from schemas import PatientCreate, PatientRead, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(patient_in: PatientCreate, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = Patient(**patient_in.model_dump())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.get("", response_model=list[PatientRead])
def list_patients(session: Session = Depends(get_session)):
    patients = session.exec(
        select(Patient).where(Patient.deleted_at == None).order_by(Patient.name)
    ).all()
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, patient_in: PatientUpdate, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = patient_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(patient, field, value)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.deleted_at = datetime.utcnow()
    session.add(patient)
    session.commit()
