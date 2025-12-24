"""Unit tests for catalog resources.

T097: [US6] Add unit tests for CatalogResource and PolarisCatalogResource
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from floe_dagster.resources.catalog import (
    CatalogProtocol,
    CatalogResource,
    PolarisCatalogResource,
)


class TestCatalogProtocol:
    """Test CatalogProtocol definition."""

    def test_catalog_protocol_is_runtime_checkable(self) -> None:
        """Test that CatalogProtocol is runtime checkable."""
        # Create a mock that implements the protocol
        mock_catalog = MagicMock()
        mock_catalog.load_table = MagicMock()
        mock_catalog.table_exists = MagicMock()
        mock_catalog.list_tables = MagicMock()
        mock_catalog.inner_catalog = MagicMock()

        # Should pass isinstance check
        assert isinstance(mock_catalog, CatalogProtocol)

    def test_catalog_protocol_requires_load_table(self) -> None:
        """Test that CatalogProtocol requires load_table method."""
        mock = MagicMock()
        del mock.load_table  # Remove the method

        # Should not satisfy protocol
        assert not isinstance(mock, CatalogProtocol)


class TestCatalogResource:
    """Test CatalogResource abstract base class."""

    def test_catalog_resource_is_abstract(self) -> None:
        """Test that CatalogResource cannot be instantiated directly."""
        # CatalogResource requires get_catalog implementation
        with pytest.raises(TypeError):
            CatalogResource()  # type: ignore[abstract]

    def test_catalog_resource_delegates_to_get_catalog(self) -> None:
        """Test that methods delegate to get_catalog()."""
        # Test by directly calling methods on a PolarisCatalogResource with mocked catalog

        resource = PolarisCatalogResource(
            uri="http://polaris:8181/api/catalog",
            warehouse="demo_catalog",
        )

        mock_catalog = MagicMock()
        mock_catalog.load_table.return_value = "table"
        mock_catalog.table_exists.return_value = True
        mock_catalog.list_tables.return_value = ["table1", "table2"]
        mock_catalog.inner_catalog = "inner"

        # Patch the _catalog attribute directly
        resource._catalog = mock_catalog

        assert resource.load_table("test") == "table"
        assert resource.table_exists("test") is True
        assert resource.list_tables("ns") == ["table1", "table2"]
        assert resource.inner_catalog == "inner"


class TestPolarisCatalogResourceConfig:
    """Test PolarisCatalogResource configuration."""

    def test_polaris_resource_requires_uri_and_warehouse(self) -> None:
        """Test that PolarisCatalogResource requires uri and warehouse."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PolarisCatalogResource()  # type: ignore[call-arg]

    def test_polaris_resource_with_minimal_config(self) -> None:
        """Test PolarisCatalogResource with minimal configuration."""
        resource = PolarisCatalogResource(
            uri="http://polaris:8181/api/catalog",
            warehouse="demo_catalog",
        )
        assert resource.uri == "http://polaris:8181/api/catalog"
        assert resource.warehouse == "demo_catalog"
        assert resource.client_id is None
        assert resource.client_secret is None
        assert resource.scope == "PRINCIPAL_ROLE:ALL"

    def test_polaris_resource_with_full_config(self) -> None:
        """Test PolarisCatalogResource with full configuration."""
        resource = PolarisCatalogResource(
            uri="http://polaris:8181/api/catalog",
            warehouse="demo_catalog",
            client_id="my_client",
            client_secret="my_secret",
            scope="PRINCIPAL_ROLE:DATA_ENGINEER",
            s3_endpoint="http://localstack:4566",
            s3_region="us-west-2",
            s3_path_style_access=True,
            s3_access_key_id="test-key",
            s3_secret_access_key="test-secret",
        )
        assert resource.uri == "http://polaris:8181/api/catalog"
        assert resource.warehouse == "demo_catalog"
        assert resource.client_id == "my_client"
        assert resource.client_secret == "my_secret"
        assert resource.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"
        assert resource.s3_endpoint == "http://localstack:4566"
        assert resource.s3_region == "us-west-2"
        assert resource.s3_path_style_access is True
        assert resource.s3_access_key_id == "test-key"


class TestPolarisCatalogResourceSecretResolution:
    """Test secret resolution in PolarisCatalogResource."""

    def test_resolve_value_returns_direct_value(self) -> None:
        """Test that _resolve_value returns direct values unchanged."""
        result = PolarisCatalogResource._resolve_value("my_value")
        assert result == "my_value"

    def test_resolve_value_returns_none_for_none(self) -> None:
        """Test that _resolve_value returns None for None input."""
        result = PolarisCatalogResource._resolve_value(None)
        assert result is None

    def test_resolve_value_resolves_env_var_reference(self) -> None:
        """Test that _resolve_value resolves $VAR_NAME references."""
        with patch.dict(os.environ, {"TEST_VAR": "resolved_value"}):
            result = PolarisCatalogResource._resolve_value("$TEST_VAR")
            assert result == "resolved_value"

    def test_resolve_value_returns_empty_for_missing_env_var(self) -> None:
        """Test that _resolve_value returns empty string for missing env var."""
        # Ensure the env var doesn't exist
        os.environ.pop("NONEXISTENT_VAR", None)
        result = PolarisCatalogResource._resolve_value("$NONEXISTENT_VAR")
        assert result == ""

    def test_resolve_value_resolves_secret_ref_pattern(self) -> None:
        """Test that _resolve_value resolves secret_ref:NAME references."""
        with patch.dict(os.environ, {"MY_SECRET": "secret_value"}):
            result = PolarisCatalogResource._resolve_value("secret_ref:MY_SECRET")
            assert result == "secret_value"

    def test_resolve_value_returns_empty_for_missing_secret_ref(self) -> None:
        """Test that _resolve_value returns empty for missing secret_ref."""
        os.environ.pop("MISSING_SECRET", None)
        result = PolarisCatalogResource._resolve_value("secret_ref:MISSING_SECRET")
        assert result == ""


class TestPolarisCatalogResourceGetCatalog:
    """Test PolarisCatalogResource.get_catalog() method."""

    @patch("floe_polaris.client.PolarisCatalog")
    @patch("floe_polaris.config.PolarisCatalogConfig")
    def test_get_catalog_creates_polaris_catalog(
        self,
        mock_config_class: MagicMock,
        mock_polaris_catalog: MagicMock,
    ) -> None:
        """Test that get_catalog creates a PolarisCatalog instance."""
        mock_config_instance = MagicMock()
        mock_config_class.return_value = mock_config_instance
        mock_catalog_instance = MagicMock()
        mock_polaris_catalog.return_value = mock_catalog_instance

        resource = PolarisCatalogResource(
            uri="http://polaris:8181/api/catalog",
            warehouse="demo_catalog",
            client_id="test_client",
            client_secret="test_secret",
        )

        catalog = resource.get_catalog()

        # Config should be created with resolved values
        mock_config_class.assert_called_once()
        call_kwargs = mock_config_class.call_args[1]
        assert call_kwargs["uri"] == "http://polaris:8181/api/catalog"
        assert call_kwargs["warehouse"] == "demo_catalog"
        assert call_kwargs["client_id"] == "test_client"

        # PolarisCatalog should be created with config
        mock_polaris_catalog.assert_called_once_with(mock_config_instance)

        assert catalog == mock_catalog_instance

    @patch("floe_polaris.client.PolarisCatalog")
    @patch("floe_polaris.config.PolarisCatalogConfig")
    def test_get_catalog_caches_instance(
        self,
        mock_config_class: MagicMock,
        mock_polaris_catalog: MagicMock,
    ) -> None:
        """Test that get_catalog caches the catalog instance."""
        mock_catalog_instance = MagicMock()
        mock_polaris_catalog.return_value = mock_catalog_instance

        resource = PolarisCatalogResource(
            uri="http://polaris:8181/api/catalog",
            warehouse="demo_catalog",
        )

        # Call twice
        catalog1 = resource.get_catalog()
        catalog2 = resource.get_catalog()

        # Should only create once
        assert mock_polaris_catalog.call_count == 1
        assert catalog1 is catalog2

    @patch("floe_polaris.client.PolarisCatalog")
    @patch("floe_polaris.config.PolarisCatalogConfig")
    def test_get_catalog_resolves_env_var_credentials(
        self,
        mock_config_class: MagicMock,
        mock_polaris_catalog: MagicMock,
    ) -> None:
        """Test that get_catalog resolves env var references in credentials."""
        with patch.dict(
            os.environ,
            {"POLARIS_CLIENT_ID": "env_client", "POLARIS_SECRET": "env_secret"},
        ):
            resource = PolarisCatalogResource(
                uri="http://polaris:8181/api/catalog",
                warehouse="demo_catalog",
                client_id="$POLARIS_CLIENT_ID",
                client_secret="$POLARIS_SECRET",
            )

            resource.get_catalog()

            call_kwargs = mock_config_class.call_args[1]
            assert call_kwargs["client_id"] == "env_client"
            # client_secret is resolved and wrapped in SecretStr
            assert call_kwargs["client_secret"].get_secret_value() == "env_secret"


class TestPolarisCatalogResourceFromCompiledArtifacts:
    """Test PolarisCatalogResource.from_compiled_artifacts()."""

    def test_from_compiled_artifacts_v2_format(self) -> None:
        """Test creation from v2 CompiledArtifacts format."""
        artifacts: dict[str, Any] = {
            "resolved_catalog": {
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "demo_catalog",
                "credentials": {
                    "client_id": "demo_engineer",
                    "client_secret": "secret_value",
                    "scope": "PRINCIPAL_ROLE:DATA_ENGINEER",
                },
                "s3_endpoint": "http://localstack:4566",
                "s3_region": "us-west-2",
                "s3_path_style_access": True,
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)

        assert resource.uri == "http://polaris:8181/api/catalog"
        assert resource.warehouse == "demo_catalog"
        assert resource.client_id == "demo_engineer"
        assert resource.client_secret == "secret_value"
        assert resource.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"
        assert resource.s3_endpoint == "http://localstack:4566"
        assert resource.s3_region == "us-west-2"
        assert resource.s3_path_style_access is True

    def test_from_compiled_artifacts_v1_format(self) -> None:
        """Test creation from v1 CompiledArtifacts format (catalogs dict)."""
        artifacts: dict[str, Any] = {
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "my_warehouse",
                    "credentials": {
                        "client_id": "client1",
                        "client_secret": "secret1",
                    },
                },
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)

        assert resource.uri == "http://polaris:8181/api/catalog"
        assert resource.warehouse == "my_warehouse"
        assert resource.client_id == "client1"

    def test_from_compiled_artifacts_with_secret_ref(self) -> None:
        """Test creation with secret_ref pattern in credentials."""
        artifacts: dict[str, Any] = {
            "resolved_catalog": {
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "demo_catalog",
                "credentials": {
                    "client_id": {"secret_ref": "POLARIS_CLIENT_ID"},
                    "client_secret": {"secret_ref": "POLARIS_CLIENT_SECRET"},
                },
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)

        assert resource.client_id == "secret_ref:POLARIS_CLIENT_ID"
        assert resource.client_secret == "secret_ref:POLARIS_CLIENT_SECRET"

    def test_from_compiled_artifacts_with_custom_profile(self) -> None:
        """Test creation with non-default profile name."""
        artifacts: dict[str, Any] = {
            "catalogs": {
                "production": {
                    "uri": "http://prod-polaris:8181/api/catalog",
                    "warehouse": "prod_warehouse",
                    "credentials": {},
                },
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(
            artifacts, profile_name="production"
        )

        assert resource.uri == "http://prod-polaris:8181/api/catalog"
        assert resource.warehouse == "prod_warehouse"

    def test_from_compiled_artifacts_with_empty_credentials(self) -> None:
        """Test creation when credentials section is empty."""
        artifacts: dict[str, Any] = {
            "resolved_catalog": {
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "demo_catalog",
                "credentials": {},
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)

        assert resource.uri == "http://polaris:8181/api/catalog"
        assert resource.warehouse == "demo_catalog"
        assert resource.client_id is None
        assert resource.client_secret is None

    def test_from_compiled_artifacts_defaults_scope(self) -> None:
        """Test that scope defaults to PRINCIPAL_ROLE:ALL."""
        artifacts: dict[str, Any] = {
            "resolved_catalog": {
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "demo_catalog",
                "credentials": {},
            },
        }

        resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)

        assert resource.scope == "PRINCIPAL_ROLE:ALL"


class TestCatalogTypeAlias:
    """Test the Catalog type alias."""

    def test_catalog_is_alias_for_catalog_resource(self) -> None:
        """Test that Catalog is an alias for CatalogResource."""
        from floe_dagster.resources.catalog import Catalog

        # Should be the same type
        assert Catalog is CatalogResource
