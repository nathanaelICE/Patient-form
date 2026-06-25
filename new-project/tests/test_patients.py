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
