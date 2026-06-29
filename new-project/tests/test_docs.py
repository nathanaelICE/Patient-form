import os


def test_docs_requires_auth(client):
    resp = client.get("/docs")
    assert resp.status_code == 401


def test_openapi_requires_auth(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 401


def test_docs_accessible_with_basic_auth(client):
    os.environ["ADMIN_USERNAME"] = "docsadmin"
    os.environ["ADMIN_PASSWORD"] = "docspass"
    resp = client.get("/docs", auth=("docsadmin", "docspass"))
    assert resp.status_code == 200


def test_docs_rejects_wrong_basic_auth(client):
    os.environ["ADMIN_USERNAME"] = "docsadmin"
    os.environ["ADMIN_PASSWORD"] = "docspass"
    resp = client.get("/docs", auth=("docsadmin", "wrong"))
    assert resp.status_code == 401


def test_openapi_accessible_with_basic_auth(client):
    os.environ["ADMIN_USERNAME"] = "docsadmin"
    os.environ["ADMIN_PASSWORD"] = "docspass"
    resp = client.get("/openapi.json", auth=("docsadmin", "docspass"))
    assert resp.status_code == 200
