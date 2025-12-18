"""Catalog client factory.

This module provides the create_catalog() factory function for creating
configured PolarisCatalog instances from configuration objects.
"""

from __future__ import annotations

from typing import Any

from floe_polaris.client import PolarisCatalog
from floe_polaris.config import PolarisCatalogConfig
from floe_polaris.observability import catalog_operation, get_logger


def create_catalog(
    config: PolarisCatalogConfig | Any,
) -> PolarisCatalog:
    """Create a Polaris catalog client from configuration.

    This is the primary entry point for creating catalog connections.
    It accepts either a PolarisCatalogConfig or a CatalogConfig from floe-core.

    Args:
        config: Catalog configuration. Can be:
            - PolarisCatalogConfig: Native floe-polaris configuration
            - CatalogConfig: Configuration from floe-core CompiledArtifacts
              (will be converted to PolarisCatalogConfig)

    Returns:
        PolarisCatalog: Configured catalog client with retry and observability.

    Raises:
        CatalogConnectionError: If connection cannot be established.
        CatalogAuthenticationError: If authentication fails.
        ValueError: If config type is not supported.

    Example:
        >>> from floe_polaris import create_catalog, PolarisCatalogConfig
        >>> config = PolarisCatalogConfig(
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     client_id="my_client",
        ...     client_secret="my_secret",
        ... )
        >>> catalog = create_catalog(config)
        >>> namespaces = catalog.list_namespaces()

    Example with floe-core CatalogConfig:
        >>> from floe_core.schemas import CatalogConfig
        >>> from floe_polaris import create_catalog
        >>>
        >>> core_config = CatalogConfig(
        ...     type="polaris",
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ... )
        >>> catalog = create_catalog(core_config)
    """
    logger = get_logger()

    # Convert CatalogConfig to PolarisCatalogConfig if needed
    if isinstance(config, PolarisCatalogConfig):
        polaris_config = config
    else:
        polaris_config = _convert_catalog_config(config)

    with catalog_operation(
        "create_catalog",
        uri=polaris_config.uri,
        warehouse=polaris_config.warehouse,
    ):
        logger.info(
            "creating_catalog",
            uri=polaris_config.uri,
            warehouse=polaris_config.warehouse,
        )
        return PolarisCatalog(polaris_config)


def _convert_catalog_config(config: Any) -> PolarisCatalogConfig:
    """Convert a floe-core CatalogConfig to PolarisCatalogConfig.

    Args:
        config: A CatalogConfig-like object from floe-core.

    Returns:
        PolarisCatalogConfig: Converted configuration.

    Raises:
        ValueError: If conversion fails or config is not supported.
    """
    # Check if this looks like a CatalogConfig from floe-core
    if hasattr(config, "uri") and hasattr(config, "warehouse"):
        # Extract fields that exist
        kwargs: dict[str, Any] = {
            "uri": config.uri,
            "warehouse": config.warehouse,
        }

        # Optional fields
        if hasattr(config, "client_id") and config.client_id:
            kwargs["client_id"] = config.client_id

        if hasattr(config, "client_secret") and config.client_secret:
            kwargs["client_secret"] = config.client_secret

        if hasattr(config, "token") and config.token:
            kwargs["token"] = config.token

        if hasattr(config, "scope") and config.scope:
            kwargs["scope"] = config.scope

        return PolarisCatalogConfig(**kwargs)

    msg = (
        f"Unsupported config type: {type(config).__name__}. "
        "Expected PolarisCatalogConfig or CatalogConfig."
    )
    raise ValueError(msg)
