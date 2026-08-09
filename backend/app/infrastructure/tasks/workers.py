import asyncio
import uuid
from typing import List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.infrastructure.repositories.postgres_repository import DatasetRepository
from app.application.analytics.services import AnalyticsService


def run_async(coro):
    """Bridge synchronous Celery threads with async Database repositories."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _get_dataset_path(dataset_id_str: str) -> str:
    """Async helper to retrieve file path from Postgres."""
    ds_uuid = uuid.UUID(dataset_id_str)
    async with AsyncSessionLocal() as session:
        repo = DatasetRepository(session)
        dataset = await repo.get_by_id(ds_uuid)
        if not dataset:
            raise FileNotFoundError(f"Dataset with ID {dataset_id_str} not registered in database.")
        return dataset.file_path


@celery_app.task(bind=True, name="tasks.run_correlation")
def run_correlation_task(self, file_path: str, columns: List[str], method: str = "pearson"):
    """Background task computing pairwise correlations."""
    logger.info(f"Celery correlation task {self.request.id} started.")
    result = AnalyticsService.calculate_correlations(file_path, columns, method)
    return result.model_dump()


@celery_app.task(bind=True, name="tasks.run_statistical_test")
def run_statistical_test_task(
    self, 
    file_path: str, 
    test_type: str, 
    group_col: str, 
    value_col: str,
    control_val: Optional[str] = None,
    treatment_val: Optional[str] = None
):
    """Background task executing statistical hypothesis tests."""
    logger.info(f"Celery statistical test task {self.request.id} started.")
    result = AnalyticsService.run_statistical_test(
        file_path=file_path,
        test_type=test_type,
        group_col=group_col,
        value_col=value_col,
        control_val=control_val,
        treatment_val=treatment_val
    )
    return result.model_dump()


@celery_app.task(bind=True, name="tasks.run_anomaly_detection")
def run_anomaly_detection_task(
    self, 
    file_path: str, 
    columns: List[str], 
    algorithm: str = "isolation_forest", 
    contamination: float = 0.05
):
    """Background task evaluating ML anomalies."""
    logger.info(f"Celery anomaly detection task {self.request.id} started.")
    result = AnalyticsService.detect_anomalies(file_path, columns, algorithm, contamination)
    return result.model_dump()


@celery_app.task(bind=True, name="tasks.run_forecast")
def run_forecast_task(self, file_path: str, time_col: str, value_col: str, steps: int = 6):
    """Background task running Holt-Winters time-series projections."""
    logger.info(f"Celery forecast task {self.request.id} started.")
    result = AnalyticsService.generate_forecast(file_path, time_col, value_col, steps)
    return result.model_dump()
