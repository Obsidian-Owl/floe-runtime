"""Unit tests for LayerResolver.

Tests layer configuration resolution from platform.yaml into fully resolved
layer configurations with complete storage and catalog profile bindings.
"""

from __future__ import annotations

import pytest

from floe_core.compiler.layer_resolver import LayerResolver, ResolvedLayerConfig
from floe_core.schemas import (
    CatalogProfile,
    LayerConfig,
    PlatformSpec,
    StorageProfile,
)


class TestResolvedLayerConfig:
    """Tests for ResolvedLayerConfig model."""

    def test_resolved_layer_config_creation(self) -> None:
        """Test ResolvedLayerConfig can be created with full profiles."""
        storage = StorageProfile(bucket="iceberg-bronze")
        catalog = CatalogProfile(
            uri="http://localhost:8181/api/catalog",
            warehouse="demo_catalog",
        )

        resolved = ResolvedLayerConfig(
            name="bronze",
            storage=storage,
            catalog=catalog,
            namespace="demo_catalog.bronze",
            retention_days=2555,
            properties={"owner": "data-engineering"},
        )

        assert resolved.name == "bronze"
        assert resolved.storage.bucket == "iceberg-bronze"
        assert resolved.catalog.warehouse == "demo_catalog"
        assert resolved.namespace == "demo_catalog.bronze"
        assert resolved.retention_days == 2555
        assert resolved.properties["owner"] == "data-engineering"

    def test_resolved_layer_config_frozen(self) -> None:
        """Test ResolvedLayerConfig is immutable."""
        from pydantic import ValidationError

        storage = StorageProfile(bucket="iceberg-bronze")
        catalog = CatalogProfile(
            uri="http://localhost:8181/api/catalog",
            warehouse="demo_catalog",
        )

        resolved = ResolvedLayerConfig(
            name="bronze",
            storage=storage,
            catalog=catalog,
            namespace="demo_catalog.bronze",
        )

        with pytest.raises(ValidationError, match="Instance is frozen"):
            resolved.name = "silver"  # type: ignore[misc]

    def test_resolved_layer_config_optional_retention(self) -> None:
        """Test ResolvedLayerConfig with None retention_days."""
        storage = StorageProfile(bucket="iceberg-bronze")
        catalog = CatalogProfile(
            uri="http://localhost:8181/api/catalog",
            warehouse="demo_catalog",
        )

        resolved = ResolvedLayerConfig(
            name="bronze",
            storage=storage,
            catalog=catalog,
            namespace="demo_catalog.bronze",
        )

        assert resolved.retention_days is None


class TestLayerResolverResolveAll:
    """Tests for LayerResolver.resolve_all() method."""

    def test_resolve_all_with_medallion_layers(self) -> None:
        """Test resolve_all() with bronze/silver/gold layers."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={
                "bronze": StorageProfile(bucket="iceberg-bronze"),
                "silver": StorageProfile(bucket="iceberg-silver"),
                "gold": StorageProfile(bucket="iceberg-gold"),
            },
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    catalog_ref="default",
                    namespace="demo_catalog.bronze",
                    retention_days=2555,
                ),
                "silver": LayerConfig(
                    name="silver",
                    storage_ref="silver",
                    namespace="demo_catalog.silver",
                    retention_days=730,
                ),
                "gold": LayerConfig(
                    name="gold",
                    storage_ref="gold",
                    namespace="demo_catalog.gold",
                    retention_days=365,
                ),
            },
        )

        resolver = LayerResolver()
        resolved = resolver.resolve_all(platform)

        assert len(resolved) == 3
        assert "bronze" in resolved
        assert "silver" in resolved
        assert "gold" in resolved

        # Verify bronze resolution
        bronze = resolved["bronze"]
        assert bronze.name == "bronze"
        assert bronze.storage.bucket == "iceberg-bronze"
        assert bronze.catalog.warehouse == "demo_catalog"
        assert bronze.namespace == "demo_catalog.bronze"
        assert bronze.retention_days == 2555

    def test_resolve_all_with_flexible_layer_names(self) -> None:
        """Test resolve_all() supports flexible layer names."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={
                "raw": StorageProfile(bucket="iceberg-raw"),
                "curated": StorageProfile(bucket="iceberg-curated"),
            },
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "raw": LayerConfig(
                    name="raw",
                    storage_ref="raw",
                    namespace="demo_catalog.raw",
                ),
                "curated": LayerConfig(
                    name="curated",
                    storage_ref="curated",
                    namespace="demo_catalog.curated",
                ),
            },
        )

        resolver = LayerResolver()
        resolved = resolver.resolve_all(platform)

        assert len(resolved) == 2
        assert "raw" in resolved
        assert "curated" in resolved
        assert resolved["raw"].storage.bucket == "iceberg-raw"
        assert resolved["curated"].storage.bucket == "iceberg-curated"

    def test_resolve_all_with_empty_layers(self) -> None:
        """Test resolve_all() returns empty dict when no layers defined."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={"default": StorageProfile(bucket="test-bucket")},
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={},  # No layers
        )

        resolver = LayerResolver()
        resolved = resolver.resolve_all(platform)

        assert resolved == {}

    def test_resolve_all_preserves_properties(self) -> None:
        """Test resolve_all() preserves layer properties."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={"bronze": StorageProfile(bucket="iceberg-bronze")},
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    namespace="demo_catalog.bronze",
                    properties={
                        "owner": "data-engineering",
                        "sensitivity": "internal",
                        "compliance": "SOC2",
                    },
                ),
            },
        )

        resolver = LayerResolver()
        resolved = resolver.resolve_all(platform)

        bronze = resolved["bronze"]
        assert bronze.properties["owner"] == "data-engineering"
        assert bronze.properties["sensitivity"] == "internal"
        assert bronze.properties["compliance"] == "SOC2"

    def test_resolve_all_with_multiple_catalog_profiles(self) -> None:
        """Test resolve_all() resolves different catalog profiles per layer."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={
                "bronze": StorageProfile(bucket="iceberg-bronze"),
                "gold": StorageProfile(bucket="iceberg-gold"),
            },
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                ),
                "analytics": CatalogProfile(
                    uri="http://analytics:8181/api/catalog",
                    warehouse="analytics_catalog",
                ),
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    catalog_ref="default",
                    namespace="demo_catalog.bronze",
                ),
                "gold": LayerConfig(
                    name="gold",
                    storage_ref="gold",
                    catalog_ref="analytics",
                    namespace="analytics_catalog.gold",
                ),
            },
        )

        resolver = LayerResolver()
        resolved = resolver.resolve_all(platform)

        assert resolved["bronze"].catalog.warehouse == "demo_catalog"
        assert resolved["gold"].catalog.warehouse == "analytics_catalog"


class TestLayerResolverResolveLayer:
    """Tests for LayerResolver.resolve_layer() method."""

    def test_resolve_layer_by_name(self) -> None:
        """Test resolve_layer() resolves single layer by name."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={"bronze": StorageProfile(bucket="iceberg-bronze")},
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    namespace="demo_catalog.bronze",
                    retention_days=2555,
                ),
            },
        )

        resolver = LayerResolver()
        bronze = resolver.resolve_layer("bronze", platform)

        assert bronze is not None
        assert bronze.name == "bronze"
        assert bronze.storage.bucket == "iceberg-bronze"
        assert bronze.retention_days == 2555

    def test_resolve_layer_nonexistent_returns_none(self) -> None:
        """Test resolve_layer() returns None for non-existent layer."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={"bronze": StorageProfile(bucket="iceberg-bronze")},
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    namespace="demo_catalog.bronze",
                ),
            },
        )

        resolver = LayerResolver()
        result = resolver.resolve_layer("nonexistent", platform)

        assert result is None

    def test_resolve_layer_with_properties(self) -> None:
        """Test resolve_layer() preserves layer properties."""
        platform = PlatformSpec(
            version="1.2.0",
            storage={"bronze": StorageProfile(bucket="iceberg-bronze")},
            catalogs={
                "default": CatalogProfile(
                    uri="http://localhost:8181/api/catalog",
                    warehouse="demo_catalog",
                )
            },
            compute={},
            layers={
                "bronze": LayerConfig(
                    name="bronze",
                    storage_ref="bronze",
                    namespace="demo_catalog.bronze",
                    properties={"owner": "data-engineering"},
                ),
            },
        )

        resolver = LayerResolver()
        bronze = resolver.resolve_layer("bronze", platform)

        assert bronze is not None
        assert bronze.properties["owner"] == "data-engineering"
