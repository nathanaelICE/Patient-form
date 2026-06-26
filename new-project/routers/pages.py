from uuid import uuid4
from urllib.parse import urlparse
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlmodel import Session, select

from database import get_session
from models import AdminUser, Patient, Visit

router = APIRouter()
templates = Jinja2Templates(directory="templates")
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _is_admin(request: Request) -> bool:
    sid = request.cookies.get("session_id")
    return bool(sid and sid in request.app.state.sessions)


def _safe_next(url: str) -> str:
    """Reject absolute URLs to prevent open redirect."""
    return url if not urlparse(url).netloc else "/patients"


@router.get("/login")
def login_page(request: Request, error: int = 0, next: str = "/patients"):
    return templates.TemplateResponse(request, "auth/login.html", {
        "is_admin": _is_admin(request),
        "error": error,
        "next": next,
    })


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/patients"),
    session: Session = Depends(get_session),
):
    admin = session.exec(select(AdminUser).where(AdminUser.username == username)).first()
    if not admin or not _pwd.verify(password, admin.hashed_password):
        return RedirectResponse(f"/login?error=1&next={next}", status_code=303)
    sid = str(uuid4())
    request.app.state.sessions[sid] = admin.id
    resp = RedirectResponse(_safe_next(next), status_code=303)
    resp.set_cookie("session_id", sid, httponly=True, samesite="strict")
    return resp


@router.post("/logout")
def logout_post(request: Request):
    sid = request.cookies.get("session_id")
    if sid:
        request.app.state.sessions.pop(sid, None)
    resp = RedirectResponse("/patients", status_code=303)
    resp.delete_cookie("session_id")
    return resp


@router.get("/")
def index():
    return RedirectResponse("/patients", status_code=303)


@router.get("/patients")
def patients_list(request: Request, session: Session = Depends(get_session)):
    patients = session.exec(
        select(Patient).where(Patient.deleted_at == None).order_by(Patient.name)
    ).all()
    return templates.TemplateResponse(request, "patients/list.html", {
        "request": request,
        "is_admin": _is_admin(request),
        "patients": patients,
    })


@router.get("/patients/new")
def patients_new_form(request: Request):
    if not _is_admin(request):
        return RedirectResponse("/login?next=/patients/new", status_code=303)
    return templates.TemplateResponse(request, "patients/new.html", {
        "request": request,
        "is_admin": True,
    })


@router.post("/patients")
def patients_create(
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login?next=/patients/new", status_code=303)
    patient = Patient(
        name=name.strip(),
        date_of_birth=date_type.fromisoformat(date_of_birth),
        gender=gender.strip().lower(),
        phone=phone.strip() or None,
    )
    session.add(patient)
    session.commit()
    return RedirectResponse("/patients", status_code=303)


@router.get("/patients/{patient_id}/edit")
def patient_edit_form(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse(request, "patients/edit.html", {
        "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}/delete")
def patient_delete(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.deleted_at = datetime.utcnow()
    session.add(patient)
    session.commit()
    return RedirectResponse("/patients", status_code=303)


@router.get("/patients/{patient_id}/confirm-delete")
def patient_confirm_delete(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/confirm-delete", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse(request, "patients/confirm_delete.html", {
        "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}")
def patient_update(
    patient_id: int,
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.name = name.strip()
    patient.date_of_birth = date_type.fromisoformat(date_of_birth)
    patient.gender = gender.strip().lower()
    patient.phone = phone.strip() or None
    session.add(patient)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/visits/new")
def visit_new_form(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/new", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse(request, "visits/new.html", {
        "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}/visits")
def visit_create(
    patient_id: int,
    request: Request,
    date: str = Form(...),
    chief_complaint: str = Form(...),
    diagnosis: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(
        patient_id=patient_id,
        date=date_type.fromisoformat(date),
        chief_complaint=chief_complaint.strip(),
        diagnosis=diagnosis.strip() or None,
        notes=notes.strip() or None,
    )
    session.add(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/visits/{visit_id}/edit")
def visit_edit_form(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/{visit_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    return templates.TemplateResponse(request, "visits/edit.html", {
        "is_admin": True, "patient": patient, "visit": visit,
    })


@router.post("/patients/{patient_id}/visits/{visit_id}")
def visit_update(
    patient_id: int,
    visit_id: int,
    request: Request,
    date: str = Form(...),
    chief_complaint: str = Form(...),
    diagnosis: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.date = date_type.fromisoformat(date)
    visit.chief_complaint = chief_complaint.strip()
    visit.diagnosis = diagnosis.strip() or None
    visit.notes = notes.strip() or None
    session.add(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/visits/{visit_id}/confirm-delete")
def visit_confirm_delete(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/{visit_id}/confirm-delete", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    return templates.TemplateResponse(request, "visits/confirm_delete.html", {
        "is_admin": True, "patient": patient, "visit": visit,
    })


@router.post("/patients/{patient_id}/visits/{visit_id}/delete")
def visit_delete(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}")
def patient_detail(patient_id: int, request: Request, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visits = session.exec(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc())
    ).all()
    return templates.TemplateResponse(request, "patients/detail.html", {
        "is_admin": _is_admin(request),
        "patient": patient,
        "visits": visits,
    })
