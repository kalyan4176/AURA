import pytest
import uuid
from app.application.report.services import ReportService
from app.application.knowledge.services import KnowledgeService
from app.domain.report.entities import ReportComponent


@pytest.mark.asyncio
async def test_report_service_lifecycle(db_session):
    report_service = ReportService(db_session)
    ws_id = uuid.uuid4()

    # 1. Create Report
    components = [
        ReportComponent(
            id="c1",
            type="text",
            title="Analysis Card",
            config={"content": "Core findings..."},
            annotations=[]
        )
    ]
    layout = [{"i": "c1", "x": 0, "y": 0, "w": 6, "h": 2}]
    
    report = await report_service.create_report(
        workspace_id=str(ws_id),
        name="Quarterly Quality Briefing",
        components=components,
        layout=layout
    )
    
    assert report.id is not None
    assert report.name == "Quarterly Quality Briefing"
    assert len(report.components) == 1

    # 2. Add Annotation to Card
    updated_report = await report_service.add_annotation(
        report_id=str(report.id),
        component_id="c1",
        text="Outliers detected on column Y."
    )
    assert "Outliers detected on column Y." in updated_report.components[0].annotations

    # 3. Add Collaborative Comment
    commented_report = await report_service.add_comment(
        report_id=str(report.id),
        user_email="analyst@aura.ai",
        content="Should we verify outlier significance?"
    )
    assert len(commented_report.comments) == 1
    assert commented_report.comments[0].user_email == "analyst@aura.ai"

    # 4. Compile Markdown check
    md_export = await report_service.compile_to_markdown(str(report.id))
    assert "# AURA Intelligence Report: Quarterly Quality Briefing" in md_export
    assert "Outliers detected on column Y." in md_export
    assert "Should we verify outlier significance?" in md_export


@pytest.mark.asyncio
async def test_knowledge_base_retrieval(db_session):
    knowledge_service = KnowledgeService(db_session)

    # 1. Index Business Rules
    doc1 = await knowledge_service.add_document(
        title="Outlier Handling Directive",
        content="Standard Operating Procedure (SOP): Always filter out-of-bounds anomaly counts above 30 percent before scoring models.",
        metadata={"category": "compliance"}
    )
    assert doc1.id is not None

    doc2 = await knowledge_service.add_document(
        title="Missing Values Policy",
        content="Standard clean rules: If a numerical column has over 40 percent empty indices, discard or request database re-runs.",
        metadata={"category": "cleaning"}
    )

    # 2. Hybrid Query Match checks
    # Query should score doc1 higher due to outlier reference
    results = await knowledge_service.retrieve_hybrid("outlier anomaly percentage rules", limit=1)
    
    assert len(results) == 1
    assert results[0]["document"].title == "Outlier Handling Directive"
    assert results[0]["score"] > 0.0
