from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import unknown_short_code, url_disabled, url_expired
from app.repositories import url_repository
from app.services.analytics import categorize_user_agent, extract_referrer_domain
from app.time_utils import utc_now

router = APIRouter(tags=["redirect"])


@router.get("/{short_code}")
def redirect_short_code(
    short_code: str, request: Request, db: Session = Depends(get_db)
) -> RedirectResponse:
    short_url = url_repository.get_by_code(db, short_code)
    if short_url is None:
        raise unknown_short_code()

    now = utc_now()
    if short_url.status == "disabled":
        raise url_disabled()
    if short_url.is_expired(now):
        raise url_expired()

    correlation_id = getattr(request.state, "correlation_id", "unknown")
    url_repository.record_click(
        db,
        short_url_id=short_url.id,
        accessed_at=now,
        referrer_domain=extract_referrer_domain(request.headers.get("referer")),
        user_agent_category=categorize_user_agent(request.headers.get("user-agent")),
        correlation_id=correlation_id,
    )
    return RedirectResponse(url=short_url.original_url, status_code=307)
