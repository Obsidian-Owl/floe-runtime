"""Unit tests for ComputeTarget enum.

T010: [US1] Unit tests for ComputeTarget enum
Tests the 7 compute target enum values per data-model.md.
"""

from __future__ import annotations

import pytest


class TestComputeTarget:
    """Tests for ComputeTarget enum values."""

    def test_compute_target_has_seven_values(self) -> None:
        """ComputeTarget should have exactly 7 target values."""
        from floe_core.schemas import ComputeTarget

        assert len(ComputeTarget) == 7

    def test_compute_target_duckdb_exists(self) -> None:
        """ComputeTarget should have duckdb value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.duckdb.value == "duckdb"

    def test_compute_target_snowflake_exists(self) -> None:
        """ComputeTarget should have snowflake value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.snowflake.value == "snowflake"

    def test_compute_target_bigquery_exists(self) -> None:
        """ComputeTarget should have bigquery value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.bigquery.value == "bigquery"

    def test_compute_target_redshift_exists(self) -> None:
        """ComputeTarget should have redshift value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.redshift.value == "redshift"

    def test_compute_target_databricks_exists(self) -> None:
        """ComputeTarget should have databricks value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.databricks.value == "databricks"

    def test_compute_target_postgres_exists(self) -> None:
        """ComputeTarget should have postgres value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.postgres.value == "postgres"

    def test_compute_target_spark_exists(self) -> None:
        """ComputeTarget should have spark value."""
        from floe_core.schemas import ComputeTarget

        assert ComputeTarget.spark.value == "spark"

    def test_compute_target_values_match_dbt_adapters(self) -> None:
        """ComputeTarget values should match dbt adapter names."""
        from floe_core.schemas import ComputeTarget

        expected_values = {
            "duckdb",
            "snowflake",
            "bigquery",
            "redshift",
            "databricks",
            "postgres",
            "spark",
        }
        actual_values = {target.value for target in ComputeTarget}
        assert actual_values == expected_values

    def test_compute_target_from_string(self) -> None:
        """ComputeTarget should be constructible from string value."""
        from floe_core.schemas import ComputeTarget

        target = ComputeTarget("snowflake")
        assert target == ComputeTarget.snowflake

    def test_compute_target_invalid_value_raises(self) -> None:
        """ComputeTarget should reject invalid values."""
        from floe_core.schemas import ComputeTarget

        with pytest.raises(ValueError):
            ComputeTarget("invalid_target")
