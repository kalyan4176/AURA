from celery import Celery
from app.core.config import settings

# Initialize Celery Application
# Redis is the primary Message Broker.
# Redis is also used for storing Task Results.
celery_app = Celery(
    "aura_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.infrastructure.tasks.workers"]
)

# Enterprise configuration parameters
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes hard limit
    task_soft_time_limit=1200  # 20 minutes soft limit
)
