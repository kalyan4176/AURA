from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.dataset.services import DatasetService
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.workers import (
    run_correlation_task, run_statistical_test_task, 
    run_anomaly_detection_task, run_forecast_task
)
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/analytics", tags=["Asynchronous Analytical Engine"])


# Request payload schemas
class CorrelationRequest(BaseModel):
    dataset_id: str
    columns: List[str] = Field(..., min_items=2)
    method: str = "pearson"  # pearson or spearman


class StatisticalTestRequest(BaseModel):
    dataset_id: str
    test_type: str  # t_test, anova, mann_whitney
    group_col: str
    value_col: str
    control_val: Optional[str] = None
    treatment_val: Optional[str] = None


class AnomalyRequest(BaseModel):
    dataset_id: str
    columns: List[str]
    algorithm: str = "isolation_forest"  # isolation_forest or lof
    contamination: float = Field(0.05, ge=0.001, le=0.5)


class ForecastRequest(BaseModel):
    dataset_id: str
    time_col: str
    value_col: str
    steps: int = Field(6, ge=1, le=24)


# Response payload schemas
class TaskSubmissionResponse(BaseModel):
    task_id: str
    status: str = "ACCEPTED"


async def verify_dataset_access(dataset_id: str, db: AsyncSession) -> str:
    """Helper dependency to verify dataset availability before worker queueing."""
    dataset_service = DatasetService(db)
    try:
        dataset = await dataset_service.get_dataset(dataset_id)
        return dataset.id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {e}"
        )


EAGER_TASK_STORE = {}

def handle_task_submission(task) -> TaskSubmissionResponse:
    if getattr(celery_app.conf, "task_always_eager", False):
        EAGER_TASK_STORE[task.id] = {
            "task_id": task.id,
            "state": task.state,
            "result": task.result if task.state == "SUCCESS" else None,
            "error": str(task.result) if task.state == "FAILURE" else None
        }
    return TaskSubmissionResponse(task_id=task.id)


@router.post("/correlations", response_model=TaskSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_correlations(
    payload: CorrelationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Submit a task to calculate pairwise column correlations."""
    await verify_dataset_access(payload.dataset_id, db)
    
    # Launch Celery background task
    task = run_correlation_task.delay(
        dataset_id=payload.dataset_id,
        columns=payload.columns,
        method=payload.method
    )
    return handle_task_submission(task)


@router.post("/statistics-test", response_model=TaskSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_statistical_test(
    payload: StatisticalTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Submit a task to run standard hypothesis tests."""
    await verify_dataset_access(payload.dataset_id, db)
    
    task = run_statistical_test_task.delay(
        dataset_id=payload.dataset_id,
        test_type=payload.test_type,
        group_col=payload.group_col,
        value_col=payload.value_col,
        control_val=payload.control_val,
        treatment_val=payload.treatment_val
    )
    return handle_task_submission(task)


@router.post("/anomalies", response_model=TaskSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_anomaly_detection(
    payload: AnomalyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Submit a task to execute Isolation Forest / LOF anomaly detection."""
    await verify_dataset_access(payload.dataset_id, db)
    
    task = run_anomaly_detection_task.delay(
        dataset_id=payload.dataset_id,
        columns=payload.columns,
        algorithm=payload.algorithm,
        contamination=payload.contamination
    )
    return handle_task_submission(task)


@router.post("/forecast", response_model=TaskSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_forecast(
    payload: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Submit a task to calculate exponential smoothing forecasting metrics."""
    await verify_dataset_access(payload.dataset_id, db)
    
    task = run_forecast_task.delay(
        dataset_id=payload.dataset_id,
        time_col=payload.time_col,
        value_col=payload.value_col,
        steps=payload.steps
    )
    return handle_task_submission(task)


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Check background task execution progress, state, and retrieve results upon success."""
    if getattr(celery_app.conf, "task_always_eager", False) and task_id in EAGER_TASK_STORE:
        return EAGER_TASK_STORE[task_id]

    res = AsyncResult(task_id, app=celery_app)
    
    # Task metadata response builder
    response_payload = {
        "task_id": task_id,
        "state": res.state
    }
    
    if res.state == "SUCCESS":
        response_payload["result"] = res.result
    elif res.state == "FAILURE":
        response_payload["error"] = str(res.result)
        
    return response_payload
