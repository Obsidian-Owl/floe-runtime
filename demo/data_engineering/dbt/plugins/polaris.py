"""dbt-duckdb plugin for Polaris REST Catalog + Apache Iceberg.

This plugin enables dbt-duckdb to write external materializations directly to
Iceberg tables via the Polaris REST catalog, implementing proper medallion
architecture for floe-runtime.

Architecture:
    dbt-duckdb (DuckDB SQL) → Parquet file → Plugin → PyIceberg → Polaris → S3

Usage in profiles.yml:
    outputs:
      dev:
        type: duckdb
        path: ':memory:'
        plugins:
          - module: 'demo.dbt.plugins.polaris'
            config:
              catalog_uri: 'http://floe-infra-polaris:8181/api/catalog/v1'
              warehouse: 'demo_catalog'
              s3_endpoint: 'http://floe-infra-localstack:4566'
              s3_region: 'us-east-1'
              s3_access_key_id: 'test'
              s3_secret_access_key: 'test'

Usage in models:
    {{ config(
        materialized='external',
        location='s3://temp-dbt/{{ this.schema }}/{{ this.name }}',
        format='parquet',
        polaris_namespace='demo.{{ this.schema }}',
        polaris_table='{{ this.name }}'
    ) }}
    SELECT * FROM ...
"""

from typing import Any

try:
    from dbt.adapters.duckdb.plugins import BasePlugin
    from dbt.adapters.duckdb.utils import TargetConfig
except ImportError as e:
    raise ImportError(
        "dbt-duckdb is required for Polaris plugin. Install with: pip install dbt-duckdb"
    ) from e

try:
    import pyarrow.parquet as pq
    from pyiceberg.catalog import Catalog, load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType,
        DateType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )
except ImportError as e:
    raise ImportError(
        "PyIceberg and PyArrow are required for Polaris plugin. "
        "Install with: pip install 'pyiceberg[s3]' pyarrow"
    ) from e


class Plugin(BasePlugin):
    """dbt-duckdb plugin for writing to Iceberg tables via Polaris catalog."""

    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize Polaris catalog connection.

        Args:
            config: Plugin configuration from profiles.yml with keys:
                - catalog_uri: Polaris REST endpoint
                - warehouse: Catalog warehouse name
                - s3_endpoint: S3-compatible endpoint (LocalStack)
                - s3_region: S3 region
                - s3_access_key_id: S3 access key
                - s3_secret_access_key: S3 secret key
        """
        self.config = config

        # Build catalog configuration for PyIceberg
        catalog_config = {
            "uri": config["catalog_uri"],
            "warehouse": config["warehouse"],
            "s3.endpoint": config.get("s3_endpoint"),
            "s3.region": config.get("s3_region", "us-east-1"),
            "s3.access-key-id": config.get("s3_access_key_id"),
            "s3.secret-access-key": config.get("s3_secret_access_key"),
            "s3.path-style-access": "true",
        }

        # Load Polaris catalog via PyIceberg
        self.catalog: Catalog = load_catalog("polaris", **catalog_config)

    def store(self, target_config: TargetConfig) -> None:
        """Write dbt transformation output to Iceberg table via Polaris.

        Args:
            target_config: dbt-duckdb target configuration containing:
                - location: Path to parquet file dbt created
                - config: Model config with polaris_namespace and polaris_table
                - column_list: List of columns and types
        """
        # Get configuration from dbt model
        namespace = target_config.config.get("polaris_namespace")
        table_name = target_config.config.get("polaris_table")

        if not namespace or not table_name:
            raise ValueError(
                "polaris_namespace and polaris_table must be specified in model config"
            )

        full_table_id = f"{namespace}.{table_name}"

        # Read parquet file that dbt created
        parquet_path = target_config.location.path
        table_data = pq.read_table(parquet_path)

        # Convert dbt column types to Iceberg schema
        iceberg_fields = []
        for idx, col in enumerate(target_config.column_list):
            field_id = idx + 1
            field_name = col.name
            field_type = self._map_dbt_type_to_iceberg(col.data_type)
            iceberg_fields.append(
                NestedField(
                    field_id=field_id,
                    name=field_name,
                    field_type=field_type,
                    required=False,
                )
            )

        iceberg_schema = Schema(*iceberg_fields)

        # Create or replace Iceberg table
        try:
            # Check if table exists
            existing_table = self.catalog.load_table(full_table_id)
            # Table exists - append/overwrite based on config
            existing_table.overwrite(table_data)
        except Exception:
            # Table doesn't exist - create it
            # Determine S3 location based on schema (silver/gold)
            schema = namespace.split(".")[-1]  # Extract "silver" or "gold"
            if schema == "silver":
                bucket = "iceberg-silver"
            elif schema == "gold":
                bucket = "iceberg-gold"
            else:
                bucket = "iceberg-data"  # fallback

            location = f"s3://{bucket}/{namespace.replace('.', '/')}/{table_name}"

            self.catalog.create_table(
                identifier=full_table_id,
                schema=iceberg_schema,
                location=location,
            )

            # Append data to newly created table
            table = self.catalog.load_table(full_table_id)
            table.append(table_data)

    def _map_dbt_type_to_iceberg(self, dbt_type: str) -> Any:
        """Map dbt/DuckDB data types to Iceberg types.

        Args:
            dbt_type: dbt column data type (e.g., "INTEGER", "VARCHAR")

        Returns:
            Corresponding Iceberg type
        """
        dbt_type_upper = dbt_type.upper()

        # Integer types
        if dbt_type_upper in ("TINYINT", "SMALLINT", "INTEGER", "INT"):
            return IntegerType()
        if dbt_type_upper in ("BIGINT",):
            return LongType()

        # Floating point types
        if dbt_type_upper in ("REAL", "FLOAT"):
            return FloatType()
        if dbt_type_upper in ("DOUBLE", "DECIMAL", "NUMERIC"):
            return DoubleType()

        # String types
        if dbt_type_upper in ("VARCHAR", "CHAR", "TEXT", "STRING"):
            return StringType()

        # Boolean
        if dbt_type_upper in ("BOOLEAN", "BOOL"):
            return BooleanType()

        # Date/Time types
        if dbt_type_upper in ("DATE",):
            return DateType()
        if dbt_type_upper in ("TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ"):
            return TimestampType()

        # Default to string for unknown types
        return StringType()
