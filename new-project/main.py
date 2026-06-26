import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from database import create_db_and_tables, seed_admin, engine
from routers import patients, visits, auth as auth_router
from sqlmodel import Session

app = FastAPI(title="Patient Registration")
app.state.sessions = {}

DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin(session)


app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(auth_router.router)

# Serve the built React SPA (production). In dev, use the Vite server on :5173.
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # API routes are matched above; everything else returns the SPA shell.
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
