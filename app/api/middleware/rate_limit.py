"""Basic rate limiting - the one net-new control in the ambiguous scenario's
approved interpretation (requirements-baseline.md SCEN-03); scheme/SSRF
blocking and secure random codes already exist from the greenfield build.

A simple in-memory sliding window, keyed by client IP, scoped to the URL
creation endpoint only (the meaningful abuse vector for this service)."""

import threading
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import error_envelope

RATE_LIMITED_PATH = "/api/v1/urls"
RATE_LIMITED_METHOD = "POST"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, requests_per_window: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == RATE_LIMITED_METHOD and request.url.path == RATE_LIMITED_PATH:
            client_ip = request.client.host if request.client else "unknown"
            now = time.monotonic()
            with self._lock:
                hits = self._hits[client_ip]
                cutoff = now - self.window_seconds
                while hits and hits[0] < cutoff:
                    hits.pop(0)
                if len(hits) >= self.requests_per_window:
                    # Exceptions raised inside BaseHTTPMiddleware.dispatch() do NOT
                    # reach FastAPI's @app.exception_handler(AppError) - a Starlette
                    # middleware limitation - so this returns the response directly.
                    correlation_id = getattr(request.state, "correlation_id", "unknown")
                    message = (
                        f"More than {self.requests_per_window} URL creation requests "
                        f"in {self.window_seconds}s from this client."
                    )
                    return JSONResponse(
                        status_code=429,
                        content=error_envelope("RATE_LIMIT_EXCEEDED", message, correlation_id),
                    )
                hits.append(now)
        return await call_next(request)
