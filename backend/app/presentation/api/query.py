from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.application.dataset.services import DatasetService
from app.application.budget.services import ai_budget_manager
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/analytics", tags=["Decision Intelligence Engine"])


class QueryRequest(BaseModel):
    dataset_id: str
    query: str


@router.post("/query")
async def execute_analysis_query(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Cost-optimized inquiry endpoint.

    Uses AI Budget Manager to route to SQL engines or cached LLMs safely.
    """
    dataset_service = DatasetService(db)
    
    # Retrieve dataset details
    try:
        dataset = await dataset_service.get_dataset(payload.dataset_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Dataset reference not found: {e}"
        )

    # Route and execute query
    try:
        response = await ai_budget_manager.execute_query(
            dataset_path=dataset.file_path,
            user_query=payload.query
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed processing analytical request: {e}"
        )


@router.get("/budget/spend")
async def get_budget_spend(
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Fetch current daily LLM spend metrics."""
    spend = ai_budget_manager.get_current_daily_spend()
    return {
        "daily_spend_usd": spend,
        "daily_limit_usd": 10.0,  # Or load from config settings dynamically
        "remaining_budget_usd": max(0.0, 10.0 - spend)
    }
