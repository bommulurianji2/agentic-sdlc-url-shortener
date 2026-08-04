"""Dedicated rate-limit tests build their own tiny app with a small, explicit
window - the real app's shared middleware instance uses a generous
production default (100/min) specifically so the full test suite's normal
POST /api/v1/urls traffic never trips it; testing the *behavior* needs a
small window, which would make that shared instance too fragile to reuse
here."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware.rate_limit import RateLimitMiddleware
from app.errors import AppError


def _make_app(requests_per_window: int) -> FastAPI:
    app = FastAPI()

    @app.post("/api/v1/urls")
    def create() -> dict:
        return {"ok": True}

    @app.post("/other")
    def other() -> dict:
        return {"ok": True}

    @app.exception_handler(AppError)
    async def handle_app_error(request, exc: AppError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=exc.http_status, content={"error": {"code": exc.code}})

    app.add_middleware(
        RateLimitMiddleware, requests_per_window=requests_per_window, window_seconds=60
    )
    return app


def test_requests_within_the_limit_all_succeed():
    client = TestClient(_make_app(requests_per_window=3))
    for _ in range(3):
        assert client.post("/api/v1/urls").status_code == 200


def test_exceeding_the_limit_returns_429():
    client = TestClient(_make_app(requests_per_window=3))
    for _ in range(3):
        client.post("/api/v1/urls")
    response = client.post("/api/v1/urls")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_only_the_creation_endpoint_is_rate_limited():
    client = TestClient(_make_app(requests_per_window=1))
    client.post("/api/v1/urls")
    assert client.post("/api/v1/urls").status_code == 429
    assert client.post("/other").status_code == 200  # different path, unaffected
