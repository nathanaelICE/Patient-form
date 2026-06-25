from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = "sqlite:///registration.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    # TODO: implement after models.py is complete (Tab 1)
    pass


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
