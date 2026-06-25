import pytest


@pytest.fixture
def patient(client):
    resp = client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
    })
    return resp.json()


def test_create_visit(client, patient):
    response = client.post(f"/api/patients/{patient['id']}/visits", json={
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


def test_create_visit_minimal_fields(client, patient):
    response = client.post(f"/api/patients/{patient['id']}/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Fever",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["diagnosis"] is None
    assert data["notes"] is None


def test_create_visit_patient_not_found(client):
    response = client.post("/api/patients/9999/visits", json={
        "date": "2024-06-01",
        "chief_complaint": "Fever",
    })
    assert response.status_code == 404


def test_list_visits_empty(client, patient):
    response = client.get(f"/api/patients/{patient['id']}/visits")
    assert response.status_code == 200
    assert response.json() == []


def test_list_visits_returns_all(client, patient):
    client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-01-01", "chief_complaint": "Cough"})
    client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-03-15", "chief_complaint": "Fever"})

    response = client.get(f"/api/patients/{patient['id']}/visits")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_visits_sorted_newest_first(client, patient):
    client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-01-01", "chief_complaint": "Cough"})
    client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-06-15", "chief_complaint": "Fever"})

    visits = client.get(f"/api/patients/{patient['id']}/visits").json()
    dates = [v["date"] for v in visits]
    assert dates == sorted(dates, reverse=True)


def test_list_visits_patient_not_found(client):
    response = client.get("/api/patients/9999/visits")
    assert response.status_code == 404


def test_visits_isolated_between_patients(client, patient):
    other = client.post("/api/patients", json={
        "name": "Siti Rahma", "date_of_birth": "1985-03-20", "gender": "female"
    }).json()

    client.post(f"/api/patients/{patient['id']}/visits", json={"date": "2024-06-01", "chief_complaint": "Back pain"})

    response = client.get(f"/api/patients/{other['id']}/visits")
    assert response.json() == []
