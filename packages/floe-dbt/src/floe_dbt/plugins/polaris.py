"""Platform dbt-duckdb plugin for Polaris REST Catalog + Apache Iceberg.

This is the PLATFORM-PROVIDED plugin that replaces demo-specific custom plugins.
It leverages floe-polaris abstractions and reads configuration from environment
variables set by platform.yaml.

Architecture (Two-Tier):
    platform.yaml → DbtProfilesGenerator → profiles.yml (generated)
                 → env vars (K8s secrets) → THIS PLUGIN → floe-polaris → PolarisCatalog

Key Differences from Demo Custom Plugin:
    - ✅ Uses environment variables (not static config)
    - ✅ Leverages floe-polaris PolarisCatalog (not direct PyIceberg)
    - ✅ Proper OAuth2 handling (via PolarisCatalogConfig)
    - ✅ Part of platform (batteries-included for all users)

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

import os
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

try:
    from floe_polaris.client import PolarisCatalog
    from floe_polaris.config import PolarisCatalogConfig
except ImportError as e:
    raise ImportError(
        "floe-polaris is required for platform Polaris plugin. "
        "Install with: pip install floe-polaris"
    ) from e


class Plugin(BasePlugin):
    """Platform dbt-duckdb plugin for Polaris/Iceberg materializations.

    This plugin is platform-managed and reads configuration from environment
    variables set by the platform's Two-Tier Architecture.

    Environment Variables (Set by platform.yaml → K8s secrets):
        - POLARIS_CLIENT_ID: OAuth2 client ID
        - POLARIS_CLIENT_SECRET: OAuth2 client secret
        - AWS_ACCESS_KEY_ID: S3 access key
        - AWS_SECRET_ACCESS_KEY: S3 secret key

    Configuration (from generated profiles.yml):
        - catalog_uri: Polaris REST endpoint
        - warehouse: Catalog warehouse name
        - s3_endpoint: S3-compatible endpoint
        - s3_region: S3 region
        - scope: OAuth2 scope (default: PRINCIPAL_ROLE:ALL)
    """

    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize Polaris catalog connection.

        Args:
            config: Plugin configuration from generated profiles.yml.
                   Values use {{ env_var('VAR') }} interpolation.
                   Includes storage_mapping from platform.yaml.
        """
        self.config = config

        catalog_uri = config["catalog_uri"]
        warehouse = config["warehouse"]

        client_id = config.get("client_id") or os.getenv("POLARIS_CLIENT_ID")
        client_secret = config.get("client_secret") or os.getenv("POLARIS_CLIENT_SECRET")
        scope = config.get("scope", "PRINCIPAL_ROLE:ALL")

        s3_endpoint = config.get("s3_endpoint")
        s3_region = config.get("s3_region", "us-east-1")
        s3_access_key = config.get("s3_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID")
        s3_secret_key = config.get("s3_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY")

        catalog_config = PolarisCatalogConfig(
            uri=catalog_uri,
            warehouse=warehouse,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            s3_endpoint=s3_endpoint,
            s3_region=s3_region,
            s3_access_key_id=s3_access_key,
            s3_secret_access_key=s3_secret_key,
            s3_path_style_access=True,
        )

        self.catalog = PolarisCatalog(catalog_config)

        self.storage_mapping = config.get("storage_mapping", {})

    def configure_connection(self, conn: Any) -> None:
        """Attach Polaris Iceberg catalog to DuckDB connection.

        This method is called by dbt-duckdb to configure the DuckDB connection
        before running queries. We use it to ATTACH the Polaris catalog so that
        DuckDB SQL can reference Iceberg tables.

        Args:
            conn: DuckDB connection object.
        """
        self._validate_catalog_control_plane()

        catalog_uri = self.config["catalog_uri"]
        warehouse = self.config["warehouse"]

        # Get credentials from config or environment
        client_id = self.config.get("client_id") or os.getenv("POLARIS_CLIENT_ID", "")
        client_secret = self.config.get("client_secret") or os.getenv("POLARIS_CLIENT_SECRET", "")

        try:
            # Create Polaris Iceberg secret with OAuth2 credentials
            # DuckDB Iceberg extension requires UPPERCASE parameter names in secret
            # NOTE: We do NOT create an S3 secret here because DuckDB's secret manager
            # locks after the first CREATE SECRET, preventing additional secrets.
            # Instead, S3 credentials are provided via environment variables:
            # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (auto-detected by httpfs extension)
            polaris_secret_sql = f"""
            CREATE OR REPLACE SECRET polaris_secret (
                TYPE ICEBERG,
                CLIENT_ID '{client_id}',
                CLIENT_SECRET '{client_secret}',
                ENDPOINT '{catalog_uri}'
            )
            """
            conn.execute(polaris_secret_sql)

            # ATTACH Polaris catalog using the secret
            # Catalog name is the warehouse, not full URL path
            attach_sql = f"""
            ATTACH '{warehouse}' AS polaris_catalog (
                TYPE ICEBERG,
                SECRET polaris_secret
            )
            """
            conn.execute(attach_sql)

        except Exception as e:
            # Log error for debugging
            import traceback

            traceback.print_exc()
            print(f"Warning: Failed to attach Polaris catalog: {e}")

    def _validate_catalog_control_plane(self) -> None:
        """Enforce catalog control plane - reject patterns that bypass the catalog.

        Scans dbt manifest for forbidden patterns that would bypass Polaris catalog:
        • materialized='external' with location parameter (direct S3 writes)
        • Hardcoded S3 paths in model configs
        • Direct storage/endpoint references

        This enforces the architectural principle that ALL Iceberg writes must go
        through the Polaris catalog control plane for:
        • Access control (RBAC)
        • Audit trails
        • Governance policies
        • Environment portability

        Raises:
            ValueError: If architectural violations are detected.
        """
        import json
        from pathlib import Path

        manifest_path = Path.cwd() / "target" / "manifest.json"
        if not manifest_path.exists():
            return

        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception:
            return

        violations = []

        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") != "model":
                continue

            config = node.get("config", {})
            model_name = node.get("name", node_id)

            if config.get("materialized") == "external":
                violations.append(
                    f"{model_name}: 'external' materialization bypasses Polaris catalog. "
                    f"Use materialized='iceberg' to enforce catalog control plane."
                )

            location = config.get("location", "")
            if location and location.startswith("s3://"):
                violations.append(
                    f"{model_name}: Hardcoded S3 path '{location}' detected. "
                    f"Remove 'location' parameter - storage resolved from platform.yaml."
                )

            for key in config:
                if "endpoint" in key.lower() or "bucket" in key.lower():
                    violations.append(
                        f"{model_name}: Infrastructure key '{key}' forbidden. "
                        f"All infrastructure configured in platform.yaml."
                    )

        if violations:
            error_msg = (
                "\n" + "=" * 70 + "\n"
                "🚨 CATALOG CONTROL PLANE VIOLATION DETECTED\n" + "=" * 70 + "\n\n"
                "All Iceberg table writes MUST go through the Polaris catalog.\n"
                "Direct S3 writes bypass:\n"
                "  • Access control (RBAC)\n"
                "  • Audit trails\n"
                "  • Governance policies\n"
                "  • Environment portability\n\n"
                "Violations found:\n\n"
                + "\n".join(f"  ❌ {v}" for v in violations)
                + "\n\n"
                + "=" * 70
                + "\n"
            )
            raise ValueError(error_msg)

    def store(self, target_config: TargetConfig) -> None:
        """Write dbt transformation output to Iceberg table via Polaris.

        Args:
            target_config: dbt-duckdb target configuration containing:
                - location: Path to parquet file dbt created
                - config: Model config with polaris_namespace and polaris_table
                - column_list: List of columns and types
        """
        namespace = target_config.config.get("polaris_namespace")
        table_name = target_config.config.get("polaris_table")

        if not namespace or not table_name:
            raise ValueError(
                "polaris_namespace and polaris_table must be specified in model config"
            )

        full_table_id = f"{namespace}.{table_name}"

        parquet_path = target_config.location.path
        table_data = pq.read_table(parquet_path)

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

        schema = target_config.config.get("schema", "default")

        storage_config = self.storage_mapping.get(schema)
        if not storage_config:
            storage_config = self.storage_mapping.get("default", {})

        if not storage_config:
            raise ValueError(
                f"No storage configuration found for schema '{schema}'. "
                f"Available schemas: {list(self.storage_mapping.keys())}"
            )

        bucket = storage_config.get("bucket", "iceberg-data")
        location = f"s3://{bucket}/demo/{table_name}"

        try:
            existing_table = self.catalog._catalog.load_table(full_table_id)
            existing_table.overwrite(table_data)
        except Exception:
            self.catalog._catalog.create_table(
                identifier=full_table_id,
                schema=iceberg_schema,
                location=location,
            )

            table = self.catalog._catalog.load_table(full_table_id)
            table.append(table_data)

    def _map_dbt_type_to_iceberg(self, dbt_type: str) -> Any:
        """Map dbt/DuckDB data types to Iceberg types.

        Args:
            dbt_type: dbt column data type (e.g., "INTEGER", "VARCHAR")

        Returns:
            Corresponding Iceberg type
        """
        dbt_type_upper = dbt_type.upper()

        if dbt_type_upper in ("TINYINT", "SMALLINT", "INTEGER", "INT"):
            return IntegerType()
        if dbt_type_upper in ("BIGINT",):
            return LongType()
        if dbt_type_upper in ("REAL", "FLOAT"):
            return FloatType()
        if dbt_type_upper in ("DOUBLE", "DECIMAL", "NUMERIC"):
            return DoubleType()
        if dbt_type_upper in ("VARCHAR", "CHAR", "TEXT", "STRING"):
            return StringType()
        if dbt_type_upper in ("BOOLEAN", "BOOL"):
            return BooleanType()
        if dbt_type_upper in ("DATE",):
            return DateType()
        if dbt_type_upper in ("TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ"):
            return TimestampType()

        return StringType()
