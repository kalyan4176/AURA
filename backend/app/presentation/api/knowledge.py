from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.domain.knowledge.entities import KnowledgeDocument
from app.application.knowledge.services import KnowledgeService
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/knowledge", tags=["Knowledge Engine"])


class CreateDocumentRequest(BaseModel):
    title: str
    content: str
    metadata_fields: Optional[Dict[str, Any]] = None


@router.post("/documents", response_model=KnowledgeDocument, status_code=status.HTTP_201_CREATED)
async def add_knowledge_document(
    payload: CreateDocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Add a context catalog sheet or business rules catalog to knowledge engine."""
    service = KnowledgeService(db)
    return await service.add_document(
        title=payload.title,
        content=payload.content,
        metadata=payload.metadata_fields
    )


@router.get("/retrieve")
async def retrieve_knowledge_context(
    query: str,
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Run keyword-embedding hybrid search to find corresponding business rules or details."""
    service = KnowledgeService(db)
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )
    
    results = await service.retrieve_hybrid(query_text=query, limit=limit)
    return results
