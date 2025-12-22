"""Demo pipeline configuration.

Centralized configuration for the production-quality demo pipeline.
All configuration is read from environment variables with sensible defaults.

Environment Variables:
    DEMO_CUSTOMERS_COUNT: Number of customers to generate (default: 1000)
    DEMO_ORDERS_COUNT: Number of orders to generate (default: 5000)
    DEMO_PRODUCTS_COUNT: Number of products to generate (default: 100)
    DEMO_ORDER_ITEMS_COUNT: Number of order items to generate (default: 10000)
    POLARIS_URI: Polaris catalog URI (default: http://polaris:8181/api/catalog)
    POLARIS_WAREHOUSE: Polaris warehouse name (default: warehouse)
    POLARIS_CLIENT_ID: OAuth2 client ID (from polaris-credentials.env)
    POLARIS_CLIENT_SECRET: OAuth2 client secret (from polaris-credentials.env)
    AWS_ENDPOINT_URL: S3 endpoint (default: http://localstack:4566)
    AWS_ACCESS_KEY_ID: S3 access key (default: test)
    AWS_SECRET_ACCESS_KEY: S3 secret key (default: test)
    AWS_REGION: S3 region (default: us-east-1)
    OTEL_EXPORTER_OTLP_ENDPOINT: Jaeger OTLP endpoint (default: None)
    OTEL_SERVICE_NAME: Service name for traces (default: floe-demo)
    OPENLINEAGE_URL: Marquez lineage endpoint (default: None)
    OPENLINEAGE_NAMESPACE: Lineage namespace (default: demo)

Covers: 007-FR-029 (E2E validation tests)
Covers: 007-FR-031 (Medallion architecture demo)
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

# =============================================================================
# Data Volume Configuration (Configurable via environment)
# =============================================================================

DEMO_CUSTOMERS_COUNT = int(os.environ.get("DEMO_CUSTOMERS_COUNT", "1000"))
DEMO_ORDERS_COUNT = int(os.environ.get("DEMO_ORDERS_COUNT", "5000"))
DEMO_PRODUCTS_COUNT = int(os.environ.get("DEMO_PRODUCTS_COUNT", "100"))
DEMO_ORDER_ITEMS_COUNT = int(os.environ.get("DEMO_ORDER_ITEMS_COUNT", "10000"))

# Random seed for reproducible data generation
DEMO_SEED = int(os.environ.get("DEMO_SEED", "42"))


# =============================================================================
# Polaris Configuration
# =============================================================================


class DemoPolarisConfig(BaseModel):
    """Polaris catalog configuration for demo pipeline.

    Reads OAuth2 credentials from environment variables set by polaris-init.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str = Field(
        default_factory=lambda: os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog"),
        description="Polaris REST API endpoint",
    )
    warehouse: str = Field(
        default_factory=lambda: os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        description="Polaris warehouse name",
    )
    client_id: str | None = Field(
        default_factory=lambda: os.environ.get("POLARIS_CLIENT_ID"),
        description="OAuth2 client ID",
    )
    client_secret: SecretStr | None = Field(
        default_factory=lambda: (
            SecretStr(os.environ["POLARIS_CLIENT_SECRET"])
            if os.environ.get("POLARIS_CLIENT_SECRET")
            else None
        ),
        description="OAuth2 client secret",
    )
    scope: str = Field(
        default="PRINCIPAL_ROLE:ALL",  # Demo uses broad scope - narrow in production
        description="OAuth2 scope for token requests",
    )
    # S3 FileIO properties for LocalStack
    s3_endpoint: str = Field(
        default_factory=lambda: os.environ.get("AWS_ENDPOINT_URL", "http://localstack:4566"),
        description="S3-compatible endpoint URL",
    )
    s3_access_key_id: str = Field(
        default_factory=lambda: os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        description="S3 access key ID",
    )
    s3_secret_access_key: SecretStr = Field(
        default_factory=lambda: SecretStr(os.environ.get("AWS_SECRET_ACCESS_KEY", "test")),
        description="S3 secret access key",
    )
    s3_region: str = Field(
        default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"),
        description="S3 region",
    )
    s3_path_style_access: bool = Field(
        default=True,
        description="Use path-style S3 access (required for LocalStack)",
    )


# =============================================================================
# Observability Configuration
# =============================================================================


class DemoTracingConfig(BaseModel):
    """OpenTelemetry tracing configuration for Jaeger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str | None = Field(
        default_factory=lambda: os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
        description="OTLP endpoint URL (None = disabled)",
    )
    service_name: str = Field(
        default_factory=lambda: os.environ.get("OTEL_SERVICE_NAME", "floe-demo"),
        description="Service name for traces",
    )
    batch_export: bool = Field(
        default=True,
        description="Use batch span processor for efficiency",
    )

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self.endpoint is not None


class DemoLineageConfig(BaseModel):
    """OpenLineage configuration for Marquez."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str | None = Field(
        default_factory=lambda: os.environ.get("OPENLINEAGE_URL"),
        description="OpenLineage backend URL (None = disabled)",
    )
    namespace: str = Field(
        default_factory=lambda: os.environ.get("OPENLINEAGE_NAMESPACE", "demo"),
        description="Job namespace for lineage events",
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="HTTP timeout in seconds",
    )

    @property
    def enabled(self) -> bool:
        """Check if lineage is enabled."""
        return self.endpoint is not None


# =============================================================================
# dbt Configuration
# =============================================================================


class DemoDBTConfig(BaseModel):
    """dbt configuration for Trino transformations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(
        default_factory=lambda: os.environ.get("TRINO_HOST", "trino"),
        description="Trino host",
    )
    port: int = Field(
        default_factory=lambda: int(os.environ.get("TRINO_PORT", "8080")),
        description="Trino port",
    )
    catalog: str = Field(
        default="iceberg",
        description="Trino catalog name",
    )
    schema_name: str = Field(
        default_factory=lambda: os.environ.get("FLOE_DEMO_SCHEMA", "default"),
        description="Default schema for dbt models",
    )
    threads: int = Field(
        default=4,
        description="Number of dbt threads",
    )


# =============================================================================
# Factory Functions
# =============================================================================


def get_polaris_config() -> DemoPolarisConfig:
    """Get Polaris configuration from environment."""
    return DemoPolarisConfig()


def get_tracing_config() -> DemoTracingConfig:
    """Get tracing configuration from environment."""
    return DemoTracingConfig()


def get_lineage_config() -> DemoLineageConfig:
    """Get lineage configuration from environment."""
    return DemoLineageConfig()


def get_dbt_config() -> DemoDBTConfig:
    """Get dbt configuration from environment."""
    return DemoDBTConfig()


def get_demo_config() -> dict[str, Any]:
    """Get full demo configuration dictionary.

    Returns a dictionary with all configuration for backwards compatibility
    with the existing demo code.
    """
    return {
        "catalog": os.environ.get("FLOE_DEMO_CATALOG", "floe_demo"),
        "schema": os.environ.get("FLOE_DEMO_SCHEMA", "raw"),
        "polaris_url": os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog"),
        "cube_url": os.environ.get("CUBE_API_URL", "http://cube:4000"),
        "data_volumes": {
            "customers": DEMO_CUSTOMERS_COUNT,
            "orders": DEMO_ORDERS_COUNT,
            "products": DEMO_PRODUCTS_COUNT,
            "order_items": DEMO_ORDER_ITEMS_COUNT,
        },
        "seed": DEMO_SEED,
    }
