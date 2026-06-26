import os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select
from passlib.context import CryptContext

from database import get_session
from models import AdminUser
from schemas import LoginRequest, MeResponse

COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "1") != "0"

router = APIRouter(prefix="/api", tags=["auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    admin = session.exec(select(AdminUser).where(AdminUser.username == body.username)).first()
    if not admin or not _pwd_context.verify(body.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = str(uuid4())
    request.app.state.sessions[session_id] = admin.id
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="strict", secure=COOKIE_SECURE)
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id:
        request.app.state.sessions.pop(session_id, None)
    response.delete_cookie(key="session_id")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in request.app.state.sessions:
        return MeResponse(is_admin=True)
    return MeResponse(is_admin=False)
