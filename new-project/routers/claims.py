from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, Claim, Visit, AdminUser
from schemas import ClaimCreate, ClaimRead, ClaimUpdate

router = APIRouter(prefix="/api/patients", tags=["claims"])


def _get_live_patient(session: Session, patient_id: int) -> Patient:
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("/{patient_id}/claims", response_model=ClaimRead, status_code=201)
def create_claim(
    patient_id: int,
    claim_in: ClaimCreate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    if claim_in.visit_id is not None:
        visit = session.get(Visit, claim_in.visit_id)
        if not visit or visit.patient_id != patient_id:
            raise HTTPException(status_code=400, detail="visit_id does not belong to this patient")
    claim = Claim(patient_id=patient_id, **claim_in.model_dump())
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


@router.get("/{patient_id}/claims", response_model=list[ClaimRead])
def list_claims(patient_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    _get_live_patient(session, patient_id)
    claims = session.exec(
        select(Claim).where(Claim.patient_id == patient_id).order_by(Claim.claim_date.desc())
    ).all()
    return claims


@router.put("/{patient_id}/claims/{claim_id}", response_model=ClaimRead)
def update_claim(
    patient_id: int,
    claim_id: int,
    claim_in: ClaimUpdate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    claim = session.get(Claim, claim_id)
    if not claim or claim.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Claim not found")
    data = claim_in.model_dump(exclude_unset=True)
    if 'visit_id' in data and data['visit_id'] is not None:
        visit = session.get(Visit, data['visit_id'])
        if not visit or visit.patient_id != patient_id:
            raise HTTPException(status_code=400, detail="visit_id does not belong to this patient")
    for field, value in data.items():
        setattr(claim, field, value)
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


@router.delete("/{patient_id}/claims/{claim_id}", status_code=204)
def delete_claim(
    patient_id: int,
    claim_id: int,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    _get_live_patient(session, patient_id)
    claim = session.get(Claim, claim_id)
    if not claim or claim.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Claim not found")
    session.delete(claim)
    session.commit()
