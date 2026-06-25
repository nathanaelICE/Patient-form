import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from passlib.context import CryptContext

from main import app
from database import get_session
import models  # noqa: F401 — registers Patient/Visit/AdminUser with SQLModel metadata

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    app.state.sessions = {}
    yield TestClient(app)
    app.dependency_overrides.clear()
    app.state.sessions = {}


@pytest.fixture(name="admin_client")
def admin_client_fixture(client: TestClient, session: Session):
    admin = models.AdminUser(
        username="testadmin",
        hashed_password=_pwd_context.hash("testpass"),
    )
    session.add(admin)
    session.commit()

    resp = client.post("/api/login", json={"username": "testadmin", "password": "testpass"})
    assert resp.status_code == 200
    return client
