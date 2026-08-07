from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple, Any


class CorrelationMatrixResult(BaseModel):
    columns: List[str]
    matrix: List[List[float]]
    method: str  # pearson or spearman


class StatisticalTestResult(BaseModel):
    test_name: str
    statistic: float
    p_value: float
    is_significant: bool
    confidence_interval: Optional[Tuple[float, float]] = None
    normality_p_value: Optional[float] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)
    business_explanation: str


class AnomalyReport(BaseModel):
    total_anomalies: int
    anomaly_percentage: float
    anomaly_indices: List[int]
    confidence_scores: List[float]
    summary: str


class ForecastResult(BaseModel):
    timeline: List[str]
    historical_values: List[float]
    forecast_timeline: List[str]
    forecast_values: List[float]
    lower_confidence_bounds: List[float]
    upper_confidence_bounds: List[float]
    confidence_level: float = 0.95
    model_details: str
