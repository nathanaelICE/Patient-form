from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Patient, Visit
from schemas import VisitCreate, VisitRead

router = APIRouter(prefix="/api/patients", tags=["visits"])


@router.post("/{patient_id}/visits", response_model=VisitRead, status_code=201)
def create_visit(
    patient_id: int,
    visit_in: VisitCreate,
    session: Session = Depends(get_session),
):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visit = Visit(patient_id=patient_id, **visit_in.model_dump())
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


@router.get("/{patient_id}/visits", response_model=list[VisitRead])
def list_visits(patient_id: int, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    visits = session.exec(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc())
    ).all()
    return visits
