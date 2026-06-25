def test_create_patient(client):
    response = client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "phone": "08123456789",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Budi Santoso"
    assert data["id"] is not None


def test_create_patient_without_phone(client):
    response = client.post("/api/patients", json={
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


def test_list_patients_returns_all(client):
    client.post("/api/patients", json={"name": "Zara", "date_of_birth": "2000-01-01", "gender": "female"})
    client.post("/api/patients", json={"name": "Andi", "date_of_birth": "1995-06-10", "gender": "male"})

    response = client.get("/api/patients")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Zara" in names
    assert "Andi" in names


def test_list_patients_sorted_by_name(client):
    client.post("/api/patients", json={"name": "Zara", "date_of_birth": "2000-01-01", "gender": "female"})
    client.post("/api/patients", json={"name": "Andi", "date_of_birth": "1995-06-10", "gender": "male"})

    names = [p["name"] for p in client.get("/api/patients").json()]
    assert names == sorted(names)


def test_get_patient_by_id(client):
    created = client.post("/api/patients", json={
        "name": "Budi Santoso",
        "date_of_birth": "1990-05-15",
        "gender": "male",
    }).json()

    response = client.get(f"/api/patients/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Budi Santoso"


def test_get_patient_not_found(client):
    response = client.get("/api/patients/9999")
    assert response.status_code == 404
