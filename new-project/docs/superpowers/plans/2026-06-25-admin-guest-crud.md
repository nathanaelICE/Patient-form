# Admin/Guest UI + Full CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-side session auth with a seeded admin account, then expose Edit and Delete controls for patients and visits in the UI — visible only when logged in as admin.

**Architecture:** A `SessionStore` dict lives on `app.state.sessions`; a `get_admin` FastAPI dependency validates the session cookie on every protected route. The frontend calls `GET /api/me` on page load to detect its role and conditionally injects admin controls (edit/delete buttons, login/logout) into the DOM.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, SQLite, passlib[bcrypt], vanilla HTML/CSS/JS (no bundler).

## Global Constraints

- Python ≥ 3.12
- All new endpoints live under `/api/`
- Session cookie name: `session_id`; flags: `httponly=True`, `samesite="strict"`
- Soft delete for patients: set `deleted_at`; all reads filter `WHERE deleted_at IS NULL`
- Hard delete for visits
- `GET /api/me` never returns 4xx — always `{"is_admin": bool}`
- Protected endpoints return `401` (not `403`) when session is absent or invalid
- No JS framework, no bundler — plain `<script>` blocks in HTML files
- Test runner: `pytest` from project root (`uv run pytest`)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `passlib[bcrypt]` dependency |
| `.env` | Create | `ADMIN_USERNAME`, `ADMIN_PASSWORD` for seeding |
| `models.py` | Modify | Add `AdminUser`; add `deleted_at` to `Patient` |
| `schemas.py` | Modify | Add `PatientUpdate`, `VisitUpdate`, `LoginRequest`, `MeResponse` |
| `deps.py` | Create | `get_admin` dependency |
| `routers/auth.py` | Create | `POST /api/login`, `POST /api/logout`, `GET /api/me` |
| `routers/patients.py` | Modify | Add `PUT /{id}` and `DELETE /{id}` |
| `routers/visits.py` | Modify | Add `PUT /{patient_id}/visits/{visit_id}` and `DELETE /{patient_id}/visits/{visit_id}` |
| `database.py` | Modify | Admin seeding on startup |
| `main.py` | Modify | Init `app.state.sessions`; include auth router |
| `tests/conftest.py` | Modify | Clear sessions between tests; add `admin_client` fixture |
| `tests/test_auth.py` | Create | Auth endpoint tests |
| `tests/test_patients.py` | Modify | Add update + soft-delete tests |
| `tests/test_visits.py` | Modify | Add update + hard-delete tests |
| `public/style.css` | Modify | Admin badge, icon buttons, confirmation strip, login error |
| `public/index.html` | Modify | Role detection, login modal, admin controls on patient list |
| `public/patient.html` | Modify | Role detection, admin controls on patient info + visit history |

---

### Task 1: Add `passlib[bcrypt]` dependency and `.env`

**Files:**
- Modify: `pyproject.toml`
- Create: `.env`

**Interfaces:**
- Produces: `passlib.context.CryptContext` available for import in later tasks

- [ ] **Step 1: Add dependency**

Edit `pyproject.toml` — add `"passlib[bcrypt]>=1.7.4"` to the `dependencies` list:

```toml
[project]
name = "new-project"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.138.0",
    "httpx>=0.28.1",
    "passlib[bcrypt]>=1.7.4",
    "pytest>=9.1.1",
    "sqlmodel>=0.0.38",
    "uvicorn[standard]>=0.49.0",
]
```

- [ ] **Step 2: Install**

```bash
uv sync
```

Expected: resolves and installs `passlib` and `bcrypt`.

- [ ] **Step 3: Create `.env`**

Create `.env` in the project root:

```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
```

- [ ] **Step 4: Verify import works**

```bash
uv run python -c "from passlib.context import CryptContext; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .env
git commit -m "chore: add passlib[bcrypt] dependency and .env for admin seed"
```

---

### Task 2: Add `AdminUser` model and `deleted_at` to `Patient`; update schemas

**Files:**
- Modify: `models.py`
- Modify: `schemas.py`

**Interfaces:**
- Produces:
  - `AdminUser` — SQLModel table with fields `id: Optional[int]`, `username: str`, `hashed_password: str`
  - `Patient.deleted_at: Optional[datetime]` — defaults to `None`
  - `PatientUpdate(BaseModel)` — all fields Optional: `name`, `date_of_birth`, `gender`, `phone`
  - `VisitUpdate(BaseModel)` — all fields Optional: `date`, `chief_complaint`, `diagnosis`, `notes`
  - `LoginRequest(BaseModel)` — `username: str`, `password: str`
  - `MeResponse(BaseModel)` — `is_admin: bool`

- [ ] **Step 1: Write failing test for AdminUser existence**

Add to `tests/test_auth.py` (create the file):

```python
from sqlmodel import Session, select
from models import AdminUser


def test_admin_user_model_exists(session: Session):
    admin = AdminUser(username="testadmin", hashed_password="fakehash")
    session.add(admin)
    session.commit()
    result = session.exec(select(AdminUser).where(AdminUser.username == "testadmin")).first()
    assert result is not None
    assert result.username == "testadmin"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_auth.py::test_admin_user_model_exists -v
```

Expected: FAIL — `ImportError: cannot import name 'AdminUser' from 'models'`

- [ ] **Step 3: Update `models.py`**

```python
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AdminUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    hashed_password: str


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)


class Visit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Update `schemas.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class PatientCreate(BaseModel):
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str] = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    gender: str
    phone: Optional[str]
    created_at: datetime


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None


class VisitCreate(BaseModel):
    date: date
    chief_complaint: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    date: date
    chief_complaint: str
    diagnosis: Optional[str]
    notes: Optional[str]
    created_at: datetime


class VisitUpdate(BaseModel):
    date: Optional[date] = None
    chief_complaint: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    is_admin: bool
```

- [ ] **Step 5: Update `tests/conftest.py` to import `AdminUser`**

The existing `import models` line already imports the whole module, which now includes `AdminUser`, so no change is needed. But we need to clear `app.state.sessions` between tests and add the `admin_client` fixture. Replace `tests/conftest.py` with:

```python
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
```

- [ ] **Step 6: Run test to verify it passes**

```bash
uv run pytest tests/test_auth.py::test_admin_user_model_exists -v
```

Expected: PASS

- [ ] **Step 7: Run full suite to confirm no regressions**

```bash
uv run pytest -v
```

Expected: all previously passing tests still PASS.

- [ ] **Step 8: Commit**

```bash
git add models.py schemas.py tests/conftest.py tests/test_auth.py
git commit -m "feat: add AdminUser model, deleted_at to Patient, update schemas"
```

---

### Task 3: Update `database.py` for seeding; update `main.py`

**Files:**
- Modify: `database.py`
- Modify: `main.py`

**Interfaces:**
- Consumes: `AdminUser` from `models`; `CryptContext` from `passlib`
- Produces: `app.state.sessions: dict[str, int]` initialized on startup; admin row seeded if table empty

- [ ] **Step 1: Write failing test for seeding**

Add to `tests/test_auth.py`:

```python
import os
from sqlmodel import select
from models import AdminUser


def test_admin_seeded_on_startup(session):
    from database import seed_admin
    os.environ["ADMIN_USERNAME"] = "seedtest"
    os.environ["ADMIN_PASSWORD"] = "seedpass"
    seed_admin(session)
    result = session.exec(select(AdminUser)).first()
    assert result is not None
    assert result.username == "seedtest"


def test_admin_not_duplicated_on_second_seed(session):
    from database import seed_admin
    os.environ["ADMIN_USERNAME"] = "seedtest"
    os.environ["ADMIN_PASSWORD"] = "seedpass"
    seed_admin(session)
    seed_admin(session)
    results = session.exec(select(AdminUser)).all()
    assert len(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_auth.py::test_admin_seeded_on_startup tests/test_auth.py::test_admin_not_duplicated_on_second_seed -v
```

Expected: FAIL — `ImportError: cannot import name 'seed_admin' from 'database'`

- [ ] **Step 3: Update `database.py`**

```python
import os
from sqlmodel import SQLModel, create_engine, Session, select
from typing import Generator
from passlib.context import CryptContext

DATABASE_URL = "sqlite:///registration.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_db_and_tables():
    from models import Patient, Visit, AdminUser  # noqa: F401
    SQLModel.metadata.create_all(engine)


def seed_admin(session: Session) -> None:
    from models import AdminUser
    existing = session.exec(select(AdminUser)).first()
    if existing:
        return
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "changeme123")
    admin = AdminUser(username=username, hashed_password=_pwd_context.hash(password))
    session.add(admin)
    session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 4: Update `main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import create_db_and_tables, seed_admin, get_session
from routers import patients, visits
from routers import auth as auth_router
from sqlmodel import Session

app = FastAPI(title="Patient Registration")
app.state.sessions = {}


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with Session(__import__('database').engine) as session:
        seed_admin(session)


app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(auth_router.router)

app.mount("/", StaticFiles(directory="public", html=True), name="static")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_auth.py::test_admin_seeded_on_startup tests/test_auth.py::test_admin_not_duplicated_on_second_seed -v
```

Expected: PASS

- [ ] **Step 6: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS (auth router import will fail until Task 4 creates the file — create a stub if needed: `routers/auth.py` with just `from fastapi import APIRouter; router = APIRouter()`).

- [ ] **Step 7: Commit**

```bash
git add database.py main.py
git commit -m "feat: seed admin on startup, init session store in app.state"
```

---

### Task 4: Create `deps.py` with `get_admin` dependency

**Files:**
- Create: `deps.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `app.state.sessions: dict[str, int]`; `AdminUser` from `models`; `get_session` from `database`
- Produces: `get_admin(request, session) -> AdminUser` — raises `HTTPException(401)` if session cookie absent or invalid

- [ ] **Step 1: Write failing tests**

Add to `tests/test_auth.py`:

```python
from fastapi.testclient import TestClient
from main import app


def test_protected_route_without_session_returns_401(client):
    # Use the patient update endpoint as a proxy for any protected route
    response = client.put("/api/patients/1", json={"name": "X"})
    assert response.status_code == 401


def test_protected_route_with_invalid_cookie_returns_401(client):
    client.cookies.set("session_id", "totally-fake-session-id")
    response = client.put("/api/patients/1", json={"name": "X"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_auth.py::test_protected_route_without_session_returns_401 tests/test_auth.py::test_protected_route_with_invalid_cookie_returns_401 -v
```

Expected: FAIL — PUT endpoint doesn't exist yet (404), not 401.

- [ ] **Step 3: Create `deps.py`**

```python
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
```

- [ ] **Step 4: Commit stub + deps**

```bash
git add deps.py
git commit -m "feat: add get_admin dependency"
```

---

### Task 5: Create `routers/auth.py`

**Files:**
- Create: `routers/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: `AdminUser` from `models`; `LoginRequest`, `MeResponse` from `schemas`; `get_session` from `database`; `app.state.sessions`
- Produces:
  - `POST /api/login` → sets `session_id` cookie, returns `{"ok": true}`
  - `POST /api/logout` → clears session + cookie, returns `{"ok": true}`
  - `GET /api/me` → returns `{"is_admin": bool}` (never 401)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_auth.py`:

```python
def test_login_success(client, session):
    from passlib.context import CryptContext
    from models import AdminUser
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    session.add(AdminUser(username="admin", hashed_password=pwd.hash("secret")))
    session.commit()

    resp = client.post("/api/login", json={"username": "admin", "password": "secret"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert "session_id" in resp.cookies


def test_login_wrong_password(client, session):
    from passlib.context import CryptContext
    from models import AdminUser
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    session.add(AdminUser(username="admin", hashed_password=pwd.hash("secret")))
    session.commit()

    resp = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_logout_clears_session(admin_client):
    resp = admin_client.post("/api/logout")
    assert resp.status_code == 200
    # After logout, a protected route should return 401
    resp2 = admin_client.put("/api/patients/1", json={"name": "X"})
    assert resp2.status_code == 401


def test_me_unauthenticated(client):
    resp = client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json() == {"is_admin": False}


def test_me_authenticated(admin_client):
    resp = admin_client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json() == {"is_admin": True}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_auth.py::test_login_success tests/test_auth.py::test_login_wrong_password tests/test_auth.py::test_login_unknown_user tests/test_auth.py::test_me_unauthenticated tests/test_auth.py::test_me_authenticated tests/test_auth.py::test_logout_clears_session -v
```

Expected: FAIL — router not yet implemented.

- [ ] **Step 3: Create `routers/auth.py`**

```python
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select
from passlib.context import CryptContext

from database import get_session
from models import AdminUser
from schemas import LoginRequest, MeResponse

router = APIRouter(prefix="/api", tags=["auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    admin = session.exec(select(AdminUser).where(AdminUser.username == body.username)).first()
    if not admin or not _pwd_context.verify(body.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = str(uuid4())
    request.app.state.sessions[session_id] = admin.id
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="strict")
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id:
        request.app.state.sessions.pop(session_id, None)
    response.delete_cookie(key="session_id")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in request.app.state.sessions:
        return MeResponse(is_admin=True)
    return MeResponse(is_admin=False)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_auth.py -v
```

Expected: all auth tests PASS.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/auth.py tests/test_auth.py
git commit -m "feat: add auth router (login, logout, me)"
```

---

### Task 6: Add `PUT` and `DELETE` to patients router

**Files:**
- Modify: `routers/patients.py`
- Modify: `tests/test_patients.py`

**Interfaces:**
- Consumes: `get_admin` from `deps`; `PatientUpdate` from `schemas`
- Produces:
  - `PUT /api/patients/{patient_id}` → `PatientRead` (admin only)
  - `DELETE /api/patients/{patient_id}` → `204` (admin only, soft delete)
  - `GET /api/patients` and `GET /api/patients/{id}` filter out soft-deleted rows

- [ ] **Step 1: Write failing tests**

Add to `tests/test_patients.py`:

```python
def test_update_patient(admin_client, session):
    created = admin_client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
    }).json()

    resp = admin_client.put(f"/api/patients/{created['id']}", json={"name": "Budi Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Budi Updated"
    assert resp.json()["gender"] == "male"  # unchanged field preserved


def test_update_patient_not_found(admin_client):
    resp = admin_client.put("/api/patients/9999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_update_patient_requires_auth(client):
    resp = client.put("/api/patients/1", json={"name": "Ghost"})
    assert resp.status_code == 401


def test_delete_patient_soft(admin_client):
    created = admin_client.post("/api/patients", json={
        "name": "Delete Me",
        "date_of_birth": "1990-01-01",
        "gender": "male",
    }).json()
    patient_id = created["id"]

    resp = admin_client.delete(f"/api/patients/{patient_id}")
    assert resp.status_code == 204

    # Patient should not appear in list
    list_resp = admin_client.get("/api/patients")
    names = [p["name"] for p in list_resp.json()]
    assert "Delete Me" not in names

    # GET by ID should also return 404
    get_resp = admin_client.get(f"/api/patients/{patient_id}")
    assert get_resp.status_code == 404


def test_delete_patient_requires_auth(client):
    resp = client.delete("/api/patients/1")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_patients.py::test_update_patient tests/test_patients.py::test_delete_patient_soft -v
```

Expected: FAIL — endpoints don't exist (404/405).

- [ ] **Step 3: Update `routers/patients.py`**

```python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, AdminUser
from schemas import PatientCreate, PatientRead, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(patient_in: PatientCreate, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = Patient(**patient_in.model_dump())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.get("", response_model=list[PatientRead])
def list_patients(session: Session = Depends(get_session)):
    patients = session.exec(
        select(Patient).where(Patient.deleted_at == None).order_by(Patient.name)
    ).all()
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, patient_in: PatientUpdate, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    data = patient_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(patient, field, value)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, session: Session = Depends(get_session), _: AdminUser = Depends(get_admin)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.deleted_at = datetime.utcnow()
    session.add(patient)
    session.commit()
```

**Note:** `create_patient` now requires admin auth. This matches the spec (only admins can register patients).

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_patients.py -v
```

Expected: all patient tests PASS. Note: the existing `test_create_patient*` tests will now fail because they use `client` (not `admin_client`). Update those tests to use `admin_client`:

Update existing patient create tests in `tests/test_patients.py` to replace `client` with `admin_client` in the create/list/get tests that POST patients:

```python
def test_create_patient(admin_client):
    response = admin_client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "phone": "08123456789",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Budi Santoso"
    assert data["id"] is not None


def test_create_patient_without_phone(admin_client):
    response = admin_client.post("/api/patients", json={
        "name": "Siti Rahma",
        "date_of_birth": "1985-03-20",
        "gender": "female",
    })
    assert response.status_code == 201
    assert response.json()["phone"] is None


def test_list_patients_empty(client):
    response = client.get("/api/patients")
    assert response.status_code == 200
    assert response.json() == []


def test_list_patients_returns_all(admin_client):
    admin_client.post("/api/patients", json={"name": "Zara", "date_of_birth": "2000-01-01", "gender": "female"})
    admin_client.post("/api/patients", json={"name": "Andi", "date_of_birth": "1995-06-10", "gender": "male"})
    response = admin_client.get("/api/patients")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Zara" in names
    assert "Andi" in names


def test_list_patients_sorted_by_name(admin_client):
    admin_client.post("/api/patients", json={"name": "Zara", "date_of_birth": "2000-01-01", "gender": "female"})
    admin_client.post("/api/patients", json={"name": "Andi", "date_of_birth": "1995-06-10", "gender": "male"})
    names = [p["name"] for p in admin_client.get("/api/patients").json()]
    assert names == sorted(names)


def test_get_patient_by_id(admin_client):
    created = admin_client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
    }).json()
    response = admin_client.get(f"/api/patients/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Budi Santoso"


def test_get_patient_not_found(client):
    response = client.get("/api/patients/9999")
    assert response.status_code == 404
```

- [ ] **Step 5: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/patients.py tests/test_patients.py
git commit -m "feat: add patient update and soft delete endpoints"
```

---

### Task 7: Add `PUT` and `DELETE` to visits router

**Files:**
- Modify: `routers/visits.py`
- Modify: `tests/test_visits.py`

**Interfaces:**
- Consumes: `get_admin` from `deps`; `VisitUpdate` from `schemas`
- Produces:
  - `PUT /api/patients/{patient_id}/visits/{visit_id}` → `VisitRead` (admin only)
  - `DELETE /api/patients/{patient_id}/visits/{visit_id}` → `204` (admin only, hard delete)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_visits.py` — update `patient` fixture to use `admin_client`, and add new tests:

```python
import pytest


@pytest.fixture
def patient(admin_client):
    resp = admin_client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
    })
    return resp.json()


def test_create_visit(admin_client, patient):
    response = admin_client.post(f"/api/patients/{patient['id']}/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Headache",
        "diagnosis": "Tension headache",
        "notes": "Rest and hydration advised",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["chief_complaint"] == "Headache"
    assert data["patient_id"] == patient["id"]
    assert data["id"] is not None


def test_create_visit_minimal_fields(admin_client, patient):
    response = admin_client.post(f"/api/patients/{patient['id']}/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Fever",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["diagnosis"] is None
    assert data["notes"] is None


def test_create_visit_patient_not_found(admin_client):
    response = admin_client.post("/api/patients/9999/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Fever",
    })
    assert response.status_code == 404


def test_list_visits_empty(client, patient):
    response = client.get(f"/api/patients/{patient['id']}/visits")
    assert response.status_code == 200
    assert response.json() == []


def test_list_visits_returns_all(admin_client, patient):
    admin_client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-01-01", "chief_complaint": "Cough"})
    admin_client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-03-15", "chief_complaint": "Fever"})
    response = admin_client.get(f"/api/patients/{patient['id']}/visits")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_visits_sorted_newest_first(admin_client, patient):
    admin_client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-01-01", "chief_complaint": "Cough"})
    admin_client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-06-15", "chief_complaint": "Fever"})
    visits = admin_client.get(f"/api/patients/{patient['id']}/visits").json()
    dates = [v["date"] for v in visits]
    assert dates == sorted(dates, reverse=True)


def test_list_visits_patient_not_found(client):
    response = client.get("/api/patients/9999/visits")
    assert response.status_code == 404


def test_visits_isolated_between_patients(admin_client, patient):
    other = admin_client.post("/api/patients", json={
        "name": "Siti Rahma", "date_of_birth": "1985-03-20", "gender": "female"
    }).json()
    admin_client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-06-01", "chief_complaint": "Back pain"})
    response = admin_client.get(f"/api/patients/{other['id']}/visits")
    assert response.json() == []


def test_update_visit(admin_client, patient):
    created = admin_client.post(f"/api/patients/{patient['id']}/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Headache",
    }).json()

    resp = admin_client.put(
        f"/api/patients/{patient['id']}/visits/{created['id']}",
        json={"chief_complaint": "Migraine", "diagnosis": "Migraine with aura"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chief_complaint"] == "Migraine"
    assert data["diagnosis"] == "Migraine with aura"
    assert data["date"] == "2024-06-01"  # unchanged field preserved


def test_update_visit_not_found(admin_client, patient):
    resp = admin_client.put(f"/api/patients/{patient['id']}/visits/9999", json={"chief_complaint": "X"})
    assert resp.status_code == 404


def test_update_visit_requires_auth(client, patient):
    resp = client.put(f"/api/patients/{patient['id']}/visits/1", json={"chief_complaint": "X"})
    assert resp.status_code == 401


def test_delete_visit_hard(admin_client, patient):
    created = admin_client.post(f"/api/patients/{patient['id']}/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Cough",
    }).json()
    visit_id = created["id"]

    resp = admin_client.delete(f"/api/patients/{patient['id']}/visits/{visit_id}")
    assert resp.status_code == 204

    visits = admin_client.get(f"/api/patients/{patient['id']}/visits").json()
    assert all(v["id"] != visit_id for v in visits)


def test_delete_visit_requires_auth(client, patient):
    resp = client.delete(f"/api/patients/{patient['id']}/visits/1")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify new ones fail**

```bash
uv run pytest tests/test_visits.py::test_update_visit tests/test_visits.py::test_delete_visit_hard -v
```

Expected: FAIL — endpoints don't exist.

- [ ] **Step 3: Update `routers/visits.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from deps import get_admin
from models import Patient, Visit, AdminUser
from schemas import VisitCreate, VisitRead, VisitUpdate

router = APIRouter(prefix="/api/patients", tags=["visits"])


@router.post("/{patient_id}/visits", response_model=VisitRead, status_code=201)
def create_visit(
    patient_id: int,
    visit_in: VisitCreate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(patient_id=patient_id, **visit_in.model_dump())
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


@router.get("/{patient_id}/visits", response_model=list[VisitRead])
def list_visits(patient_id: int, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visits = session.exec(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc())
    ).all()
    return visits


@router.put("/{patient_id}/visits/{visit_id}", response_model=VisitRead)
def update_visit(
    patient_id: int,
    visit_id: int,
    visit_in: VisitUpdate,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    data = visit_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(visit, field, value)
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


@router.delete("/{patient_id}/visits/{visit_id}", status_code=204)
def delete_visit(
    patient_id: int,
    visit_id: int,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(get_admin),
):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(visit)
    session.commit()
```

- [ ] **Step 4: Run full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add routers/visits.py tests/test_visits.py
git commit -m "feat: add visit update and hard delete endpoints"
```

---

### Task 8: Update `style.css` with new UI components

**Files:**
- Modify: `public/style.css`

**Interfaces:**
- Produces CSS classes:
  - `.admin-badge` — muted blue pill shown in header next to title for admins
  - `.btn-ghost` — transparent button for header Login/Logout
  - `.btn-icon` — small square icon-only button (edit/delete in table cells)
  - `.btn-danger` — red variant for delete confirm button
  - `.confirm-strip` — inline confirmation row that replaces a table row temporarily
  - `.form-error` — red inline error text below a form field
  - `.header-right` — flex wrapper for right side of header (badge + button)

- [ ] **Step 1: Append new styles to `public/style.css`**

Add the following block at the end of `public/style.css`:

```css
/* ── Admin badge ───────────────────────────────────────────────────────────── */
.header-right {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.admin-badge {
  background-color: #bee3f8;
  color: #1a365d;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

/* ── Ghost button (header Login/Logout) ────────────────────────────────────── */
.btn-ghost {
  background: transparent;
  color: #bee3f8;
  border-color: #bee3f8;
}

.btn-ghost:hover {
  background: rgba(255,255,255,0.12);
  color: #fff;
  border-color: #fff;
}

/* ── Icon button (edit / delete in table rows) ─────────────────────────────── */
.btn-icon {
  padding: 0.25rem 0.45rem;
  font-size: 0.8rem;
  border-radius: 5px;
  line-height: 1;
  min-width: 28px;
  min-height: 28px;
}

/* ── Danger button (delete confirmation) ───────────────────────────────────── */
.btn-danger {
  background-color: #e53e3e;
  color: #fff;
  border-color: #e53e3e;
}

.btn-danger:hover {
  background-color: #c53030;
  border-color: #c53030;
}

/* ── Inline confirmation strip ─────────────────────────────────────────────── */
.confirm-strip td {
  background-color: #fff5f5 !important;
  padding: 0.5rem 0.9rem;
}

.confirm-strip-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  font-size: 0.88rem;
  color: #742a2a;
}

/* ── Inline form error ─────────────────────────────────────────────────────── */
.form-error {
  color: #e53e3e;
  font-size: 0.82rem;
  margin-top: 0.25rem;
  display: none;
}

.form-error.visible {
  display: block;
}

/* ── Actions column in tables ──────────────────────────────────────────────── */
.actions-cell {
  white-space: nowrap;
  display: flex;
  gap: 0.35rem;
  align-items: center;
}
```

- [ ] **Step 2: Verify CSS loads without syntax errors**

Start the server and open the app in a browser, or just check via:

```bash
uv run python -c "print('CSS is static, no parse step needed')"
```

Visual check: open `http://localhost:8000` after `uv run uvicorn main:app --reload` and confirm the page still looks correct.

- [ ] **Step 3: Commit**

```bash
git add public/style.css
git commit -m "feat: add admin badge, icon button, confirm strip, form error styles"
```

---

### Task 9: Update `index.html` with role detection, login modal, and admin controls

**Files:**
- Modify: `public/index.html`

**Interfaces:**
- Consumes: `GET /api/me`, `POST /api/login`, `POST /api/logout`, `PUT /api/patients/{id}`, `DELETE /api/patients/{id}`
- Produces: fully functional guest + admin patient list page

- [ ] **Step 1: Replace `public/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Patient Registration</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>

  <header class="app-header">
    <h1 class="app-title">Patient Registration</h1>
    <div class="header-right" id="headerRight">
      <!-- Populated by JS after role detection -->
    </div>
  </header>

  <main class="main-content">
    <div class="table-wrapper">
      <table class="patient-table" id="patientTable">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Gender</th>
            <th>Phone</th>
            <th>Date of Birth</th>
            <th class="admin-col" hidden>Actions</th>
          </tr>
        </thead>
        <tbody id="patientTableBody"></tbody>
      </table>
      <p class="empty-state" id="emptyState">No patients registered yet.</p>
    </div>
  </main>

  <!-- Login Modal -->
  <div class="modal-overlay" id="loginModal" role="dialog" aria-modal="true" aria-labelledby="loginModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="loginModalTitle">Admin Login</h2>
      <form id="loginForm" novalidate>
        <div class="form-group">
          <label for="loginUsername">Username <span class="required">*</span></label>
          <input type="text" id="loginUsername" name="username" required autocomplete="username" />
        </div>
        <div class="form-group">
          <label for="loginPassword">Password <span class="required">*</span></label>
          <input type="password" id="loginPassword" name="password" required autocomplete="current-password" />
          <span class="form-error" id="loginError">Invalid credentials. Please try again.</span>
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Login as Admin</button>
          <button type="button" class="btn btn-secondary" id="cancelLoginBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Register Patient Modal -->
  <div class="modal-overlay" id="registerModal" role="dialog" aria-modal="true" aria-labelledby="registerModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="registerModalTitle">Register Patient</h2>
      <form id="registerForm" novalidate>
        <div class="form-group">
          <label for="regName">Name <span class="required">*</span></label>
          <input type="text" id="regName" name="name" required placeholder="Full name" />
        </div>
        <div class="form-group">
          <label for="regDob">Date of Birth <span class="required">*</span></label>
          <input type="date" id="regDob" name="date_of_birth" required />
        </div>
        <div class="form-group">
          <label for="regGender">Gender <span class="required">*</span></label>
          <select id="regGender" name="gender" required>
            <option value="" disabled selected>Select gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group">
          <label for="regPhone">Phone <span class="optional">(optional)</span></label>
          <input type="text" id="regPhone" name="phone" placeholder="e.g. 08123456789" />
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Submit</button>
          <button type="button" class="btn btn-secondary" id="cancelRegisterBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Edit Patient Modal -->
  <div class="modal-overlay" id="editPatientModal" role="dialog" aria-modal="true" aria-labelledby="editPatientModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="editPatientModalTitle">Edit Patient</h2>
      <form id="editPatientForm" novalidate>
        <input type="hidden" id="editPatientId" />
        <div class="form-group">
          <label for="editName">Name <span class="required">*</span></label>
          <input type="text" id="editName" name="name" required placeholder="Full name" />
        </div>
        <div class="form-group">
          <label for="editDob">Date of Birth <span class="required">*</span></label>
          <input type="date" id="editDob" name="date_of_birth" required />
        </div>
        <div class="form-group">
          <label for="editGender">Gender <span class="required">*</span></label>
          <select id="editGender" name="gender" required>
            <option value="" disabled>Select gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group">
          <label for="editPhone">Phone <span class="optional">(optional)</span></label>
          <input type="text" id="editPhone" name="phone" placeholder="e.g. 08123456789" />
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" class="btn btn-secondary" id="cancelEditPatientBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    var isAdmin = false;
    var patients = [];

    // ── Role detection ────────────────────────────────────────────────────────
    async function detectRole() {
      try {
        var resp = await fetch('/api/me');
        var data = await resp.json();
        isAdmin = data.is_admin === true;
      } catch (e) {
        isAdmin = false;
      }
      renderHeader();
      renderAdminCols();
    }

    function renderHeader() {
      var headerRight = document.getElementById('headerRight');
      if (isAdmin) {
        headerRight.innerHTML =
          '<span class="admin-badge">Admin</span>' +
          '<button class="btn btn-ghost btn-sm" id="logoutBtn">Logout</button>' +
          '<button class="btn btn-primary" id="openRegisterBtn">+ Register Patient</button>';
        document.getElementById('logoutBtn').addEventListener('click', logout);
        document.getElementById('openRegisterBtn').addEventListener('click', openRegisterModal);
      } else {
        headerRight.innerHTML =
          '<button class="btn btn-ghost" id="loginBtn">Login</button>';
        document.getElementById('loginBtn').addEventListener('click', openLoginModal);
      }
    }

    function renderAdminCols() {
      var th = document.querySelector('.admin-col');
      if (th) th.hidden = !isAdmin;
    }

    // ── Logout ────────────────────────────────────────────────────────────────
    async function logout() {
      await fetch('/api/logout', { method: 'POST' });
      isAdmin = false;
      renderHeader();
      renderAdminCols();
      loadPatients();
    }

    // ── Login modal ───────────────────────────────────────────────────────────
    var loginModal = document.getElementById('loginModal');
    var loginForm = document.getElementById('loginForm');
    var loginError = document.getElementById('loginError');

    function openLoginModal() {
      loginModal.hidden = false;
      loginError.classList.remove('visible');
      loginForm.reset();
      document.getElementById('loginUsername').focus();
    }

    function closeLoginModal() {
      loginModal.hidden = true;
      loginForm.reset();
    }

    document.getElementById('cancelLoginBtn').addEventListener('click', closeLoginModal);
    loginModal.addEventListener('click', function(e) { if (e.target === loginModal) closeLoginModal(); });

    loginForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      loginError.classList.remove('visible');
      var body = {
        username: document.getElementById('loginUsername').value.trim(),
        password: document.getElementById('loginPassword').value,
      };
      try {
        var resp = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) {
          loginError.classList.add('visible');
          return;
        }
        closeLoginModal();
        isAdmin = true;
        renderHeader();
        renderAdminCols();
        loadPatients();
      } catch (err) {
        loginError.classList.add('visible');
      }
    });

    // ── Register modal ────────────────────────────────────────────────────────
    var registerModal = document.getElementById('registerModal');
    var registerForm = document.getElementById('registerForm');

    function openRegisterModal() {
      registerModal.hidden = false;
      document.getElementById('regName').focus();
    }

    function closeRegisterModal() {
      registerModal.hidden = true;
      registerForm.reset();
    }

    document.getElementById('cancelRegisterBtn').addEventListener('click', closeRegisterModal);
    registerModal.addEventListener('click', function(e) { if (e.target === registerModal) closeRegisterModal(); });

    registerForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var phone = document.getElementById('regPhone').value.trim();
      var formData = {
        name: document.getElementById('regName').value.trim(),
        date_of_birth: document.getElementById('regDob').value,
        gender: document.getElementById('regGender').value,
      };
      if (phone) formData.phone = phone;
      try {
        var resp = await fetch('/api/patients', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        closeRegisterModal();
        loadPatients();
      } catch (err) {
        console.error('Failed to register patient:', err);
      }
    });

    // ── Edit patient modal ────────────────────────────────────────────────────
    var editPatientModal = document.getElementById('editPatientModal');
    var editPatientForm = document.getElementById('editPatientForm');

    function openEditPatientModal(p) {
      document.getElementById('editPatientId').value = p.id;
      document.getElementById('editName').value = p.name || '';
      document.getElementById('editDob').value = p.date_of_birth || '';
      document.getElementById('editGender').value = p.gender || '';
      document.getElementById('editPhone').value = p.phone || '';
      editPatientModal.hidden = false;
      document.getElementById('editName').focus();
    }

    function closeEditPatientModal() {
      editPatientModal.hidden = true;
      editPatientForm.reset();
    }

    document.getElementById('cancelEditPatientBtn').addEventListener('click', closeEditPatientModal);
    editPatientModal.addEventListener('click', function(e) { if (e.target === editPatientModal) closeEditPatientModal(); });

    editPatientForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var id = document.getElementById('editPatientId').value;
      var phone = document.getElementById('editPhone').value.trim();
      var body = {
        name: document.getElementById('editName').value.trim(),
        date_of_birth: document.getElementById('editDob').value,
        gender: document.getElementById('editGender').value,
        phone: phone || null,
      };
      try {
        var resp = await fetch('/api/patients/' + id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        closeEditPatientModal();
        loadPatients();
      } catch (err) {
        console.error('Failed to update patient:', err);
      }
    });

    // ── Patient list ──────────────────────────────────────────────────────────
    function navigateToPatient(patientId) {
      window.location.href = 'patient.html?id=' + encodeURIComponent(patientId);
    }

    async function loadPatients() {
      try {
        var resp = await fetch('/api/patients');
        patients = await resp.json();
        renderPatients(patients);
      } catch (err) {
        console.error('Failed to load patients:', err);
      }
    }

    function renderPatients(list) {
      var tbody = document.getElementById('patientTableBody');
      var emptyState = document.getElementById('emptyState');
      tbody.innerHTML = '';

      if (!list || list.length === 0) {
        emptyState.style.display = 'block';
        return;
      }
      emptyState.style.display = 'none';

      list.forEach(function(p) {
        var tr = document.createElement('tr');
        tr.classList.add('patient-row');
        tr.setAttribute('tabindex', '0');
        tr.setAttribute('role', 'button');
        tr.setAttribute('aria-label', 'View patient ' + p.name);

        var actionsHtml = '';
        if (isAdmin) {
          actionsHtml = '<td class="actions-cell" onclick="event.stopPropagation()">' +
            '<button class="btn btn-secondary btn-icon" title="Edit patient" onclick="openEditPatientModal(' + JSON.stringify(p) + ')">&#9998;</button>' +
            '<button class="btn btn-danger btn-icon" title="Delete patient" onclick="showDeleteConfirm(this, ' + p.id + ', ' + JSON.stringify(p.name) + ')">&#128465;</button>' +
            '</td>';
        }

        tr.innerHTML =
          '<td>' + (p.id || '') + '</td>' +
          '<td>' + (p.name || '') + '</td>' +
          '<td>' + (p.gender || '') + '</td>' +
          '<td>' + (p.phone || '-') + '</td>' +
          '<td>' + (p.date_of_birth || '') + '</td>' +
          actionsHtml;

        tr.addEventListener('click', function() { navigateToPatient(p.id); });
        tr.addEventListener('keydown', function(e) {
          if (e.key === 'Enter' || e.key === ' ') navigateToPatient(p.id);
        });

        tbody.appendChild(tr);
      });
    }

    function showDeleteConfirm(btn, patientId, patientName) {
      var tr = btn.closest('tr');
      var colCount = tr.cells.length;
      var confirmTr = document.createElement('tr');
      confirmTr.classList.add('confirm-strip');
      confirmTr.innerHTML =
        '<td colspan="' + colCount + '">' +
        '<div class="confirm-strip-content">' +
        '<span>Delete <strong>' + patientName + '</strong>? This cannot be undone.</span>' +
        '<button class="btn btn-danger btn-icon" onclick="confirmDeletePatient(' + patientId + ', this.closest(\'tr\'))">Confirm</button>' +
        '<button class="btn btn-secondary btn-icon" onclick="this.closest(\'tr\').remove()">Cancel</button>' +
        '</div></td>';
      tr.after(confirmTr);
    }

    async function confirmDeletePatient(patientId, confirmTr) {
      try {
        var resp = await fetch('/api/patients/' + patientId, { method: 'DELETE' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        confirmTr.remove();
        loadPatients();
      } catch (err) {
        console.error('Failed to delete patient:', err);
      }
    }

    // ── Keyboard close modals ─────────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        if (!loginModal.hidden) closeLoginModal();
        if (!registerModal.hidden) closeRegisterModal();
        if (!editPatientModal.hidden) closeEditPatientModal();
      }
    });

    // ── Init ──────────────────────────────────────────────────────────────────
    detectRole().then(loadPatients);
  </script>

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add public/index.html
git commit -m "feat: add role detection, login modal, admin controls to index.html"
```

---

### Task 10: Update `patient.html` with admin controls

**Files:**
- Modify: `public/patient.html`

**Interfaces:**
- Consumes: `GET /api/me`, `PUT /api/patients/{id}`, `PUT /api/patients/{id}/visits/{visit_id}`, `DELETE /api/patients/{id}/visits/{visit_id}`
- Produces: fully functional guest + admin patient detail page

- [ ] **Step 1: Replace `public/patient.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Patient Detail</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>

  <header class="app-header">
    <a href="index.html" class="back-link">&larr; Back to list</a>
    <h1 class="app-title">Patient Detail</h1>
    <div class="header-right" id="headerRight"></div>
  </header>

  <main class="main-content">

    <!-- Patient Info Section -->
    <section class="patient-info card" id="patientInfo">
      <div class="section-header">
        <h2 class="section-title">Patient Information</h2>
        <button class="btn btn-secondary admin-only" id="editPatientInfoBtn" hidden>&#9998; Edit</button>
      </div>
      <dl class="info-grid">
        <dt>Name</dt>       <dd id="infoName"><span class="placeholder">—</span></dd>
        <dt>Date of Birth</dt> <dd id="infoDob"><span class="placeholder">—</span></dd>
        <dt>Gender</dt>     <dd id="infoGender"><span class="placeholder">—</span></dd>
        <dt>Phone</dt>      <dd id="infoPhone"><span class="placeholder">—</span></dd>
      </dl>
    </section>

    <!-- Visit History Section -->
    <section class="visit-history card">
      <div class="section-header">
        <h2 class="section-title">Visit History</h2>
        <button class="btn btn-primary admin-only" id="openAddVisitBtn" hidden>+ Add Visit</button>
      </div>
      <div class="table-wrapper">
        <table class="visit-table" id="visitTable">
          <thead>
            <tr>
              <th>Date</th>
              <th>Chief Complaint</th>
              <th>Diagnosis</th>
              <th>Notes</th>
              <th class="admin-col" hidden>Actions</th>
            </tr>
          </thead>
          <tbody id="visitTableBody"></tbody>
        </table>
        <p class="empty-state" id="visitEmptyState">No visits recorded yet.</p>
      </div>
    </section>

  </main>

  <!-- Edit Patient Modal -->
  <div class="modal-overlay" id="editPatientModal" role="dialog" aria-modal="true" aria-labelledby="editPatientModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="editPatientModalTitle">Edit Patient</h2>
      <form id="editPatientForm" novalidate>
        <div class="form-group">
          <label for="editName">Name <span class="required">*</span></label>
          <input type="text" id="editName" name="name" required placeholder="Full name" />
        </div>
        <div class="form-group">
          <label for="editDob">Date of Birth <span class="required">*</span></label>
          <input type="date" id="editDob" name="date_of_birth" required />
        </div>
        <div class="form-group">
          <label for="editGender">Gender <span class="required">*</span></label>
          <select id="editGender" name="gender" required>
            <option value="" disabled>Select gender</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="form-group">
          <label for="editPhone">Phone <span class="optional">(optional)</span></label>
          <input type="text" id="editPhone" name="phone" placeholder="e.g. 08123456789" />
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" class="btn btn-secondary" id="cancelEditPatientBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Add Visit Modal -->
  <div class="modal-overlay" id="addVisitModal" role="dialog" aria-modal="true" aria-labelledby="addVisitModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="addVisitModalTitle">Add Visit</h2>
      <form id="addVisitForm" novalidate>
        <div class="form-group">
          <label for="visitDate">Date <span class="required">*</span></label>
          <input type="date" id="visitDate" name="date" required />
        </div>
        <div class="form-group">
          <label for="visitComplaint">Chief Complaint <span class="required">*</span></label>
          <input type="text" id="visitComplaint" name="chief_complaint" required placeholder="e.g. Headache, fever" />
        </div>
        <div class="form-group">
          <label for="visitDiagnosis">Diagnosis <span class="optional">(optional)</span></label>
          <input type="text" id="visitDiagnosis" name="diagnosis" placeholder="e.g. Migraine" />
        </div>
        <div class="form-group">
          <label for="visitNotes">Notes <span class="optional">(optional)</span></label>
          <textarea id="visitNotes" name="notes" rows="3" placeholder="Additional notes..."></textarea>
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Submit</button>
          <button type="button" class="btn btn-secondary" id="cancelAddVisitBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Edit Visit Modal -->
  <div class="modal-overlay" id="editVisitModal" role="dialog" aria-modal="true" aria-labelledby="editVisitModalTitle" hidden>
    <div class="modal-dialog">
      <h2 class="modal-title" id="editVisitModalTitle">Edit Visit</h2>
      <form id="editVisitForm" novalidate>
        <input type="hidden" id="editVisitId" />
        <div class="form-group">
          <label for="editVisitDate">Date <span class="required">*</span></label>
          <input type="date" id="editVisitDate" name="date" required />
        </div>
        <div class="form-group">
          <label for="editVisitComplaint">Chief Complaint <span class="required">*</span></label>
          <input type="text" id="editVisitComplaint" name="chief_complaint" required placeholder="e.g. Headache, fever" />
        </div>
        <div class="form-group">
          <label for="editVisitDiagnosis">Diagnosis <span class="optional">(optional)</span></label>
          <input type="text" id="editVisitDiagnosis" name="diagnosis" placeholder="e.g. Migraine" />
        </div>
        <div class="form-group">
          <label for="editVisitNotes">Notes <span class="optional">(optional)</span></label>
          <textarea id="editVisitNotes" name="notes" rows="3" placeholder="Additional notes..."></textarea>
        </div>
        <div class="modal-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" class="btn btn-secondary" id="cancelEditVisitBtn">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    var isAdmin = false;
    var currentPatient = null;

    function getPatientId() {
      return new URLSearchParams(window.location.search).get('id');
    }

    // ── Role detection ────────────────────────────────────────────────────────
    async function detectRole() {
      try {
        var resp = await fetch('/api/me');
        var data = await resp.json();
        isAdmin = data.is_admin === true;
      } catch (e) {
        isAdmin = false;
      }
      renderHeader();
      renderAdminControls();
    }

    function renderHeader() {
      var headerRight = document.getElementById('headerRight');
      if (isAdmin) {
        headerRight.innerHTML =
          '<span class="admin-badge">Admin</span>' +
          '<button class="btn btn-ghost" id="logoutBtn">Logout</button>';
        document.getElementById('logoutBtn').addEventListener('click', logout);
      } else {
        headerRight.innerHTML = '';
      }
    }

    function renderAdminControls() {
      document.getElementById('editPatientInfoBtn').hidden = !isAdmin;
      document.getElementById('openAddVisitBtn').hidden = !isAdmin;
      var th = document.querySelector('.admin-col');
      if (th) th.hidden = !isAdmin;
    }

    async function logout() {
      await fetch('/api/logout', { method: 'POST' });
      window.location.reload();
    }

    // ── Patient info ──────────────────────────────────────────────────────────
    async function loadPatientInfo() {
      var patientId = getPatientId();
      if (!patientId) { document.getElementById('infoName').textContent = 'Unknown patient'; return; }
      try {
        var resp = await fetch('/api/patients/' + patientId);
        currentPatient = await resp.json();
        renderPatientInfo(currentPatient);
      } catch (err) {
        console.error('Failed to load patient info:', err);
      }
    }

    function renderPatientInfo(patient) {
      document.getElementById('infoName').textContent = patient.name || '—';
      document.getElementById('infoDob').textContent = patient.date_of_birth || '—';
      document.getElementById('infoGender').textContent = patient.gender || '—';
      document.getElementById('infoPhone').textContent = patient.phone || '—';
      document.title = 'Patient — ' + (patient.name || 'Detail');
    }

    // ── Edit patient modal ────────────────────────────────────────────────────
    var editPatientModal = document.getElementById('editPatientModal');
    var editPatientForm = document.getElementById('editPatientForm');

    document.getElementById('editPatientInfoBtn').addEventListener('click', function() {
      if (!currentPatient) return;
      document.getElementById('editName').value = currentPatient.name || '';
      document.getElementById('editDob').value = currentPatient.date_of_birth || '';
      document.getElementById('editGender').value = currentPatient.gender || '';
      document.getElementById('editPhone').value = currentPatient.phone || '';
      editPatientModal.hidden = false;
      document.getElementById('editName').focus();
    });

    document.getElementById('cancelEditPatientBtn').addEventListener('click', function() {
      editPatientModal.hidden = true; editPatientForm.reset();
    });
    editPatientModal.addEventListener('click', function(e) {
      if (e.target === editPatientModal) { editPatientModal.hidden = true; editPatientForm.reset(); }
    });

    editPatientForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var id = getPatientId();
      var phone = document.getElementById('editPhone').value.trim();
      var body = {
        name: document.getElementById('editName').value.trim(),
        date_of_birth: document.getElementById('editDob').value,
        gender: document.getElementById('editGender').value,
        phone: phone || null,
      };
      try {
        var resp = await fetch('/api/patients/' + id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        currentPatient = await resp.json();
        renderPatientInfo(currentPatient);
        editPatientModal.hidden = true;
        editPatientForm.reset();
      } catch (err) {
        console.error('Failed to update patient:', err);
      }
    });

    // ── Visit history ─────────────────────────────────────────────────────────
    async function loadVisits() {
      var patientId = getPatientId();
      if (!patientId) return;
      try {
        var resp = await fetch('/api/patients/' + patientId + '/visits');
        renderVisits(await resp.json());
      } catch (err) {
        console.error('Failed to load visits:', err);
      }
    }

    function renderVisits(visits) {
      var tbody = document.getElementById('visitTableBody');
      var emptyState = document.getElementById('visitEmptyState');
      tbody.innerHTML = '';

      if (!visits || visits.length === 0) {
        emptyState.style.display = 'block';
        return;
      }
      emptyState.style.display = 'none';

      visits.forEach(function(v) {
        var tr = document.createElement('tr');
        var actionsHtml = '';
        if (isAdmin) {
          actionsHtml = '<td class="actions-cell">' +
            '<button class="btn btn-secondary btn-icon" title="Edit visit" onclick="openEditVisitModal(' + JSON.stringify(v) + ')">&#9998;</button>' +
            '<button class="btn btn-danger btn-icon" title="Delete visit" onclick="showDeleteVisitConfirm(this, ' + v.id + ')">&#128465;</button>' +
            '</td>';
        }
        tr.innerHTML =
          '<td>' + (v.date || '') + '</td>' +
          '<td>' + (v.chief_complaint || '') + '</td>' +
          '<td>' + (v.diagnosis || '-') + '</td>' +
          '<td>' + (v.notes || '-') + '</td>' +
          actionsHtml;
        tbody.appendChild(tr);
      });
    }

    // ── Add visit modal ───────────────────────────────────────────────────────
    var addVisitModal = document.getElementById('addVisitModal');
    var addVisitForm = document.getElementById('addVisitForm');

    document.getElementById('openAddVisitBtn').addEventListener('click', function() {
      addVisitModal.hidden = false;
      document.getElementById('visitDate').focus();
    });
    document.getElementById('cancelAddVisitBtn').addEventListener('click', function() {
      addVisitModal.hidden = true; addVisitForm.reset();
    });
    addVisitModal.addEventListener('click', function(e) {
      if (e.target === addVisitModal) { addVisitModal.hidden = true; addVisitForm.reset(); }
    });

    addVisitForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var patientId = getPatientId();
      var body = {
        date: document.getElementById('visitDate').value,
        chief_complaint: document.getElementById('visitComplaint').value.trim(),
        diagnosis: document.getElementById('visitDiagnosis').value.trim() || null,
        notes: document.getElementById('visitNotes').value.trim() || null,
      };
      try {
        var resp = await fetch('/api/patients/' + patientId + '/visits', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        addVisitModal.hidden = true;
        addVisitForm.reset();
        loadVisits();
      } catch (err) {
        console.error('Failed to add visit:', err);
      }
    });

    // ── Edit visit modal ──────────────────────────────────────────────────────
    var editVisitModal = document.getElementById('editVisitModal');
    var editVisitForm = document.getElementById('editVisitForm');

    function openEditVisitModal(v) {
      document.getElementById('editVisitId').value = v.id;
      document.getElementById('editVisitDate').value = v.date || '';
      document.getElementById('editVisitComplaint').value = v.chief_complaint || '';
      document.getElementById('editVisitDiagnosis').value = v.diagnosis || '';
      document.getElementById('editVisitNotes').value = v.notes || '';
      editVisitModal.hidden = false;
      document.getElementById('editVisitDate').focus();
    }

    document.getElementById('cancelEditVisitBtn').addEventListener('click', function() {
      editVisitModal.hidden = true; editVisitForm.reset();
    });
    editVisitModal.addEventListener('click', function(e) {
      if (e.target === editVisitModal) { editVisitModal.hidden = true; editVisitForm.reset(); }
    });

    editVisitForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      var patientId = getPatientId();
      var visitId = document.getElementById('editVisitId').value;
      var body = {
        date: document.getElementById('editVisitDate').value,
        chief_complaint: document.getElementById('editVisitComplaint').value.trim(),
        diagnosis: document.getElementById('editVisitDiagnosis').value.trim() || null,
        notes: document.getElementById('editVisitNotes').value.trim() || null,
      };
      try {
        var resp = await fetch('/api/patients/' + patientId + '/visits/' + visitId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        editVisitModal.hidden = true;
        editVisitForm.reset();
        loadVisits();
      } catch (err) {
        console.error('Failed to update visit:', err);
      }
    });

    // ── Delete visit ──────────────────────────────────────────────────────────
    function showDeleteVisitConfirm(btn, visitId) {
      var tr = btn.closest('tr');
      var colCount = tr.cells.length;
      var confirmTr = document.createElement('tr');
      confirmTr.classList.add('confirm-strip');
      confirmTr.innerHTML =
        '<td colspan="' + colCount + '">' +
        '<div class="confirm-strip-content">' +
        '<span>Delete this visit? This cannot be undone.</span>' +
        '<button class="btn btn-danger btn-icon" onclick="confirmDeleteVisit(' + visitId + ', this.closest(\'tr\'))">Confirm</button>' +
        '<button class="btn btn-secondary btn-icon" onclick="this.closest(\'tr\').remove()">Cancel</button>' +
        '</div></td>';
      tr.after(confirmTr);
    }

    async function confirmDeleteVisit(visitId, confirmTr) {
      var patientId = getPatientId();
      try {
        var resp = await fetch('/api/patients/' + patientId + '/visits/' + visitId, { method: 'DELETE' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        confirmTr.remove();
        loadVisits();
      } catch (err) {
        console.error('Failed to delete visit:', err);
      }
    }

    // ── Keyboard close ────────────────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        if (!editPatientModal.hidden) { editPatientModal.hidden = true; editPatientForm.reset(); }
        if (!addVisitModal.hidden) { addVisitModal.hidden = true; addVisitForm.reset(); }
        if (!editVisitModal.hidden) { editVisitModal.hidden = true; editVisitForm.reset(); }
      }
    });

    // ── Init ──────────────────────────────────────────────────────────────────
    detectRole().then(function() {
      loadPatientInfo();
      loadVisits();
    });
  </script>

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add public/patient.html
git commit -m "feat: add role detection and admin controls to patient.html"
```

---

### Task 11: Final integration verification

**Files:** none — verification only

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS. Count should include auth, patient update/delete, and visit update/delete tests.

- [ ] **Step 2: Start server and smoke-test manually**

```bash
uv run uvicorn main:app --reload
```

Open `http://localhost:8000`:
- Guest view: no Register button, no edit/delete columns, Login button in header.
- Click Login → enter `admin` / `changeme123` (from `.env`) → Admin badge + Logout appear, Register button appears, Actions column appears.
- Register a patient → appears in list.
- Click ✏️ Edit → modal pre-filled → save → row updates in place.
- Click 🗑️ Delete → confirmation strip → Confirm → row disappears.
- Click a patient row → navigate to `patient.html`.
- On patient detail: Edit button on info card, Add Visit + edit/delete on each visit row.
- Logout → controls disappear.

- [ ] **Step 3: Tag the release**

```bash
git tag v0.2.0 -m "feat: admin/guest CRUD with session auth"
```
