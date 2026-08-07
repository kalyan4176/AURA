import os
import tempfile
import pytest
import numpy as np
import polars as pl

from app.application.analytics.services import AnalyticsService


@pytest.fixture
def clean_parquet_dataset():
    """Generates a synthetic time-series and grouped dataset in Parquet format."""
    np.random.seed(42)
    n = 20
    
    # Linear trend values for forecasting
    historical_vals = [float(10.0 + 2.5 * i + np.random.normal(0, 0.5)) for i in range(n)]
    
    # 2 groups for hypothesis tests (Group A vs Group B)
    # Group A: lower values, Group B: higher values
    group_col = ["A"] * 10 + ["B"] * 10
    value_col = list(np.random.normal(5, 0.5, 10)) + list(np.random.normal(15, 0.5, 10))
    
    # Multimodal values for correlations
    x1 = np.random.uniform(10, 100, n)
    x2 = x1 * 2 + np.random.normal(0, 5, n)  # highly correlated with x1
    
    data = {
        "date": [f"2026-08-{str(i+1).zfill(2)}" for i in range(n)],
        "value": historical_vals,
        "group": group_col,
        "score": [float(v) for v in value_col],
        "feature_x": [float(x) for x in x1],
        "feature_y": [float(x) for x in x2]
    }
    
    df = pl.DataFrame(data)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        df.write_parquet(tmp.name)
        file_path = tmp.name
        
    yield file_path
    
    if os.path.exists(file_path):
        os.remove(file_path)


def test_calculate_correlations(clean_parquet_dataset):
    # Calculate pearson correlations
    result = AnalyticsService.calculate_correlations(
        file_path=clean_parquet_dataset,
        columns=["feature_x", "feature_y"],
        method="pearson"
    )
    
    assert result.method == "pearson"
    assert "feature_x" in result.columns
    assert "feature_y" in result.columns
    # Check that diagonal coefficients are 1.0
    assert result.matrix[0][0] == 1.0
    # Check that correlation coefficient is high (> 0.9)
    assert result.matrix[0][1] > 0.9


def test_hypothesis_statistical_tests(clean_parquet_dataset):
    # Run two-sample Welchs t-test
    result_ttest = AnalyticsService.run_statistical_test(
        file_path=clean_parquet_dataset,
        test_type="t_test",
        group_col="group",
        value_col="score"
    )
    
    assert result_ttest.test_name == "Independent Two-Sample T-Test (Welch)"
    # Since Group A and Group B are highly distinct (5 vs 15), results should be significant
    assert result_ttest.is_significant is True
    assert result_ttest.p_value < 0.01
    assert "group1" in result_ttest.additional_metadata
    assert result_ttest.business_explanation != ""

    # Run ANOVA test
    result_anova = AnalyticsService.run_statistical_test(
        file_path=clean_parquet_dataset,
        test_type="anova",
        group_col="group",
        value_col="score"
    )
    
    assert result_anova.test_name == "One-way ANOVA (F-Test)"
    assert result_anova.is_significant is True
    assert result_anova.p_value < 0.01


def test_anomaly_detection_ml(clean_parquet_dataset):
    # Let's inject a massive outlier in the Parquet file to verify detection
    df = pl.read_parquet(clean_parquet_dataset)
    # Edit index 5 score to make it a massive outlier
    df[5, "score"] = 999.0
    
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        df.write_parquet(tmp.name)
        outlier_file = tmp.name
        
    try:
        # Run Isolation Forest
        report = AnalyticsService.detect_anomalies(
            file_path=outlier_file,
            columns=["score"],
            algorithm="isolation_forest",
            contamination=0.1
        )
        
        assert report.total_anomalies >= 1
        # Index 5 should be flagged as an anomaly
        assert 5 in report.anomaly_indices
        assert report.anomaly_percentage > 0.0
        assert len(report.confidence_scores) == report.total_anomalies
    finally:
        if os.path.exists(outlier_file):
            os.remove(outlier_file)


def test_exponential_smoothing_forecast(clean_parquet_dataset):
    # Run forecasting
    result = AnalyticsService.generate_forecast(
        file_path=clean_parquet_dataset,
        time_col="date",
        value_col="value",
        steps=5
    )
    
    assert len(result.forecast_values) == 5
    assert len(result.forecast_timeline) == 5
    # Historical timelines and values should match
    assert len(result.timeline) == 20
    assert len(result.historical_values) == 20
    
    # Projections should be increasing generally due to linear trend
    assert result.forecast_values[-1] > result.historical_values[-1]
    # Check that confidence bounds encapsulate predictions
    assert result.lower_confidence_bounds[0] <= result.forecast_values[0]
    assert result.upper_confidence_bounds[0] >= result.forecast_values[0]
