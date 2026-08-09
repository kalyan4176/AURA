from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.repositories.models import UserModel, WorkspaceModel, DatasetModel, ReportModel, KnowledgeDocumentModel, NotificationModel
from app.domain.auth.entities import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: UUID) -> Optional[UserModel]:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, user_in: UserCreate, hashed_password: str) -> UserModel:
        db_user = UserModel(
            email=user_in.email,
            hashed_password=hashed_password,
            role=user_in.role.value if user_in.role else "viewer"
        )
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, workspace_id: UUID) -> Optional[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, name: str, description: Optional[str] = None) -> WorkspaceModel:
        db_ws = WorkspaceModel(name=name, description=description)
        self.session.add(db_ws)
        await self.session.commit()
        await self.session.refresh(db_ws)
        return db_ws

    async def list_all(self) -> List[WorkspaceModel]:
        stmt = select(WorkspaceModel).order_by(WorkspaceModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, workspace_id: UUID) -> bool:
        stmt = select(WorkspaceModel).where(WorkspaceModel.id == workspace_id)
        result = await self.session.execute(stmt)
        db_ws = result.scalars().first()
        if db_ws:
            await self.session.delete(db_ws)
            await self.session.commit()
            return True
        return False


class DatasetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, dataset_id: UUID) -> Optional[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_workspace(self, workspace_id: UUID) -> List[DatasetModel]:
        stmt = select(DatasetModel).where(DatasetModel.workspace_id == workspace_id).order_by(DatasetModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, 
        workspace_id: UUID, 
        name: str, 
        filename: str, 
        file_format: str, 
        file_path: str, 
        schema_definition: dict,
        quality_report: dict,
        row_count: int,
        column_count: int,
        file_size_bytes: int
    ) -> DatasetModel:
        db_ds = DatasetModel(
            workspace_id=workspace_id,
            name=name,
            filename=filename,
            file_format=file_format,
            file_path=file_path,
            schema_definition=schema_definition,
            quality_report=quality_report,
            row_count=row_count,
            column_count=column_count,
            file_size_bytes=file_size_bytes
        )
        self.session.add(db_ds)
        await self.session.commit()
        await self.session.refresh(db_ds)
        return db_ds

    async def delete(self, dataset_id: UUID) -> bool:
        stmt = select(DatasetModel).where(DatasetModel.id == dataset_id)
        result = await self.session.execute(stmt)
        db_ds = result.scalars().first()
        if db_ds:
            import os
            if os.path.exists(db_ds.file_path):
                try:
                    os.remove(db_ds.file_path)
                except Exception:
                    pass
            await self.session.delete(db_ds)
            await self.session.commit()
            return True
        return False


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, report_id: UUID) -> Optional[ReportModel]:
        stmt = select(ReportModel).where(ReportModel.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_workspace(self, workspace_id: UUID) -> List[ReportModel]:
        stmt = select(ReportModel).where(ReportModel.workspace_id == workspace_id).order_by(ReportModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, workspace_id: UUID, name: str, components: list, layout: list) -> ReportModel:
        db_report = ReportModel(
            workspace_id=workspace_id,
            name=name,
            components=components,
            layout=layout,
            comments=[]
        )
        self.session.add(db_report)
        await self.session.commit()
        await self.session.refresh(db_report)
        return db_report

    async def update(self, report_id: UUID, components: list, layout: list, comments: list) -> Optional[ReportModel]:
        db_report = await self.get_by_id(report_id)
        if not db_report:
            return None
        
        db_report.components = components
        db_report.layout = layout
        db_report.comments = comments
        
        self.session.add(db_report)
        await self.session.commit()
        await self.session.refresh(db_report)
        return db_report


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, doc_id: UUID) -> Optional[KnowledgeDocumentModel]:
        stmt = select(KnowledgeDocumentModel).where(KnowledgeDocumentModel.id == doc_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_all(self) -> List[KnowledgeDocumentModel]:
        stmt = select(KnowledgeDocumentModel).order_by(KnowledgeDocumentModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, title: str, content: str, metadata_fields: dict, embedding: list = None) -> KnowledgeDocumentModel:
        db_doc = KnowledgeDocumentModel(
            title=title,
            content=content,
            metadata_fields=metadata_fields,
            embedding=embedding
        )
        self.session.add(db_doc)
        await self.session.commit()
        await self.session.refresh(db_doc)
        return db_doc


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, notif_id: UUID) -> Optional[NotificationModel]:
        stmt = select(NotificationModel).where(NotificationModel.id == notif_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_unread(self) -> List[NotificationModel]:
        stmt = select(NotificationModel).where(NotificationModel.is_read == False).order_by(NotificationModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, type: str, message: str) -> NotificationModel:
        db_notif = NotificationModel(type=type, message=message)
        self.session.add(db_notif)
        await self.session.commit()
        await self.session.refresh(db_notif)
        return db_notif

    async def mark_read(self, notif_id: UUID) -> Optional[NotificationModel]:
        db_notif = await self.get_by_id(notif_id)
        if not db_notif:
            return None
        db_notif.is_read = True
        self.session.add(db_notif)
        await self.session.commit()
        await self.session.refresh(db_notif)
        return db_notif


