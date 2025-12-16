"""Profile generators for dbt targets.

T010: Create profiles subpackage __init__.py

This package provides profile generators for all 7 supported compute targets.
Each generator implements the ProfileGenerator protocol from base.py.

Supported Targets:
    - DuckDB: Local/embedded analytics
    - Snowflake: Cloud data warehouse
    - BigQuery: Google Cloud data warehouse
    - Redshift: AWS data warehouse
    - Databricks: Unified analytics with Unity Catalog
    - PostgreSQL: Open-source RDBMS
    - Spark: Distributed compute engine

Example:
    >>> from floe_dbt.profiles import ProfileFactory, ProfileGeneratorConfig
    >>> config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
    >>> generator = ProfileFactory.create("snowflake")
    >>> profile = generator.generate(artifacts, config)
"""

from __future__ import annotations

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from floe_dbt.profiles.bigquery import BigQueryProfileGenerator
from floe_dbt.profiles.databricks import DatabricksProfileGenerator
from floe_dbt.profiles.duckdb import DuckDBProfileGenerator
from floe_dbt.profiles.postgres import PostgreSQLProfileGenerator
from floe_dbt.profiles.redshift import RedshiftProfileGenerator
from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator
from floe_dbt.profiles.spark import SparkProfileGenerator

__all__ = [
    "ProfileGenerator",
    "ProfileGeneratorConfig",
    "BigQueryProfileGenerator",
    "DatabricksProfileGenerator",
    "DuckDBProfileGenerator",
    "PostgreSQLProfileGenerator",
    "RedshiftProfileGenerator",
    "SnowflakeProfileGenerator",
    "SparkProfileGenerator",
]
