from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.dataset.entities import Dataset as DomainDataset, Workspace as DomainWorkspace
from app.application.dataset.services import DatasetService
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser, UserRole

router = APIRouter(prefix="/workspaces", tags=["Workspace & Datasets"])


def require_role(roles: List[UserRole]):
    """Decorator-like dependency factory to enforce RBAC permissions on endpoints."""
    def dependency(current_user: DomainUser = Depends(get_current_user_dependency)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not authorized for your role level."
            )
        return current_user
    return dependency


@router.post("", response_model=DomainWorkspace, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    name: str, 
    description: Optional[str] = None, 
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST]))
):
    service = DatasetService(db)
    return await service.create_workspace(name, description)


@router.get("", response_model=List[DomainWorkspace])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = DatasetService(db)
    return await service.list_workspaces()


@router.post("/{workspace_id}/datasets", response_model=DomainDataset, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    workspace_id: str,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(require_role([UserRole.ADMIN, UserRole.ANALYST]))
):
    service = DatasetService(db)
    try:
        return await service.upload_dataset(workspace_id, file, name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{workspace_id}/datasets", response_model=List[DomainDataset])
async def list_datasets(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = DatasetService(db)
    return await service.list_workspace_datasets(workspace_id)


@router.get("/datasets/{dataset_id}", response_model=DomainDataset)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = DatasetService(db)
    try:
        return await service.get_dataset(dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Fetch preview rows from Parquet file using in-memory DuckDB."""
    service = DatasetService(db)
    from app.infrastructure.engine.duckdb_client import duckdb_client
    try:
        dataset = await service.get_dataset(dataset_id)
        preview_df = duckdb_client.get_preview(dataset.file_path, dataset.file_format, limit=limit)
        return {
            "columns": [{"name": c} for c in preview_df.columns],
            "rows": preview_df.to_dicts()
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

