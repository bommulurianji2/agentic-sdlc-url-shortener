from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import ClickEvent, ShortUrl


def get_by_code(db: Session, short_code: str) -> ShortUrl | None:
    return db.scalar(select(ShortUrl).where(ShortUrl.short_code == short_code))


def exists_by_code(db: Session, short_code: str) -> bool:
    return get_by_code(db, short_code) is not None


def create(
    db: Session,
    *,
    short_code: str,
    original_url: str,
    created_at: datetime,
    expires_at: datetime | None,
    creating_workflow_id: str | None = None,
) -> ShortUrl:
    short_url = ShortUrl(
        short_code=short_code,
        original_url=original_url,
        created_at=created_at,
        expires_at=expires_at,
        status="active",
        click_count=0,
        version=1,
        creating_workflow_id=creating_workflow_id,
    )
    db.add(short_url)
    db.commit()
    db.refresh(short_url)
    return short_url


def update_status(
    db: Session, short_url: ShortUrl, new_status: str, *, now: datetime
) -> ShortUrl | None:
    """Optimistic-concurrency status update (NFR-09 concurrency-safety, applied here to
    status/version rather than the click counter, which uses record_click's atomic UPDATE).
    Returns None on a version conflict - the caller maps that to WORKFLOW_CONFLICT.

    Brownfield addition: disabled_at is stamped when transitioning to 'disabled'
    and cleared on reactivation - the disabled_at column itself is additive/
    nullable, so this is fully backward compatible with rows that predate it."""
    disabled_at = now if new_status == "disabled" else None
    result = db.execute(
        update(ShortUrl)
        .where(ShortUrl.id == short_url.id, ShortUrl.version == short_url.version)
        .values(status=new_status, version=ShortUrl.version + 1, disabled_at=disabled_at)
    )
    db.commit()
    if result.rowcount == 0:  # type: ignore[attr-defined]
        return None
    db.refresh(short_url)
    return short_url


def record_click(
    db: Session,
    *,
    short_url_id: int,
    accessed_at: datetime,
    referrer_domain: str | None,
    user_agent_category: str | None,
    correlation_id: str,
) -> None:
    """NFR-09: a single atomic UPDATE, not read-then-write, so concurrent redirects
    never lose a click-count increment."""
    db.execute(
        update(ShortUrl)
        .where(ShortUrl.id == short_url_id)
        .values(click_count=ShortUrl.click_count + 1, last_accessed_at=accessed_at)
    )
    db.add(
        ClickEvent(
            short_url_id=short_url_id,
            accessed_at=accessed_at,
            referrer_domain=referrer_domain,
            user_agent_category=user_agent_category,
            correlation_id=correlation_id,
        )
    )
    db.commit()


def list_click_events(db: Session, short_url_id: int) -> list[ClickEvent]:
    return list(
        db.scalars(
            select(ClickEvent)
            .where(ClickEvent.short_url_id == short_url_id)
            .order_by(ClickEvent.accessed_at)
        )
    )
