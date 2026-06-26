from fastapi import Request, Depends, HTTPException
from sqlmodel import Session
from database import get_session
from models import AdminUser


def get_admin(request: Request, session: Session = Depends(get_session)) -> AdminUser:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = request.app.state.sessions.get(session_id)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    admin = session.get(AdminUser, user_id)
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")
    return admin
