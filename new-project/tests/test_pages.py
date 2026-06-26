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


# ── Patient List ──────────────────────────────────────────────────────────────

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


# ── Patient Register ─────────────────────────────────────────────────────────

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
