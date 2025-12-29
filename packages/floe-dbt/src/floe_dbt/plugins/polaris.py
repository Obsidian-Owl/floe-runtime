"""Simplified Polaris dbt-duckdb plugin for DuckDB native Iceberg writes.

ARCHITECTURE CHANGE (v2 - Native Writes):
    This plugin ONLY handles ATTACH configuration.
    ALL table writes use DuckDB native Iceberg extension via custom
    table materialization macro (no plugin store() method needed).

    platform.yaml → DbtProfilesGenerator → profiles.yml
                 → THIS PLUGIN → configure_connection() → DuckDB ATTACH
                 → Custom table.sql macro → DuckDB native Iceberg writes

Responsibilities:
    ✅ Initialize Polaris catalog connection (for metadata operations)
    ✅ ATTACH Polaris catalog to DuckDB (enables native writes)
    ❌ store() method REMOVED (DuckDB handles via CREATE TABLE AS SELECT)
    ❌ Validation REMOVED (moved to compile-time in floe_spec.py)

Configuration (from generated profiles.yml):
    - catalog_uri: Polaris REST endpoint
    - warehouse: Catalog warehouse name
    - client_id/client_secret: OAuth2 credentials (from env vars)
    - s3_endpoint/s3_region: S3 configuration

Data Engineer Experience:
    {{ config(
        materialized='table',
        schema='gold'
    ) }}
    SELECT * FROM ...

    Platform transparently executes:
        CREATE TABLE polaris_catalog.demo.gold.{table} AS SELECT ...
"""

import os
from typing import Any

try:
    from dbt.adapters.duckdb.plugins import BasePlugin
except ImportError as e:
    raise ImportError(
        "dbt-duckdb is required for Polaris plugin. Install with: pip install dbt-duckdb"
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
    """Simplified Polaris plugin for DuckDB ATTACH configuration.

    REMOVED COMPLEXITY (v1 → v2):
        - ❌ store() method (~150 lines) - DuckDB native writes handle this
        - ❌ _validate_catalog_control_plane() (~60 lines) - moved to compile-time
        - ❌ _map_dbt_type_to_iceberg() (~30 lines) - DuckDB handles schema
        - ❌ PyIceberg table creation logic - DuckDB handles via ATTACH

    RETAINED FUNCTIONALITY:
        - ✅ initialize() - Create PolarisCatalog for metadata operations
        - ✅ configure_connection() - ATTACH polaris_catalog for native writes

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

        Creates PolarisCatalog instance for metadata operations.
        The ATTACH in configure_connection() enables DuckDB native writes.

        Args:
            config: Plugin configuration from generated profiles.yml.
                   Values use {{ env_var('VAR') }} interpolation.
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

    def configure_connection(self, conn: Any) -> None:
        """ATTACH Polaris catalog to DuckDB for native Iceberg writes.

        Uses inline OAuth2 credentials to avoid DuckDB secret manager initialization issues.
        The secret manager is already initialized when this method runs, preventing
        CREATE SECRET operations. Inline credentials bypass this limitation.

        Args:
            conn: DuckDB connection object.

        Raises:
            RuntimeError: If ATTACH fails (catalog unavailable, auth failure, etc.)
        """
        catalog_uri = self.config["catalog_uri"]
        warehouse = self.config["warehouse"]

        client_id = self.config.get("client_id") or os.getenv("POLARIS_CLIENT_ID")
        client_secret = self.config.get("client_secret") or os.getenv("POLARIS_CLIENT_SECRET")

        try:
            oauth2_server_uri = f"{catalog_uri}/v1/oauth/tokens"

            attach_sql = f"""
            ATTACH IF NOT EXISTS '{warehouse}' AS polaris_catalog (
                TYPE ICEBERG,
                CLIENT_ID '{client_id}',
                CLIENT_SECRET '{client_secret}',
                OAUTH2_SERVER_URI '{oauth2_server_uri}',
                ENDPOINT '{catalog_uri}'
            )
            """
            conn.execute(attach_sql)

        except Exception as e:
            import traceback

            traceback.print_exc()

            raise RuntimeError(
                f"Failed to ATTACH Polaris catalog '{warehouse}' at {catalog_uri}. Error: {e}"
            ) from e
