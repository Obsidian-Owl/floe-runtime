"""Shared CompiledArtifacts fixtures for cross-package testing.

This module provides factory functions and fixtures for creating
CompiledArtifacts instances with various configurations.

The factories here mirror the structure in packages/floe-dbt/tests/conftest.py
but are designed for cross-package use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def base_metadata(
    *,
    floe_core_version: str = "0.1.0",
    source_hash: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
) -> dict[str, Any]:
    """Create base artifact metadata.

    Args:
        floe_core_version: Version of floe-core that compiled the artifacts.
        source_hash: SHA256 hash of the source floe.yaml.

    Returns:
        Metadata dictionary for CompiledArtifacts.
    """
    return {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "floe_core_version": floe_core_version,
        "source_hash": source_hash,
    }


# Pre-defined compute configurations for all 7 supported targets
COMPUTE_CONFIGS: dict[str, dict[str, Any]] = {
    "duckdb": {
        "target": "duckdb",
        "connection_secret_ref": None,
        "properties": {
            "path": ":memory:",
            "threads": 4,
        },
    },
    "snowflake": {
        "target": "snowflake",
        "connection_secret_ref": "snowflake-creds",
        "properties": {
            "account": "xy12345.us-east-1",
            "warehouse": "COMPUTE_WH",
            "database": "ANALYTICS",
            "schema": "PUBLIC",
            "role": "TRANSFORMER",
        },
    },
    "bigquery": {
        "target": "bigquery",
        "connection_secret_ref": None,
        "properties": {
            "project": "my-gcp-project",
            "dataset": "analytics",
            "location": "US",
            "method": "oauth",
        },
    },
    "redshift": {
        "target": "redshift",
        "connection_secret_ref": "redshift-creds",
        "properties": {
            "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
            "port": 5439,
            "database": "analytics",
            "schema": "public",
        },
    },
    "databricks": {
        "target": "databricks",
        "connection_secret_ref": "databricks-creds",
        "properties": {
            "host": "adb-1234567890.12.azuredatabricks.net",
            "http_path": "/sql/1.0/warehouses/abc123",
            "catalog": "main",
            "schema": "default",
        },
    },
    "postgres": {
        "target": "postgres",
        "connection_secret_ref": "postgres-creds",
        "properties": {
            "host": "localhost",
            "port": 5432,
            "database": "analytics",
            "schema": "public",
        },
    },
    "spark": {
        "target": "spark",
        "connection_secret_ref": None,
        "properties": {
            "host": "spark://master:7077",
            "method": "thrift",
            "schema": "default",
        },
    },
}


def make_compiled_artifacts(
    target: str = "duckdb",
    *,
    environment: str = "dev",
    observability_enabled: bool = False,
    lineage_enabled: bool = False,
    with_classifications: bool = False,
    dbt_profiles_path: str = ".floe/profiles",
    metadata: dict[str, Any] | None = None,
    compute_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory for creating CompiledArtifacts test fixtures.

    This factory creates CompiledArtifacts-compatible dictionaries for testing.
    All fields match the expected structure of the CompiledArtifacts Pydantic model.

    Args:
        target: Compute target name (duckdb, snowflake, bigquery, etc.).
        environment: Environment name (dev, staging, prod).
        observability_enabled: Enable traces and metrics.
        lineage_enabled: Enable OpenLineage integration.
        with_classifications: Include sample column classifications.
        dbt_profiles_path: Path for dbt profiles output.
        metadata: Override metadata dict. If None, uses defaults.
        compute_overrides: Override specific compute properties.

    Returns:
        CompiledArtifacts-compatible dictionary.

    Raises:
        ValueError: If target is not one of the 7 supported targets.

    Example:
        >>> artifacts = make_compiled_artifacts("snowflake", environment="prod")
        >>> artifacts["compute"]["target"]
        'snowflake'
    """
    if target not in COMPUTE_CONFIGS:
        supported = ", ".join(sorted(COMPUTE_CONFIGS.keys()))
        raise ValueError(f"Unknown target '{target}'. Supported: {supported}")

    # Get base compute config and apply overrides
    compute = COMPUTE_CONFIGS[target].copy()
    if compute_overrides:
        compute["properties"] = {**compute.get("properties", {}), **compute_overrides}

    # Build observability config
    observability: dict[str, Any] = {
        "traces": {"enabled": observability_enabled},
        "lineage": {"enabled": lineage_enabled},
    }

    # Build classifications if requested
    column_classifications: dict[str, Any] | None = None
    if with_classifications:
        column_classifications = {
            "customers": {
                "email": {"classification": "pii", "pii_type": "email"},
                "phone": {"classification": "pii", "pii_type": "phone"},
            },
        }

    # Build environment context if not dev
    environment_context: dict[str, Any] | None = None
    if environment != "dev":
        environment_context = {
            "environment": environment,
            "tenant_id": f"tenant-{environment}",
        }

    return {
        "version": "1.0.0",
        "metadata": metadata or base_metadata(),
        "compute": compute,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": dbt_profiles_path}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": observability,
        "catalog": None,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": dbt_profiles_path,
        "lineage_namespace": "floe" if lineage_enabled else None,
        "environment_context": environment_context,
        "column_classifications": column_classifications,
    }


def make_minimal_artifacts(target: str = "duckdb") -> dict[str, Any]:
    """Create minimal CompiledArtifacts with only required fields.

    Useful for testing backward compatibility and minimal configurations.

    Args:
        target: Compute target name.

    Returns:
        Minimal CompiledArtifacts-compatible dictionary.
    """
    return {
        "version": "1.0.0",
        "metadata": base_metadata(),
        "compute": {"target": target},
        "transforms": [{"type": "dbt", "path": "./dbt"}],
        "consumption": {},
        "governance": {},
        "observability": {},
    }


# =============================================================================
# Production-Like Configurations (FR-022)
# =============================================================================

# Environment variable patterns matching production deployments
ENV_VAR_PATTERNS: dict[str, dict[str, str]] = {
    "snowflake": {
        "user": "{{ env_var('SNOWFLAKE_{ENV}_USER') }}",
        "password": "{{ env_var('SNOWFLAKE_{ENV}_PASSWORD') }}",
    },
    "bigquery": {
        "keyfile": "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}",
    },
    "redshift": {
        "user": "{{ env_var('REDSHIFT_{ENV}_USER') }}",
        "password": "{{ env_var('REDSHIFT_{ENV}_PASSWORD') }}",
    },
    "databricks": {
        "token": "{{ env_var('DATABRICKS_{ENV}_TOKEN') }}",
    },
    "postgres": {
        "user": "{{ env_var('POSTGRES_{ENV}_USER') }}",
        "password": "{{ env_var('POSTGRES_{ENV}_PASSWORD') }}",
    },
}

# Production-like URIs for catalog and services
PRODUCTION_URIS: dict[str, dict[str, str]] = {
    "polaris": {
        "dev": "http://localhost:8181/api/catalog",
        "staging": "https://polaris.staging.internal/api/catalog",
        "prod": "https://polaris.prod.internal/api/catalog",
    },
    "localstack": {
        "dev": "http://localhost:4566",
        "staging": "https://s3.staging.amazonaws.com",
        "prod": "https://s3.prod.amazonaws.com",
    },
    "jaeger": {
        "dev": "http://localhost:4317",
        "staging": "https://jaeger.staging.internal:4317",
        "prod": "https://jaeger.prod.internal:4317",
    },
    "marquez": {
        "dev": "http://localhost:5001",
        "staging": "https://marquez.staging.internal:5001",
        "prod": "https://marquez.prod.internal:5001",
    },
}


def make_production_artifacts(
    target: str = "snowflake",
    *,
    environment: str = "prod",
    observability_enabled: bool = True,
    lineage_enabled: bool = True,
    with_classifications: bool = True,
    catalog_uri: str | None = None,
    s3_endpoint: str | None = None,
    otel_endpoint: str | None = None,
    lineage_endpoint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory for creating production-like CompiledArtifacts (FR-022).

    This factory creates artifacts that mimic production deployment configurations:
    - Environment-prefixed secret references
    - Production-like service URIs
    - Full observability and lineage enabled
    - Column classifications for governance

    Use this for integration tests that validate production deployment patterns.

    Args:
        target: Compute target (snowflake, bigquery, etc.). Defaults to snowflake
            as it's the most common production target.
        environment: Environment name (dev, staging, prod).
        observability_enabled: Enable OTel traces and metrics.
        lineage_enabled: Enable OpenLineage integration.
        with_classifications: Include sample column classifications.
        catalog_uri: Override Polaris catalog URI.
        s3_endpoint: Override S3/storage endpoint.
        otel_endpoint: Override OpenTelemetry collector endpoint.
        lineage_endpoint: Override OpenLineage/Marquez endpoint.
        metadata: Override metadata dict.

    Returns:
        Production-like CompiledArtifacts dictionary.

    Example:
        >>> artifacts = make_production_artifacts("snowflake", environment="prod")
        >>> artifacts["observability"]["tracing"]["endpoint"]
        'https://jaeger.prod.internal:4317'
        >>> "SNOWFLAKE_PROD_USER" in str(artifacts["compute"]["credentials"])
        True
    """
    if target not in COMPUTE_CONFIGS:
        supported = ", ".join(sorted(COMPUTE_CONFIGS.keys()))
        raise ValueError(f"Unknown target '{target}'. Supported: {supported}")

    # Get base compute config
    compute = COMPUTE_CONFIGS[target].copy()
    compute["properties"] = compute.get("properties", {}).copy()

    # Add environment-specific credential patterns
    env_upper = environment.upper()
    if target in ENV_VAR_PATTERNS:
        credential_patterns = {}
        for key, pattern in ENV_VAR_PATTERNS[target].items():
            credential_patterns[key] = pattern.replace("{ENV}", env_upper)
        compute["credentials"] = credential_patterns

    # Resolve service URIs based on environment
    polaris_uri = catalog_uri or PRODUCTION_URIS["polaris"].get(environment, "")
    storage_endpoint = s3_endpoint or PRODUCTION_URIS["localstack"].get(environment, "")
    jaeger_endpoint = otel_endpoint or PRODUCTION_URIS["jaeger"].get(environment, "")
    marquez_endpoint = lineage_endpoint or PRODUCTION_URIS["marquez"].get(environment, "")

    # Build catalog configuration
    catalog_config: dict[str, Any] | None = None
    if polaris_uri:
        catalog_config = {
            "type": "rest",
            "uri": polaris_uri,
            "warehouse": "warehouse",
            "credential": f"{{{{ env_var('POLARIS_{env_upper}_CLIENT_ID') }}}}",
            "s3": {
                "endpoint": storage_endpoint,
                "region": "us-east-1",
            },
        }

    # Build observability config with production endpoints
    observability: dict[str, Any] = {
        "traces": {
            "enabled": observability_enabled,
        },
        "lineage": {
            "enabled": lineage_enabled,
        },
    }

    if observability_enabled and jaeger_endpoint:
        observability["tracing"] = {
            "endpoint": jaeger_endpoint,
            "service_name": f"floe-{environment}",
            "attributes": {
                "environment": environment,
                "deployment.environment": environment,
            },
        }

    if lineage_enabled and marquez_endpoint:
        observability["lineage"] = {
            "enabled": True,
            "endpoint": marquez_endpoint,
            "namespace": f"floe-{environment}",
        }

    # Build governance config with classifications
    governance: dict[str, Any] = {"enabled": with_classifications}
    column_classifications: dict[str, Any] | None = None
    if with_classifications:
        column_classifications = {
            "customers": {
                "email": {"classification": "pii", "pii_type": "email", "sensitivity": "high"},
                "phone": {"classification": "pii", "pii_type": "phone", "sensitivity": "high"},
                "ssn": {"classification": "pii", "pii_type": "ssn", "sensitivity": "critical"},
            },
            "orders": {
                "credit_card": {
                    "classification": "pci",
                    "pci_type": "pan",
                    "sensitivity": "critical",
                },
                "customer_email": {
                    "classification": "pii",
                    "pii_type": "email",
                    "sensitivity": "high",
                },
            },
        }
        governance["column_classifications"] = column_classifications

    # Build environment context
    environment_context: dict[str, Any] = {
        "environment": environment,
        "tenant_id": f"tenant-{environment}",
        "region": "us-east-1",
        "deployment_id": f"deploy-{environment}-001",
    }

    return {
        "version": "1.0.0",
        "metadata": metadata or base_metadata(),
        "compute": compute,
        "transforms": [
            {
                "type": "dbt",
                "project_dir": ".",
                "profiles_dir": ".floe/profiles",
            }
        ],
        "consumption": {
            "enabled": True,
            "cube": {
                "enabled": True,
                "api_url": f"http://cube.{environment}.internal:4000",
            },
        },
        "governance": governance,
        "observability": observability,
        "catalog": catalog_config,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": ".floe/profiles",
        "lineage_namespace": f"floe-{environment}" if lineage_enabled else None,
        "environment_context": environment_context,
        "column_classifications": column_classifications,
    }


def make_docker_integration_artifacts(
    target: str = "postgres",
    *,
    polaris_uri: str = "http://polaris:8181/api/catalog",
    localstack_endpoint: str = "http://localstack:4566",
    jaeger_endpoint: str = "http://jaeger:4317",
    marquez_endpoint: str = "http://marquez:5001",
) -> dict[str, Any]:
    """Factory for Docker integration test artifacts (FR-023).

    Creates artifacts configured for the Docker test environment with
    internal Docker network hostnames.

    This factory uses hostnames that resolve within Docker Compose networks
    (e.g., 'polaris', 'localstack', 'jaeger', 'marquez').

    Args:
        target: Compute target (postgres recommended for Docker).
        polaris_uri: Polaris catalog URI (internal Docker hostname).
        localstack_endpoint: LocalStack S3 endpoint.
        jaeger_endpoint: Jaeger/OTel collector endpoint.
        marquez_endpoint: Marquez/OpenLineage endpoint.

    Returns:
        Docker-ready CompiledArtifacts dictionary.

    Example:
        >>> artifacts = make_docker_integration_artifacts()
        >>> artifacts["catalog"]["uri"]
        'http://polaris:8181/api/catalog'
    """
    return make_production_artifacts(
        target=target,
        environment="dev",
        catalog_uri=polaris_uri,
        s3_endpoint=localstack_endpoint,
        otel_endpoint=jaeger_endpoint,
        lineage_endpoint=marquez_endpoint,
    )
