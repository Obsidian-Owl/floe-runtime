# floe-polaris API Contract

**Package**: floe-polaris
**Version**: 0.1.0
**Date**: 2025-12-17

## Overview

This document defines the public API contract for the floe-polaris package. The package provides a thin wrapper over PyIceberg's RestCatalog with added observability, retry policies, and configuration management.

---

## Public API

### Module: `floe_polaris`

#### `create_catalog`

Factory function to create a configured Polaris catalog client.

```python
def create_catalog(
    config: PolarisCatalogConfig | CatalogConfig,
) -> PolarisCatalog:
    """Create a Polaris catalog client from configuration.

    Args:
        config: Catalog configuration (PolarisCatalogConfig or CatalogConfig from floe-core).

    Returns:
        PolarisCatalog: Configured catalog client with retry and observability.

    Raises:
        CatalogConnectionError: If connection cannot be established.
        CatalogAuthenticationError: If authentication fails.

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
```

---

### Class: `PolarisCatalog`

Wrapper around PyIceberg's RestCatalog with observability and retry policies.

#### Constructor

```python
class PolarisCatalog:
    """Polaris catalog client with observability and retry support.

    This class wraps PyIceberg's RestCatalog and adds:
    - Configurable retry policies with exponential backoff
    - Structured logging via structlog
    - OpenTelemetry span tracing
    - Automatic token refresh

    Attributes:
        config: Catalog configuration.
        retry_config: Retry policy configuration.

    Note:
        Use create_catalog() factory function instead of direct instantiation.
    """

    def __init__(
        self,
        config: PolarisCatalogConfig,
        *,
        tracer: Tracer | None = None,
        logger: BoundLogger | None = None,
    ) -> None: ...
```

#### Namespace Operations

```python
def create_namespace(
    self,
    namespace: str | tuple[str, ...],
    properties: dict[str, str] | None = None,
    *,
    create_parents: bool = True,
) -> NamespaceInfo:
    """Create a namespace in the catalog.

    Args:
        namespace: Namespace name (string or tuple for nested).
        properties: Optional namespace properties.
        create_parents: If True, create parent namespaces if they don't exist.

    Returns:
        NamespaceInfo: Created namespace information.

    Raises:
        NamespaceExistsError: If namespace already exists and not idempotent.
        CatalogConnectionError: If catalog is unreachable.

    Example:
        >>> catalog.create_namespace("bronze.raw", {"owner": "data_team"})
        NamespaceInfo(name='bronze.raw', properties={'owner': 'data_team'})
    """

def create_namespace_if_not_exists(
    self,
    namespace: str | tuple[str, ...],
    properties: dict[str, str] | None = None,
) -> NamespaceInfo:
    """Create namespace if it doesn't exist (idempotent).

    Args:
        namespace: Namespace name.
        properties: Optional namespace properties.

    Returns:
        NamespaceInfo: Namespace information (created or existing).
    """

def list_namespaces(
    self,
    parent: str | tuple[str, ...] | None = None,
) -> list[NamespaceInfo]:
    """List namespaces in the catalog.

    Args:
        parent: Optional parent namespace to list children of.
            If None, lists top-level namespaces.

    Returns:
        List of NamespaceInfo objects.

    Example:
        >>> catalog.list_namespaces()
        [NamespaceInfo(name='bronze'), NamespaceInfo(name='silver')]
        >>> catalog.list_namespaces("bronze")
        [NamespaceInfo(name='bronze.raw'), NamespaceInfo(name='bronze.staging')]
    """

def load_namespace(
    self,
    namespace: str | tuple[str, ...],
) -> NamespaceInfo:
    """Load namespace information.

    Args:
        namespace: Namespace name.

    Returns:
        NamespaceInfo: Namespace information with properties.

    Raises:
        NamespaceNotFoundError: If namespace doesn't exist.
    """

def drop_namespace(
    self,
    namespace: str | tuple[str, ...],
) -> None:
    """Drop an empty namespace.

    Args:
        namespace: Namespace name to drop.

    Raises:
        NamespaceNotEmptyError: If namespace contains tables.
        NamespaceNotFoundError: If namespace doesn't exist.
    """

def update_namespace_properties(
    self,
    namespace: str | tuple[str, ...],
    updates: dict[str, str] | None = None,
    removals: set[str] | None = None,
) -> NamespaceInfo:
    """Update namespace properties.

    Args:
        namespace: Namespace name.
        updates: Properties to add or update.
        removals: Property keys to remove.

    Returns:
        Updated NamespaceInfo.
    """
```

#### Table Operations (delegated to PyIceberg)

```python
def load_table(
    self,
    identifier: str | TableIdentifier,
) -> Table:
    """Load an Iceberg table.

    Args:
        identifier: Table identifier (string or TableIdentifier).

    Returns:
        PyIceberg Table object.

    Raises:
        TableNotFoundError: If table doesn't exist.
    """

def table_exists(
    self,
    identifier: str | TableIdentifier,
) -> bool:
    """Check if a table exists.

    Args:
        identifier: Table identifier.

    Returns:
        True if table exists.
    """

def list_tables(
    self,
    namespace: str | tuple[str, ...],
) -> list[str]:
    """List tables in a namespace.

    Args:
        namespace: Namespace name.

    Returns:
        List of table names.
    """
```

#### Connection Management

```python
def is_connected(self) -> bool:
    """Check if catalog connection is active."""

def reconnect(self) -> None:
    """Force reconnection to catalog (refreshes token)."""

@property
def inner_catalog(self) -> Catalog:
    """Access the underlying PyIceberg Catalog object."""
```

---

### Class: `RetryConfig`

```python
class RetryConfig(BaseModel):
    """Retry policy configuration.

    Attributes:
        max_attempts: Maximum retry attempts (1-10, default 3).
        initial_wait_seconds: Initial backoff wait (0.1-30s, default 1.0).
        max_wait_seconds: Maximum backoff cap (1-300s, default 30.0).
        jitter_seconds: Random jitter range (0-10s, default 1.0).
        circuit_breaker_threshold: Failures before circuit opens (default 5, 0=disabled).
    """

    max_attempts: int = 3
    initial_wait_seconds: float = 1.0
    max_wait_seconds: float = 30.0
    jitter_seconds: float = 1.0
    circuit_breaker_threshold: int = 5
```

---

### Class: `PolarisCatalogConfig`

```python
class PolarisCatalogConfig(BaseModel):
    """Polaris catalog configuration.

    Attributes:
        uri: Polaris REST API endpoint.
        warehouse: Warehouse name.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        token: Pre-fetched bearer token (alternative to client credentials).
        scope: OAuth2 scope (default "PRINCIPAL_ROLE:ALL").
        token_refresh_enabled: Enable automatic token refresh (default True).
        access_delegation: Iceberg access delegation mode (default "vended-credentials").
        retry: Retry policy configuration.
    """

    uri: str
    warehouse: str
    client_id: str | None = None
    client_secret: SecretStr | None = None
    token: SecretStr | None = None
    scope: str = "PRINCIPAL_ROLE:ALL"
    token_refresh_enabled: bool = True
    access_delegation: str = "vended-credentials"
    retry: RetryConfig = Field(default_factory=RetryConfig)
```

---

### Exceptions

```python
class FloeStorageError(Exception):
    """Base exception for storage operations."""

class CatalogConnectionError(FloeStorageError):
    """Failed to connect to catalog."""

class CatalogAuthenticationError(FloeStorageError):
    """Authentication failed."""

class NamespaceExistsError(FloeStorageError):
    """Namespace already exists."""

class NamespaceNotFoundError(FloeStorageError):
    """Namespace not found."""

class NamespaceNotEmptyError(FloeStorageError):
    """Cannot drop non-empty namespace."""

class TableNotFoundError(FloeStorageError):
    """Table not found in catalog."""
```

---

## Usage Examples

### Basic Connection

```python
from floe_polaris import create_catalog, PolarisCatalogConfig

config = PolarisCatalogConfig(
    uri="http://localhost:8181/api/catalog",
    warehouse="my_warehouse",
    client_id="my_client",
    client_secret="my_secret",
)

catalog = create_catalog(config)
```

### Namespace Management

```python
# Create nested namespace
catalog.create_namespace("bronze.raw.events", {"owner": "team_a"})

# List all namespaces
for ns in catalog.list_namespaces():
    print(f"{ns.name}: {ns.properties}")

# Idempotent creation
catalog.create_namespace_if_not_exists("bronze")
```

### With Custom Retry Policy

```python
from floe_polaris import PolarisCatalogConfig, RetryConfig

config = PolarisCatalogConfig(
    uri="http://localhost:8181/api/catalog",
    warehouse="my_warehouse",
    client_id="my_client",
    client_secret="my_secret",
    retry=RetryConfig(
        max_attempts=5,
        initial_wait_seconds=0.5,
        max_wait_seconds=60.0,
    ),
)
```

### From floe-core CatalogConfig

```python
from floe_core.schemas import CatalogConfig
from floe_polaris import create_catalog

# CatalogConfig from CompiledArtifacts
core_config = CatalogConfig(
    type="polaris",
    uri="http://localhost:8181/api/catalog",
    warehouse="my_warehouse",
    credential_secret_ref="polaris-credentials",
)

# create_catalog accepts both types
catalog = create_catalog(core_config)
```
