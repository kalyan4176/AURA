import math
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from loguru import logger

from app.domain.analytics.entities import (
    CorrelationMatrixResult, StatisticalTestResult, AnomalyReport, ForecastResult
)


class AnalyticsService:
    """Enterprise Statistical Analytics & Machine Learning Execution Engine.

    Operates purely deterministically using scientific computing tools.
    """

    @staticmethod
    def calculate_correlations(file_path: str, columns: List[str], method: str = "pearson") -> CorrelationMatrixResult:
        """Calculate pairwise correlation coefficients between numeric columns using Polars."""
        logger.info(f"Computing {method} correlations for columns: {columns} on {file_path}")
        
        # Load columns lazily, drop null rows
        df = pl.scan_parquet(file_path).select(columns).drop_nulls().collect()
        
        if df.height < 3:
            raise ValueError("Dataset has insufficient non-null rows for correlation computation (minimum 3 required).")

        matrix = []
        for col_x in columns:
            row_coeffs = []
            for col_y in columns:
                x = df.get_column(col_x).to_numpy()
                y = df.get_column(col_y).to_numpy()
                
                if method == "pearson":
                    coef, _ = stats.pearsonr(x, y)
                elif method == "spearman":
                    coef, _ = stats.spearmanr(x, y)
                else:
                    raise ValueError(f"Unsupported correlation method: {method}")
                
                # Treat NaN results (e.g. constant columns) safely
                if math.isnan(coef):
                    coef = 0.0
                row_coeffs.append(round(float(coef), 4))
            matrix.append(row_coeffs)

        return CorrelationMatrixResult(columns=columns, matrix=matrix, method=method)

    @staticmethod
    def run_statistical_test(
        file_path: str, 
        test_type: str, 
        group_col: str, 
        value_col: str,
        control_val: Optional[str] = None,
        treatment_val: Optional[str] = None
    ) -> StatisticalTestResult:
        """Run standard hypothesis tests (t-test, ANOVA, Mann-Whitney U, normality shapiro)."""
        logger.info(f"Executing statistical test: {test_type} on {value_col} grouped by {group_col}")

        # Scan dataset Parquet
        df = pl.scan_parquet(file_path).select([group_col, value_col]).drop_nulls().collect()
        
        # Segment groups
        unique_groups = df.get_column(group_col).unique().to_list()
        
        if len(unique_groups) < 2:
            raise ValueError(f"Grouping column '{group_col}' needs at least 2 distinct groups. Found: {unique_groups}")

        # If running 2-sample tests, extract samples
        if test_type in ("t_test", "mann_whitney"):
            g1_name = control_val or unique_groups[0]
            g2_name = treatment_val or unique_groups[1]
            
            sample1 = df.filter(pl.col(group_col) == g1_name).get_column(value_col).to_numpy()
            sample2 = df.filter(pl.col(group_col) == g2_name).get_column(value_col).to_numpy()
            
            if len(sample1) < 3 or len(sample2) < 3:
                raise ValueError("Insufficient sample sizes per group. Groups require at least 3 records.")
            
            # Normality test
            _, shapiro_p1 = stats.shapiro(sample1)
            _, shapiro_p2 = stats.shapiro(sample2)
            avg_normality_p = float((shapiro_p1 + shapiro_p2) / 2)
            
            if test_type == "t_test":
                stat, p_val = stats.ttest_ind(sample1, sample2, equal_var=False)
                test_name = "Independent Two-Sample T-Test (Welch)"
                business_explanation = (
                    f"Comparing '{g1_name}' (mean={np.mean(sample1):.2f}) and '{g2_name}' (mean={np.mean(sample2):.2f}). "
                    f"A p-value of {p_val:.5f} indicates the differences are "
                    f"{'statistically significant' if p_val < 0.05 else 'not statistically significant'}."
                )
            else:
                stat, p_val = stats.mannwhitneyu(sample1, sample2, alternative="two-sided")
                test_name = "Mann-Whitney U Rank Test"
                business_explanation = (
                    f"Rank sum comparison indicates the distributions of '{g1_name}' and '{g2_name}' are "
                    f"{'statistically distinct' if p_val < 0.05 else 'not statistically distinct'}."
                )
                
            return StatisticalTestResult(
                test_name=test_name,
                statistic=float(stat),
                p_value=float(p_val),
                is_significant=p_val < 0.05,
                normality_p_value=avg_normality_p,
                additional_metadata={"group1": str(g1_name), "group2": str(g2_name)},
                business_explanation=business_explanation
            )
            
        elif test_type == "anova":
            groups_data = []
            for g in unique_groups:
                g_samples = df.filter(pl.col(group_col) == g).get_column(value_col).to_numpy()
                if len(g_samples) < 3:
                    raise ValueError(f"Group '{g}' has insufficient samples for ANOVA.")
                groups_data.append(g_samples)
                
            stat, p_val = stats.f_oneway(*groups_data)
            business_explanation = (
                f"One-Way ANOVA tested differences across {len(unique_groups)} groups. "
                f"The difference is {'significant' if p_val < 0.05 else 'not significant'} (p={p_val:.5f})."
            )
            return StatisticalTestResult(
                test_name="One-way ANOVA (F-Test)",
                statistic=float(stat),
                p_value=float(p_val),
                is_significant=p_val < 0.05,
                business_explanation=business_explanation
            )
        else:
            raise ValueError(f"Unsupported statistical test: {test_type}")

    @staticmethod
    def detect_anomalies(file_path: str, columns: List[str], algorithm: str = "isolation_forest", contamination: float = 0.05) -> AnomalyReport:
        """Run anomaly detection using Isolation Forest or Local Outlier Factor."""
        logger.info(f"Running ML anomaly detection ({algorithm}) on columns {columns}")
        
        # Load dataset, fill null values with mean/median to satisfy ML model inputs
        df = pl.scan_parquet(file_path).select(columns).collect()
        
        # Convert to numpy and fill NaNs
        X = df.to_numpy().copy()
        col_means = np.nanmean(X, axis=0)
        # Handle cases where columns are entirely NaN
        col_means = np.nan_to_num(col_means)
        inds = np.where(np.isnan(X))
        X[inds] = np.take(col_means, inds[1])
        
        if len(X) < 5:
            raise ValueError("Too few records for anomaly detection model (minimum 5 required).")

        if algorithm == "isolation_forest":
            model = IsolationForest(contamination=contamination, random_state=42)
            preds = model.fit_predict(X)
            # Higher decision score indicates normal; negative indicate anomalous
            decision_scores = model.decision_function(X)
            # Map score to positive confidence [0, 1]
            min_s, max_s = np.min(decision_scores), np.max(decision_scores)
            span = (max_s - min_s) if max_s != min_s else 1.0
            confidence = [float(1.0 - (s - min_s) / span) for s in decision_scores]
        elif algorithm == "lof":
            model = LocalOutlierFactor(contamination=contamination, novelty=True)
            model.fit(X)
            preds = model.predict(X)
            negative_outlier_factor = model.negative_outlier_factor_
            min_s, max_s = np.min(negative_outlier_factor), np.max(negative_outlier_factor)
            span = (max_s - min_s) if max_s != min_s else 1.0
            confidence = [float(1.0 - (s - min_s) / span) for s in negative_outlier_factor]
        else:
            raise ValueError(f"Unsupported anomaly algorithm: {algorithm}")

        # -1 indicates outlier/anomaly
        anomaly_indices = np.where(preds == -1)[0].tolist()
        total_anomalies = len(anomaly_indices)
        pct = (total_anomalies / len(X)) * 100

        if total_anomalies > 0:
            avg_conf = float(np.mean([confidence[i] for i in anomaly_indices]))
            summary = (
                f"Detected {total_anomalies} anomalies ({pct:.2f}% of data) using {algorithm.upper()}. "
                f"Average confidence index for flagged outliers is {avg_conf:.2f}."
            )
        else:
            summary = f"No anomalies detected using {algorithm.upper()}."

        return AnomalyReport(
            total_anomalies=total_anomalies,
            anomaly_percentage=pct,
            anomaly_indices=anomaly_indices,
            confidence_scores=[confidence[i] for i in anomaly_indices],
            summary=summary
        )

    @staticmethod
    def generate_forecast(file_path: str, time_col: str, value_col: str, steps: int = 6) -> ForecastResult:
        """Run Holt-Winters exponential smoothing time-series forecast on columns."""
        logger.info(f"Running exponential smoothing forecasting on time column {time_col} and value column {value_col}")

        # Load time series data, sort chronologically
        df = pl.scan_parquet(file_path).select([time_col, value_col]).drop_nulls().collect()
        
        # Sort values
        df = df.sort(time_col)
        
        historical_times = [str(x) for x in df.get_column(time_col).to_list()]
        historical_vals = [float(x) for x in df.get_column(value_col).to_list()]

        if len(historical_vals) < 6:
            raise ValueError("Time series dataset has insufficient historical observations (minimum 6 required for Holt-Winters).")

        # Fit Holt-Winters Exponential Smoothing model
        # Uses simple additive trend, optimized parameters
        try:
            model = ExponentialSmoothing(
                historical_vals, 
                trend='add', 
                seasonal=None, 
                initialization_method='estimated'
            )
            fit_model = model.fit()
            forecasts = fit_model.forecast(steps)
            
            # Estimate prediction intervals using standard errors approximations
            residuals_std = np.std(fit_model.resid)
            
            lower_bounds = []
            upper_bounds = []
            forecast_times = []
            
            # Simple chronological time stepper
            last_date = historical_times[-1]
            
            for i, val in enumerate(forecasts):
                # Standard error increments with steps (sqrt(i+1) expansion)
                margin = 1.96 * residuals_std * math.sqrt(i + 1)
                lower_bounds.append(max(0.0, float(val - margin)))
                upper_bounds.append(float(val + margin))
                
                # Approximate next time stepping index label
                forecast_times.append(f"F+{i+1} (Horizon)")
                
            model_details = f"Holt-Winters Exponential Smoothing Model (AIC={fit_model.aic:.2f})"
        except Exception as e:
            logger.error(f"Holt-Winters failed: {e}. Falling back to Linear Trend projection.")
            # Simple linear regression fallback if model fails to converge
            x = np.arange(len(historical_vals))
            slope, intercept, _, _, stderr = stats.linregress(x, historical_vals)
            if stderr is None or math.isnan(stderr):
                stderr = 0.0
            
            forecasts = []
            lower_bounds = []
            upper_bounds = []
            forecast_times = []
            
            for i in range(steps):
                step_idx = len(historical_vals) + i
                val = slope * step_idx + intercept
                margin = 1.96 * stderr * math.sqrt(step_idx)
                
                forecasts.append(float(val))
                lower_bounds.append(max(0.0, float(val - margin)))
                upper_bounds.append(float(val + margin))
                forecast_times.append(f"F+{i+1} (Horizon)")
                
            model_details = "Fallback Ordinary Least Squares (OLS) Linear Trend Model"

        return ForecastResult(
            timeline=historical_times,
            historical_values=historical_vals,
            forecast_timeline=forecast_times,
            forecast_values=[float(x) for x in forecasts],
            lower_confidence_bounds=lower_bounds,
            upper_confidence_bounds=upper_bounds,
            model_details=model_details
        )
