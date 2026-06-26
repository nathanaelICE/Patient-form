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


# ── Patient Detail ───────────────────────────────────────────────────────────

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


# ── Patient Edit ─────────────────────────────────────────────────────────────

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


# ── Visit Pages ───────────────────────────────────────────────────────────────

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


def test_visit_create_requires_admin(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Qui", date_of_birth=date(1990, 1, 1), gender="female")
    session.add(p); session.commit()
    resp = client.post(
        f"/patients/{p.id}/visits",
        data={"date": "2024-01-01", "chief_complaint": "Test", "diagnosis": "", "notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_visit_update_requires_admin(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Rex", date_of_birth=date(1990, 1, 1), gender="male")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 1, 1), chief_complaint="Cough")
    session.add(v); session.commit()
    resp = client.post(
        f"/patients/{p.id}/visits/{v.id}",
        data={"date": "2024-01-01", "chief_complaint": "Updated", "diagnosis": "", "notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_visit_delete_requires_admin(client: TestClient, session: Session):
    import models
    from datetime import date
    p = models.Patient(name="Sam", date_of_birth=date(1990, 1, 1), gender="female")
    session.add(p); session.commit()
    v = models.Visit(patient_id=p.id, date=date(2024, 1, 1), chief_complaint="Fever")
    session.add(v); session.commit()
    resp = client.post(f"/patients/{p.id}/visits/{v.id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_patient_detail_soft_deleted_returns_404(client: TestClient, session: Session):
    import models
    from datetime import date, datetime
    p = models.Patient(name="Tia", date_of_birth=date(1990, 1, 1), gender="female", deleted_at=datetime.utcnow())
    session.add(p); session.commit()
    resp = client.get(f"/patients/{p.id}", follow_redirects=False)
    assert resp.status_code == 404
