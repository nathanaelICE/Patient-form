import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from database import create_db_and_tables, seed_admin, engine
from routers import patients, visits, auth as auth_router
from sqlmodel import Session

# Hide the built-in docs endpoints so we can re-expose them behind auth below.
app = FastAPI(title="Patient Registration", docs_url=None, redoc_url=None, openapi_url=None)
app.state.sessions = {}

DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

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
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin(session)


app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(auth_router.router)


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
