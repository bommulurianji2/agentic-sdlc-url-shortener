from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import health, redirect, urls
from app.config import get_settings
from app.errors import AppError
from app.logging_config import configure_logging
from app.middleware import CorrelationIdMiddleware

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="Agentic SDLC URL Shortener", version=settings.app_version)
app.add_middleware(CorrelationIdMiddleware)


def _envelope(code: str, message: str, correlation_id: str, details: object = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
            "details": details,
        }
    }


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=exc.http_status,
        content=_envelope(exc.code, exc.message, correlation_id, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=422,
        content=_envelope(
            "VALIDATION_FAILURE", "Request validation failed.", correlation_id, exc.errors()
        ),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=500,
        content=_envelope("INTERNAL_ERROR", "An internal error occurred.", correlation_id),
    )


# Order matters: specific routers must be registered before the redirect
# catch-all, or /health, /api/... would be swallowed as if they were short codes.
app.include_router(health.router)
app.include_router(urls.router)
app.include_router(redirect.router)
