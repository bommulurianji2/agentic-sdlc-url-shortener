import datetime as dt


def utc_now() -> dt.datetime:
    """SQLite has no tz-aware storage - every datetime in this app is naive-UTC
    by convention so stored and in-memory values are always comparable."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
