"""Profile factory for creating target-specific generators.

T032: [US2] Implement ProfileFactory with target registry
"""

from __future__ import annotations

from collections.abc import Callable

from floe_dbt.profiles.base import ProfileGenerator
from floe_dbt.profiles.bigquery import BigQueryProfileGenerator
from floe_dbt.profiles.databricks import DatabricksProfileGenerator
from floe_dbt.profiles.duckdb import DuckDBProfileGenerator
from floe_dbt.profiles.postgres import PostgreSQLProfileGenerator
from floe_dbt.profiles.redshift import RedshiftProfileGenerator
from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator
from floe_dbt.profiles.spark import SparkProfileGenerator


class ProfileFactory:
    """Factory for creating target-specific profile generators.

    Provides a registry of all 7 supported compute targets and creates
    the appropriate generator instance for each target.

    Supported Targets (FR-002):
        - duckdb: DuckDB embedded analytics
        - snowflake: Snowflake cloud data warehouse
        - bigquery: Google BigQuery
        - redshift: Amazon Redshift
        - databricks: Databricks with Unity Catalog
        - postgres: PostgreSQL
        - spark: Apache Spark

    Example:
        >>> generator = ProfileFactory.create("snowflake")
        >>> profile = generator.generate(artifacts, config)
    """

    # Registry mapping target names to generator classes
    _GENERATORS: dict[str, Callable[[], ProfileGenerator]] = {
        "duckdb": DuckDBProfileGenerator,
        "snowflake": SnowflakeProfileGenerator,
        "bigquery": BigQueryProfileGenerator,
        "redshift": RedshiftProfileGenerator,
        "databricks": DatabricksProfileGenerator,
        "postgres": PostgreSQLProfileGenerator,
        "spark": SparkProfileGenerator,
    }

    @classmethod
    def create(cls, target: str) -> ProfileGenerator:
        """Create a profile generator for the specified target.

        Args:
            target: Compute target name (e.g., "snowflake", "duckdb").

        Returns:
            ProfileGenerator instance for the specified target.

        Raises:
            ValueError: If target is not supported.
        """
        # Normalize to lowercase for consistency
        target_lower = target.lower()

        if target_lower not in cls._GENERATORS:
            supported = ", ".join(sorted(cls._GENERATORS.keys()))
            raise ValueError(
                f"Unsupported compute target: '{target}'. Supported targets: {supported}"
            )

        generator_class = cls._GENERATORS[target_lower]
        return generator_class()

    @classmethod
    def supported_targets(cls) -> list[str]:
        """Get list of supported compute targets.

        Returns:
            List of supported target names.
        """
        return sorted(cls._GENERATORS.keys())

    @classmethod
    def is_supported(cls, target: str) -> bool:
        """Check if a target is supported.

        Args:
            target: Target name to check.

        Returns:
            True if target is supported, False otherwise.
        """
        return target.lower() in cls._GENERATORS
