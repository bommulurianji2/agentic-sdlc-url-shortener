from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


def test_health_reports_degraded_when_db_check_fails(client):
    with patch.object(Session, "execute", side_effect=RuntimeError("db unreachable")):
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"


def test_unexpected_exception_returns_structured_internal_error():
    # TestClient's default raise_server_exceptions=True re-raises unhandled
    # exceptions for debugging rather than routing them through FastAPI's
    # registered exception handler - real uvicorn traffic doesn't do this, so
    # this test explicitly opts out to exercise the actual production path.
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    with patch("app.repositories.url_repository.get_by_code", side_effect=RuntimeError("boom")):
        response = no_raise_client.get("/api/v1/urls/whatever")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "correlation_id" in body["error"]
