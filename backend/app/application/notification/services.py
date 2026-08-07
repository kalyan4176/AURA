import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.domain.notification.entities import Notification
from app.infrastructure.repositories.postgres_repository import NotificationRepository


class NotificationService:
    """Enterprise Alerting and Alert Dispatching Engine.

    Pushes operational notices to analysts based on analytical updates,
    background job states, and data quality indicators.
    """

    def __init__(self, session: AsyncSession):
        self.repo = NotificationRepository(session)

    async def list_unread(self) -> List[Notification]:
        db_notifs = await self.repo.get_unread()
        return [Notification.model_validate(n) for n in db_notifs]

    async def mark_read(self, notif_id: str) -> Optional[Notification]:
        notif_uuid = uuid.UUID(notif_id)
        db_notif = await self.repo.mark_read(notif_uuid)
        if not db_notif:
            return None
        return Notification.model_validate(db_notif)

    async def publish_notification(self, type: str, message: str) -> Notification:
        """Create and broadcast a system notification event."""
        logger.info(f"Publishing system notification type '{type}': {message}")
        db_notif = await self.repo.create(type=type, message=message)
        return Notification.model_validate(db_notif)

    async def check_dataset_and_alert(self, dataset_name: str, health_score: int) -> Optional[Notification]:
        """Auto-evaluates health scores and fires a warning notification if score falls below 80%."""
        if health_score < 80:
            msg = (
                f"Data quality alert: Dataset '{dataset_name}' profile scored a low "
                f"health rating of {health_score}%. Inconsistent rows, duplicates, or empty fields detected."
            )
            return await self.publish_notification(type="warning", message=msg)
        return None
