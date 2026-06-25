from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import create_db_and_tables
from routers import patients, visits, auth as auth_router

app = FastAPI(title="Patient Registration")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(auth_router.router)

app.mount("/", StaticFiles(directory="public", html=True), name="static")
