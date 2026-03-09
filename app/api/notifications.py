#!/usr/bin/env python
# MODIFIED: 2026-03-03 - Added full list and mark-all-read endpoint
"""Notifications API. Section 6.12."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, CurrentUser
from app.db.models import Notification
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread", response_model=list[NotificationResponse])
def unread_list(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).order_by(Notification.created_at.desc()).all()


@router.put("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if n:
        n.is_read = True
        db.commit()
    return {"message": "OK"}


@router.put("/read-all")
def mark_all_read(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({Notification.is_read: True})
    db.commit()
    return {"message": "OK"}


@router.get("", response_model=list[NotificationResponse])
def notification_list(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List all notifications for the current user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.post("/mark-all-read")
def mark_all_read_post(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Alias for read-all using POST as per HTTP semantics."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({Notification.is_read: True})
    db.commit()
    return {"message": "OK"}
