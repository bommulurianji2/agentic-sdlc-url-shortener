from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateUrlRequest(BaseModel):
    original_url: str = Field(min_length=1, max_length=2048)
    custom_alias: str | None = Field(default=None, min_length=3, max_length=32)
    expires_at: datetime | None = None


class UpdateUrlRequest(BaseModel):
    status: Literal["active", "disabled"]


class UrlResponse(BaseModel):
    model_config = {"from_attributes": True}

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    status: str
    click_count: int = 0
    last_accessed_at: datetime | None = None


class ClickEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    accessed_at: datetime
    referrer_domain: str | None
    user_agent_category: str | None


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    created_at: datetime
    last_accessed_at: datetime | None
    click_events: list[ClickEventResponse]
