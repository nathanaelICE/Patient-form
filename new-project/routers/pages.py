from uuid import uuid4
from urllib.parse import urlparse
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from database import get_session
from models import AdminUser, Patient, Visit

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _is_admin(request: Request) -> bool:
    sid = request.cookies.get("session_id")
    return bool(sid and sid in request.app.state.sessions)


def _safe_next(url: str) -> str:
    """Reject absolute URLs to prevent open redirect."""
    return url if not urlparse(url).netloc else "/patients"
