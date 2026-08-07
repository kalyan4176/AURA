from typing import Dict, Any, List
from loguru import logger

from app.application.budget.services import ai_budget_manager


class NarrativeService:
    """Enterprise AI Narrative & Report Narration Engine.

    Translates quantitative analysis into evidence-backed business insights.
    """

    @staticmethod
    async def generate_chart_narration(chart_title: str, chart_type: str, chart_data: Dict[str, Any]) -> str:
        """Query LLM (Ollama/Gemini) through the budget manager to describe a visualization."""
        logger.info(f"Generating semantic narration for chart: {chart_title}")

        evidence_payload = {
            "title": chart_title,
            "type": chart_type,
            "analytics_result_preview": chart_data
        }

        prompt = (
            f"Please narrate the business implications of this chart visualization: '{chart_title}'. "
            f"Focus on key insights, correlations, or trends. "
            f"Evidence details:\n{evidence_payload}"
        )

        try:
            # We bypass the standard deterministic sql route and ask for LLM directly
            # By triggering execute_query with is_deterministic overridden or sending a structured prompt
            # We mock a dataset path or pass it to budget manager execution
            response = await ai_budget_manager.execute_query(
                dataset_path="data/uploads/virtual_evidence.parquet",
                user_query=prompt
            )
            return response.get("response", "Could not generate chart summary.")
        except Exception as e:
            logger.error(f"Chart narrative generation failed: {e}")
            return "Chart summary generation currently unavailable."

    @staticmethod
    async def generate_report_executive_summary(report_name: str, components: List[Dict[str, Any]]) -> str:
        """Compile a summary of multiple analytical cards into a coherent executive report narrative."""
        logger.info(f"Compiling executive summary for report: {report_name}")

        briefing = []
        for i, c in enumerate(components):
            briefing.append({
                "index": i + 1,
                "card_title": c.get("title", "Metric"),
                "card_type": c.get("type", "unknown"),
                "annotations": c.get("annotations", [])
            })

        prompt = (
            f"Generate a professional, high-level Executive Summary for the business report titled: '{report_name}'. "
            f"Synthesize the observations from the following cards and annotations, highlighting key decision recommendations. "
            f"Report Structure:\n{briefing}"
        )

        try:
            response = await ai_budget_manager.execute_query(
                dataset_path="data/uploads/virtual_evidence.parquet",
                user_query=prompt
            )
            return response.get("response", "Could not generate report summary.")
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return "Executive report summary generation currently unavailable."
