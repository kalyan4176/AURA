import duckdb
from typing import Any, Dict, List
from loguru import logger
import polars as pl


class DuckDBClient:
    """Manages thread-safe in-memory DuckDB connections.

    Queries parquet/csv files directly without locking write instances.
    """

    def __init__(self):
        # We use in-memory connections to allow concurrency.
        # Data is stored as Parquet files on disk/object-storage.
        # DuckDB queries them dynamically.
        self.conn = duckdb.connect(database=":memory:")
        logger.info("Initialized thread-safe in-memory DuckDB connection pool.")

    def query(self, sql_query: str, parameters: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SQL query against the in-memory engine and return records as list of dicts.

        Useful for general DB querying and analytical aggregations.
        """
        try:
            cursor = self.conn.cursor()
            if parameters:
                cursor.execute(sql_query, parameters)
            else:
                cursor.execute(sql_query)
            
            # Fetch results as dictionary
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"DuckDB SQL Execution failed: {sql_query}. Error: {e}")
            raise ValueError(f"Analytical query execution failed: {e}") from e

    def query_as_polars(self, sql_query: str, parameters: tuple = None) -> pl.DataFrame:
        """Execute SQL query and return results directly as a Polars DataFrame.

        Allows zero-copy analytical pipeline operations.
        """
        try:
            cursor = self.conn.cursor()
            if parameters:
                cursor.execute(sql_query, parameters)
            else:
                cursor.execute(sql_query)
            return cursor.pl()
        except Exception as e:
            logger.error(f"DuckDB Polars conversion query failed: {sql_query}. Error: {e}")
            raise ValueError(f"Analytical data conversion query failed: {e}") from e
            
    def get_preview(self, file_path: str, format: str, limit: int = 100) -> pl.DataFrame:
        """Fetch a preview of any dataset file directly from disk using DuckDB."""
        if format.lower() == "parquet":
            query = f"SELECT * FROM read_parquet(?) LIMIT {limit}"
        elif format.lower() == "csv":
            query = f"SELECT * FROM read_csv_auto(?, HEADER=True) LIMIT {limit}"
        elif format.lower() == "json":
            query = f"SELECT * FROM read_json_auto(?) LIMIT {limit}"
        else:
            raise ValueError(f"Unsupported format for DuckDB preview: {format}")
        
        return self.query_as_polars(query, (file_path,))


duckdb_client = DuckDBClient()
