from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.application.dataset.services import DatasetService
from app.application.budget.services import ai_budget_manager
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

from sqlalchemy import select, delete
from app.infrastructure.repositories.models import ChatMessageModel

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
        
        # Save user message to persistent history
        user_msg = ChatMessageModel(
            dataset_id=payload.dataset_id,
            role="user",
            content=payload.query
        )
        db.add(user_msg)
        
        # Save assistant message to persistent history
        assistant_content = response.get("response", "")
        assistant_msg = ChatMessageModel(
            dataset_id=payload.dataset_id,
            role="assistant",
            content=assistant_content,
            chart_spec=response.get("chart_spec"),
            query_executed=response.get("data", {}).get("query_executed") if isinstance(response.get("data"), dict) else None
        )
        db.add(assistant_msg)
        await db.commit()
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed processing analytical request: {e}"
        )


@router.get("/chat/{dataset_id}")
async def get_chat_history(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Fetch persistent multi-turn chat message history for a dataset."""
    stmt = select(ChatMessageModel).where(ChatMessageModel.dataset_id == dataset_id).order_by(ChatMessageModel.created_at.asc())
    res = await db.execute(stmt)
    messages = res.scalars().all()
    
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "chart_spec": m.chart_spec,
            "query_executed": m.query_executed,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]


@router.delete("/chat/{dataset_id}")
async def clear_chat_history(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Clear chat message history for a dataset."""
    stmt = delete(ChatMessageModel).where(ChatMessageModel.dataset_id == dataset_id)
    await db.execute(stmt)
    await db.commit()
    return {"message": "Chat history cleared successfully"}


@router.get("/budget/spend")
async def get_budget_spend(
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Fetch current daily LLM spend metrics."""
    spend = ai_budget_manager.get_current_daily_spend()
    return {
        "daily_spend_usd": spend,
        "daily_limit_usd": 10.0,
        "remaining_budget_usd": max(0.0, 10.0 - spend)
    }
