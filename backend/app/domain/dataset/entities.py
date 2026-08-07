from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DatasetFormat(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"
    EXCEL = "excel"
    JSON = "json"


class DataType(str, Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"
    UNKNOWN = "unknown"


class ColumnMetadata(BaseModel):
    name: str
    data_type: DataType
    null_count: int
    null_percentage: float
    distinct_count: int
    is_unique: bool
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    most_frequent_values: List[Dict[str, Any]] = Field(default_factory=list)


class TableSchema(BaseModel):
    columns: List[ColumnMetadata] = Field(default_factory=list)
    row_count: int
    column_count: int
    file_size_bytes: int


class Relationship(BaseModel):
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    confidence: float  # Value between 0.0 and 1.0 based on uniqueness and overlap
    relationship_type: str = "one_to_many"  # one_to_one, one_to_many, many_to_many


class DataQualityIssue(BaseModel):
    column: Optional[str] = None
    issue_type: str  # e.g., missing_values, duplicate_rows, invalid_type, outlier
    severity: str  # e.g., high, medium, low
    description: str
    impacted_rows_count: int
    recommendation: str


class DataQualityReport(BaseModel):
    health_score: float  # Health score between 0.0 and 100.0
    issues: List[DataQualityIssue] = Field(default_factory=list)
    duplicate_rows_count: int
    total_rows: int


class Dataset(BaseModel):
    id: Optional[UUID] = None
    workspace_id: UUID
    name: str
    filename: str
    file_format: DatasetFormat
    file_path: str
    schema_definition: Optional[TableSchema] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Workspace(BaseModel):
    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
