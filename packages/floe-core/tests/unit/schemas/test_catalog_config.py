"""Unit tests for CatalogConfig model.

T016: [US1] Unit tests for CatalogConfig validation
Tests CatalogConfig with Polaris OAuth2 fields and catalog types.
"""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError


class TestCatalogConfig:
    """Tests for CatalogConfig model."""

    def test_catalog_config_requires_type(self) -> None:
        """CatalogConfig should require type field."""
        from floe_core.schemas import CatalogConfig

        with pytest.raises(ValidationError) as exc_info:
            CatalogConfig(uri="http://polaris:8181")  # type: ignore[call-arg]

        assert "type" in str(exc_info.value)

    def test_catalog_config_requires_uri(self) -> None:
        """CatalogConfig should require uri field."""
        from floe_core.schemas import CatalogConfig

        with pytest.raises(ValidationError) as exc_info:
            CatalogConfig(type="polaris")  # type: ignore[call-arg]

        assert "uri" in str(exc_info.value)

    def test_catalog_config_type_polaris(self) -> None:
        """CatalogConfig should accept 'polaris' type."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
        )
        catalog_type: Literal["polaris", "glue", "nessie"] = config.type
        assert catalog_type == "polaris"

    def test_catalog_config_type_glue(self) -> None:
        """CatalogConfig should accept 'glue' type."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="glue",
            uri="arn:aws:glue:us-east-1:123456789:catalog",
        )
        assert config.type == "glue"

    def test_catalog_config_type_nessie(self) -> None:
        """CatalogConfig should accept 'nessie' type."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="nessie",
            uri="http://nessie:19120/api/v2",
        )
        assert config.type == "nessie"

    def test_catalog_config_invalid_type(self) -> None:
        """CatalogConfig should reject invalid type."""
        from floe_core.schemas import CatalogConfig

        with pytest.raises(ValidationError) as exc_info:
            CatalogConfig(
                type="invalid",  # type: ignore[arg-type]
                uri="http://invalid:8181",
            )

        assert "type" in str(exc_info.value)

    def test_catalog_config_credential_secret_ref_optional(self) -> None:
        """CatalogConfig.credential_secret_ref should be optional."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
        )
        assert config.credential_secret_ref is None

    def test_catalog_config_valid_credential_secret_ref(self) -> None:
        """CatalogConfig should accept valid credential_secret_ref."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            credential_secret_ref="polaris-credentials",
        )
        assert config.credential_secret_ref == "polaris-credentials"

    def test_catalog_config_invalid_credential_secret_ref(self) -> None:
        """CatalogConfig should reject invalid credential_secret_ref."""
        from floe_core.schemas import CatalogConfig

        with pytest.raises(ValidationError) as exc_info:
            CatalogConfig(
                type="polaris",
                uri="http://polaris:8181/api/catalog",
                credential_secret_ref="-invalid-start",
            )

        assert "credential_secret_ref" in str(exc_info.value)

    def test_catalog_config_warehouse_optional(self) -> None:
        """CatalogConfig.warehouse should be optional."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
        )
        assert config.warehouse is None

    def test_catalog_config_warehouse(self) -> None:
        """CatalogConfig should accept warehouse."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            warehouse="my_warehouse",
        )
        assert config.warehouse == "my_warehouse"

    def test_catalog_config_polaris_oauth2_scope(self) -> None:
        """CatalogConfig should accept Polaris OAuth2 scope."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            scope="PRINCIPAL_ROLE:ALL",
        )
        assert config.scope == "PRINCIPAL_ROLE:ALL"

    def test_catalog_config_polaris_token_refresh(self) -> None:
        """CatalogConfig should accept token_refresh_enabled."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            token_refresh_enabled=True,
        )
        assert config.token_refresh_enabled is True

    def test_catalog_config_polaris_access_delegation(self) -> None:
        """CatalogConfig should accept access_delegation."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            access_delegation="vended-credentials",
        )
        assert config.access_delegation == "vended-credentials"

    def test_catalog_config_polaris_full_oauth2(self) -> None:
        """CatalogConfig should accept full Polaris OAuth2 configuration."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            credential_secret_ref="polaris-oauth2-secret",
            warehouse="my_warehouse",
            scope="PRINCIPAL_ROLE:ALL",
            token_refresh_enabled=True,
            access_delegation="vended-credentials",
        )
        assert config.scope == "PRINCIPAL_ROLE:ALL"
        assert config.token_refresh_enabled is True
        assert config.access_delegation == "vended-credentials"

    def test_catalog_config_properties_default_empty(self) -> None:
        """CatalogConfig.properties should default to empty dict."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
        )
        assert config.properties == {}

    def test_catalog_config_properties_with_values(self) -> None:
        """CatalogConfig should accept custom properties."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="glue",
            uri="arn:aws:glue:us-east-1:123456789:catalog",
            properties={
                "region": "us-east-1",
                "catalog_id": "123456789",
            },
        )
        assert config.properties["region"] == "us-east-1"
        assert config.properties["catalog_id"] == "123456789"

    def test_catalog_config_nessie_properties(self) -> None:
        """CatalogConfig should accept Nessie-specific properties."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="nessie",
            uri="http://nessie:19120/api/v2",
            properties={
                "branch": "main",
                "hash": "abc123",
            },
        )
        assert config.properties["branch"] == "main"
        assert config.properties["hash"] == "abc123"

    def test_catalog_config_is_frozen(self) -> None:
        """CatalogConfig should be immutable."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
        )

        with pytest.raises(ValidationError):
            config.uri = "http://new-uri:8181"  # type: ignore[misc]

    def test_catalog_config_rejects_extra_fields(self) -> None:
        """CatalogConfig should reject unknown fields."""
        from floe_core.schemas import CatalogConfig

        with pytest.raises(ValidationError) as exc_info:
            CatalogConfig(
                type="polaris",
                uri="http://polaris:8181/api/catalog",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_catalog_config_default_factory_isolation(self) -> None:
        """CatalogConfig defaults should be isolated (no shared state)."""
        from floe_core.schemas import CatalogConfig

        config1 = CatalogConfig(type="polaris", uri="http://polaris:8181")
        config2 = CatalogConfig(type="polaris", uri="http://polaris:8181")

        # Verify they are independent objects
        assert config1 is not config2
        assert config1.properties is not config2.properties
