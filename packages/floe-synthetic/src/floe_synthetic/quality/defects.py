"""Data quality defect injection for synthetic data.

Provides configurable injection of data quality issues:
- Null values in specified columns
- Duplicate rows
- Late-arriving data (backdated timestamps)

Covers: 007-FR-027b (configurable data quality scenarios for dbt validation demos)
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field


class DefectConfig(BaseModel):
    """Configuration for data quality defect injection.

    Attributes:
        null_rate: Probability of injecting NULL (0.0 to 1.0)
        null_columns: Columns to inject NULLs into (empty = all nullable columns)
        duplicate_rate: Probability of duplicating a row (0.0 to 1.0)
        late_arrival_rate: Probability of backdating timestamp (0.0 to 1.0)
        late_arrival_min_hours: Minimum hours to backdate (default: 24)
        late_arrival_max_hours: Maximum hours to backdate (default: 168 = 7 days)
        timestamp_column: Column name for late arrival injection

    Example:
        >>> config = DefectConfig(
        ...     null_rate=0.05,
        ...     null_columns=["email"],
        ...     duplicate_rate=0.02,
        ...     late_arrival_rate=0.01,
        ...     timestamp_column="created_at",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    null_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Null injection rate")
    null_columns: list[str] = Field(default_factory=list, description="Columns for null injection")
    duplicate_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Duplicate row rate")
    late_arrival_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Late arrival rate")
    late_arrival_min_hours: int = Field(default=24, ge=1, description="Minimum backdate hours")
    late_arrival_max_hours: int = Field(default=168, ge=1, description="Maximum backdate hours")
    timestamp_column: str = Field(default="created_at", description="Timestamp column name")


class QualityDefectInjector:
    """Injects data quality defects into PyArrow tables.

    Thread-safe, deterministic injection using configurable seed and rates.
    Designed for generating realistic test data with known quality issues.

    Attributes:
        seed: Random seed for reproducibility
        config: DefectConfig with injection rates and settings

    Example:
        >>> config = DefectConfig(null_rate=0.05, null_columns=["email"])
        >>> injector = QualityDefectInjector(seed=42, config=config)
        >>> dirty_data = injector.apply(clean_data)
    """

    def __init__(self, seed: int = 42, config: DefectConfig | None = None) -> None:
        """Initialize the injector.

        Args:
            seed: Random seed for reproducible defect patterns
            config: DefectConfig with injection settings (default: no defects)
        """
        self.seed = seed
        self.config = config or DefectConfig()
        self._rng = random.Random(seed)  # noqa: S311 - not used for security

    def inject_nulls(self, table: pa.Table) -> pa.Table:
        """Inject NULL values into specified columns.

        Args:
            table: Input PyArrow table

        Returns:
            Table with NULLs injected at configured rate
        """
        # Use math.isclose for float comparison (S1244)
        if self.config.null_rate < 1e-9:
            return table

        # Reset RNG for reproducibility
        self._rng.seed(self.seed)

        target_columns = self.config.null_columns
        if not target_columns:
            # Default to all string columns if none specified
            target_columns = [
                field.name
                for field in table.schema
                if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
            ]

        # Convert to dict of columns for modification
        result_columns: dict[str, list[Any]] = {}
        for column_name in table.column_names:
            values = table.column(column_name).to_pylist()

            if column_name in target_columns:
                # Inject nulls at configured rate
                values = [None if self._rng.random() < self.config.null_rate else v for v in values]

            result_columns[column_name] = values

        # Rebuild table with same schema
        return self._rebuild_table(table.schema, result_columns)

    def inject_duplicates(self, table: pa.Table) -> pa.Table:
        """Inject duplicate rows into the table.

        Args:
            table: Input PyArrow table

        Returns:
            Table with duplicate rows added
        """
        # Use threshold comparison for float (S1244)
        if self.config.duplicate_rate < 1e-9:
            return table

        # Reset RNG for reproducibility
        self._rng.seed(self.seed + 1)  # Different seed for duplicates

        # Get all rows as list of dicts
        rows: list[dict[str, Any]] = []
        for i in range(table.num_rows):
            row = {col: table.column(col)[i].as_py() for col in table.column_names}
            rows.append(row)

            # Possibly add duplicate
            if self._rng.random() < self.config.duplicate_rate:
                rows.append(row.copy())

        # Convert back to column format
        result_columns: dict[str, list[Any]] = {col: [] for col in table.column_names}
        for row in rows:
            for col, value in row.items():
                result_columns[col].append(value)

        return self._rebuild_table(table.schema, result_columns)

    def inject_late_arrivals(self, table: pa.Table) -> pa.Table:
        """Inject late-arriving data by backdating timestamps.

        Args:
            table: Input PyArrow table

        Returns:
            Table with some timestamps backdated
        """
        # Use threshold comparison for float (S1244)
        if self.config.late_arrival_rate < 1e-9:
            return table

        timestamp_col = self.config.timestamp_column
        if timestamp_col not in table.column_names:
            return table

        # Reset RNG for reproducibility
        self._rng.seed(self.seed + 2)  # Different seed for late arrivals

        # Convert to dict of columns for modification
        result_columns: dict[str, list[Any]] = {}
        for column_name in table.column_names:
            values = table.column(column_name).to_pylist()

            if column_name == timestamp_col:
                # Backdate some timestamps
                new_values: list[datetime | None] = []
                for v in values:
                    if v is not None and self._rng.random() < self.config.late_arrival_rate:
                        # Backdate by random hours within configured range
                        delay_hours = self._rng.randint(
                            self.config.late_arrival_min_hours,
                            self.config.late_arrival_max_hours,
                        )
                        backdated = v - timedelta(hours=delay_hours)
                        new_values.append(backdated)
                    else:
                        new_values.append(v)
                values = new_values

            result_columns[column_name] = values

        return self._rebuild_table(table.schema, result_columns)

    def apply(self, table: pa.Table) -> pa.Table:
        """Apply all configured defects to the table.

        Applies defects in order:
        1. Null injection
        2. Duplicate injection
        3. Late arrival injection

        Args:
            table: Input PyArrow table

        Returns:
            Table with all configured defects applied
        """
        result = table
        result = self.inject_nulls(result)
        result = self.inject_duplicates(result)
        result = self.inject_late_arrivals(result)
        return result

    def _rebuild_table(
        self,
        schema: pa.Schema,
        columns: dict[str, list[Any]],
    ) -> pa.Table:
        """Rebuild a PyArrow table from column data with original schema.

        Args:
            schema: Original table schema
            columns: Dict of column name to list of values

        Returns:
            Reconstructed PyArrow table
        """
        arrays: dict[str, pa.Array] = {}
        for field in schema:
            values = columns[field.name]
            # Create array with proper type from schema
            arrays[field.name] = pa.array(values, type=field.type)

        return pa.table(arrays)
