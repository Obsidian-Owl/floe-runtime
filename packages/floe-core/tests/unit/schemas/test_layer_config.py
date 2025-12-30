"""Unit tests for data layer configuration models.

This module tests:
- LayerConfig parsing and validation
- Layer name validation (flexible naming)
- Namespace format validation
- Retention days validation
- Storage and catalog reference validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_core.schemas.layer_config import LayerConfig


class TestLayerConfigCreation:
    """Tests for LayerConfig creation and validation."""

    def test_minimal_layer_config_valid(self) -> None:
        """Minimal LayerConfig with required fields is valid."""
        layer = LayerConfig(
            name="bronze",
            storage_ref="bronze",
            namespace="demo_catalog.bronze",
        )
        assert layer.name == "bronze"
        assert layer.storage_ref == "bronze"
        assert layer.catalog_ref == "default"  # Default value
        assert layer.namespace == "demo_catalog.bronze"
        assert layer.description == ""  # Default empty
        assert layer.retention_days is None  # Default None
        assert layer.properties == {}  # Default empty dict

    def test_full_layer_config_valid(self) -> None:
        """LayerConfig with all fields populated."""
        layer = LayerConfig(
            name="bronze",
            description="Raw and lightly cleaned data",
            storage_ref="bronze",
            catalog_ref="polaris",
            namespace="demo_catalog.bronze",
            retention_days=2555,  # 7 years
            properties={"owner": "data-engineering", "sensitivity": "internal"},
        )
        assert layer.name == "bronze"
        assert layer.description == "Raw and lightly cleaned data"
        assert layer.storage_ref == "bronze"
        assert layer.catalog_ref == "polaris"
        assert layer.namespace == "demo_catalog.bronze"
        assert layer.retention_days == 2555
        assert layer.properties["owner"] == "data-engineering"
        assert layer.properties["sensitivity"] == "internal"

    def test_layer_config_frozen(self) -> None:
        """LayerConfig is frozen (immutable)."""
        layer = LayerConfig(name="bronze", storage_ref="bronze", namespace="demo.bronze")
        with pytest.raises(ValidationError, match="Instance is frozen"):
            layer.name = "silver"  # type: ignore[misc]


class TestLayerNameValidation:
    """Tests for layer name validation (flexible naming)."""

    @pytest.mark.parametrize(
        "layer_name",
        [
            "bronze",  # Medallion
            "silver",
            "gold",
            "raw",  # Alternative
            "curated",
            "analytics",
            "landing",  # Staging pattern
            "staging",
            "production",
            "layer_1",  # With underscore
            "my-layer",  # With hyphen
            "dataLayer123",  # Alphanumeric
        ],
    )
    def test_valid_layer_names(self, layer_name: str) -> None:
        """Valid layer names accepted (flexible naming)."""
        layer = LayerConfig(name=layer_name, storage_ref="storage1", namespace="demo.layer")
        assert layer.name == layer_name

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "123invalid",  # Starts with number
            "-invalid",  # Starts with hyphen
            "_invalid",  # Starts with underscore
            "invalid space",  # Contains space
            "invalid.dot",  # Contains dot
            "invalid/slash",  # Contains slash
            "",  # Empty string
        ],
    )
    def test_invalid_layer_names(self, invalid_name: str) -> None:
        """Invalid layer names rejected."""
        with pytest.raises(ValidationError):
            LayerConfig(name=invalid_name, storage_ref="storage1", namespace="demo.layer")


class TestNamespaceValidation:
    """Tests for namespace format validation."""

    @pytest.mark.parametrize(
        "valid_namespace",
        [
            "demo_catalog.bronze",  # Standard medallion
            "prod.silver",  # Short warehouse
            "warehouse123.gold",  # Alphanumeric warehouse
            "demo.raw",  # Alternative naming
            "prod.curated.zone1",  # Multi-level namespace
        ],
    )
    def test_valid_namespace_formats(self, valid_namespace: str) -> None:
        """Valid namespace formats accepted."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace=valid_namespace)
        assert layer.namespace == valid_namespace

    @pytest.mark.parametrize(
        "invalid_namespace",
        [
            "bronze",  # Missing warehouse prefix
            "nocatalog",  # No dot separator
            "BRONZE",  # Just layer name
        ],
    )
    def test_invalid_namespace_formats(self, invalid_namespace: str) -> None:
        """Invalid namespace formats rejected."""
        with pytest.raises(
            ValidationError, match="Catalog namespace must include warehouse prefix"
        ):
            LayerConfig(name="bronze", storage_ref="storage1", namespace=invalid_namespace)


class TestRetentionDaysValidation:
    """Tests for retention_days validation."""

    @pytest.mark.parametrize(
        "retention_days",
        [
            1,  # Minimum (1 day)
            30,  # Short retention
            365,  # 1 year
            730,  # 2 years (silver)
            2555,  # 7 years (bronze compliance)
            36500,  # Maximum (100 years)
        ],
    )
    def test_valid_retention_days(self, retention_days: int) -> None:
        """Valid retention days accepted."""
        layer = LayerConfig(
            name="bronze",
            storage_ref="storage1",
            namespace="demo.bronze",
            retention_days=retention_days,
        )
        assert layer.retention_days == retention_days

    def test_retention_days_optional(self) -> None:
        """retention_days is optional (None by default)."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        assert layer.retention_days is None

    @pytest.mark.parametrize(
        "invalid_days",
        [
            0,  # Too small
            -1,  # Negative
            36501,  # Exceeds max (100 years)
            100000,  # Way too large
        ],
    )
    def test_invalid_retention_days(self, invalid_days: int) -> None:
        """Invalid retention days rejected."""
        with pytest.raises(ValidationError):
            LayerConfig(
                name="bronze",
                storage_ref="storage1",
                namespace="demo.bronze",
                retention_days=invalid_days,
            )


class TestStorageAndCatalogReferences:
    """Tests for storage_ref and catalog_ref validation."""

    def test_storage_ref_required(self) -> None:
        """storage_ref is required."""
        with pytest.raises(ValidationError, match="Field required"):
            LayerConfig(name="bronze", namespace="demo.bronze")  # type: ignore[call-arg]

    def test_catalog_ref_defaults_to_default(self) -> None:
        """catalog_ref defaults to 'default'."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        assert layer.catalog_ref == "default"

    @pytest.mark.parametrize(
        "storage_ref",
        ["bronze", "silver", "gold", "my-storage", "storage_1", "s3Backend"],
    )
    def test_valid_storage_refs(self, storage_ref: str) -> None:
        """Valid storage_ref names accepted."""
        layer = LayerConfig(name="bronze", storage_ref=storage_ref, namespace="demo.bronze")
        assert layer.storage_ref == storage_ref

    @pytest.mark.parametrize(
        "invalid_ref",
        ["123invalid", "-invalid", "_invalid", "invalid space"],
    )
    def test_invalid_storage_refs(self, invalid_ref: str) -> None:
        """Invalid storage_ref names rejected."""
        with pytest.raises(ValidationError):
            LayerConfig(name="bronze", storage_ref=invalid_ref, namespace="demo.bronze")


class TestLayerProperties:
    """Tests for layer properties dict."""

    def test_empty_properties_default(self) -> None:
        """Properties default to empty dict."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        assert layer.properties == {}

    def test_properties_with_values(self) -> None:
        """Properties can store arbitrary key-value pairs."""
        properties = {
            "owner": "data-engineering",
            "sensitivity": "confidential",
            "compliance": "SOC2,GDPR",
            "layer": "bronze",
        }
        layer = LayerConfig(
            name="bronze", storage_ref="storage1", namespace="demo.bronze", properties=properties
        )
        assert layer.properties == properties
        assert layer.properties["owner"] == "data-engineering"
        assert layer.properties["sensitivity"] == "confidential"
        assert layer.properties["compliance"] == "SOC2,GDPR"


class TestLayerConfigImmutability:
    """Tests for LayerConfig immutability (frozen)."""

    def test_cannot_modify_name(self) -> None:
        """Cannot modify name after creation."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        with pytest.raises(ValidationError, match="Instance is frozen"):
            layer.name = "silver"  # type: ignore[misc]

    def test_cannot_modify_storage_ref(self) -> None:
        """Cannot modify storage_ref after creation."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        with pytest.raises(ValidationError, match="Instance is frozen"):
            layer.storage_ref = "storage2"  # type: ignore[misc]

    def test_cannot_add_properties(self) -> None:
        """Cannot modify properties dict after creation."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        with pytest.raises(ValidationError, match="Instance is frozen"):
            layer.properties["new_key"] = "value"  # type: ignore[index]


class TestLayerConfigDescription:
    """Tests for layer description field."""

    def test_description_default_empty(self) -> None:
        """Description defaults to empty string."""
        layer = LayerConfig(name="bronze", storage_ref="storage1", namespace="demo.bronze")
        assert layer.description == ""

    def test_description_can_be_set(self) -> None:
        """Description can be set during creation."""
        layer = LayerConfig(
            name="bronze",
            description="Raw and lightly cleaned data for audit compliance",
            storage_ref="storage1",
            namespace="demo.bronze",
        )
        assert layer.description == "Raw and lightly cleaned data for audit compliance"

    def test_description_max_length(self) -> None:
        """Description has max length of 500 characters."""
        long_desc = "x" * 500  # Exactly 500 chars
        layer = LayerConfig(
            name="bronze", description=long_desc, storage_ref="storage1", namespace="demo.bronze"
        )
        assert len(layer.description) == 500

        # Exceeds max
        too_long = "x" * 501
        with pytest.raises(ValidationError, match="String should have at most 500 characters"):
            LayerConfig(
                name="bronze", description=too_long, storage_ref="storage1", namespace="demo.bronze"
            )
