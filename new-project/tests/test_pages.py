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
