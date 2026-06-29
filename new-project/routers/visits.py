from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, Visit, AdminUser
from schemas import VisitCreate, VisitRead, VisitUpdate

router = APIRouter(prefix="/api/patients", tags=["visits"])


@router.post("/{patient_id}/visits", response_model=VisitRead, status_code=201)
def create_visit(
    patient_id: int,
    visit_in: VisitCreate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(patient_id=patient_id, **visit_in.model_dump())
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


@router.get("/{patient_id}/visits", response_model=list[VisitRead])
def list_visits(patient_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visits = session.exec(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc())
    ).all()
    return visits


@router.put("/{patient_id}/visits/{visit_id}", response_model=VisitRead)
def update_visit(
    patient_id: int,
    visit_id: int,
    visit_in: VisitUpdate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    data = visit_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(visit, field, value)
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


@router.delete("/{patient_id}/visits/{visit_id}", status_code=204)
def delete_visit(
    patient_id: int,
    visit_id: int,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(visit)
    session.commit()
