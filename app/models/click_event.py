from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.short_url import ShortUrl


class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    short_url_id: Mapped[int] = mapped_column(ForeignKey("short_urls.id"), nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    referrer_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_agent_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)

    short_url: Mapped["ShortUrl"] = relationship(back_populates="click_events")
