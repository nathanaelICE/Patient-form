def _make_patient(admin_client):
    resp = admin_client.post("/api/patients", json={
        "name": "Jane", "date_of_birth": "1990-01-01", "gender": "female",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def _claim_body(**over):
    body = {
        "claim_date": "2026-06-01",
        "claim_amount": 1200.5,
        "claim_type": "outpatient",
        "claim_submission_method": "online",
    }
    body.update(over)
    return body


def test_create_and_list_claim(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["patient_id"] == pid
    assert data["claim_status"] == "pending"
    assert data["claim_type"] == "outpatient"

    listed = admin_client.get(f"/api/patients/{pid}/claims")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_claim_rejects_bad_enum(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body(claim_type="nope"))
    assert resp.status_code == 422


def test_create_claim_rejects_negative_amount(admin_client):
    pid = _make_patient(admin_client)
    resp = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body(claim_amount=-1))
    assert resp.status_code == 422


def test_create_claim_missing_patient_404(admin_client):
    resp = admin_client.post("/api/patients/9999/claims", json=_claim_body())
    assert resp.status_code == 404


def test_update_claim(admin_client):
    pid = _make_patient(admin_client)
    cid = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body()).json()["id"]
    resp = admin_client.put(f"/api/patients/{pid}/claims/{cid}", json={"claim_status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["claim_status"] == "approved"


def test_delete_claim(admin_client):
    pid = _make_patient(admin_client)
    cid = admin_client.post(f"/api/patients/{pid}/claims", json=_claim_body()).json()["id"]
    assert admin_client.delete(f"/api/patients/{pid}/claims/{cid}").status_code == 204
    assert admin_client.get(f"/api/patients/{pid}/claims").json() == []


def test_claims_require_auth(client):
    resp = client.get("/api/patients/1/claims")
    assert resp.status_code == 401
