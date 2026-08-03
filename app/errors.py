from typing import Any


class AppError(Exception):
    """Structured application error - always rendered via the single error envelope
    in docs/architecture/detailed-technical-design.md #3, never a raw stack trace."""

    def __init__(self, code: str, http_status: int, message: str, details: Any = None):
        self.code = code
        self.http_status = http_status
        self.message = message
        self.details = details
        super().__init__(message)


def invalid_url(message: str = "The provided URL is not valid.") -> AppError:
    return AppError("INVALID_URL", 422, message)


def unsafe_scheme(message: str = "URL scheme is not allowed.") -> AppError:
    return AppError("UNSAFE_SCHEME", 422, message)


def blocked_private_destination(
    message: str = "URL resolves to a blocked private or internal address.",
) -> AppError:
    return AppError("BLOCKED_PRIVATE_DESTINATION", 422, message)


def unknown_short_code(message: str = "No short URL exists for this code.") -> AppError:
    return AppError("UNKNOWN_SHORT_CODE", 404, message)


def url_expired(message: str = "This link has expired.") -> AppError:
    return AppError("URL_EXPIRED", 410, message)


def url_disabled(message: str = "This link has been disabled.") -> AppError:
    return AppError("URL_DISABLED", 410, message)


def duplicate_alias(message: str = "This alias is already in use.") -> AppError:
    return AppError("DUPLICATE_ALIAS", 409, message)


def validation_failure(message: str, details: Any = None) -> AppError:
    return AppError("VALIDATION_FAILURE", 422, message, details)


def workflow_conflict(
    message: str = "This record changed concurrently; reload and retry.",
) -> AppError:
    return AppError("WORKFLOW_CONFLICT", 409, message)


def internal_error(message: str = "An internal error occurred.") -> AppError:
    return AppError("INTERNAL_ERROR", 500, message)
