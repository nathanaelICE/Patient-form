from uuid import uuid4
from urllib.parse import urlparse
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, Form, Request
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


@router.get("/patients/new")
def patient_new_page(request: Request):
    """Stub for Task 4 — register patient form."""
    return templates.TemplateResponse(request, "patients/new.html", {
        "is_admin": _is_admin(request),
    })
