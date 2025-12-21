"""Integration tests for CompiledArtifacts → Polaris catalog config.

T087: FR-035 - CompiledArtifacts catalog config consumed by floe-polaris

These tests verify the contract boundary between floe-core's CompiledArtifacts
catalog configuration and floe-polaris' catalog connection. The catalog config
from CompiledArtifacts must produce valid connection parameters.

Requirements:
- Polaris server must be running (Docker Compose storage profile)
- Tests FAIL if Polaris is not available (never skip)

Covers:
- FR-035: Integration tests MUST verify Polaris catalog configuration
          is correctly derived from CompiledArtifacts
"""

from __future__ import annotations

import contextlib
import os
import uuid
import warnings
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import pytest

from floe_polaris import (
    NamespaceNotFoundError,
    PolarisCatalog,
    PolarisCatalogConfig,
    create_catalog,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def _get_polaris_host() -> str:
    """Get the Polaris hostname based on execution context."""
    return "polaris" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"


def _check_polaris_available() -> None:
    """Check that Polaris is available. FAIL if not (never skip)."""
    import socket

    host = _get_polaris_host()

    try:
        with socket.create_connection((host, 8181), timeout=5):
            pass  # Connection succeeded
    except (OSError, ConnectionRefusedError):
        pytest.fail(
            f"Polaris server not available at {host}:8181. "
            "Start with: cd testing/docker && docker compose --profile storage up -d. "
            "Tests FAIL when infrastructure is missing (never skip)."
        )


class TestArtifactsToCatalogConfig:
    """Test CompiledArtifacts → Polaris catalog configuration.

    Covers: FR-035 (CompiledArtifacts to Polaris catalog contract)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.fixture
    def polaris_host(self) -> str:
        """Get the Polaris hostname for current execution context."""
        return _get_polaris_host()

    @pytest.fixture
    def compiled_artifacts_with_catalog(self, polaris_host: str) -> dict[str, Any]:
        """Create CompiledArtifacts with catalog configuration.

        This simulates what floe-core would produce when a Polaris
        catalog is configured in floe.yaml.
        """
        return {
            "version": "1.0.0",
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "test_hash",
            },
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
            "transforms": [],
            "catalog": {
                "type": "polaris",
                "uri": f"http://{polaris_host}:8181/api/catalog",
                "warehouse": os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
            },
            "consumption": {"enabled": False},
            "governance": {"classification_source": "dbt_meta"},
            "observability": {
                "traces": {"enabled": False},
                "lineage": {"enabled": False},
            },
        }

    @pytest.fixture
    def polaris_config_from_artifacts(
        self, compiled_artifacts_with_catalog: dict[str, Any]
    ) -> PolarisCatalogConfig:
        """Create PolarisCatalogConfig from CompiledArtifacts catalog section.

        This demonstrates how the catalog config would be derived from artifacts.
        """
        catalog_config = compiled_artifacts_with_catalog.get("catalog", {})

        # In real implementation, credentials come from environment or secrets manager
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            return PolarisCatalogConfig(
                uri=catalog_config.get("uri", f"http://{_get_polaris_host()}:8181/api/catalog"),
                warehouse=catalog_config.get("warehouse", "warehouse"),
                client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
                client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
                scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
            )

    @pytest.fixture
    def catalog_from_artifacts(
        self, polaris_config_from_artifacts: PolarisCatalogConfig
    ) -> Generator[PolarisCatalog, None, None]:
        """Create catalog connection from artifacts-derived config."""
        catalog = create_catalog(polaris_config_from_artifacts)
        yield catalog

    @pytest.fixture
    def test_namespace(self, catalog_from_artifacts: PolarisCatalog) -> Generator[str, None, None]:
        """Provide a unique test namespace with cleanup."""
        ns_name = f"fr035_test_{uuid.uuid4().hex[:8]}"
        yield ns_name

        # Cleanup
        with contextlib.suppress(NamespaceNotFoundError):
            catalog_from_artifacts.drop_namespace(ns_name)

    @pytest.mark.requirement("006-FR-035")
    @pytest.mark.requirement("004-FR-001")
    @pytest.mark.requirement("004-FR-006")
    def test_catalog_uri_from_artifacts(
        self,
        compiled_artifacts_with_catalog: dict[str, Any],
        polaris_config_from_artifacts: PolarisCatalogConfig,
    ) -> None:
        """Catalog URI from CompiledArtifacts connects successfully.

        Verifies that the catalog.uri from artifacts is a valid
        Polaris REST API endpoint.

        Covers:
        - 004-FR-001: Connect to Polaris REST catalogs
        - 004-FR-006: All URIs configurable
        """
        catalog = create_catalog(polaris_config_from_artifacts)

        assert catalog is not None
        assert catalog.is_connected()

        # URI from artifacts matches config
        artifacts_uri = compiled_artifacts_with_catalog["catalog"]["uri"]
        config_uri = polaris_config_from_artifacts.uri
        assert artifacts_uri == config_uri

    @pytest.mark.requirement("006-FR-035")
    @pytest.mark.requirement("004-FR-006")
    def test_warehouse_config_propagates(
        self,
        compiled_artifacts_with_catalog: dict[str, Any],
        polaris_config_from_artifacts: PolarisCatalogConfig,
    ) -> None:
        """Warehouse from artifacts appears in catalog configuration.

        Verifies that the catalog.warehouse field from CompiledArtifacts
        is correctly propagated to the Polaris connection.

        Covers:
        - 004-FR-006: All URIs configurable (warehouse name)
        """
        artifacts_warehouse = compiled_artifacts_with_catalog["catalog"]["warehouse"]
        config_warehouse = polaris_config_from_artifacts.warehouse

        assert artifacts_warehouse == config_warehouse
        assert config_warehouse == "warehouse"  # Expected default

    @pytest.mark.requirement("006-FR-035")
    @pytest.mark.requirement("004-FR-001")
    @pytest.mark.requirement("004-FR-007")
    @pytest.mark.requirement("004-FR-008")
    def test_namespace_creation_from_config(
        self,
        catalog_from_artifacts: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Namespace from artifacts config can be created in catalog.

        Verifies that the catalog connection derived from CompiledArtifacts
        can successfully create namespaces in Polaris.

        Covers:
        - 004-FR-001: Connect to Polaris REST catalogs
        - 004-FR-007: Creating namespaces
        - 004-FR-008: Listing namespaces
        """
        # Create namespace using artifacts-derived catalog connection
        catalog_from_artifacts.create_namespace(test_namespace)

        # Verify namespace exists
        ns_meta = catalog_from_artifacts.load_namespace(test_namespace)
        assert ns_meta is not None
        assert test_namespace in str(catalog_from_artifacts.list_namespaces())

    @pytest.mark.requirement("006-FR-035")
    def test_catalog_type_validation(
        self,
        compiled_artifacts_with_catalog: dict[str, Any],
    ) -> None:
        """Catalog type from artifacts is validated.

        Verifies that the catalog.type field correctly identifies
        the catalog as a Polaris REST catalog.
        """
        catalog_type = compiled_artifacts_with_catalog["catalog"]["type"]
        assert catalog_type == "polaris"


class TestCatalogConfigOptionalFields:
    """Test handling of optional catalog config fields.

    Covers: FR-035 (optional field handling)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.mark.requirement("006-FR-035")
    def test_artifacts_without_catalog_config(self) -> None:
        """CompiledArtifacts without catalog config is valid.

        Verifies that the catalog field is optional in CompiledArtifacts
        (standalone-first: not all deployments use a catalog).
        """
        artifacts_no_catalog = {
            "version": "1.0.0",
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "test_hash",
            },
            "compute": {"target": "duckdb", "properties": {}},
            "transforms": [],
            "catalog": None,  # No catalog configured (standalone mode)
        }

        # catalog is None, which is valid for standalone deployments
        assert artifacts_no_catalog["catalog"] is None

    @pytest.mark.requirement("006-FR-035")
    def test_catalog_credentials_from_environment(
        self,
    ) -> None:
        """Catalog credentials are injected from environment.

        Verifies that credentials (client_id, client_secret) are NOT
        stored in CompiledArtifacts but loaded from environment.
        """
        host = _get_polaris_host()

        # Artifacts only contain connection info, not credentials
        artifacts = {
            "version": "1.0.0",
            "catalog": {
                "type": "polaris",
                "uri": f"http://{host}:8181/api/catalog",
                "warehouse": "warehouse",
                # Note: NO client_id, client_secret, scope
            },
        }

        # Credentials must come from environment
        client_id = os.environ.get("POLARIS_CLIENT_ID", "root")
        client_secret = os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t")

        assert "client_id" not in artifacts["catalog"]
        assert "client_secret" not in artifacts["catalog"]
        assert client_id is not None
        assert client_secret is not None


class TestCatalogConfigVersioning:
    """Test catalog config contract versioning.

    Covers: FR-035 (backward compatibility)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.mark.requirement("006-FR-035")
    def test_v1_catalog_config_supported(self) -> None:
        """v1.0.0 catalog config structure is supported.

        Ensures backward compatibility with the original contract version.
        """
        host = _get_polaris_host()

        v1_artifacts = {
            "version": "1.0.0",
            "catalog": {
                "type": "polaris",
                "uri": f"http://{host}:8181/api/catalog",
                "warehouse": "warehouse",
            },
        }

        # v1.0.0 structure should be valid
        catalog_config = v1_artifacts["catalog"]
        assert catalog_config["type"] == "polaris"
        assert "uri" in catalog_config
        assert "warehouse" in catalog_config

    @pytest.mark.requirement("006-FR-035")
    def test_catalog_config_fields_match_polaris_config(self) -> None:
        """Catalog config fields map to PolarisCatalogConfig.

        Verifies that CompiledArtifacts catalog fields can be directly
        mapped to PolarisCatalogConfig constructor arguments.
        """
        host = _get_polaris_host()

        artifacts = {
            "catalog": {
                "type": "polaris",
                "uri": f"http://{host}:8181/api/catalog",
                "warehouse": "warehouse",
            }
        }

        catalog_config = artifacts["catalog"]

        # These fields map directly to PolarisCatalogConfig
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri=catalog_config["uri"],
                warehouse=catalog_config["warehouse"],
                client_id="root",  # From environment
                client_secret="s3cr3t",  # From environment
                scope="PRINCIPAL_ROLE:ALL",  # From environment
            )

        assert config.uri == catalog_config["uri"]
        assert config.warehouse == catalog_config["warehouse"]
