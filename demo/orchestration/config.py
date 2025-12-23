"""Demo pipeline configuration - Two-Tier Architecture.

Centralized configuration for the production-quality demo pipeline.
Uses the Two-Tier Configuration Architecture:
- Platform config loaded from platform.yaml (via FLOE_PLATFORM_ENV)
- Credentials injected via environment variables (from K8s secrets)

Environment Variables:
    FLOE_PLATFORM_ENV: Platform environment (local, dev, staging, prod)
    DEMO_CUSTOMERS_COUNT: Number of customers to generate (default: 1000)
    DEMO_ORDERS_COUNT: Number of orders to generate (default: 5000)
    DEMO_PRODUCTS_COUNT: Number of products to generate (default: 100)
    DEMO_ORDER_ITEMS_COUNT: Number of order items to generate (default: 10000)
    POLARIS_CLIENT_ID: OAuth2 client ID (from polaris-credentials secret)
    POLARIS_CLIENT_SECRET: OAuth2 client secret (from polaris-credentials secret)
    AWS_ACCESS_KEY_ID: S3 access key (from storage-credentials secret)
    AWS_SECRET_ACCESS_KEY: S3 secret key (from storage-credentials secret)
    AWS_ENDPOINT_URL: Override for S3 endpoint (optional, platform.yaml preferred)

Covers: 007-FR-029 (E2E validation tests)
Covers: 007-FR-031 (Medallion architecture demo)
Covers: 009-FR-001 (Two-Tier Configuration Architecture)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

logger = logging.getLogger(__name__)

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
    access_delegation: str = Field(
        default="",
        description="Iceberg access delegation mode (empty string disables vending for MinIO)",
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


# =============================================================================
# Two-Tier Architecture: Platform Config Loading
# =============================================================================


def _load_platform_config() -> Any:
    """Load platform configuration from platform.yaml.

    Uses PlatformResolver to find and load the platform.yaml based on
    FLOE_PLATFORM_ENV environment variable.

    Returns:
        PlatformSpec instance, or None if not available.

    Note:
        This is an internal function. Public API uses get_*_config() functions
        which fall back to environment variables if platform.yaml is not found.
    """
    try:
        from floe_core.compiler.platform_resolver import PlatformResolver

        resolver = PlatformResolver()
        return resolver.load()
    except ImportError:
        logger.debug("floe_core not available, using environment variables")
        return None
    except Exception as e:
        logger.debug("Platform config not found, using environment variables: %s", e)
        return None


def get_polaris_config_from_platform() -> DemoPolarisConfig | None:
    """Get Polaris config from platform.yaml (Two-Tier Architecture).

    Loads catalog profile from platform.yaml and merges with environment
    variables for credentials. This is the preferred method for Two-Tier.

    Returns:
        DemoPolarisConfig from platform.yaml, or None if not available.
    """
    platform = _load_platform_config()
    if platform is None:
        return None

    try:
        catalog = platform.get_catalog_profile("default")
        storage = platform.get_storage_profile("default")

        # Get credential values from environment (K8s secrets)
        client_id = os.environ.get("POLARIS_CLIENT_ID")
        client_secret_str = os.environ.get("POLARIS_CLIENT_SECRET")
        client_secret = SecretStr(client_secret_str) if client_secret_str else None

        # S3 credentials from environment (K8s secrets)
        s3_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "test")
        s3_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")

        # Get endpoint from storage profile, with env var override
        s3_endpoint = os.environ.get("AWS_ENDPOINT_URL")
        if not s3_endpoint:
            s3_endpoint = storage.get_endpoint() or "http://localstack:4566"

        # Get scope from catalog credentials config
        scope = "PRINCIPAL_ROLE:ALL"  # Default for demo
        if catalog.credentials and catalog.credentials.scope:
            scope = catalog.credentials.scope

        return DemoPolarisConfig(
            uri=catalog.get_uri(),
            warehouse=catalog.warehouse,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            s3_endpoint=s3_endpoint,
            s3_access_key_id=s3_access_key,
            s3_secret_access_key=SecretStr(s3_secret_key),
            s3_region=storage.region,
            s3_path_style_access=storage.path_style_access,
            access_delegation=catalog.access_delegation.value if catalog.access_delegation else "",
        )
    except Exception as e:
        logger.debug("Error loading catalog profile: %s", e)
        return None


def get_tracing_config_from_platform() -> DemoTracingConfig | None:
    """Get tracing config from platform.yaml (Two-Tier Architecture).

    Returns:
        DemoTracingConfig from platform.yaml, or None if not available.
    """
    platform = _load_platform_config()
    if platform is None or platform.observability is None:
        return None

    try:
        obs = platform.observability
        endpoint = getattr(obs, "otlp_endpoint", None)
        if not endpoint:
            return None

        attrs = getattr(obs, "attributes", {}) or {}
        service_name = attrs.get("service.name", "floe-demo")

        return DemoTracingConfig(
            endpoint=endpoint,
            service_name=service_name,
            batch_export=True,
        )
    except Exception as e:
        logger.debug("Error loading observability config: %s", e)
        return None


def get_lineage_config_from_platform() -> DemoLineageConfig | None:
    """Get lineage config from platform.yaml (Two-Tier Architecture).

    Returns:
        DemoLineageConfig from platform.yaml, or None if not available.
    """
    platform = _load_platform_config()
    if platform is None or platform.observability is None:
        return None

    try:
        obs = platform.observability
        endpoint = getattr(obs, "lineage_endpoint", None)
        if not endpoint:
            return None

        namespace = os.environ.get("OPENLINEAGE_NAMESPACE", "demo")

        return DemoLineageConfig(
            endpoint=endpoint,
            namespace=namespace,
            timeout=5.0,
        )
    except Exception as e:
        logger.debug("Error loading lineage config: %s", e)
        return None
