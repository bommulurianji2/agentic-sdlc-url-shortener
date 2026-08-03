import datetime as dt

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.errors import duplicate_alias, unknown_short_code, workflow_conflict
from app.models import ShortUrl
from app.repositories import url_repository
from app.schemas.url import (
    AnalyticsResponse,
    ClickEventResponse,
    CreateUrlRequest,
    UpdateUrlRequest,
    UrlResponse,
)
from app.services.url_safety import (
    generate_short_code,
    validate_custom_alias,
    validate_original_url,
)
from app.time_utils import utc_now

router = APIRouter(prefix="/api/v1/urls", tags=["urls"])


def _to_response(short_url: ShortUrl, request: Request) -> UrlResponse:
    base = str(request.base_url).rstrip("/")
    return UrlResponse(
        short_code=short_url.short_code,
        short_url=f"{base}/{short_url.short_code}",
        original_url=short_url.original_url,
        created_at=short_url.created_at,
        expires_at=short_url.expires_at,
        status=short_url.status,
        click_count=short_url.click_count,
        last_accessed_at=short_url.last_accessed_at,
    )


@router.post("", status_code=201, response_model=UrlResponse)
def create_short_url(
    payload: CreateUrlRequest, request: Request, db: Session = Depends(get_db)
) -> UrlResponse:
    settings = get_settings()
    original_url = validate_original_url(payload.original_url)

    if payload.custom_alias:
        code = validate_custom_alias(payload.custom_alias)
        if url_repository.exists_by_code(db, code):
            raise duplicate_alias()
    else:
        code = generate_short_code(settings.short_code_length)
        while url_repository.exists_by_code(db, code):
            code = generate_short_code(settings.short_code_length)

    now = utc_now()
    expires_at = payload.expires_at.replace(tzinfo=None) if payload.expires_at else None
    if expires_at is None:
        expires_at = now + dt.timedelta(days=settings.default_expiry_days)

    short_url = url_repository.create(
        db,
        short_code=code,
        original_url=original_url,
        created_at=now,
        expires_at=expires_at,
    )
    return _to_response(short_url, request)


@router.get("/{short_code}", response_model=UrlResponse)
def get_url_details(
    short_code: str, request: Request, db: Session = Depends(get_db)
) -> UrlResponse:
    short_url = url_repository.get_by_code(db, short_code)
    if short_url is None:
        raise unknown_short_code()
    return _to_response(short_url, request)


@router.get("/{short_code}/analytics", response_model=AnalyticsResponse)
def get_url_analytics(short_code: str, db: Session = Depends(get_db)) -> AnalyticsResponse:
    short_url = url_repository.get_by_code(db, short_code)
    if short_url is None:
        raise unknown_short_code()
    events = url_repository.list_click_events(db, short_url.id)
    return AnalyticsResponse(
        short_code=short_url.short_code,
        total_clicks=short_url.click_count,
        created_at=short_url.created_at,
        last_accessed_at=short_url.last_accessed_at,
        click_events=[
            ClickEventResponse(
                accessed_at=e.accessed_at,
                referrer_domain=e.referrer_domain,
                user_agent_category=e.user_agent_category,
            )
            for e in events
        ],
    )


@router.patch("/{short_code}", response_model=UrlResponse)
def update_url_status(
    short_code: str,
    payload: UpdateUrlRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UrlResponse:
    short_url = url_repository.get_by_code(db, short_code)
    if short_url is None:
        raise unknown_short_code()
    updated = url_repository.update_status(db, short_url, payload.status)
    if updated is None:
        raise workflow_conflict()
    return _to_response(updated, request)
