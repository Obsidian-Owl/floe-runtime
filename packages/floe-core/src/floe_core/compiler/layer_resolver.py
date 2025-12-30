"""Layer resolution for declarative medallion architecture.

This module resolves layer references from platform.yaml into fully resolved
layer configurations with complete storage and catalog profile bindings.

Covers: Declarative Layer Configuration (v1.2.0)
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.catalog_profile import CatalogProfile
from floe_core.schemas.platform_spec import PlatformSpec
from floe_core.schemas.storage_profile import StorageProfile

logger = logging.getLogger(__name__)


class ResolvedLayerConfig(BaseModel):
    """Resolved layer configuration with full profile bindings.

    Contains fully resolved storage and catalog profiles for a single layer,
    ready for consumption by floe-dagster. This model is included in
    CompiledArtifacts.resolved_layers.

    Attributes:
        name: Layer name (e.g., "bronze", "silver", "gold").
        storage: Fully resolved storage profile with bucket, endpoint, credentials.
        catalog: Fully resolved catalog profile with URI, warehouse, credentials.
        namespace: Catalog namespace for this layer (e.g., "demo_catalog.bronze").
        retention_days: Data retention policy in days (metadata only, not enforced).
        properties: Additional layer-specific properties (tags, owner, etc.).

    Example:
        >>> resolved = ResolvedLayerConfig(
        ...     name="bronze",
        ...     storage=StorageProfile(bucket="iceberg-bronze"),
        ...     catalog=CatalogProfile(
        ...         uri="http://polaris:8181/api/catalog",
        ...         warehouse="demo_catalog",
        ...     ),
        ...     namespace="demo_catalog.bronze",
        ...     retention_days=2555,
        ...     properties={"owner": "data-engineering"},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Layer name (e.g., bronze, silver, gold)",
    )
    storage: StorageProfile = Field(
        ...,
        description="Fully resolved storage profile for this layer",
    )
    catalog: CatalogProfile = Field(
        ...,
        description="Fully resolved catalog profile for this layer",
    )
    namespace: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Catalog namespace for this layer (e.g., demo_catalog.bronze)",
    )
    retention_days: int | None = Field(
        default=None,
        ge=1,
        le=36500,
        description="Data retention policy in days (metadata only, not enforced in v1.2.0)",
    )
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Additional layer-specific properties (tags, owner, etc.)",
    )


class LayerResolver:
    """Resolves layer references to full configurations.

    Resolves layer configurations from platform.yaml by looking up storage_ref
    and catalog_ref in the platform's storage and catalogs dicts, creating
    ResolvedLayerConfig objects with full profile bindings.

    Example:
        >>> platform = PlatformSpec.from_yaml(Path("platform/local/platform.yaml"))
        >>> resolver = LayerResolver()
        >>> resolved_layers = resolver.resolve_all(platform)
        >>> bronze = resolved_layers["bronze"]
        >>> bronze.storage.bucket
        'iceberg-bronze'
    """

    def resolve_all(self, platform: PlatformSpec) -> dict[str, ResolvedLayerConfig]:
        """Resolve all layers from platform.yaml.

        Args:
            platform: PlatformSpec with layers, storage, and catalogs configured.

        Returns:
            Dictionary mapping layer names to ResolvedLayerConfig objects.

        Example:
            >>> platform = PlatformSpec(
            ...     layers={
            ...         "bronze": LayerConfig(
            ...             name="bronze",
            ...             storage_ref="bronze",
            ...             catalog_ref="default",
            ...             namespace="demo.bronze",
            ...             retention_days=2555,
            ...         )
            ...     },
            ...     storage={
            ...         "bronze": StorageProfile(bucket="iceberg-bronze"),
            ...     },
            ...     catalogs={
            ...         "default": CatalogProfile(
            ...             uri="http://polaris:8181/api/catalog",
            ...             warehouse="demo",
            ...         ),
            ...     },
            ... )
            >>> resolver = LayerResolver()
            >>> resolved = resolver.resolve_all(platform)
            >>> resolved["bronze"].storage.bucket
            'iceberg-bronze'
        """
        resolved: dict[str, ResolvedLayerConfig] = {}

        if not platform.layers:
            logger.debug("No layers configured in platform.yaml")
            return resolved

        for layer_name, layer_config in platform.layers.items():
            # Resolve storage profile
            storage = platform.storage[layer_config.storage_ref]

            # Resolve catalog profile
            catalog = platform.catalogs[layer_config.catalog_ref]

            # Create resolved layer config
            resolved[layer_name] = ResolvedLayerConfig(
                name=layer_config.name,
                storage=storage,
                catalog=catalog,
                namespace=layer_config.namespace,
                retention_days=layer_config.retention_days,
                properties=layer_config.properties,
            )

            logger.debug(
                f"Resolved layer '{layer_name}': "
                f"storage={layer_config.storage_ref} (bucket={storage.bucket}), "
                f"catalog={layer_config.catalog_ref} (warehouse={catalog.warehouse}), "
                f"namespace={layer_config.namespace}"
            )

        logger.info(f"Resolved {len(resolved)} layer configurations")
        return resolved

    def resolve_layer(self, layer_name: str, platform: PlatformSpec) -> ResolvedLayerConfig | None:
        """Resolve a single layer by name.

        Args:
            layer_name: Name of the layer to resolve (e.g., "bronze").
            platform: PlatformSpec with layers, storage, and catalogs configured.

        Returns:
            ResolvedLayerConfig if layer exists, None otherwise.

        Example:
            >>> platform = PlatformSpec.from_yaml(Path("platform/local/platform.yaml"))
            >>> resolver = LayerResolver()
            >>> bronze = resolver.resolve_layer("bronze", platform)
            >>> bronze.retention_days
            2555
        """
        if layer_name not in platform.layers:
            logger.warning(f"Layer '{layer_name}' not found in platform.yaml")
            return None

        layer_config = platform.layers[layer_name]
        storage = platform.storage[layer_config.storage_ref]
        catalog = platform.catalogs[layer_config.catalog_ref]

        return ResolvedLayerConfig(
            name=layer_config.name,
            storage=storage,
            catalog=catalog,
            namespace=layer_config.namespace,
            retention_days=layer_config.retention_days,
            properties=layer_config.properties,
        )
