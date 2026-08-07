from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.notification.entities import Notification
from app.application.notification.services import NotificationService
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/notifications", tags=["Notification Engine"])


@router.get("", response_model=List[Notification])
async def list_unread_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Retrieve all active unread warning and info notifications."""
    service = NotificationService(db)
    return await service.list_unread()


@router.post("/{notif_id}/read", response_model=Notification)
async def mark_alert_as_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Mark a notification warning alert as read/processed."""
    service = NotificationService(db)
    result = await service.mark_read(notif_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification alert reference not found."
        )
    return result
