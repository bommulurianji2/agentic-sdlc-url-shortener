import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

# Point the app at a fresh temp SQLite file BEFORE importing app.main, since
# app.database.session builds its engine at import time from get_settings().
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.database import Base  # noqa: E402
from app.database.session import engine as app_engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(app_engine)
    yield
    Base.metadata.drop_all(app_engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
