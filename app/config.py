from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

from pydantic_settings import BaseSettings, SettingsConfigDict


def _app_version() -> str:
    try:
        return version("agentic-sdlc-url-shortener")
    except PackageNotFoundError:
        return "1.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    agent_mode: str = "deterministic"
    llm_api_key: str = ""
    log_level: str = "INFO"
    short_code_length: int = 7
    default_expiry_days: int = 30
    rate_limit_per_minute: int = 100
    """SCEN-03 (ambiguous scenario): the one net-new control added beyond the
    greenfield baseline. 100/min/IP is generous enough for normal use and the
    test suite, while still bounding abuse of the creation endpoint."""
    app_version: str = _app_version()


@lru_cache
def get_settings() -> Settings:
    return Settings()
