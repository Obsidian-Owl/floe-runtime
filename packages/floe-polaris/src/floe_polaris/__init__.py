"""floe-polaris: Apache Polaris catalog integration for floe-runtime.

This package provides a thin wrapper over PyIceberg's RestCatalog with:
- Configurable retry policies with exponential backoff
- Structured logging via structlog
- OpenTelemetry span tracing
- OAuth2 authentication with automatic token refresh

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
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API exports
# Note: Actual implementations are in Phase 2. These are forward declarations.
__all__ = [
    # Factory function
    "create_catalog",
    # Client class
    "PolarisCatalog",
    # Configuration models
    "PolarisCatalogConfig",
    "RetryConfig",
    # Data models
    "NamespaceInfo",
    # Exceptions
    "FloeStorageError",
    "CatalogConnectionError",
    "CatalogAuthenticationError",
    "NamespaceExistsError",
    "NamespaceNotFoundError",
    "NamespaceNotEmptyError",
    "TableNotFoundError",
]

# Lazy imports to avoid circular dependencies and allow gradual implementation
# These will be populated as Phase 2 tasks are completed


def __getattr__(name: str) -> object:
    """Lazy import of public API members."""
    if name == "create_catalog":
        from floe_polaris.factory import create_catalog

        return create_catalog
    if name == "PolarisCatalog":
        from floe_polaris.client import PolarisCatalog

        return PolarisCatalog
    if name in ("PolarisCatalogConfig", "RetryConfig"):
        from floe_polaris import config as config_module

        return getattr(config_module, name)
    if name == "NamespaceInfo":
        from floe_polaris import config as config_module

        return getattr(config_module, name)
    if name in (
        "FloeStorageError",
        "CatalogConnectionError",
        "CatalogAuthenticationError",
        "NamespaceExistsError",
        "NamespaceNotFoundError",
        "NamespaceNotEmptyError",
        "TableNotFoundError",
    ):
        from floe_polaris import errors as errors_module

        return getattr(errors_module, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
