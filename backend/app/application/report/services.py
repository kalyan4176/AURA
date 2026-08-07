import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.domain.report.entities import Report, ReportComponent, Comment
from app.infrastructure.repositories.postgres_repository import ReportRepository


class ReportService:
    """Enterprise Report Document Model Service.

    Coordinates document model layouts, annotations, collaborative comments,
    and markdown report compilations.
    """

    def __init__(self, session: AsyncSession):
        self.repo = ReportRepository(session)

    async def create_report(
        self, 
        workspace_id: str, 
        name: str, 
        components: List[ReportComponent],
        layout: List[Dict[str, Any]]
    ) -> Report:
        """Create a new report document layout under a workspace."""
        ws_uuid = uuid.UUID(workspace_id)
        comp_dicts = [c.model_dump(mode='json') for c in components]
        
        db_report = await self.repo.create(
            workspace_id=ws_uuid,
            name=name,
            components=comp_dicts,
            layout=layout
        )
        return Report.model_validate(db_report)

    async def list_reports(self, workspace_id: str) -> List[Report]:
        ws_uuid = uuid.UUID(workspace_id)
        db_reports = await self.repo.get_by_workspace(ws_uuid)
        return [Report.model_validate(r) for r in db_reports]

    async def get_report(self, report_id: str) -> Report:
        r_uuid = uuid.UUID(report_id)
        db_report = await self.repo.get_by_id(r_uuid)
        if not db_report:
            raise ValueError(f"Report with ID {report_id} not found.")
        return Report.model_validate(db_report)

    async def add_annotation(self, report_id: str, component_id: str, text: str) -> Report:
        """Append an analytical annotation to a report card component."""
        report = await self.get_report(report_id)
        
        updated_comps = []
        for c in report.components:
            if c.id == component_id:
                c.annotations.append(text)
            updated_comps.append(c)

        db_report = await self.repo.update(
            report_id=uuid.UUID(report_id),
            components=[c.model_dump(mode='json') for c in updated_comps],
            layout=report.layout,
            comments=[com.model_dump(mode='json') for com in report.comments]
        )
        return Report.model_validate(db_report)

    async def add_comment(self, report_id: str, user_email: str, content: str) -> Report:
        """Log a collaborative comment on the report timeline."""
        report = await self.get_report(report_id)
        
        new_comment = Comment(
            id=str(uuid.uuid4()),
            user_email=user_email,
            content=content,
            created_at=datetime.now(timezone.utc)
        )
        
        comments_list = report.comments + [new_comment]
        
        db_report = await self.repo.update(
            report_id=uuid.UUID(report_id),
            components=[c.model_dump(mode='json') for c in report.components],
            layout=report.layout,
            comments=[c.model_dump(mode='json') for c in comments_list]
        )
        return Report.model_validate(db_report)

    async def update_layout(self, report_id: str, layout: List[Dict[str, Any]], components: List[ReportComponent]) -> Report:
        """Update report layout coordinates and card configs."""
        report = await self.get_report(report_id)
        
        db_report = await self.repo.update(
            report_id=uuid.UUID(report_id),
            components=[c.model_dump(mode='json') for c in components],
            layout=layout,
            comments=[c.model_dump(mode='json') for c in report.comments]
        )
        return Report.model_validate(db_report)

    async def compile_to_markdown(self, report_id: str) -> str:
        """Translate the structured Report Document Model into a compiled human-readable Markdown file."""
        report = await self.get_report(report_id)
        
        md = []
        md.append(f"# AURA Intelligence Report: {report.name}")
        md.append(f"**Generated at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"**Workspace reference:** {report.workspace_id}")
        md.append("\n---\n")

        md.append("## Executive Report Components")
        
        for c in report.components:
            md.append(f"\n### Card Element: {c.title} (Type: {c.type.upper()})")
            
            # Formulate textual schema details
            if c.type == 'text':
                content = c.config.get("content", "Empty text card.")
                md.append(f"\n> {content}\n")
            elif c.type == 'chart':
                chart_type = c.config.get("chart_type", "Apache EChart Configuration")
                md.append(f"\n*Interactive analytical visualization of type **{chart_type}**.*")
            elif c.type == 'table':
                md.append("\n*Data Grid View preview panel.*")

            # Append analyst annotations
            if c.annotations:
                md.append("\n**Analyst Annotations & Observations:**")
                for note in c.annotations:
                    md.append(f"- *{note}*")

        # Collaborative comments thread
        if report.comments:
            md.append("\n---\n")
            md.append("## Collaborative Discussion Thread")
            for com in report.comments:
                time_str = com.created_at.strftime('%Y-%m-%d %H:%M:%S')
                md.append(f"- **{com.user_email}** *({time_str})*: {com.content}")

        return "\n".join(md)
