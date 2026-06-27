import uuid
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.api.dependencies import get_current_user, RoleChecker
from app.models.models import Notification, User
from app.schemas.notification import NotificationOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Role Checkers
allow_admin_or_manager = RoleChecker(["Admin", "Manager"])

@router.get("", response_model=List[NotificationOut])
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all unread dashboard alerts for the currently logged in user.
    """
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).order_by(Notification.created_at.desc()).all()
    return notifications

@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a dashboard alert notification as read.
    """
    try:
        notif_uuid = uuid.UUID(notification_id)
    except ValueError:
        raise EntityNotFoundError(message=f"Notification not found: {notification_id}")

    notif = db.query(Notification).filter(
        Notification.id == notif_uuid,
        Notification.user_id == current_user.id
    ).first()
    
    if not notif:
        raise EntityNotFoundError(message=f"Notification not found: {notification_id}")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/trigger-daily-summary", status_code=status.HTTP_200_OK)
def trigger_daily_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_admin_or_manager)
):
    """
    Triggers the generation and email dispatches of daily summaries for active employees.
    Restricted to Admins and Managers.
    """
    NotificationService.send_daily_summary(db)
    return {"message": "Daily summaries dispatched successfully."}

@router.post("/trigger-escalations", status_code=status.HTTP_200_OK)
def trigger_escalations(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_admin_or_manager)
):
    """
    Triggers scans and manager escalations for all tasks overdue by > 24 hours.
    Restricted to Admins and Managers.
    """
    NotificationService.escalate_overdue_tasks(db)
    return {"message": "Overdue task escalations run completed."}
