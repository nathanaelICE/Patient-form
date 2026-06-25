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
