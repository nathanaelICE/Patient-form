from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import create_db_and_tables, seed_admin, get_session, engine
from routers import patients, visits, auth as auth_router, pages
from sqlmodel import Session

app = FastAPI(title="Patient Registration")
app.state.sessions = {}


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(engine) as session:
        seed_admin(session)


app.include_router(pages.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(auth_router.router)

app.mount("/static", StaticFiles(directory="public"), name="static")
