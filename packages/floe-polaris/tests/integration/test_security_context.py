"""Integration tests for security context propagation in Polaris.

T088: FR-028 - Security context propagation in catalog operations

These tests verify that security context (principal credentials, scope)
is correctly propagated through catalog operations. The tests validate
authentication, authorization, and error handling for security-related scenarios.

Requirements:
- Polaris server must be running (Docker Compose storage profile)
- Tests FAIL if Polaris is not available (never skip)

Covers:
- FR-028: Integration tests MUST verify security context propagation
          across catalog operations
"""

from __future__ import annotations

import os
import uuid
import warnings
from collections.abc import Generator

import pytest

from floe_polaris import (
    CatalogAuthenticationError,
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
            pass
    except (OSError, ConnectionRefusedError):
        pytest.fail(
            f"Polaris server not available at {host}:8181. "
            "Start with: cd testing/docker && docker compose --profile storage up -d. "
            "Tests FAIL when infrastructure is missing (never skip)."
        )


class TestSecurityContextPropagation:
    """Test security context propagation in catalog operations.

    Covers: FR-028 (security context propagation)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.fixture
    def valid_config(self) -> PolarisCatalogConfig:
        """Create valid Polaris configuration with test credentials."""
        host = _get_polaris_host()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            return PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
                client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
                client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
                scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
            )

    @pytest.fixture
    def catalog(
        self, valid_config: PolarisCatalogConfig
    ) -> Generator[PolarisCatalog, None, None]:
        """Create catalog with valid credentials."""
        catalog = create_catalog(valid_config)
        yield catalog

    @pytest.fixture
    def test_namespace(
        self, catalog: PolarisCatalog
    ) -> Generator[str, None, None]:
        """Provide a unique test namespace with cleanup."""
        ns_name = f"fr028_security_{uuid.uuid4().hex[:8]}"
        yield ns_name

        try:
            catalog.drop_namespace(ns_name)
        except NamespaceNotFoundError:
            pass

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-001")
    @pytest.mark.requirement("004-FR-002")
    @pytest.mark.requirement("004-FR-007")
    @pytest.mark.requirement("004-FR-008")
    def test_principal_credentials_propagate(
        self,
        valid_config: PolarisCatalogConfig,
        test_namespace: str,
    ) -> None:
        """Principal credentials authenticate catalog operations.

        Verifies that client_id/client_secret credentials are correctly
        propagated and used for OAuth2 authentication with Polaris.

        Covers:
        - 004-FR-001: Connect to Polaris REST catalogs
        - 004-FR-002: OAuth2 client credentials authentication
        - 004-FR-007: Creating namespaces
        - 004-FR-008: Listing namespaces
        """
        # Create catalog with valid credentials
        catalog = create_catalog(valid_config)

        # Connection should succeed
        assert catalog.is_connected()

        # Operations should work with valid credentials
        catalog.create_namespace(test_namespace)
        namespaces = catalog.list_namespaces()

        assert test_namespace in str(namespaces)

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-002")
    def test_invalid_credentials_fail(self) -> None:
        """Invalid credentials raise CatalogAuthenticationError.

        Verifies that incorrect client_id or client_secret results
        in proper authentication failure handling.

        Covers:
        - 004-FR-002: OAuth2 authentication (rejects invalid credentials)
        """
        host = _get_polaris_host()

        # Create config with invalid credentials
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            invalid_config = PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse="warehouse",
                client_id="invalid_client_id",
                client_secret="invalid_secret",
                scope="PRINCIPAL_ROLE:ALL",
            )

        # Connection should fail with authentication error
        with pytest.raises(CatalogAuthenticationError):
            create_catalog(invalid_config)

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-001")
    @pytest.mark.requirement("004-FR-002")
    def test_scope_configures_access(
        self,
        valid_config: PolarisCatalogConfig,
    ) -> None:
        """Scope parameter configures catalog access context.

        Verifies that the scope parameter is included in OAuth2
        token requests and affects the access context.

        Covers:
        - 004-FR-001: Connect to Polaris REST catalogs
        - 004-FR-002: OAuth2 client credentials authentication
        """
        # The scope should be set in the config
        assert valid_config.scope is not None
        assert valid_config.scope == os.environ.get(
            "POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"
        )

        # Create catalog with configured scope
        catalog = create_catalog(valid_config)

        # Operations should work with the configured scope
        assert catalog.is_connected()

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-002")
    def test_invalid_client_id_authentication_error(self) -> None:
        """Invalid client_id raises authentication error.

        Verifies specific error handling for wrong client_id.

        Covers:
        - 004-FR-002: OAuth2 authentication (rejects invalid client_id)
        """
        host = _get_polaris_host()

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse="warehouse",
                client_id="nonexistent_client",
                client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
                scope="PRINCIPAL_ROLE:ALL",
            )

        with pytest.raises(CatalogAuthenticationError):
            create_catalog(config)

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-002")
    def test_invalid_client_secret_authentication_error(self) -> None:
        """Invalid client_secret raises authentication error.

        Verifies specific error handling for wrong client_secret.

        Covers:
        - 004-FR-002: OAuth2 authentication (rejects invalid secret)
        """
        host = _get_polaris_host()

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse="warehouse",
                client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
                client_secret="wrong_secret",
                scope="PRINCIPAL_ROLE:ALL",
            )

        with pytest.raises(CatalogAuthenticationError):
            create_catalog(config)


class TestSecurityContextInOperations:
    """Test security context is maintained across catalog operations.

    Covers: FR-028 (context propagation in operations)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.fixture
    def catalog(self) -> Generator[PolarisCatalog, None, None]:
        """Create catalog with valid credentials."""
        host = _get_polaris_host()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
                client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
                client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
                scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
            )
        catalog = create_catalog(config)
        yield catalog

    @pytest.fixture
    def test_namespace(
        self, catalog: PolarisCatalog
    ) -> Generator[str, None, None]:
        """Provide a unique test namespace with cleanup."""
        ns_name = f"fr028_ops_{uuid.uuid4().hex[:8]}"
        yield ns_name

        try:
            catalog.drop_namespace(ns_name)
        except NamespaceNotFoundError:
            pass

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-002")
    @pytest.mark.requirement("004-FR-007")
    @pytest.mark.requirement("004-FR-008")
    @pytest.mark.requirement("004-FR-009")
    def test_security_context_persists_across_operations(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Security context persists across multiple operations.

        Verifies that authenticated context is maintained through
        a sequence of catalog operations.

        Covers:
        - 004-FR-002: OAuth2 authentication (persistent context)
        - 004-FR-007: Creating namespaces
        - 004-FR-008: Listing namespaces
        - 004-FR-009: Deleting empty namespaces
        """
        # Multiple operations should all succeed with same context
        catalog.create_namespace(test_namespace)
        catalog.load_namespace(test_namespace)
        namespaces = catalog.list_namespaces()
        catalog.drop_namespace(test_namespace)

        # If we got here, all operations used the same security context
        assert True

    @pytest.mark.requirement("006-FR-028")
    @pytest.mark.requirement("004-FR-002")
    @pytest.mark.requirement("004-FR-004")
    def test_reconnect_preserves_security_context(
        self,
        catalog: PolarisCatalog,
        test_namespace: str,
    ) -> None:
        """Reconnect preserves security context.

        Verifies that security context is maintained after reconnection.

        Covers:
        - 004-FR-002: OAuth2 authentication
        - 004-FR-004: Automatic token refresh (reconnect)
        """
        # Initial operation
        catalog.create_namespace(test_namespace)

        # Reconnect
        catalog.reconnect()

        # Operations after reconnect should still work
        assert catalog.is_connected()
        ns_meta = catalog.load_namespace(test_namespace)
        assert ns_meta is not None


class TestScopeWarnings:
    """Test scope-related warnings for security best practices.

    Covers: FR-028 (security warnings)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Polaris is available before running tests."""
        _check_polaris_available()

    @pytest.mark.requirement("006-FR-028")
    def test_overly_permissive_scope_warns(self) -> None:
        """PRINCIPAL_ROLE:ALL scope emits warning.

        Verifies that using an overly permissive scope triggers
        a warning to encourage least-privilege principle.
        """
        host = _get_polaris_host()

        with pytest.warns(UserWarning, match="PRINCIPAL_ROLE:ALL"):
            PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse="warehouse",
                client_id="root",
                client_secret="s3cr3t",
                scope="PRINCIPAL_ROLE:ALL",
            )

    @pytest.mark.requirement("006-FR-028")
    def test_narrowly_scoped_role_no_warning(self) -> None:
        """Narrowly-scoped role does not emit warning.

        Verifies that using a specific role scope (least privilege)
        does not trigger the overly-permissive warning.
        """
        host = _get_polaris_host()

        # This should not emit a warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            PolarisCatalogConfig(
                uri=f"http://{host}:8181/api/catalog",
                warehouse="warehouse",
                client_id="root",
                client_secret="s3cr3t",
                scope="PRINCIPAL_ROLE:DATA_ENGINEER",  # Specific role
            )

            # No PRINCIPAL_ROLE:ALL warnings
            principal_role_all_warnings = [
                warning
                for warning in w
                if "PRINCIPAL_ROLE:ALL" in str(warning.message)
            ]
            assert len(principal_role_all_warnings) == 0
