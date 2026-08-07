import os
import uuid
import shutil
from typing import List, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import polars as pl

from app.domain.dataset.entities import Dataset as DomainDataset, Workspace as DomainWorkspace, DatasetFormat
from app.infrastructure.repositories.postgres_repository import DatasetRepository, WorkspaceRepository
from app.infrastructure.engine.polars_processor import polars_processor
from app.core.config import settings


class DatasetService:
    """Manages workspace environments, dataset storage, schema profiling, and parquet conversions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dataset_repo = DatasetRepository(session)
        self.workspace_repo = WorkspaceRepository(session)

    async def create_workspace(self, name: str, description: str = None) -> DomainWorkspace:
        db_ws = await self.workspace_repo.create(name, description)
        return DomainWorkspace.model_validate(db_ws)

    async def list_workspaces(self) -> List[DomainWorkspace]:
        db_workspaces = await self.workspace_repo.list_all()
        return [DomainWorkspace.model_validate(ws) for ws in db_workspaces]

    async def upload_dataset(
        self, 
        workspace_id: str, 
        file: UploadFile,
        dataset_name: Optional[str] = None
    ) -> DomainDataset:
        """Upload, profile, convert to Parquet (if CSV), and register a dataset within a workspace."""
        ws_uuid = uuid.UUID(workspace_id)
        
        # Verify workspace exists
        workspace = await self.workspace_repo.get_by_id(ws_uuid)
        if not workspace:
            raise ValueError(f"Workspace with ID {workspace_id} does not exist.")

        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1].lower()

        # Resolve format
        if file_ext == ".csv":
            source_format = DatasetFormat.CSV
        elif file_ext == ".parquet":
            source_format = DatasetFormat.PARQUET
        elif file_ext in (".xlsx", ".xls"):
            source_format = DatasetFormat.EXCEL
        elif file_ext == ".json":
            source_format = DatasetFormat.JSON
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        # Unique name in storage
        unique_file_id = uuid.uuid4()
        temp_filename = f"{unique_file_id}{file_ext}"
        temp_file_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

        logger.info(f"Saving temporary upload to: {temp_file_path}")
        
        # Stream file to disk (protects against high memory usage)
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed writing upload file to storage: {e}")
            raise IOError("Could not save upload dataset.") from e

        # Analyze using Polars (determines Schema and Data Quality)
        try:
            schema, quality_report = polars_processor.profile_dataset(temp_file_path, source_format)
        except Exception as e:
            logger.error(f"Failed profiling dataset schema: {e}")
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise ValueError(f"Dataset profiling failed. The file is corrupt or has an invalid structure: {e}") from e

        # Production optimization: If format is CSV, convert to Parquet to save storage and drastically speed up future analytical queries.
        final_file_path = temp_file_path
        final_format = source_format

        if source_format == DatasetFormat.CSV:
            try:
                parquet_filename = f"{unique_file_id}.parquet"
                parquet_file_path = os.path.join(settings.UPLOAD_DIR, parquet_filename)
                
                logger.info(f"Converting CSV {temp_file_path} to optimized Parquet: {parquet_file_path}")
                # Load CSV and sink to parquet
                lf = polars_processor.load_lazy_frame(temp_file_path, source_format)
                lf.sink_parquet(parquet_file_path)
                
                # Delete old CSV
                os.remove(temp_file_path)
                final_file_path = parquet_file_path
                final_format = DatasetFormat.PARQUET
            except Exception as e:
                logger.warning(f"Parquet conversion failed, keeping original CSV structure. Error: {e}")

        # Register metadata in transactional DB
        name = dataset_name or os.path.splitext(original_filename)[0]
        db_ds = await self.dataset_repo.create(
            workspace_id=ws_uuid,
            name=name,
            filename=os.path.basename(final_file_path),
            file_format=final_format.value,
            file_path=final_file_path,
            schema_definition=schema.model_dump(),
            quality_report=quality_report.model_dump(),
            row_count=schema.row_count,
            column_count=schema.column_count,
            file_size_bytes=schema.file_size_bytes
        )

        # Trigger quality warning alerts
        try:
            from app.application.notification.services import NotificationService
            notif_service = NotificationService(self.session)
            await notif_service.check_dataset_and_alert(name, quality_report.health_score)
        except Exception as e:
            logger.warning(f"Failed to trigger automated notification checking: {e}")

        logger.info(f"Dataset '{name}' successfully registered in database under id {db_ds.id}.")
        return DomainDataset.model_validate(db_ds)

    async def list_workspace_datasets(self, workspace_id: str) -> List[DomainDataset]:
        ws_uuid = uuid.UUID(workspace_id)
        db_datasets = await self.dataset_repo.get_by_workspace(ws_uuid)
        return [DomainDataset.model_validate(ds) for ds in db_datasets]

    async def get_dataset(self, dataset_id: str) -> DomainDataset:
        ds_uuid = uuid.UUID(dataset_id)
        db_dataset = await self.dataset_repo.get_by_id(ds_uuid)
        if not db_dataset:
            raise ValueError(f"Dataset with ID {dataset_id} not found.")
        return DomainDataset.model_validate(db_dataset)
