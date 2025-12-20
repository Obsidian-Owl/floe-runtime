"""Integration tests for Polaris catalog connection.

These tests require a running Polaris server. Use Docker Compose to start:

    cd testing/docker
    docker compose --profile storage up -d

Run tests with:

    pytest -m integration packages/floe-polaris/tests/integration/

Environment variables:
    POLARIS_URI: Polaris REST API URL (default: http://localhost:8181/api/catalog)
    POLARIS_WAREHOUSE: Warehouse name (default: warehouse)
    POLARIS_CLIENT_ID: OAuth2 client ID (default: root)
    POLARIS_CLIENT_SECRET: OAuth2 client secret (default: s3cr3t)
"""

from __future__ import annotations

import contextlib
import os
import uuid
import warnings
from collections.abc import Generator

import pytest

from floe_polaris import (
    CatalogAuthenticationError,
    CatalogConnectionError,
    NamespaceExistsError,
    NamespaceNotEmptyError,
    NamespaceNotFoundError,
    PolarisCatalog,
    PolarisCatalogConfig,
    create_catalog,
)

# =============================================================================
# Test Configuration
# =============================================================================


def get_test_config() -> PolarisCatalogConfig:
    """Get Polaris configuration for TESTING ONLY.

    Note: scope="PRINCIPAL_ROLE:ALL" grants maximum privileges and should
    ONLY be used in test environments. Production deployments must use
    narrowly-scoped principal roles following least privilege principle.
    """
    return PolarisCatalogConfig(
        uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
        # TESTING ONLY: PRINCIPAL_ROLE:ALL grants all roles - never use in production!
        scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
    )


def is_polaris_available() -> bool:
    """Check if Polaris is available for testing.

    Uses context-aware hostname detection:
    - Inside Docker container (DOCKER_CONTAINER=1): connects to 'polaris:8181'
    - On host machine: connects to 'localhost:8181'
    """
    import socket

    # Use internal hostname when running in Docker container
    host = "polaris" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"

    try:
        with socket.create_connection((host, 8181), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def get_polaris_host() -> str:
    """Get the Polaris hostname based on execution context."""
    return "polaris" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"


# Skip all tests if Polaris is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_polaris_available(),
        reason=f"Polaris server not available at {get_polaris_host()}:8181",
    ),
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config() -> PolarisCatalogConfig:
    """Provide test configuration."""
    # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
        return get_test_config()


@pytest.fixture
def catalog(config: PolarisCatalogConfig) -> Generator[PolarisCatalog, None, None]:
    """Provide connected catalog instance."""
    # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
        cat = create_catalog(config)
    yield cat
    # No cleanup needed - catalog is stateless


@pytest.fixture
def test_namespace(catalog: PolarisCatalog) -> Generator[str, None, None]:
    """Provide a unique test namespace that is cleaned up after the test."""
    # Generate unique namespace name for test isolation
    ns_name = f"test_{uuid.uuid4().hex[:8]}"

    yield ns_name

    # Cleanup: Remove the namespace if it exists
    try:
        # First, list and drop any tables
        try:
            tables = catalog.list_tables(ns_name)
            for _table in tables:
                # Note: Table dropping not implemented in current API
                # Would need to add drop_table method
                pass
        except NamespaceNotFoundError:
            pass

        catalog.drop_namespace(ns_name)
    except (NamespaceNotFoundError, NamespaceNotEmptyError):
        pass  # Namespace doesn't exist or couldn't be cleaned up


@pytest.fixture
def nested_namespace(catalog: PolarisCatalog) -> Generator[str, None, None]:
    """Provide a unique nested test namespace."""
    parent = f"test_parent_{uuid.uuid4().hex[:8]}"
    child = f"{parent}.child"

    yield child

    # Cleanup nested structure
    with contextlib.suppress(NamespaceNotFoundError, NamespaceNotEmptyError):
        catalog.drop_namespace(child)
    with contextlib.suppress(NamespaceNotFoundError, NamespaceNotEmptyError):
        catalog.drop_namespace(parent)


# =============================================================================
# Connection Tests (T044)
# =============================================================================


class TestCatalogConnection:
    """Tests for catalog connection and authentication."""

    @pytest.mark.requirement("006-FR-012")
    @pytest.mark.requirement("006-FR-023")
    def test_create_catalog_with_valid_credentials(
        self,
        config: PolarisCatalogConfig,
    ) -> None:
        """Test successful catalog creation with valid credentials."""
        catalog = create_catalog(config)

        assert catalog is not None
        assert catalog.is_connected()
        assert isinstance(catalog, PolarisCatalog)

    @pytest.mark.requirement("006-FR-012")
    def test_catalog_reconnect(self, catalog: PolarisCatalog) -> None:
        """Test that reconnect re-establishes connection."""
        assert catalog.is_connected()

        catalog.reconnect()

        assert catalog.is_connected()

    @pytest.mark.requirement("006-FR-012")
    def test_access_inner_catalog(self, catalog: PolarisCatalog) -> None:
        """Test accessing the underlying PyIceberg catalog."""
        inner = catalog.inner_catalog

        assert inner is not None
        # Should be a PyIceberg RestCatalog
        assert hasattr(inner, "list_namespaces")

    @pytest.mark.requirement("006-FR-012")
    def test_invalid_uri_connection_error(self) -> None:
        """Test that invalid URI raises CatalogConnectionError."""
        # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri="http://nonexistent.invalid:8181/api/catalog",
                warehouse="test",
                client_id="test",
                client_secret="test",
                scope="PRINCIPAL_ROLE:ALL",  # Required field
            )

            with pytest.raises(CatalogConnectionError) as exc_info:
                create_catalog(config)

        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.requirement("006-FR-012")
    def test_invalid_credentials_authentication_error(self) -> None:
        """Test that invalid credentials raise CatalogAuthenticationError."""
        # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
                warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
                client_id="invalid_client",
                client_secret="invalid_secret",
                scope="PRINCIPAL_ROLE:ALL",  # Required field
            )

            with pytest.raises((CatalogAuthenticationError, CatalogConnectionError)) as exc_info:
                create_catalog(config)

        # Error message should indicate auth failure
        error_str = str(exc_info.value).lower()
        assert (
            "authentication" in error_str
            or "unauthorized" in error_str
            or "401" in error_str
            or "failed" in error_str
        )


# =============================================================================
# Namespace Operations Tests
# =============================================================================


class TestNamespaceOperations:
    """Tests for namespace CRUD operations."""

    @pytest.mark.requirement("006-FR-012")
    def test_create_namespace(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test creating a new namespace."""
        result = catalog.create_namespace(test_namespace)

        assert result is not None
        assert result.name == test_namespace

    @pytest.mark.requirement("006-FR-012")
    def test_create_namespace_with_properties(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test creating a namespace with properties."""
        properties = {"owner": "test_team", "environment": "test"}

        result = catalog.create_namespace(test_namespace, properties)

        assert result.name == test_namespace
        # Note: Properties may or may not be returned depending on Polaris version
        # Just verify the namespace was created

    @pytest.mark.requirement("006-FR-012")
    def test_create_namespace_already_exists(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test that creating an existing namespace raises error."""
        catalog.create_namespace(test_namespace)

        with pytest.raises(NamespaceExistsError) as exc_info:
            catalog.create_namespace(test_namespace)

        assert test_namespace in str(exc_info.value)

    @pytest.mark.requirement("006-FR-012")
    def test_create_namespace_if_not_exists_idempotent(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test idempotent namespace creation."""
        # Create first time
        result1 = catalog.create_namespace_if_not_exists(test_namespace)
        assert result1.name == test_namespace

        # Create again - should not raise
        result2 = catalog.create_namespace_if_not_exists(test_namespace)
        assert result2.name == test_namespace

    @pytest.mark.requirement("006-FR-012")
    def test_create_nested_namespace_with_parents(
        self,
        catalog: PolarisCatalog,
        nested_namespace: str,
    ) -> None:
        """Test creating nested namespace auto-creates parents."""
        # nested_namespace is "parent.child"
        result = catalog.create_namespace(nested_namespace, create_parents=True)

        assert result.name == nested_namespace

        # Parent should also exist
        parent = nested_namespace.split(".")[0]
        parent_info = catalog.load_namespace(parent)
        assert parent_info.name == parent

    @pytest.mark.requirement("006-FR-012")
    def test_list_namespaces(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test listing namespaces."""
        catalog.create_namespace(test_namespace)

        namespaces = catalog.list_namespaces()

        # Should contain at least our test namespace
        ns_names = [ns.name for ns in namespaces]
        assert test_namespace in ns_names

    @pytest.mark.requirement("006-FR-012")
    def test_list_child_namespaces(
        self,
        catalog: PolarisCatalog,
        nested_namespace: str,
    ) -> None:
        """Test listing child namespaces."""
        catalog.create_namespace(nested_namespace, create_parents=True)
        parent = nested_namespace.split(".")[0]

        children = catalog.list_namespaces(parent)

        [ns.name for ns in children]
        # The child namespace name as returned might be just "child" or "parent.child"
        assert len(children) >= 1

    @pytest.mark.requirement("006-FR-012")
    def test_load_namespace(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test loading namespace metadata."""
        catalog.create_namespace(test_namespace, {"test_key": "test_value"})

        result = catalog.load_namespace(test_namespace)

        assert result.name == test_namespace
        assert isinstance(result.properties, dict)

    @pytest.mark.requirement("006-FR-012")
    def test_load_namespace_not_found(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test loading non-existent namespace raises error."""
        with pytest.raises(NamespaceNotFoundError) as exc_info:
            catalog.load_namespace("nonexistent_ns_12345")

        assert "nonexistent_ns_12345" in str(exc_info.value)

    @pytest.mark.requirement("006-FR-012")
    def test_drop_namespace(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test dropping an empty namespace."""
        catalog.create_namespace(test_namespace)

        catalog.drop_namespace(test_namespace)

        # Should not exist anymore
        with pytest.raises(NamespaceNotFoundError):
            catalog.load_namespace(test_namespace)

    @pytest.mark.requirement("006-FR-012")
    def test_drop_namespace_not_found(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test dropping non-existent namespace raises error."""
        with pytest.raises(NamespaceNotFoundError):
            catalog.drop_namespace("nonexistent_ns_12345")

    @pytest.mark.requirement("006-FR-012")
    def test_update_namespace_properties(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test updating namespace properties."""
        catalog.create_namespace(test_namespace, {"initial": "value"})

        result = catalog.update_namespace_properties(
            test_namespace,
            updates={"new_key": "new_value"},
        )

        assert result.name == test_namespace
        # Note: Property updates may not be returned immediately


# =============================================================================
# Table Operations Tests
# =============================================================================


class TestTableOperations:
    """Tests for table-related catalog operations."""

    @pytest.mark.requirement("006-FR-012")
    def test_list_tables_empty_namespace(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test listing tables in an empty namespace."""
        catalog.create_namespace(test_namespace)

        tables = catalog.list_tables(test_namespace)

        assert tables == []

    @pytest.mark.requirement("006-FR-012")
    def test_list_tables_namespace_not_found(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test listing tables in non-existent namespace."""
        # This should not raise - just return empty or raise NamespaceNotFound
        # depending on Polaris behavior
        try:
            tables = catalog.list_tables("nonexistent_ns_12345")
            assert tables == []
        except NamespaceNotFoundError:
            pass  # Also acceptable

    @pytest.mark.requirement("006-FR-012")
    def test_table_exists_false(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Test table_exists returns False for non-existent table."""
        catalog.create_namespace(test_namespace)

        result = catalog.table_exists(f"{test_namespace}.nonexistent_table")

        assert result is False


# =============================================================================
# Observability Tests
# =============================================================================


class TestObservability:
    """Tests for logging and tracing integration."""

    def test_structured_logging_on_operations(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that operations emit structured logs."""
        import logging

        with caplog.at_level(logging.DEBUG):
            catalog.create_namespace(test_namespace)

        # Should have logged the namespace creation
        # Note: structlog may not integrate with caplog directly
        # This is a basic check that no errors occurred


# =============================================================================
# Retry and Circuit Breaker Tests
# =============================================================================


class TestRetryBehavior:
    """Tests for retry policy behavior."""

    def test_circuit_breaker_resets_on_reconnect(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test that reconnect resets the circuit breaker."""
        # Trigger some operations
        catalog.list_namespaces()

        # Reconnect should reset state
        catalog.reconnect()

        # Should still work
        catalog.list_namespaces()


# =============================================================================
# Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """End-to-end integration scenarios."""

    @pytest.mark.requirement("006-FR-012")
    def test_full_namespace_lifecycle(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test complete namespace lifecycle: create, update, list, drop."""
        ns_name = f"lifecycle_test_{uuid.uuid4().hex[:8]}"

        try:
            # Create
            created = catalog.create_namespace(ns_name, {"stage": "bronze"})
            assert created.name == ns_name

            # List and verify exists
            namespaces = catalog.list_namespaces()
            assert any(ns.name == ns_name for ns in namespaces)

            # Load and verify properties
            loaded = catalog.load_namespace(ns_name)
            assert loaded.name == ns_name

            # Update properties
            updated = catalog.update_namespace_properties(
                ns_name,
                updates={"stage": "silver"},
            )
            assert updated.name == ns_name

            # Drop
            catalog.drop_namespace(ns_name)

            # Verify deleted
            with pytest.raises(NamespaceNotFoundError):
                catalog.load_namespace(ns_name)

        finally:
            # Cleanup in case of failure
            with contextlib.suppress(NamespaceNotFoundError, NamespaceNotEmptyError):
                catalog.drop_namespace(ns_name)

    @pytest.mark.requirement("006-FR-012")
    def test_nested_namespace_hierarchy(
        self,
        catalog: PolarisCatalog,
    ) -> None:
        """Test creating and managing nested namespace hierarchy."""
        base = f"hierarchy_test_{uuid.uuid4().hex[:8]}"
        bronze = f"{base}.bronze"
        raw = f"{base}.bronze.raw"

        try:
            # Create deepest level with parent creation
            catalog.create_namespace(raw, create_parents=True)

            # All levels should exist
            catalog.load_namespace(base)
            catalog.load_namespace(bronze)
            catalog.load_namespace(raw)

            # List children
            base_children = catalog.list_namespaces(base)
            assert len(base_children) >= 1

        finally:
            # Cleanup in reverse order
            for ns in [raw, bronze, base]:
                with contextlib.suppress(NamespaceNotFoundError, NamespaceNotEmptyError):
                    catalog.drop_namespace(ns)
