"""Notification schemas. FR-NOTIF-001."""
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    link: str | None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
