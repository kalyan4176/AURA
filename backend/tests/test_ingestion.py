import os
import tempfile
import pytest
import polars as pl

from app.infrastructure.engine.polars_processor import polars_processor
from app.domain.dataset.entities import DatasetFormat, DataType


@pytest.fixture
def sample_csv_file():
    """Generates a temporary CSV dataset with duplicates and null values."""
    data = {
        "id": [1, 2, 3, 4, 4],  # duplicate record on 4
        "name": ["Alice", "Bob", None, "Dave", "Dave"],  # null count = 1
        "age": [25, 30, 35, 40, 40],
        "is_active": [True, False, True, None, None]  # null count = 2
    }
    df = pl.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        df.write_csv(tmp.name)
        file_path = tmp.name
        
    yield file_path
    
    # Cleanup after test
    if os.path.exists(file_path):
        os.remove(file_path)


def test_polars_dataset_profiling(sample_csv_file):
    schema, quality_report = polars_processor.profile_dataset(sample_csv_file, DatasetFormat.CSV)

    # 1. Assert dimensions
    assert schema.row_count == 5
    assert schema.column_count == 4
    
    # 2. Assert column type mappings
    cols_by_name = {col.name: col for col in schema.columns}
    assert cols_by_name["id"].data_type == DataType.INTEGER
    assert cols_by_name["name"].data_type == DataType.STRING
    assert cols_by_name["is_active"].data_type == DataType.BOOLEAN

    # 3. Assert null detection
    assert cols_by_name["name"].null_count == 1
    assert cols_by_name["is_active"].null_count == 2
    assert cols_by_name["id"].null_count == 0

    # 4. Assert duplicates detection
    # Duplicate row: [4, "Dave", 40, None] appears twice
    assert quality_report.duplicate_rows_count == 1

    # 5. Assert health score is penalized (starts at 100, drops due to nulls and duplicates)
    assert quality_report.health_score < 100.0
    assert len(quality_report.issues) >= 2  # missing values + duplicate rows
