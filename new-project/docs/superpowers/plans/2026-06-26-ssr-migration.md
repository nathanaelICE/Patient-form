# SSR Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two client-side JS HTML pages with FastAPI + Jinja2 server-side rendering using clean URLs and the POST-Redirect-GET pattern for all mutations.

**Architecture:** A new `routers/pages.py` owns all HTML-serving routes. Jinja2 templates in `templates/` extend `base.html`. The existing `/api/` JSON routes are untouched. Auth is checked inline per route via `_is_admin(request)`, redirecting to `/login?next=<path>` when unauthorized.

**Tech Stack:** FastAPI, Jinja2, python-multipart, SQLModel (SQLite), pytest + FastAPI TestClient

## Global Constraints

- Zero JavaScript in any template after migration
- All `/api/` routes stay untouched and functional
- POST-Redirect-GET (PRG) pattern for all form submissions — always redirect with status 303
- Unauthenticated access to admin-only pages → redirect to `/login?next=<path>`
- CSS served at `/static/style.css` (StaticFiles mounts `public/` at `/static`)
- `next` param after login must be validated as a relative URL (no `netloc`) to prevent open redirect
- Seed admin credentials: username `admin`, password `changeme123` (or env `ADMIN_USERNAME`/`ADMIN_PASSWORD`)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `routers/pages.py` | **Create** | All HTML-serving routes + `_is_admin` helper |
| `templates/base.html` | **Create** | Shared layout: header, CSS link, block slots |
| `templates/auth/login.html` | **Create** | Login form |
| `templates/patients/list.html` | **Create** | Patient table |
| `templates/patients/new.html` | **Create** | Register patient form |
| `templates/patients/detail.html` | **Create** | Patient info card + visit history table |
| `templates/patients/edit.html` | **Create** | Edit patient form |
| `templates/patients/confirm_delete.html` | **Create** | Patient delete confirmation |
| `templates/visits/new.html` | **Create** | Add visit form |
| `templates/visits/edit.html` | **Create** | Edit visit form |
| `templates/visits/confirm_delete.html` | **Create** | Visit delete confirmation |
| `tests/test_pages.py` | **Create** | Page route tests |
| `main.py` | **Modify** | Register `pages.router`; change StaticFiles mount to `/static` |
| `public/index.html` | **Delete** | Replaced by templates |
| `public/patient.html` | **Delete** | Replaced by templates |

---

### Task 1: Install dependencies, scaffold pages.py and base.html, update main.py

**Files:**
- Create: `routers/pages.py`
- Create: `templates/base.html`
- Modify: `main.py`

**Interfaces:**
- Produces: `templates` (Jinja2Templates instance) and `router` (APIRouter) importable from `routers.pages`
- Produces: `/static/style.css` accessible in browser
- Produces: `_is_admin(request: Request) -> bool` helper used by all subsequent tasks

- [ ] **Step 1: Install Jinja2 and python-multipart**

```bash
pip install jinja2 python-multipart
```

Expected: both packages install without error. Verify:
```bash
python -c "import jinja2, multipart; print('ok')"
```

- [ ] **Step 2: Create `routers/pages.py` skeleton**

```python
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
```

- [ ] **Step 3: Update `main.py`**

Replace the entire file:

```python
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
```

Note: `pages.router` must be registered before `app.mount("/static", ...)` so page routes take priority.

- [ ] **Step 4: Create `templates/` directory and `templates/base.html`**

```bash
mkdir -p templates/auth templates/patients templates/visits
```

`templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{% block title %}Patient Registration{% endblock %}</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>

  <header class="app-header">
    <h1 class="app-title">{% block header_title %}Patient Registration{% endblock %}</h1>
    <div class="header-right">
      {% if is_admin %}
        <span class="admin-badge">Admin</span>
        <form method="POST" action="/logout" style="display:inline">
          <button type="submit" class="btn btn-ghost btn-sm">Logout</button>
        </form>
        {% block admin_header_actions %}{% endblock %}
      {% else %}
        <a href="/login" class="btn btn-ghost">Login</a>
      {% endif %}
    </div>
  </header>

  <main class="main-content">
    {% block content %}{% endblock %}
  </main>

</body>
</html>
```

- [ ] **Step 5: Verify app still starts**

```bash
uvicorn main:app --reload
```

Expected: server starts, no import errors. Visit `http://localhost:8000/static/style.css` — CSS file loads. Existing `/api/patients` still returns JSON.

- [ ] **Step 6: Commit**

```bash
git add routers/pages.py templates/base.html main.py
git commit -m "feat: scaffold Jinja2 pages router and base template"
```

---

### Task 2: Auth pages — login form, POST login, POST logout

**Files:**
- Modify: `routers/pages.py` (add auth routes)
- Create: `templates/auth/login.html`
- Create: `tests/test_pages.py`

**Interfaces:**
- Consumes: `_is_admin`, `_safe_next`, `templates`, `router` from Task 1; `AdminUser` model; `get_session` dep; `passlib.context.CryptContext`
- Produces: `GET /login`, `POST /login`, `POST /logout`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pages.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

# ── Auth ──────────────────────────────────────────────────────────────────────

def test_login_page_renders(client: TestClient):
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Admin Login" in resp.content


def test_login_bad_credentials_redirects_with_error(client: TestClient):
    resp = client.post(
        "/login",
        data={"username": "wrong", "password": "wrong", "next": "/patients"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]
    assert "error=1" in resp.headers["location"]


def test_login_success_sets_cookie_and_redirects(admin_client: TestClient):
    # admin_client fixture already logged in via /api/login
    # Verify the session cookie is present by hitting a protected page
    resp = admin_client.get("/patients/new", follow_redirects=False)
    assert resp.status_code == 200


def test_logout_clears_session_and_redirects(admin_client: TestClient):
    resp = admin_client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/patients"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd C:/MTA/Exploration/belajar-ai/new-project
python -m pytest tests/test_pages.py -v
```

Expected: all 4 tests fail (routes not defined yet).

- [ ] **Step 3: Create `templates/auth/login.html`**

```html
{% extends "base.html" %}
{% block title %}Login — Patient Registration{% endblock %}

{% block content %}
<div class="card" style="max-width:400px;margin:2rem auto">
  <h2>Admin Login</h2>
  {% if error %}
  <p class="form-error visible">Invalid credentials. Please try again.</p>
  {% endif %}
  <form method="POST" action="/login">
    <input type="hidden" name="next" value="{{ next }}" />
    <div class="form-group">
      <label for="username">Username <span class="required">*</span></label>
      <input type="text" id="username" name="username" required autocomplete="username" />
    </div>
    <div class="form-group">
      <label for="password">Password <span class="required">*</span></label>
      <input type="password" id="password" name="password" required autocomplete="current-password" />
    </div>
    <div class="modal-actions">
      <button type="submit" class="btn btn-primary">Login as Admin</button>
      <a href="/patients" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Add auth routes to `routers/pages.py`**

Add after the `_safe_next` function:

```python
from passlib.context import CryptContext
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/login")
def login_page(request: Request, error: int = 0, next: str = "/patients"):
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "is_admin": _is_admin(request),
        "error": error,
        "next": next,
    })


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/patients"),
    session: Session = Depends(get_session),
):
    admin = session.exec(select(AdminUser).where(AdminUser.username == username)).first()
    if not admin or not _pwd.verify(password, admin.hashed_password):
        return RedirectResponse(f"/login?error=1&next={next}", status_code=303)
    sid = str(uuid4())
    request.app.state.sessions[sid] = admin.id
    resp = RedirectResponse(_safe_next(next), status_code=303)
    resp.set_cookie("session_id", sid, httponly=True, samesite="strict")
    return resp


@router.post("/logout")
def logout_post(request: Request):
    sid = request.cookies.get("session_id")
    if sid:
        request.app.state.sessions.pop(sid, None)
    resp = RedirectResponse("/patients", status_code=303)
    resp.delete_cookie("session_id")
    return resp
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/pages.py templates/auth/login.html tests/test_pages.py
git commit -m "feat: add SSR login/logout pages"
```

---

### Task 3: Patient list page — GET / redirect and GET /patients

**Files:**
- Modify: `routers/pages.py`
- Create: `templates/patients/list.html`
- Modify: `tests/test_pages.py`

**Interfaces:**
- Consumes: `Patient` model, `get_session`, `_is_admin`, `templates`
- Produces: `GET /` (303 → /patients), `GET /patients`

- [ ] **Step 1: Add failing tests to `tests/test_pages.py`**

```python
def test_root_redirects_to_patients(client: TestClient):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/patients"


def test_patients_list_renders_empty(client: TestClient):
    resp = client.get("/patients", follow_redirects=False)
    assert resp.status_code == 200
    assert b"No patients registered yet" in resp.content


def test_patients_list_shows_patient(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Alice", date_of_birth=date(1990, 1, 1), gender="female")
    session.add(p)
    session.commit()
    resp = client.get("/patients", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Alice" in resp.content
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_pages.py::test_root_redirects_to_patients tests/test_pages.py::test_patients_list_renders_empty tests/test_pages.py::test_patients_list_shows_patient -v
```

Expected: all 3 FAIL.

- [ ] **Step 3: Create `templates/patients/list.html`**

```html
{% extends "base.html" %}
{% block title %}Patient Registration{% endblock %}

{% block admin_header_actions %}
  <a href="/patients/new" class="btn btn-primary">+ Register Patient</a>
{% endblock %}

{% block content %}
<div class="table-wrapper">
  {% if patients %}
  <table class="patient-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Gender</th>
        <th>Phone</th>
        <th>Date of Birth</th>
        {% if is_admin %}<th>Actions</th>{% endif %}
      </tr>
    </thead>
    <tbody>
      {% for p in patients %}
      <tr>
        <td>{{ p.id }}</td>
        <td><a href="/patients/{{ p.id }}">{{ p.name }}</a></td>
        <td>{{ p.gender }}</td>
        <td>{{ p.phone or '-' }}</td>
        <td>{{ p.date_of_birth }}</td>
        {% if is_admin %}
        <td class="actions-cell">
          <a href="/patients/{{ p.id }}/edit" class="btn btn-secondary btn-icon" title="Edit">&#9998;</a>
          <a href="/patients/{{ p.id }}/confirm-delete" class="btn btn-danger btn-icon" title="Delete">&#128465;</a>
        </td>
        {% endif %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="empty-state">No patients registered yet.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 4: Add routes to `routers/pages.py`**

```python
@router.get("/")
def index():
    return RedirectResponse("/patients", status_code=303)


@router.get("/patients")
def patients_list(request: Request, session: Session = Depends(get_session)):
    patients = session.exec(
        select(Patient).where(Patient.deleted_at == None).order_by(Patient.name)
    ).all()
    return templates.TemplateResponse("patients/list.html", {
        "request": request,
        "is_admin": _is_admin(request),
        "patients": patients,
    })
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/pages.py templates/patients/list.html tests/test_pages.py
git commit -m "feat: add patient list page with SSR"
```

---

### Task 4: Register patient — GET /patients/new and POST /patients

**Files:**
- Modify: `routers/pages.py`
- Create: `templates/patients/new.html`
- Modify: `tests/test_pages.py`

**Interfaces:**
- Consumes: `Patient` model, `get_session`, `_is_admin`
- Produces: `GET /patients/new`, `POST /patients`

- [ ] **Step 1: Add failing tests**

```python
def test_patients_new_requires_admin(client: TestClient):
    resp = client.get("/patients/new", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_patients_new_renders_for_admin(admin_client: TestClient):
    resp = admin_client.get("/patients/new", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Register Patient" in resp.content


def test_patients_create_redirects_to_list(admin_client: TestClient):
    resp = admin_client.post(
        "/patients",
        data={
            "name": "Bob",
            "date_of_birth": "1985-03-15",
            "gender": "male",
            "phone": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/patients"


def test_patients_create_requires_admin(client: TestClient):
    resp = client.post(
        "/patients",
        data={"name": "Bob", "date_of_birth": "1985-03-15", "gender": "male", "phone": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_pages.py::test_patients_new_requires_admin tests/test_pages.py::test_patients_new_renders_for_admin tests/test_pages.py::test_patients_create_redirects_to_list tests/test_pages.py::test_patients_create_requires_admin -v
```

Expected: all 4 FAIL.

- [ ] **Step 3: Create `templates/patients/new.html`**

```html
{% extends "base.html" %}
{% block title %}Register Patient — Patient Registration{% endblock %}

{% block content %}
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Register Patient</h2>
  <form method="POST" action="/patients">
    <div class="form-group">
      <label for="name">Name <span class="required">*</span></label>
      <input type="text" id="name" name="name" required placeholder="Full name" />
    </div>
    <div class="form-group">
      <label for="date_of_birth">Date of Birth <span class="required">*</span></label>
      <input type="date" id="date_of_birth" name="date_of_birth" required />
    </div>
    <div class="form-group">
      <label for="gender">Gender <span class="required">*</span></label>
      <select id="gender" name="gender" required>
        <option value="" disabled selected>Select gender</option>
        <option value="male">Male</option>
        <option value="female">Female</option>
        <option value="other">Other</option>
      </select>
    </div>
    <div class="form-group">
      <label for="phone">Phone <span class="optional">(optional)</span></label>
      <input type="text" id="phone" name="phone" placeholder="e.g. 08123456789" />
    </div>
    <div class="modal-actions">
      <button type="submit" class="btn btn-primary">Submit</button>
      <a href="/patients" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Add routes to `routers/pages.py`**

```python
@router.get("/patients/new")
def patients_new_form(request: Request):
    if not _is_admin(request):
        return RedirectResponse("/login?next=/patients/new", status_code=303)
    return templates.TemplateResponse("patients/new.html", {
        "request": request,
        "is_admin": True,
    })


@router.post("/patients")
def patients_create(
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login?next=/patients/new", status_code=303)
    patient = Patient(
        name=name.strip(),
        date_of_birth=date_type.fromisoformat(date_of_birth),
        gender=gender.strip().lower(),
        phone=phone.strip() or None,
    )
    session.add(patient)
    session.commit()
    return RedirectResponse("/patients", status_code=303)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/pages.py templates/patients/new.html tests/test_pages.py
git commit -m "feat: add register patient page"
```

---

### Task 5: Patient detail page — GET /patients/{id}

**Files:**
- Modify: `routers/pages.py`
- Create: `templates/patients/detail.html`
- Modify: `tests/test_pages.py`

**Interfaces:**
- Consumes: `Patient`, `Visit` models, `get_session`, `_is_admin`
- Produces: `GET /patients/{patient_id}`

- [ ] **Step 1: Add failing tests**

```python
def test_patient_detail_renders(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Carol", date_of_birth=date(1975, 6, 20), gender="female", phone="0812345")
    session.add(p)
    session.commit()
    resp = client.get(f"/patients/{p.id}", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Carol" in resp.content
    assert b"No visits recorded yet" in resp.content


def test_patient_detail_shows_visits(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Dan", date_of_birth=date(1980, 1, 1), gender="male")
    session.add(p)
    session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 3, 10), chief_complaint="Headache")
    session.add(v)
    session.commit()
    resp = client.get(f"/patients/{p.id}", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Headache" in resp.content


def test_patient_detail_404(client: TestClient):
    resp = client.get("/patients/99999", follow_redirects=False)
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_pages.py::test_patient_detail_renders tests/test_pages.py::test_patient_detail_shows_visits tests/test_pages.py::test_patient_detail_404 -v
```

Expected: all 3 FAIL.

- [ ] **Step 3: Create `templates/patients/detail.html`**

```html
{% extends "base.html" %}
{% block title %}{{ patient.name }} — Patient Detail{% endblock %}
{% block header_title %}Patient Detail{% endblock %}

{% block content %}
<a href="/patients" class="back-link">&#8592; Back to list</a>

<section class="patient-info card">
  <div class="section-header">
    <h2 class="section-title">Patient Information</h2>
    {% if is_admin %}
    <a href="/patients/{{ patient.id }}/edit" class="btn btn-secondary">&#9998; Edit</a>
    {% endif %}
  </div>
  <dl class="info-grid">
    <dt>Name</dt>          <dd>{{ patient.name }}</dd>
    <dt>Date of Birth</dt> <dd>{{ patient.date_of_birth }}</dd>
    <dt>Gender</dt>        <dd>{{ patient.gender }}</dd>
    <dt>Phone</dt>         <dd>{{ patient.phone or '—' }}</dd>
  </dl>
</section>

<section class="visit-history card">
  <div class="section-header">
    <h2 class="section-title">Visit History</h2>
    {% if is_admin %}
    <a href="/patients/{{ patient.id }}/visits/new" class="btn btn-primary">+ Add Visit</a>
    {% endif %}
  </div>
  <div class="table-wrapper">
    {% if visits %}
    <table class="visit-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Chief Complaint</th>
          <th>Diagnosis</th>
          <th>Notes</th>
          {% if is_admin %}<th>Actions</th>{% endif %}
        </tr>
      </thead>
      <tbody>
        {% for v in visits %}
        <tr>
          <td>{{ v.date }}</td>
          <td>{{ v.chief_complaint }}</td>
          <td>{{ v.diagnosis or '-' }}</td>
          <td>{{ v.notes or '-' }}</td>
          {% if is_admin %}
          <td class="actions-cell">
            <a href="/patients/{{ patient.id }}/visits/{{ v.id }}/edit"
               class="btn btn-secondary btn-icon" title="Edit">&#9998;</a>
            <a href="/patients/{{ patient.id }}/visits/{{ v.id }}/confirm-delete"
               class="btn btn-danger btn-icon" title="Delete">&#128465;</a>
          </td>
          {% endif %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="empty-state">No visits recorded yet.</p>
    {% endif %}
  </div>
</section>
{% endblock %}
```

- [ ] **Step 4: Add route to `routers/pages.py`**

```python
from fastapi import HTTPException


@router.get("/patients/{patient_id}")
def patient_detail(patient_id: int, request: Request, session: Session = Depends(get_session)):
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visits = session.exec(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.date.desc())
    ).all()
    return templates.TemplateResponse("patients/detail.html", {
        "request": request,
        "is_admin": _is_admin(request),
        "patient": patient,
        "visits": visits,
    })
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 14 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add routers/pages.py templates/patients/detail.html tests/test_pages.py
git commit -m "feat: add patient detail page"
```

---

### Task 6: Edit patient and delete patient

**Files:**
- Modify: `routers/pages.py`
- Create: `templates/patients/edit.html`
- Create: `templates/patients/confirm_delete.html`
- Modify: `tests/test_pages.py`

**Interfaces:**
- Consumes: `Patient` model, `get_session`, `_is_admin`, `HTTPException`
- Produces: `GET /patients/{id}/edit`, `POST /patients/{id}`, `GET /patients/{id}/confirm-delete`, `POST /patients/{id}/delete`

- [ ] **Step 1: Add failing tests**

```python
def test_patient_edit_requires_admin(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Ed", date_of_birth=date(1990, 1, 1), gender="male")
    session.add(p); session.commit()
    resp = client.get(f"/patients/{p.id}/edit", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_patient_edit_renders_for_admin(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Fay", date_of_birth=date(1992, 5, 5), gender="female")
    session.add(p); session.commit()
    resp = admin_client.get(f"/patients/{p.id}/edit", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Fay" in resp.content


def test_patient_update_redirects_to_detail(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Gil", date_of_birth=date(1988, 7, 7), gender="male")
    session.add(p); session.commit()
    resp = admin_client.post(
        f"/patients/{p.id}",
        data={"name": "Gilbert", "date_of_birth": "1988-07-07", "gender": "male", "phone": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/patients/{p.id}"


def test_patient_confirm_delete_renders(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Hal", date_of_birth=date(1970, 2, 2), gender="male")
    session.add(p); session.commit()
    resp = admin_client.get(f"/patients/{p.id}/confirm-delete", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Hal" in resp.content


def test_patient_delete_soft_deletes_and_redirects(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Ivy", date_of_birth=date(1983, 9, 9), gender="female")
    session.add(p); session.commit()
    resp = admin_client.post(f"/patients/{p.id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/patients"
    session.refresh(p)
    assert p.deleted_at is not None
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_pages.py::test_patient_edit_requires_admin tests/test_pages.py::test_patient_edit_renders_for_admin tests/test_pages.py::test_patient_update_redirects_to_detail tests/test_pages.py::test_patient_confirm_delete_renders tests/test_pages.py::test_patient_delete_soft_deletes_and_redirects -v
```

Expected: all 5 FAIL.

- [ ] **Step 3: Create `templates/patients/edit.html`**

```html
{% extends "base.html" %}
{% block title %}Edit Patient — Patient Registration{% endblock %}

{% block content %}
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Edit Patient</h2>
  <form method="POST" action="/patients/{{ patient.id }}">
    <div class="form-group">
      <label for="name">Name <span class="required">*</span></label>
      <input type="text" id="name" name="name" required value="{{ patient.name }}" />
    </div>
    <div class="form-group">
      <label for="date_of_birth">Date of Birth <span class="required">*</span></label>
      <input type="date" id="date_of_birth" name="date_of_birth" required
             value="{{ patient.date_of_birth }}" />
    </div>
    <div class="form-group">
      <label for="gender">Gender <span class="required">*</span></label>
      <select id="gender" name="gender" required>
        <option value="male"   {% if patient.gender == 'male'   %}selected{% endif %}>Male</option>
        <option value="female" {% if patient.gender == 'female' %}selected{% endif %}>Female</option>
        <option value="other"  {% if patient.gender == 'other'  %}selected{% endif %}>Other</option>
      </select>
    </div>
    <div class="form-group">
      <label for="phone">Phone <span class="optional">(optional)</span></label>
      <input type="text" id="phone" name="phone" value="{{ patient.phone or '' }}" />
    </div>
    <div class="modal-actions">
      <button type="submit" class="btn btn-primary">Save Changes</button>
      <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Create `templates/patients/confirm_delete.html`**

```html
{% extends "base.html" %}
{% block title %}Delete Patient — Patient Registration{% endblock %}

{% block content %}
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Delete Patient</h2>
  <p>Delete <strong>{{ patient.name }}</strong>? This cannot be undone.</p>
  <div class="modal-actions">
    <form method="POST" action="/patients/{{ patient.id }}/delete" style="display:inline">
      <button type="submit" class="btn btn-danger">Confirm Delete</button>
    </form>
    <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Add routes to `routers/pages.py`**

```python
@router.get("/patients/{patient_id}/edit")
def patient_edit_form(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse("patients/edit.html", {
        "request": request, "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}")
def patient_update(
    patient_id: int,
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.name = name.strip()
    patient.date_of_birth = date_type.fromisoformat(date_of_birth)
    patient.gender = gender.strip().lower()
    patient.phone = phone.strip() or None
    session.add(patient)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/confirm-delete")
def patient_confirm_delete(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/confirm-delete", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse("patients/confirm_delete.html", {
        "request": request, "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}/delete")
def patient_delete(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.deleted_at = datetime.utcnow()
    session.add(patient)
    session.commit()
    return RedirectResponse("/patients", status_code=303)
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 19 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add routers/pages.py templates/patients/edit.html templates/patients/confirm_delete.html tests/test_pages.py
git commit -m "feat: add edit and delete patient pages"
```

---

### Task 7: Visit pages — add, edit, delete

**Files:**
- Modify: `routers/pages.py`
- Create: `templates/visits/new.html`
- Create: `templates/visits/edit.html`
- Create: `templates/visits/confirm_delete.html`
- Modify: `tests/test_pages.py`

**Interfaces:**
- Consumes: `Patient`, `Visit` models, `get_session`, `_is_admin`, `HTTPException`
- Produces: `GET /patients/{id}/visits/new`, `POST /patients/{id}/visits`, `GET /patients/{id}/visits/{vid}/edit`, `POST /patients/{id}/visits/{vid}`, `GET /patients/{id}/visits/{vid}/confirm-delete`, `POST /patients/{id}/visits/{vid}/delete`

- [ ] **Step 1: Add failing tests**

```python
def test_visit_new_requires_admin(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Joe", date_of_birth=date(1990, 1, 1), gender="male")
    session.add(p); session.commit()
    resp = client.get(f"/patients/{p.id}/visits/new", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_visit_new_renders_for_admin(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Kim", date_of_birth=date(1990, 1, 1), gender="female")
    session.add(p); session.commit()
    resp = admin_client.get(f"/patients/{p.id}/visits/new", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Add Visit" in resp.content


def test_visit_create_redirects_to_detail(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Leo", date_of_birth=date(1985, 5, 5), gender="male")
    session.add(p); session.commit()
    resp = admin_client.post(
        f"/patients/{p.id}/visits",
        data={"date": "2024-01-15", "chief_complaint": "Fever", "diagnosis": "", "notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/patients/{p.id}"


def test_visit_edit_renders(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Mia", date_of_birth=date(1990, 1, 1), gender="female")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 2, 2), chief_complaint="Cough")
    session.add(v); session.commit()
    resp = admin_client.get(f"/patients/{p.id}/visits/{v.id}/edit", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Cough" in resp.content


def test_visit_update_redirects_to_detail(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Ned", date_of_birth=date(1980, 1, 1), gender="male")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 3, 3), chief_complaint="Back pain")
    session.add(v); session.commit()
    resp = admin_client.post(
        f"/patients/{p.id}/visits/{v.id}",
        data={"date": "2024-03-03", "chief_complaint": "Back pain updated", "diagnosis": "", "notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/patients/{p.id}"


def test_visit_confirm_delete_renders(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Ora", date_of_birth=date(1975, 1, 1), gender="female")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 4, 4), chief_complaint="Dizziness")
    session.add(v); session.commit()
    resp = admin_client.get(f"/patients/{p.id}/visits/{v.id}/confirm-delete", follow_redirects=False)
    assert resp.status_code == 200
    assert b"Dizziness" in resp.content


def test_visit_delete_removes_and_redirects(admin_client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Pat", date_of_birth=date(1978, 1, 1), gender="male")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 5, 5), chief_complaint="Nausea")
    session.add(v); session.commit()
    resp = admin_client.post(f"/patients/{p.id}/visits/{v.id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/patients/{p.id}"
    deleted = session.get(models.Visit, v.id)
    assert deleted is None
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python -m pytest tests/test_pages.py::test_visit_new_requires_admin tests/test_pages.py::test_visit_new_renders_for_admin tests/test_pages.py::test_visit_create_redirects_to_detail tests/test_pages.py::test_visit_edit_renders tests/test_pages.py::test_visit_update_redirects_to_detail tests/test_pages.py::test_visit_confirm_delete_renders tests/test_pages.py::test_visit_delete_removes_and_redirects -v
```

Expected: all 7 FAIL.

- [ ] **Step 3: Create `templates/visits/new.html`**

```html
{% extends "base.html" %}
{% block title %}Add Visit — Patient Registration{% endblock %}

{% block content %}
<a href="/patients/{{ patient.id }}" class="back-link">&#8592; Back to {{ patient.name }}</a>
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Add Visit</h2>
  <form method="POST" action="/patients/{{ patient.id }}/visits">
    <div class="form-group">
      <label for="date">Date <span class="required">*</span></label>
      <input type="date" id="date" name="date" required />
    </div>
    <div class="form-group">
      <label for="chief_complaint">Chief Complaint <span class="required">*</span></label>
      <input type="text" id="chief_complaint" name="chief_complaint" required
             placeholder="e.g. Headache, fever" />
    </div>
    <div class="form-group">
      <label for="diagnosis">Diagnosis <span class="optional">(optional)</span></label>
      <input type="text" id="diagnosis" name="diagnosis" placeholder="e.g. Migraine" />
    </div>
    <div class="form-group">
      <label for="notes">Notes <span class="optional">(optional)</span></label>
      <textarea id="notes" name="notes" rows="3" placeholder="Additional notes..."></textarea>
    </div>
    <div class="modal-actions">
      <button type="submit" class="btn btn-primary">Submit</button>
      <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 4: Create `templates/visits/edit.html`**

```html
{% extends "base.html" %}
{% block title %}Edit Visit — Patient Registration{% endblock %}

{% block content %}
<a href="/patients/{{ patient.id }}" class="back-link">&#8592; Back to {{ patient.name }}</a>
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Edit Visit</h2>
  <form method="POST" action="/patients/{{ patient.id }}/visits/{{ visit.id }}">
    <div class="form-group">
      <label for="date">Date <span class="required">*</span></label>
      <input type="date" id="date" name="date" required value="{{ visit.date }}" />
    </div>
    <div class="form-group">
      <label for="chief_complaint">Chief Complaint <span class="required">*</span></label>
      <input type="text" id="chief_complaint" name="chief_complaint" required
             value="{{ visit.chief_complaint }}" />
    </div>
    <div class="form-group">
      <label for="diagnosis">Diagnosis <span class="optional">(optional)</span></label>
      <input type="text" id="diagnosis" name="diagnosis" value="{{ visit.diagnosis or '' }}" />
    </div>
    <div class="form-group">
      <label for="notes">Notes <span class="optional">(optional)</span></label>
      <textarea id="notes" name="notes" rows="3">{{ visit.notes or '' }}</textarea>
    </div>
    <div class="modal-actions">
      <button type="submit" class="btn btn-primary">Save Changes</button>
      <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 5: Create `templates/visits/confirm_delete.html`**

```html
{% extends "base.html" %}
{% block title %}Delete Visit — Patient Registration{% endblock %}

{% block content %}
<a href="/patients/{{ patient.id }}" class="back-link">&#8592; Back to {{ patient.name }}</a>
<div class="card" style="max-width:480px;margin:2rem auto">
  <h2>Delete Visit</h2>
  <p>Delete the visit on <strong>{{ visit.date }}</strong> for <strong>{{ visit.chief_complaint }}</strong>? This cannot be undone.</p>
  <div class="modal-actions">
    <form method="POST" action="/patients/{{ patient.id }}/visits/{{ visit.id }}/delete" style="display:inline">
      <button type="submit" class="btn btn-danger">Confirm Delete</button>
    </form>
    <a href="/patients/{{ patient.id }}" class="btn btn-secondary">Cancel</a>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Add visit routes to `routers/pages.py`**

```python
@router.get("/patients/{patient_id}/visits/new")
def visit_new_form(patient_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/new", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return templates.TemplateResponse("visits/new.html", {
        "request": request, "is_admin": True, "patient": patient,
    })


@router.post("/patients/{patient_id}/visits")
def visit_create(
    patient_id: int,
    request: Request,
    date: str = Form(...),
    chief_complaint: str = Form(...),
    diagnosis: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(
        patient_id=patient_id,
        date=date_type.fromisoformat(date),
        chief_complaint=chief_complaint.strip(),
        diagnosis=diagnosis.strip() or None,
        notes=notes.strip() or None,
    )
    session.add(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/visits/{visit_id}/edit")
def visit_edit_form(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/{visit_id}/edit", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    return templates.TemplateResponse("visits/edit.html", {
        "request": request, "is_admin": True, "patient": patient, "visit": visit,
    })


@router.post("/patients/{patient_id}/visits/{visit_id}")
def visit_update(
    patient_id: int,
    visit_id: int,
    request: Request,
    date: str = Form(...),
    chief_complaint: str = Form(...),
    diagnosis: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    visit.date = date_type.fromisoformat(date)
    visit.chief_complaint = chief_complaint.strip()
    visit.diagnosis = diagnosis.strip() or None
    visit.notes = notes.strip() or None
    session.add(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)


@router.get("/patients/{patient_id}/visits/{visit_id}/confirm-delete")
def visit_confirm_delete(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse(f"/login?next=/patients/{patient_id}/visits/{visit_id}/confirm-delete", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    return templates.TemplateResponse("visits/confirm_delete.html", {
        "request": request, "is_admin": True, "patient": patient, "visit": visit,
    })


@router.post("/patients/{patient_id}/visits/{visit_id}/delete")
def visit_delete(patient_id: int, visit_id: int, request: Request, session: Session = Depends(get_session)):
    if not _is_admin(request):
        return RedirectResponse("/login", status_code=303)
    patient = session.get(Patient, patient_id)
    if not patient or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = session.get(Visit, visit_id)
    if not visit or visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(visit)
    session.commit()
    return RedirectResponse(f"/patients/{patient_id}", status_code=303)
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/test_pages.py -v
```

Expected: all 26 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add routers/pages.py templates/visits/ tests/test_pages.py
git commit -m "feat: add visit pages (new, edit, delete)"
```

---

### Task 8: Remove old HTML files and run full test suite

**Files:**
- Delete: `public/index.html`
- Delete: `public/patient.html`

**Interfaces:**
- Consumes: all prior tasks complete and green

- [ ] **Step 1: Run the full test suite to confirm everything is green**

```bash
python -m pytest -v
```

Expected: all tests in `tests/test_auth.py`, `tests/test_patients.py`, `tests/test_visits.py`, and `tests/test_pages.py` PASS.

- [ ] **Step 2: Delete the old static HTML files**

```bash
rm public/index.html public/patient.html
```

- [ ] **Step 3: Verify app still starts and pages load**

```bash
uvicorn main:app --reload
```

Visit in browser:
- `http://localhost:8000/` → redirects to `/patients`
- `http://localhost:8000/patients` → shows patient list
- `http://localhost:8000/login` → shows login form
- Login with `admin` / `changeme123` → redirected to `/patients`, Admin badge visible
- Click `+ Register Patient` → form at `/patients/new`
- Register a patient → redirected back to list, patient appears
- Click patient name → detail page at `/patients/{id}`
- `+ Add Visit` → form at `/patients/{id}/visits/new`
- Submit visit → redirected back to detail, visit appears
- Edit patient → form pre-filled, save → back to detail
- Delete patient → confirm page → deleted → back to list

- [ ] **Step 4: Run full test suite one final time**

```bash
python -m pytest -v
```

Expected: all tests PASS, zero failures.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: complete SSR migration — remove old JS-driven HTML pages"
```
