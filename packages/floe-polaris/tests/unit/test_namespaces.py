"""Unit tests for namespace operations.

Tests for:
- T045: create_namespace tests
- T046: list_namespaces tests
- T047: create_namespace_if_not_exists tests
- T048: nested namespace handling tests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_polaris.client import PolarisCatalog
from floe_polaris.config import PolarisCatalogConfig
from floe_polaris.errors import (
    NamespaceExistsError,
    NamespaceNotEmptyError,
    NamespaceNotFoundError,
)

# Test scope - use a least-privilege role for testing
TEST_SCOPE = "PRINCIPAL_ROLE:DATA_ENGINEER"


@pytest.fixture
def basic_config() -> PolarisCatalogConfig:
    """Create basic config with scope (required for security)."""
    return PolarisCatalogConfig(
        uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        scope=TEST_SCOPE,
    )


class TestCreateNamespace:
    """Tests for create_namespace method (T045)."""

    @patch("floe_polaris.client.RestCatalog")
    def test_create_simple_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating a simple namespace."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace("bronze")

        assert result.name == "bronze"
        assert result.properties == {}
        mock_catalog.create_namespace.assert_called_with(("bronze",), {})

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace_with_properties(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating a namespace with properties."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        properties = {"owner": "data_team", "description": "Raw data layer"}
        result = catalog.create_namespace("bronze", properties)

        assert result.name == "bronze"
        assert result.properties == properties
        mock_catalog.create_namespace.assert_called_with(("bronze",), properties)

    @patch("floe_polaris.client.RestCatalog")
    def test_create_namespace_as_tuple(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating a namespace using tuple format."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace(("bronze", "raw"))

        assert result.name == "bronze.raw"
        mock_catalog.create_namespace.assert_called()

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
        assert "already exists" in str(exc_info.value)


class TestListNamespaces:
    """Tests for list_namespaces method (T046)."""

    @patch("floe_polaris.client.RestCatalog")
    def test_list_empty_namespaces(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing namespaces returns empty list when none exist."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = []
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces()

        assert result == []
        mock_catalog.list_namespaces.assert_called_once_with(())

    @patch("floe_polaris.client.RestCatalog")
    def test_list_top_level_namespaces(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing top-level namespaces."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = [
            ("bronze",),
            ("silver",),
            ("gold",),
        ]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces()

        assert len(result) == 3
        names = [ns.name for ns in result]
        assert "bronze" in names
        assert "silver" in names
        assert "gold" in names

    @patch("floe_polaris.client.RestCatalog")
    def test_list_child_namespaces(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing child namespaces under a parent."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = [
            ("bronze", "raw"),
            ("bronze", "staging"),
        ]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces("bronze")

        mock_catalog.list_namespaces.assert_called_with(("bronze",))
        assert len(result) == 2
        assert result[0].name == "bronze.raw"
        assert result[1].name == "bronze.staging"

    @patch("floe_polaris.client.RestCatalog")
    def test_list_namespaces_parent_as_tuple(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test listing namespaces with parent specified as tuple."""
        mock_catalog = MagicMock()
        mock_catalog.list_namespaces.return_value = [("bronze", "raw", "events")]
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.list_namespaces(("bronze", "raw"))

        mock_catalog.list_namespaces.assert_called_with(("bronze", "raw"))
        assert len(result) == 1
        assert result[0].name == "bronze.raw.events"


class TestCreateNamespaceIfNotExists:
    """Tests for create_namespace_if_not_exists method (T047)."""

    @patch("floe_polaris.client.RestCatalog")
    def test_creates_new_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating a new namespace that doesn't exist."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace_if_not_exists("bronze")

        assert result.name == "bronze"
        mock_catalog.create_namespace.assert_called_once()

    @patch("floe_polaris.client.RestCatalog")
    def test_returns_existing_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test returns existing namespace when it already exists."""
        from pyiceberg.exceptions import NamespaceAlreadyExistsError

        mock_catalog = MagicMock()
        mock_catalog.create_namespace.side_effect = NamespaceAlreadyExistsError("bronze")
        mock_catalog.load_namespace_properties.return_value = {"owner": "existing_owner"}
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace_if_not_exists("bronze")

        assert result.name == "bronze"
        assert result.properties == {"owner": "existing_owner"}

    @patch("floe_polaris.client.RestCatalog")
    def test_idempotent_multiple_calls(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test multiple calls are idempotent."""
        from pyiceberg.exceptions import NamespaceAlreadyExistsError

        mock_catalog = MagicMock()
        # First call succeeds, subsequent calls fail with already exists
        mock_catalog.create_namespace.side_effect = [
            None,  # First call succeeds
            NamespaceAlreadyExistsError("bronze"),  # Second call fails
        ]
        mock_catalog.load_namespace_properties.return_value = {}
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        # Both calls should succeed without raising
        result1 = catalog.create_namespace_if_not_exists("bronze")
        result2 = catalog.create_namespace_if_not_exists("bronze")

        assert result1.name == "bronze"
        assert result2.name == "bronze"


class TestNestedNamespaceHandling:
    """Tests for nested namespace handling (T048)."""

    @patch("floe_polaris.client.RestCatalog")
    def test_create_nested_namespace_creates_parents(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating nested namespace creates parents automatically."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace("bronze.raw.events", create_parents=True)

        assert result.name == "bronze.raw.events"
        # Should attempt to create parent namespaces
        calls = mock_catalog.create_namespace.call_args_list
        assert len(calls) >= 1  # At least the final namespace

    @patch("floe_polaris.client.RestCatalog")
    def test_create_nested_namespace_without_parents(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating nested namespace without creating parents."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        catalog.create_namespace("bronze.raw", create_parents=False)

        # Should only call create_namespace once for the target
        mock_catalog.create_namespace.assert_called_once_with(("bronze", "raw"), {})

    @patch("floe_polaris.client.RestCatalog")
    def test_deeply_nested_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test creating deeply nested namespace."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace("a.b.c.d.e")

        assert result.name == "a.b.c.d.e"

    @patch("floe_polaris.client.RestCatalog")
    def test_namespace_parts_property(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test NamespaceInfo.parts property returns correct tuple."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.create_namespace("bronze.raw.events")

        assert result.parts == ("bronze", "raw", "events")


class TestLoadNamespace:
    """Tests for load_namespace method."""

    @patch("floe_polaris.client.RestCatalog")
    def test_load_existing_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading an existing namespace."""
        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.return_value = {
            "owner": "data_team",
            "location": "s3://bucket/bronze",
        }
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.load_namespace("bronze")

        assert result.name == "bronze"
        assert result.properties["owner"] == "data_team"
        assert result.properties["location"] == "s3://bucket/bronze"

    @patch("floe_polaris.client.RestCatalog")
    def test_load_nonexistent_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test loading a non-existent namespace raises error."""
        from pyiceberg.exceptions import NoSuchNamespaceError

        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.side_effect = NoSuchNamespaceError("nonexistent")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceNotFoundError) as exc_info:
            catalog.load_namespace("nonexistent")

        assert exc_info.value.namespace == "nonexistent"


class TestDropNamespace:
    """Tests for drop_namespace method."""

    @patch("floe_polaris.client.RestCatalog")
    def test_drop_empty_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test dropping an empty namespace."""
        mock_catalog = MagicMock()
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        catalog.drop_namespace("bronze")

        mock_catalog.drop_namespace.assert_called_once_with(("bronze",))

    @patch("floe_polaris.client.RestCatalog")
    def test_drop_nonexistent_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test dropping a non-existent namespace raises error."""
        from pyiceberg.exceptions import NoSuchNamespaceError

        mock_catalog = MagicMock()
        mock_catalog.drop_namespace.side_effect = NoSuchNamespaceError("nonexistent")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceNotFoundError):
            catalog.drop_namespace("nonexistent")

    @patch("floe_polaris.client.RestCatalog")
    def test_drop_non_empty_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test dropping a non-empty namespace raises error."""
        from pyiceberg.exceptions import NamespaceNotEmptyError as PyIcebergNotEmpty

        mock_catalog = MagicMock()
        mock_catalog.drop_namespace.side_effect = PyIcebergNotEmpty("bronze")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceNotEmptyError) as exc_info:
            catalog.drop_namespace("bronze")

        assert exc_info.value.namespace == "bronze"


class TestUpdateNamespaceProperties:
    """Tests for update_namespace_properties method."""

    @patch("floe_polaris.client.RestCatalog")
    def test_update_properties(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test updating namespace properties."""
        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.return_value = {
            "owner": "new_owner",
            "description": "Updated description",
        }
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        result = catalog.update_namespace_properties(
            "bronze",
            updates={"owner": "new_owner", "description": "Updated description"},
        )

        mock_catalog.update_namespace_properties.assert_called_once()
        assert result.properties["owner"] == "new_owner"

    @patch("floe_polaris.client.RestCatalog")
    def test_remove_properties(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test removing namespace properties."""
        mock_catalog = MagicMock()
        mock_catalog.load_namespace_properties.return_value = {"owner": "data_team"}
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)
        catalog.update_namespace_properties("bronze", removals={"deprecated_key"})

        call_args = mock_catalog.update_namespace_properties.call_args
        assert call_args.kwargs["removals"] == {"deprecated_key"}

    @patch("floe_polaris.client.RestCatalog")
    def test_update_nonexistent_namespace(
        self, mock_rest_catalog_cls: MagicMock, basic_config: PolarisCatalogConfig
    ) -> None:
        """Test updating properties of non-existent namespace raises error."""
        from pyiceberg.exceptions import NoSuchNamespaceError

        mock_catalog = MagicMock()
        mock_catalog.update_namespace_properties.side_effect = NoSuchNamespaceError("nonexistent")
        mock_rest_catalog_cls.return_value = mock_catalog

        catalog = PolarisCatalog(basic_config)

        with pytest.raises(NamespaceNotFoundError):
            catalog.update_namespace_properties("nonexistent", updates={"key": "value"})
