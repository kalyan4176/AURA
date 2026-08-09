import math
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import polars as pl
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
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
        
        # Load dataset and fill nulls natively in Polars with column mean (or 0.0 if entirely null)
        df = pl.scan_parquet(file_path).select(columns).collect()
        
        # Ensure selected columns are numeric to prevent ML fitting crashes
        for col in columns:
            dtype = df.get_column(col).dtype
            if not dtype.is_numeric():
                raise ValueError(f"Column '{col}' is of non-numeric type ({dtype}). Outlier models require numeric input.")
        
        filled_cols = []
        for col in columns:
            col_series = df.get_column(col)
            mean_val = col_series.mean()
            if mean_val is None or math.isnan(mean_val):
                mean_val = 0.0
            filled_cols.append(col_series.fill_null(mean_val))
            
        df = pl.DataFrame(filled_cols)
        X = df.to_numpy()
        
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
        elif algorithm == "one_class_svm":
            model = OneClassSVM(nu=contamination, kernel="rbf", gamma="scale")
            preds = model.fit_predict(X)
            scores = model.score_samples(X)
            min_s, max_s = np.min(scores), np.max(scores)
            span = (max_s - min_s) if max_s != min_s else 1.0
            confidence = [float(1.0 - (s - min_s) / span) for s in scores]
        else:
            raise ValueError(f"Unsupported anomaly algorithm: {algorithm}")

        # -1 indicates outlier/anomaly
        anomaly_indices = np.where(preds == -1)[0].tolist()
        total_anomalies = len(anomaly_indices)
        pct = (total_anomalies / len(X)) * 100

        # Select first two columns for plotting
        plot_col_x = columns[0]
        plot_col_y = columns[1] if len(columns) > 1 else columns[0]
        
        plot_data = []
        step = max(1, len(df) // 1000)
        for i in range(0, len(df), step):
            if len(plot_data) >= 1000:
                break
            val_x = float(df.get_column(plot_col_x)[i]) if df.get_column(plot_col_x)[i] is not None else 0.0
            val_y = float(df.get_column(plot_col_y)[i]) if df.get_column(plot_col_y)[i] is not None else 0.0
            is_anomaly = bool(preds[i] == -1)
            plot_data.append({
                "x": val_x,
                "y": val_y,
                "is_anomaly": is_anomaly,
                "row_index": i
            })

        avg_conf = 0.0
        if total_anomalies > 0:
            avg_conf = float(np.mean([confidence[i] for i in anomaly_indices]))
            
        base_summary = f"Detected {total_anomalies} anomalies ({pct:.2f}% of data) using {algorithm.upper()}."
        if total_anomalies > 0:
            base_summary += f" Average confidence index for flagged outliers is {avg_conf:.2f}."

        summary = base_summary
        
        # Call Gemini to generate a professional, evidence-backed narrative summary
        try:
            import asyncio
            import threading
            from app.application.budget.services import ai_budget_manager
            
            evidence_prompt = (
                f"Explain the business implications of finding {total_anomalies} anomalies ({pct:.2f}% of data) "
                f"using the ML algorithm '{algorithm.upper()}' on columns: {columns}. "
                f"Confidence scores for these anomalies average {avg_conf:.2f}. "
                f"Provide a concise, professional evidence-based explanation of these findings, "
                f"highlighting potential data quality risks and corporate decision recommendations."
            )
            
            result_container = {}
            def worker():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    res = loop.run_until_complete(
                        ai_budget_manager.execute_query(
                            dataset_path=file_path,
                            user_query=evidence_prompt
                        )
                    )
                    result_container["response"] = res
                except Exception as ex:
                    result_container["error"] = ex
                finally:
                    loop.close()

            t = threading.Thread(target=worker)
            t.start()
            t.join()

            if "error" in result_container:
                raise result_container["error"]

            response = result_container.get("response", {})
            ai_resp = response.get("response", "")
            if ai_resp and "unable to generate" not in ai_resp.lower() and "budget_blocker" not in response.get("source", ""):
                # Combine the structural metric with the AI explanation
                summary = f"{base_summary}\n\n{ai_resp}"
        except Exception as e:
            logger.warning(f"Failed generating AI summary for anomalies: {e}")

        return AnomalyReport(
            total_anomalies=total_anomalies,
            anomaly_percentage=pct,
            anomaly_indices=anomaly_indices,
            confidence_scores=[confidence[i] for i in anomaly_indices],
            summary=summary,
            plot_data=plot_data
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
