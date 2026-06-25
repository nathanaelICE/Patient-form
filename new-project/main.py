from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Patient Registration")

# TODO: import and include routers (Tab 2)
# TODO: call create_db_and_tables() on startup (Tab 1 + Tab 2)

app.mount("/", StaticFiles(directory="public", html=True), name="static")
