import math
import os
from typing import Dict, List, Tuple, Any
import polars as pl
from loguru import logger

from app.domain.dataset.entities import (
    DataType, ColumnMetadata, TableSchema, 
    DataQualityReport, DataQualityIssue, DatasetFormat
)


class PolarsProcessor:
    """Uses Polars to lazily profile and clean datasets.

    Runs fully deterministic calculations without invoking LLMs.
    """

    @staticmethod
    def _map_type(dtype: pl.DataType) -> DataType:
        """Map Polars datatypes to AURA Domain DataTypes."""
        if dtype.is_integer():
            return DataType.INTEGER
        elif dtype.is_float():
            return DataType.FLOAT
        elif dtype in (pl.Utf8, pl.Categorical):
            return DataType.STRING
        elif dtype == pl.Boolean:
            return DataType.BOOLEAN
        elif dtype in (pl.Date, pl.Datetime, pl.Time):
            return DataType.DATETIME
        else:
            return DataType.UNKNOWN

    def load_lazy_frame(self, file_path: str, file_format: DatasetFormat) -> pl.LazyFrame:
        """Load a file into a Polars LazyFrame for low-memory evaluation."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_format == DatasetFormat.CSV:
            return pl.scan_csv(file_path, ignore_errors=True)
        elif file_format == DatasetFormat.PARQUET:
            return pl.scan_parquet(file_path)
        elif file_format == DatasetFormat.EXCEL:
            # Excel does not support lazy scanning directly in Polars, read and convert
            df = pl.read_excel(file_path)
            return df.lazy()
        elif file_format == DatasetFormat.JSON:
            df = pl.read_json(file_path)
            return df.lazy()
        else:
            raise ValueError(f"Unsupported file format for Polars scanner: {file_format}")

    def profile_dataset(self, file_path: str, file_format: DatasetFormat) -> Tuple[TableSchema, DataQualityReport]:
        """Perform deterministic schema profiling and data quality assessment using Polars."""
        logger.info(f"Profiling dataset: {file_path} (Format: {file_format})")
        
        lf = self.load_lazy_frame(file_path, file_format)
        
        # Resolve dimensions
        df_schema = lf.collect_schema()
        row_count = lf.select(pl.len()).collect().item()
        column_count = len(df_schema)
        file_size_bytes = os.path.getsize(file_path)
        
        # Prepare evaluation lists for faster parallel metrics collection
        select_exprs = []
        for col_name, dtype in df_schema.items():
            mapped_type = self._map_type(dtype)
            
            # Basic stats
            select_exprs.append(pl.col(col_name).null_count().alias(f"{col_name}__null_count"))
            select_exprs.append(pl.col(col_name).n_unique().alias(f"{col_name}__distinct"))
            
            if mapped_type in (DataType.INTEGER, DataType.FLOAT):
                select_exprs.append(pl.col(col_name).min().cast(pl.Float64).alias(f"{col_name}__min"))
                select_exprs.append(pl.col(col_name).max().cast(pl.Float64).alias(f"{col_name}__max"))
                select_exprs.append(pl.col(col_name).mean().alias(f"{col_name}__mean"))
                select_exprs.append(pl.col(col_name).std().alias(f"{col_name}__std"))
            else:
                select_exprs.append(pl.lit(None).alias(f"{col_name}__min"))
                select_exprs.append(pl.lit(None).alias(f"{col_name}__max"))
                select_exprs.append(pl.lit(None).alias(f"{col_name}__mean"))
                select_exprs.append(pl.lit(None).alias(f"{col_name}__std"))

        # Run single unified collect for basic statistics
        stats_df = lf.select(select_exprs).collect()
        
        columns_meta = []
        issues = []
        null_penalties = 0.0
        
        for col_name, dtype in df_schema.items():
            mapped_type = self._map_type(dtype)
            
            null_count = stats_df.get_column(f"{col_name}__null_count")[0]
            distinct_count = stats_df.get_column(f"{col_name}__distinct")[0]
            
            null_pct = (null_count / row_count) * 100 if row_count > 0 else 0.0
            is_unique = (distinct_count == row_count) and (null_count == 0)
            
            # Penalize health score based on nulls
            null_penalties += null_pct
            
            if null_pct > 10.0:
                issues.append(DataQualityIssue(
                    column=col_name,
                    issue_type="missing_values",
                    severity="high" if null_pct > 30.0 else "medium",
                    description=f"Column '{col_name}' has {null_pct:.2f}% missing values.",
                    impacted_rows_count=null_count,
                    recommendation=f"Impute missing values using mean/median or drop rows with missing values."
                ))
            
            # Fetch numeric properties
            min_val = stats_df.get_column(f"{col_name}__min")[0]
            max_val = stats_df.get_column(f"{col_name}__max")[0]
            mean_val = stats_df.get_column(f"{col_name}__mean")[0]
            std_val = stats_df.get_column(f"{col_name}__std")[0]

            # Format min/max as readable strings
            min_str = str(min_val) if min_val is not None and not math.isnan(min_val) else None
            max_str = str(max_val) if max_val is not None and not math.isnan(max_val) else None
            
            # Extract top frequent categories for categorical columns
            most_frequent = []
            if mapped_type in (DataType.STRING, DataType.BOOLEAN) and row_count > 0:
                freq_df = lf.select(col_name).filter(pl.col(col_name).is_not_null())\
                    .group_by(col_name).len().sort("len", descending=True).limit(5).collect()
                
                for r in freq_df.iter_rows():
                    most_frequent.append({"value": str(r[0]), "count": r[1]})

            columns_meta.append(ColumnMetadata(
                name=col_name,
                data_type=mapped_type,
                null_count=null_count,
                null_percentage=null_pct,
                distinct_count=distinct_count,
                is_unique=is_unique,
                min_value=min_str,
                max_value=max_str,
                mean=mean_val if mean_val is not None and not math.isnan(mean_val) else None,
                std_dev=std_val if std_val is not None and not math.isnan(std_val) else None,
                most_frequent_values=most_frequent
            ))
            
        # Calculate duplicate rows
        # We drop null columns before checking row duplicates to prevent null-row duplication biases
        non_null_cols = [c for c in df_schema.keys()]
        duplicate_count = 0
        if len(non_null_cols) > 0 and row_count > 0:
            total_unique_rows = lf.select(non_null_cols).unique().select(pl.len()).collect().item()
            duplicate_count = max(0, row_count - total_unique_rows)
            
        if duplicate_count > 0:
            dup_pct = (duplicate_count / row_count) * 100
            issues.append(DataQualityIssue(
                column=None,
                issue_type="duplicate_rows",
                severity="medium" if dup_pct < 10.0 else "high",
                description=f"Dataset contains {duplicate_count} ({dup_pct:.2f}%) duplicate rows.",
                impacted_rows_count=duplicate_count,
                recommendation="De-duplicate the dataset by removing identical duplicate rows."
            ))

        # Calculate final Health Score (0 - 100)
        # Starts at 100, penalize for missing values and duplicate rows.
        base_penalty = (null_penalties / column_count) if column_count > 0 else 0
        dup_penalty = (duplicate_count / row_count) * 50 if row_count > 0 else 0
        health_score = max(0.0, min(100.0, 100.0 - base_penalty - dup_penalty))

        quality_report = DataQualityReport(
            health_score=round(health_score, 2),
            issues=issues,
            duplicate_rows_count=duplicate_count,
            total_rows=row_count
        )
        
        table_schema = TableSchema(
            columns=columns_meta,
            row_count=row_count,
            column_count=column_count,
            file_size_bytes=file_size_bytes
        )
        
        return table_schema, quality_report

    def detect_primary_keys(self, schema: TableSchema) -> List[str]:
        """Detect candidate primary keys from table columns."""
        candidates = []
        for col in schema.columns:
            if col.is_unique and col.null_count == 0:
                candidates.append(col.name)
        return candidates


polars_processor = PolarsProcessor()
