from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"
        status = "ok"
    except Exception:
        database_status = "error"
        status = "degraded"
    return {
        "status": status,
        "database": database_status,
        "execution_mode": settings.agent_mode,
        "version": settings.app_version,
    }
