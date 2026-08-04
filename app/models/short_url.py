from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.click_event import ClickEvent


class ShortUrl(Base):
    """See docs/architecture/detailed-technical-design.md #1 for the field-by-field rationale
    (status is only active/disabled - "expired" is derived from expires_at at read time;
    creating_workflow_id is only set for scenario-runner demo links, NULL for real traffic)."""

    __tablename__ = "short_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    creating_workflow_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    """Brownfield addition (SCEN-02): additive, nullable column - existing rows
    get NULL, so this migration is fully backward compatible. Set when status
    transitions to 'disabled', cleared on reactivation."""

    click_events: Mapped[list["ClickEvent"]] = relationship(
        back_populates="short_url", cascade="all, delete-orphan"
    )

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at < now

    def is_redirectable(self, now: datetime) -> bool:
        return self.status == "active" and not self.is_expired(now)
