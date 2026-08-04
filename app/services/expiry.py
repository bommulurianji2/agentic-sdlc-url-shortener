"""Expiry computation - extracted here as part of the brownfield enhancement
(SCEN-02) that made expiry configurable, instead of the inline 30-day-only
logic that used to live directly in the create-URL route handler."""

import datetime as dt

from app.errors import validation_failure

MIN_EXPIRY_DAYS = 1
MAX_EXPIRY_DAYS = 365


def validate_expires_in_days(days: int) -> int:
    """Regression-caught bug (SCEN-02): the initial version of compute_expiry
    below accepted expires_in_days unchecked - 0, negative, or >365 all
    silently succeeded (0/negative created an already-expired link; >365
    exceeded the configurable range this feature was supposed to enforce).
    tests/integration/test_brownfield_regression.py caught this before it
    shipped; this validation is the fix."""
    if days < MIN_EXPIRY_DAYS or days > MAX_EXPIRY_DAYS:
        raise validation_failure(
            f"expires_in_days must be between {MIN_EXPIRY_DAYS} and {MAX_EXPIRY_DAYS}."
        )
    return days


def compute_expiry(
    *,
    now: dt.datetime,
    default_days: int,
    expires_at: dt.datetime | None = None,
    expires_in_days: int | None = None,
) -> dt.datetime:
    if expires_in_days is not None:
        return now + dt.timedelta(days=validate_expires_in_days(expires_in_days))
    if expires_at is not None:
        return expires_at
    return now + dt.timedelta(days=default_days)
