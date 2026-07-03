import asyncio
import os
import secrets
import anyio
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from database import create_db_and_tables, seed_admin, engine
from routers import patients, visits, claims, auth as auth_router, ocr as ocr_router
from sqlmodel import Session, select
from models import OcrJob
import ocr_jobs

# Hide the built-in docs endpoints so we can re-expose them behind auth below.
app = FastAPI(title="Patient Registration", docs_url=None, redoc_url=None, openapi_url=None)
app.state.sessions = {}

DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

POLL_SECONDS = 1.0


def _worker_session() -> Session:
    return Session(engine)


def _process_one(job_id: int) -> None:
    # Runs in a worker thread. Opens its OWN session so no Session ever crosses
    # the thread boundary (SQLAlchemy sessions are not thread-safe).
    with _worker_session() as session:
        ocr_jobs.process_job(session, job_id)


async def _process_pending_once() -> None:
    # List pending IDs with a short-lived session that is closed before any
    # thread runs; then hand each ID to its own per-thread session.
    with _worker_session() as session:
        job_ids = [j.id for j in session.exec(select(OcrJob).where(OcrJob.status == "pending")).all()]
    for job_id in job_ids:
        await anyio.to_thread.run_sync(_process_one, job_id)


async def _ocr_worker_loop(stop: asyncio.Event) -> None:
    with _worker_session() as session:
        ocr_jobs.requeue_orphans(session)
    while not stop.is_set():
        try:
            await _process_pending_once()
        except Exception:
            # Never let a transient DB/OCR error kill the loop.
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
        except asyncio.TimeoutError:
            pass


_basic = HTTPBasic()


def require_docs_auth(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    """Guard the API docs with the admin username/password (HTTP Basic)."""
    expected_user = os.environ.get("ADMIN_USERNAME", "admin")
    expected_pass = os.environ.get("ADMIN_PASSWORD", "changeme123")
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin(session)
    app.state.ocr_stop = asyncio.Event()
    app.state.ocr_worker = asyncio.create_task(_ocr_worker_loop(app.state.ocr_stop))


@app.on_event("shutdown")
async def on_shutdown():
    stop = getattr(app.state, "ocr_stop", None)
    worker = getattr(app.state, "ocr_worker", None)
    if stop is not None:
        stop.set()
    if worker is not None:
        try:
            await worker
        except Exception:
            pass


app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(claims.router)
app.include_router(auth_router.router)
app.include_router(ocr_router.router)


# API docs, re-exposed behind HTTP Basic auth (admin credentials).
@app.get("/openapi.json", include_in_schema=False)
def protected_openapi(_: None = Depends(require_docs_auth)):
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False)
def protected_swagger(_: None = Depends(require_docs_auth)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Patient Registration — API docs")


@app.get("/redoc", include_in_schema=False)
def protected_redoc(_: None = Depends(require_docs_auth)):
    return get_redoc_html(openapi_url="/openapi.json", title="Patient Registration — API docs")


# Serve the built React SPA (production). In dev, use the Vite server on :5173.
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # API routes are matched above; everything else returns the SPA shell.
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
