from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.domain.report.entities import Report, ReportComponent
from app.application.report.services import ReportService
from app.application.narrative.services import NarrativeService
from app.presentation.api.auth import get_current_user_dependency
from app.domain.auth.entities import User as DomainUser

router = APIRouter(prefix="/reports", tags=["Interactive Reporting Engine"])


# Request schemas
class CreateReportRequest(BaseModel):
    workspace_id: str
    name: str
    components: List[ReportComponent]
    layout: List[Dict[str, Any]]


class AddAnnotationRequest(BaseModel):
    component_id: str
    text: str


class AddCommentRequest(BaseModel):
    content: str


class UpdateLayoutRequest(BaseModel):
    layout: List[Dict[str, Any]]
    components: List[ReportComponent]


@router.post("", response_model=Report, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: CreateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    return await service.create_report(
        workspace_id=payload.workspace_id,
        name=payload.name,
        components=payload.components,
        layout=payload.layout
    )


@router.get("/workspace/{workspace_id}", response_model=List[Report])
async def list_reports(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    return await service.list_reports(workspace_id)


@router.get("/{report_id}", response_model=Report)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    try:
        return await service.get_report(report_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{report_id}/annotations", response_model=Report)
async def add_annotation(
    report_id: str,
    payload: AddAnnotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    try:
        return await service.add_annotation(
            report_id=report_id,
            component_id=payload.component_id,
            text=payload.text
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{report_id}/comments", response_model=Report)
async def add_comment(
    report_id: str,
    payload: AddCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    try:
        return await service.add_comment(
            report_id=report_id,
            user_email=current_user.email,
            content=payload.content
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{report_id}/layout", response_model=Report)
async def update_layout(
    report_id: str,
    payload: UpdateLayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    service = ReportService(db)
    try:
        return await service.update_layout(
            report_id=report_id,
            layout=payload.layout,
            components=payload.components
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{report_id}/export")
async def export_report_markdown(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Compile and download Report document model as clean Markdown file."""
    service = ReportService(db)
    try:
        md_text = await service.compile_to_markdown(report_id)
        return Response(
            content=md_text,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=aura_report_{report_id}.md"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{report_id}/summary")
async def generate_report_executive_summary(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: DomainUser = Depends(get_current_user_dependency)
):
    """Query AI Narrative Engine to generate an executive briefing card for the report."""
    service = ReportService(db)
    try:
        report = await service.get_report(report_id)
        components_payload = [c.model_dump() for c in report.components]
        
        summary = await NarrativeService.generate_report_executive_summary(
            report_name=report.name,
            components=components_payload
        )
        return {"summary": summary}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
