"""Unit tests for PolarisCatalog client.

Tests for:
- T030: PolarisCatalog client initialization
- T031: OAuth2 authentication handling
- T032: create_catalog factory function
- T033-T037: Connection management and token refresh
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_polaris.client import PolarisCatalog
from floe_polaris.config import PolarisCatalogConfig
from floe_polaris.errors import (
    CatalogAuthenticationError,
    CatalogConnectionError,
    NamespaceExistsError,
    NamespaceNotFoundError,
    TableNotFoundError,
)
from floe_polaris.factory import create_catalog

# Test scope - use a least-privilege role for testing
TEST_SCOPE = "PRINCIPAL_ROLE:DATA_ENGINEER"


@pytest.fixture
def mock_rest_catalog() -> MagicMock:
    """Create a mock RestCatalog."""
    return MagicMock()


@pytest.fixture
def basic_config() -> PolarisCatalogConfig:
    """Create basic config without credentials."""
    return PolarisCatalogConfig(
        uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        scope=TEST_SCOPE,
    )


@pytest.fixture
def oauth_config() -> PolarisCatalogConfig:
    """Create config with OAuth2 credentials."""
    return PolarisCatalogConfig(
        uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        client_id="test_client",
        client_secret="test_secret",
        scope=TEST_SCOPE,
    )


@pytest.fixture
def token_config() -> PolarisCatalogConfig:
    """Create config with bearer token."""
    return PolarisCatalogConfig(
        uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        scope=TEST_SCOPE,
        token="test_bearer_token",
    )


class TestPolarisCatalogInit:
    """Tests for PolarisCatalog initialization."""

    @patch("floe_polaris.client.RestCatalog")
    def test_basic_initialization(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test basic catalog initialization without credentials."""
        catalog = PolarisCatalog(basic_config)

        assert catalog.config == basic_config
        assert catalog.is_connected()
        mock_rest_catalog_cls.assert_called_once()

    @patch("floe_polaris.client.RestCatalog")
    def test_oauth2_initialization(
        self, mock_rest_catalog_cls: MagicMock, oauth_config: PolarisCatalogConfig
    ) -> None:
        """Test catalog initialization with OAuth2 credentials."""
        _catalog = PolarisCatalog(oauth_config)  # noqa: F841

        # Verify credential was passed
        call_kwargs = mock_rest_catalog_cls.call_args.kwargs
        assert "credential" in call_kwargs
        assert call_kwargs["credential"] == "test_client:test_secret"
        assert call_kwargs["scope"] == TEST_SCOPE

    @patch("floe_polaris.client.RestCatalog")
    def test_oauth2_token_refresh_enabled_by_default(
        self, mock_rest_catalog_cls: MagicMock, oauth_config: PolarisCatalogConfig
    ) -> None:
        """Test token-refresh-enabled is passed to PyIceberg by default.

        PyIceberg's RestCatalog handles OAuth2 token refresh automatically
        when this property is set to 'true'.
        """
        _catalog = PolarisCatalog(oauth_config)  # noqa: F841

        call_kwargs = mock_rest_catalog_cls.call_args.kwargs
        assert call_kwargs.get("token-refresh-enabled") == "true"

    @patch("floe_polaris.client.RestCatalog")
    def test_oauth2_token_refresh_disabled(self, mock_rest_catalog_cls: MagicMock) -> None:
        """Test token-refresh-enabled is not passed when disabled."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
            client_id="test_client",
            client_secret="test_secret",
            scope=TEST_SCOPE,
            token_refresh_enabled=False,
        )
        _catalog = PolarisCatalog(config)  # noqa: F841

        call_kwargs = mock_rest_catalog_cls.call_args.kwargs
        assert "token-refresh-enabled" not in call_kwargs

    @patch("floe_polaris.client.RestCatalog")
    def test_token_initialization(
        self, mock_rest_catalog_cls: MagicMock, token_config: PolarisCatalogConfig
    ) -> None:
        """Test catalog initialization with bearer token."""
        _catalog = PolarisCatalog(token_config)  # noqa: F841

        call_kwargs = mock_rest_catalog_cls.call_args.kwargs
        assert "token" in call_kwargs
        assert call_kwargs["token"] == "test_bearer_token"

    @patch("floe_polaris.client.RestCatalog")
    def test_access_delegation_header(self, mock_rest_catalog_cls: MagicMock) -> None:
        """Test access delegation header is set when access_delegation is configured."""
        # Create config with explicit access_delegation
        config_with_delegation = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
            scope=TEST_SCOPE,
            access_delegation="vended-credentials",
        )
        PolarisCatalog(config_with_delegation)

        call_kwargs = mock_rest_catalog_cls.call_args.kwargs
        assert call_kwargs["header.X-Iceberg-Access-Delegation"] == "vended-credentials"

    @patch("floe_polaris.client.RestCatalog")
    def test_connection_error_handling(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test connection error is converted to CatalogConnectionError."""
        mock_rest_catalog_cls.side_effect = Exception("Connection refused")

        with pytest.raises(CatalogConnectionError) as exc_info:
            PolarisCatalog(basic_config)

        assert "Failed to connect" in str(exc_info.value)
        assert exc_info.value.uri == basic_config.uri

    @patch("floe_polaris.client.RestCatalog")
    def test_auth_error_401_handling(
        self, mock_rest_catalog_cls: MagicMock, oauth_config: PolarisCatalogConfig
    ) -> None:
        """Test 401 error is converted to CatalogAuthenticationError.

        Note: For security, CatalogAuthenticationError does not expose
        client_id or scope to prevent information leakage.
        """
        mock_rest_catalog_cls.side_effect = Exception("401 Unauthorized")

        with pytest.raises(CatalogAuthenticationError) as exc_info:
            PolarisCatalog(oauth_config)

        assert "Authentication failed" in str(exc_info.value)
        # Security: client_id is NOT exposed in exception
        assert "test_client" not in str(exc_info.value)


class TestPolarisCatalogConnectionManagement:
    """Tests for connection management methods."""

    @patch("floe_polaris.client.RestCatalog")
    def test_is_connected_true(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test is_connected returns True when connected."""
        catalog = PolarisCatalog(basic_config)

        assert catalog.is_connected() is True

    @patch("floe_polaris.client.RestCatalog")
    def test_reconnect_creates_new_catalog(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test reconnect creates a new catalog connection."""
        catalog = PolarisCatalog(basic_config)
        assert mock_rest_catalog_cls.call_count == 1

        catalog.reconnect()
        assert mock_rest_catalog_cls.call_count == 2

    @patch("floe_polaris.client.RestCatalog")
    def test_inner_catalog_property(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test inner_catalog property returns underlying catalog."""
        mock_inner = MagicMock()
        mock_rest_catalog_cls.return_value = mock_inner

        catalog = PolarisCatalog(basic_config)
        assert catalog.inner_catalog is mock_inner


class TestPolarisCatalogNamespaceOperations:
    """Tests for namespace operations."""

    @patch("floe_polaris.client.RestCatalog")
    def test_list_namespaces_empty(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing namespaces returns empty list."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = []
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces()

        assert result == []
        mock_catalog.list_namespaces.assert_called_once_with(())

    @patch("floe_polaris.client.RestCatalog")
    def test_list_namespaces_with_results(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing namespaces with results."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = [("bronze",), ("silver",)]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces()

        assert len(result) == 2
        assert result[0].name == "bronze"
        assert result[1].name == "silver"

    @patch("floe_polaris.client.RestCatalog")
    def test_list_namespaces_with_parent(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing namespaces with parent filter."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = [("bronze", "raw")]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces("bronze")

        mock_catalog.list_namespaces.assert_called_with(("bronze",))
        assert len(result) == 1
        assert result[0].name == "bronze.raw"

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating a namespace."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace("bronze", {"owner": "data_team"})

        assert result.name == "bronze"
        assert result.properties == {"owner": "data_team"}
        mock_catalog.create_namespace.assert_called_with(("bronze",), {"owner": "data_team"})

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace_already_exists(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating namespace that already exists raises error."""
        from pyiceberg.exceptions import NamespaceAlreadyExistsError

        mock_catalog = MagicMock()
        mock_catalog.create_namespace.side_effect = NamespaceAlreadyExistsError("bronze")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceExistsError) as exc_info:
            catalog.create_namespace("bronze", create_parents=False)

        assert exc_info.value.namespace == "bronze"

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace_if_not_exists_creates(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test idempotent namespace creation."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace_if_not_exists("bronze")

        assert result.name == "bronze"

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace_if_not_exists_returns_existing(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test idempotent creation returns existing namespace."""
        from pyiceberg.exceptions import NamespaceAlreadyExistsError

        mock_catalog = MagicMock()
        mock_catalog.create_namespace.side_effect = NamespaceAlreadyExistsError("bronze")
        mock_catalog.load_namespace_properties.return_value = {"owner": "existing"}
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace_if_not_exists("bronze")

        assert result.name == "bronze"
        assert result.properties == {"owner": "existing"}

    @patch("floe_polaris.client.RestCatalog")
    def test_load_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading namespace properties."""
        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.return_value = {"owner": "data_team"}
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.load_namespace("bronze")

        assert result.name == "bronze"
        assert result.properties == {"owner": "data_team"}

    @patch("floe_polaris.client.RestCatalog")
    def test_load_namespace_not_found(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading non-existent namespace raises error."""
        from pyiceberg.exceptions import NoSuchNamespaceError

        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.side_effect = NoSuchNamespaceError("bronze")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceNotFoundError) as exc_info:
            catalog.load_namespace("bronze")

        assert exc_info.value.namespace == "bronze"

    @patch("floe_polaris.client.RestCatalog")
    def test_drop_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test dropping a namespace."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        catalog.drop_namespace("bronze")

        mock_catalog.drop_namespace.assert_called_once_with(("bronze",))


class TestPolarisCatalogTableOperations:
    """Tests for table operations."""

    @patch("floe_polaris.client.RestCatalog")
    def test_load_table(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading a table."""
        mock_table = MagicMock()
        mock_catalog = MagicMock()
        mock_catalog.load_table.return_value = mock_table
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.load_table("bronze.customers")

        assert result is mock_table
        mock_catalog.load_table.assert_called_once_with("bronze.customers")

    @patch("floe_polaris.client.RestCatalog")
    def test_load_table_not_found(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading non-existent table raises error."""
        from pyiceberg.exceptions import NoSuchTableError

        mock_catalog = MagicMock()
        mock_catalog.load_table.side_effect = NoSuchTableError("bronze.customers")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(TableNotFoundError) as exc_info:
            catalog.load_table("bronze.customers")

        assert exc_info.value.table == "bronze.customers"

    @patch("floe_polaris.client.RestCatalog")
    def test_table_exists_true(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test table_exists returns True for existing table."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.table_exists("bronze.customers")

        assert result is True

    @patch("floe_polaris.client.RestCatalog")
    def test_table_exists_false(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test table_exists returns False for non-existent table."""
        from pyiceberg.exceptions import NoSuchTableError

        mock_catalog = MagicMock()
        mock_catalog.load_table.side_effect = NoSuchTableError("bronze.customers")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.table_exists("bronze.customers")

        assert result is False

    @patch("floe_polaris.client.RestCatalog")
    def test_list_tables(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing tables in a namespace."""
        mock_catalog = MagicMock()
        mock_catalog.list_tables.return_value = [
            ("bronze", "customers"),
            ("bronze", "orders"),
        ]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_tables("bronze")

        assert result == ["bronze.customers", "bronze.orders"]


class TestCreateCatalogFactory:
    """Tests for create_catalog factory function."""

    @patch("floe_polaris.factory.PolarisCatalog")
    def test_create_catalog_with_polaris_config(
        self, mock_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test factory with PolarisCatalogConfig."""
        mock_catalog = MagicMock()
        mock_catalog_cls.return_value = mock_catalog

        result = create_catalog(basic_config)

        assert result is mock_catalog
        mock_catalog_cls.assert_called_once_with(basic_config)

    @patch("floe_polaris.factory.PolarisCatalog")
    def test_create_catalog_with_generic_config(self, mock_catalog_cls: MagicMock) -> None:
        """Test factory with generic CatalogConfig-like object (legacy pattern)."""
        # Create a mock that looks like a legacy CatalogConfig
        # Use spec to limit attributes - legacy config has uri/warehouse but NOT credentials/get_uri

        class LegacyCatalogConfig:
            """Mock legacy config structure (no credentials/get_uri attributes)."""

            uri: str
            warehouse: str
            client_id: str | None
            client_secret: str | None
            token: str | None
            scope: str | None

        generic_config = MagicMock(spec=LegacyCatalogConfig)
        generic_config.uri = "http://localhost:8181/api/catalog"
        generic_config.warehouse = "test_warehouse"
        generic_config.client_id = None
        generic_config.client_secret = None
        generic_config.token = None
        generic_config.scope = TEST_SCOPE  # Scope is required

        mock_catalog = MagicMock()
        mock_catalog_cls.return_value = mock_catalog

        result = create_catalog(generic_config)

        assert result is mock_catalog
        # Verify PolarisCatalogConfig was created from generic config
        call_args = mock_catalog_cls.call_args[0][0]
        assert isinstance(call_args, PolarisCatalogConfig)
        assert call_args.uri == "http://localhost:8181/api/catalog"
        assert call_args.warehouse == "test_warehouse"
        assert call_args.scope == TEST_SCOPE

    def test_create_catalog_with_missing_scope(self) -> None:
        """Test factory with missing scope raises ValueError (security: least privilege)."""
        # Create a mock that looks like a legacy CatalogConfig without scope
        # Use spec to limit attributes - legacy config has uri/warehouse but NOT credentials/get_uri

        class LegacyCatalogConfig:
            """Mock legacy config structure (no credentials/get_uri attributes)."""

            uri: str
            warehouse: str
            client_id: str | None
            client_secret: str | None
            token: str | None
            scope: str | None

        generic_config = MagicMock(spec=LegacyCatalogConfig)
        generic_config.uri = "http://localhost:8181/api/catalog"
        generic_config.warehouse = "test_warehouse"
        generic_config.client_id = None
        generic_config.client_secret = None
        generic_config.token = None
        generic_config.scope = None  # Missing scope

        with pytest.raises(ValueError) as exc_info:
            create_catalog(generic_config)

        assert "scope is required" in str(exc_info.value)

    def test_create_catalog_with_invalid_config(self) -> None:
        """Test factory with invalid config raises ValueError."""
        invalid_config = {"not": "a config"}

        with pytest.raises(ValueError) as exc_info:
            create_catalog(invalid_config)

        assert "Unsupported config type" in str(exc_info.value)

    @patch("floe_polaris.factory.PolarisCatalog")
    def test_create_catalog_with_catalog_profile(self, mock_catalog_cls: MagicMock) -> None:
        """Test factory with CatalogProfile (two-tier architecture)."""
        # Create a mock that looks like a CatalogProfile with credentials

        class MockCredentialConfig:
            """Mock CredentialConfig structure."""

            scope: str | None
            client_id: str | None
            client_secret: object | None

        class MockCatalogProfile:
            """Mock CatalogProfile structure with get_uri and credentials."""

            warehouse: str
            credentials: MockCredentialConfig
            access_delegation: object | None
            token_refresh_enabled: bool | None

            def get_uri(self) -> str:
                """Return the catalog URI."""
                return ""

        # Create the profile mock with spec
        profile = MagicMock(spec=MockCatalogProfile)
        profile.get_uri.return_value = "http://localhost:8181/api/catalog"
        profile.warehouse = "test_warehouse"
        profile.token_refresh_enabled = True

        # Create credentials mock
        creds = MagicMock(spec=MockCredentialConfig)
        creds.scope = TEST_SCOPE
        creds.client_id = "test_client"
        creds.client_secret = None
        profile.credentials = creds

        # No access_delegation
        profile.access_delegation = None

        mock_catalog = MagicMock()
        mock_catalog_cls.return_value = mock_catalog

        result = create_catalog(profile)

        assert result is mock_catalog
        # Verify PolarisCatalogConfig was created from CatalogProfile
        call_args = mock_catalog_cls.call_args[0][0]
        assert isinstance(call_args, PolarisCatalogConfig)
        assert call_args.uri == "http://localhost:8181/api/catalog"
        assert call_args.warehouse == "test_warehouse"
        assert call_args.scope == TEST_SCOPE
        assert call_args.client_id == "test_client"
        assert call_args.token_refresh_enabled is True

    def test_create_catalog_profile_missing_scope(self) -> None:
        """Test CatalogProfile without scope raises ValueError."""

        class MockCredentialConfig:
            """Mock CredentialConfig structure."""

            scope: str | None
            client_id: str | None
            client_secret: object | None

        class MockCatalogProfile:
            """Mock CatalogProfile structure."""

            warehouse: str
            credentials: MockCredentialConfig

            def get_uri(self) -> str:
                """Return the catalog URI."""
                return ""

        profile = MagicMock(spec=MockCatalogProfile)
        profile.get_uri.return_value = "http://localhost:8181/api/catalog"
        profile.warehouse = "test_warehouse"

        # Credentials without scope
        creds = MagicMock(spec=MockCredentialConfig)
        creds.scope = None  # Missing scope
        creds.client_id = None
        creds.client_secret = None
        profile.credentials = creds

        with pytest.raises(ValueError) as exc_info:
            create_catalog(profile)

        assert "scope is required" in str(exc_info.value)

    @patch("floe_polaris.factory.PolarisCatalog")
    def test_create_catalog_profile_with_access_delegation(
        self, mock_catalog_cls: MagicMock
    ) -> None:
        """Test CatalogProfile with access_delegation is converted."""

        class MockAccessDelegation:
            """Mock AccessDelegation enum."""

            value: str

        class MockCredentialConfig:
            """Mock CredentialConfig structure."""

            scope: str | None
            client_id: str | None
            client_secret: object | None

        class MockCatalogProfile:
            """Mock CatalogProfile structure."""

            warehouse: str
            credentials: MockCredentialConfig
            access_delegation: MockAccessDelegation | None

            def get_uri(self) -> str:
                """Return the catalog URI."""
                return ""

        profile = MagicMock(spec=MockCatalogProfile)
        profile.get_uri.return_value = "http://localhost:8181/api/catalog"
        profile.warehouse = "test_warehouse"

        # Credentials with scope
        creds = MagicMock(spec=MockCredentialConfig)
        creds.scope = TEST_SCOPE
        creds.client_id = None
        creds.client_secret = None
        profile.credentials = creds

        # Access delegation enum
        access_delegation = MagicMock(spec=MockAccessDelegation)
        access_delegation.value = "vended-credentials"
        profile.access_delegation = access_delegation

        mock_catalog = MagicMock()
        mock_catalog_cls.return_value = mock_catalog

        result = create_catalog(profile)

        assert result is mock_catalog
        call_args = mock_catalog_cls.call_args[0][0]
        assert call_args.access_delegation == "vended-credentials"


class TestNormalizeNamespace:
    """Tests for namespace normalization helper."""

    @patch("floe_polaris.client.RestCatalog")
    def test_string_namespace_normalized(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test string namespace is converted to tuple."""
        result = PolarisCatalog._normalize_namespace("bronze.raw")
        assert result == ("bronze", "raw")

    @patch("floe_polaris.client.RestCatalog")
    def test_tuple_namespace_unchanged(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test tuple namespace is returned unchanged."""
        result = PolarisCatalog._normalize_namespace(("bronze", "raw"))
        assert result == ("bronze", "raw")

    @patch("floe_polaris.client.RestCatalog")
    def test_none_namespace_empty_tuple(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test None namespace returns empty tuple."""
        result = PolarisCatalog._normalize_namespace(None)
        assert result == ()
