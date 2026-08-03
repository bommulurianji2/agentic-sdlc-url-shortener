def test_health_reports_ok_and_real_db_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["execution_mode"] == "deterministic"
    assert "version" in body


def test_openapi_and_docs_are_reachable(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
