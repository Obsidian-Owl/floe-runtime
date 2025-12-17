# Research: Storage & Catalog Layer

**Feature**: 004-storage-catalog
**Date**: 2025-12-17
**Status**: Complete

## Overview

This document consolidates research findings for implementing the floe-iceberg and floe-polaris packages.

---

## 1. PyIceberg REST Catalog Integration

### Decision
Use PyIceberg's `RestCatalog` class to connect to Apache Polaris catalogs.

### Rationale
- PyIceberg 0.8+ provides native REST catalog support implementing the Iceberg REST Catalog specification
- RestCatalog handles OAuth2 token management, credential vending, and automatic token refresh
- Consistent with the Iceberg REST Catalog API standard (vendor-neutral)

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| Direct REST API calls | Would duplicate PyIceberg's tested implementation, more maintenance burden |
| SQLAlchemy-based catalog | Not applicable for Polaris (REST-only) |
| Custom catalog wrapper | Unnecessary abstraction over PyIceberg |

### Implementation Pattern

```python
from pyiceberg.catalog import load_catalog

# OAuth2 client credentials flow
catalog = load_catalog(
    "polaris",
    **{
        "type": "rest",
        "uri": config.uri,
        "warehouse": config.warehouse,
        "credential": f"{client_id}:{client_secret}",
        "scope": config.scope or "PRINCIPAL_ROLE:ALL",
        "token-refresh-enabled": "true",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    }
)

# Bearer token flow (pre-fetched)
catalog = load_catalog(
    "polaris",
    type="rest",
    uri=config.uri,
    warehouse=config.warehouse,
    token=bearer_token,
)
```

### Key PyIceberg APIs

| Operation | PyIceberg API |
|-----------|---------------|
| Create namespace | `catalog.create_namespace(namespace, properties)` |
| Create namespace if not exists | `catalog.create_namespace_if_not_exists(namespace)` |
| List namespaces | `catalog.list_namespaces(parent_namespace)` |
| Drop namespace | `catalog.drop_namespace(namespace)` |
| Create table | `catalog.create_table(identifier, schema, partition_spec)` |
| Create table if not exists | `catalog.create_table_if_not_exists(...)` |
| Load table | `catalog.load_table(identifier)` |
| Table exists | `catalog.table_exists(identifier)` |
| Drop table | `catalog.drop_table(identifier)` |
| Purge table | `catalog.purge_table(identifier)` |
| Register table | `catalog.register_table(identifier, metadata_location)` |

---

## 2. Retry Policy Implementation

### Decision
Use `tenacity` library for configurable retry policies with exponential backoff and jitter.

### Rationale
- Industry best practice (AWS, Google Cloud recommendations)
- Prevents retry storms via jitter
- Configurable via floe.yaml for different use cases (CLI vs batch)
- Circuit breaker pattern prevents cascading failures

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| No retry | Poor user experience for transient failures |
| Fixed retry count | Doesn't adapt to failure patterns |
| Custom implementation | tenacity is well-tested, feature-complete |

### Implementation Pattern

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)
from pyiceberg.exceptions import (
    NoSuchTableError,
    CommitFailedException,
)

class RetryConfig(BaseModel):
    """Configurable retry policy."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_wait_seconds: float = Field(default=1.0, ge=0.1, le=30.0)
    max_wait_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    jitter_seconds: float = Field(default=1.0, ge=0.0, le=10.0)

def create_retry_decorator(config: RetryConfig):
    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential_jitter(
            initial=config.initial_wait_seconds,
            max=config.max_wait_seconds,
            jitter=config.jitter_seconds,
        ),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
```

### Retryable vs Non-Retryable Errors

| Error Type | Retryable | Rationale |
|------------|-----------|-----------|
| ConnectionError | Yes | Transient network issue |
| TimeoutError | Yes | Temporary overload |
| 503 Service Unavailable | Yes | Server temporarily unavailable |
| 429 Too Many Requests | Yes | Rate limiting (with backoff) |
| 401 Unauthorized | No | Credential issue |
| 404 Not Found | No | Resource doesn't exist |
| 409 Conflict | Maybe | Optimistic concurrency (retry with new base) |
| ValidationError | No | Client error |

---

## 3. Dagster IOManager Implementation

### Decision
Implement `IcebergIOManager` extending `ConfigurableIOManager` for type-safe Pydantic configuration.

### Rationale
- `ConfigurableIOManager` is Dagster's recommended pattern for custom IOManagers
- Pydantic integration aligns with floe-runtime's type safety requirements
- Supports partitioned assets via `context.asset_partition_key`
- Metadata attachment via `context.add_output_metadata()`

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| ConfigurableIOManagerFactory | Unnecessary complexity for our use case |
| dagster-iceberg package | Preview status, limited partition support, may not align with our patterns |
| Raw IOManager | Loses type-safe configuration |

### Implementation Pattern

```python
from dagster import ConfigurableIOManager, OutputContext, InputContext
import pyarrow as pa
import pandas as pd

class IcebergIOManager(ConfigurableIOManager):
    """Iceberg-backed IOManager for Dagster assets."""

    catalog_uri: str
    warehouse: str
    default_namespace: str = "public"
    write_mode: WriteMode = WriteMode.APPEND
    schema_evolution_enabled: bool = True

    def handle_output(self, context: OutputContext, obj: pa.Table | pd.DataFrame) -> None:
        """Write data to Iceberg table."""
        table_id = self._get_table_identifier(context)

        # Convert pandas to PyArrow if needed
        if isinstance(obj, pd.DataFrame):
            obj = pa.Table.from_pandas(obj)

        # Handle partitions
        if context.has_partition_key:
            partition_key = context.asset_partition_key
            # Write to specific partition
            self._write_partitioned(table_id, obj, partition_key)
        else:
            self._write_table(table_id, obj)

        # Attach metadata
        context.add_output_metadata({
            "table": table_id,
            "num_rows": len(obj),
            "snapshot_id": self._get_current_snapshot_id(table_id),
        })

    def load_input(self, context: InputContext) -> pa.Table:
        """Read data from Iceberg table."""
        table_id = self._get_table_identifier(context)

        # Build scan with optional filters
        scan = self._build_scan(context, table_id)
        return scan.to_arrow()

    def _get_table_identifier(self, context: OutputContext | InputContext) -> str:
        """Map asset key to table identifier."""
        # ["bronze", "customers"] -> "bronze.customers"
        parts = context.asset_key.path
        if len(parts) >= 2:
            namespace = parts[0]
            table = "_".join(parts[1:])
            return f"{namespace}.{table}"
        return f"{self.default_namespace}.{parts[0]}"
```

### Asset Key to Table Mapping

| Asset Key Path | Iceberg Table Identifier |
|----------------|--------------------------|
| `["customers"]` | `public.customers` (default namespace) |
| `["bronze", "raw_events"]` | `bronze.raw_events` |
| `["gold", "metrics", "daily"]` | `gold.metrics_daily` |

### Partition Mapping

| Dagster Partition Type | Iceberg Partition Strategy |
|------------------------|---------------------------|
| DailyPartitionsDefinition | DayTransform on timestamp column |
| MonthlyPartitionsDefinition | MonthTransform on timestamp column |
| StaticPartitionsDefinition | IdentityTransform on partition column |
| MultiPartitionsDefinition | Multiple partition fields |

---

## 4. Schema Evolution Strategy

### Decision
Enable schema evolution by default using PyIceberg's `union_by_name` for automatic column addition.

### Rationale
- Reduces friction in iterative development
- Aligns with Iceberg's schema evolution capabilities
- Backward compatible (only additive changes)

### Implementation Pattern

```python
def _evolve_schema_if_needed(self, table: Table, new_data: pa.Table) -> None:
    """Automatically evolve schema for new columns."""
    if not self.schema_evolution_enabled:
        return

    current_schema = table.schema()
    new_schema = new_data.schema

    # Check if new columns need to be added
    with table.update_schema() as update:
        update.union_by_name(new_schema)
```

### Schema Evolution Rules

| Change Type | Supported | Notes |
|-------------|-----------|-------|
| Add column | Yes | Automatic via union_by_name |
| Widen type (int32 → int64) | Yes | Compatible promotion |
| Make nullable | Yes | Less restrictive |
| Rename column | Manual | Requires explicit API call |
| Drop column | Manual | Requires allow_incompatible_changes=True |
| Change type (string → int) | No | Incompatible |

---

## 5. Observability Integration

### Decision
Use structlog for structured logging and OpenTelemetry for distributed tracing, consistent with floe-dagster.

### Rationale
- Aligns with existing floe-dagster observability patterns
- Structured logs enable log aggregation and analysis
- OTel spans provide distributed tracing across pipeline components

### Implementation Pattern

```python
import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

class ObservableCatalog:
    """Catalog wrapper with observability."""

    def load_table(self, identifier: str) -> Table:
        with tracer.start_as_current_span("iceberg.load_table") as span:
            span.set_attribute("iceberg.table", identifier)

            logger.info("loading_table", table=identifier)
            try:
                table = self._catalog.load_table(identifier)
                logger.info("table_loaded", table=identifier,
                           snapshot_id=table.current_snapshot().snapshot_id)
                return table
            except NoSuchTableError as e:
                logger.warning("table_not_found", table=identifier)
                raise
```

### Span Attributes

| Span Name | Attributes |
|-----------|------------|
| `iceberg.load_table` | table, snapshot_id |
| `iceberg.create_table` | table, schema_id, partition_spec |
| `iceberg.append` | table, num_rows, snapshot_id |
| `iceberg.scan` | table, columns, row_filter, limit |
| `polaris.create_namespace` | namespace, properties |
| `polaris.authenticate` | scope (no secrets) |

---

## 6. Error Handling Strategy

### Decision
Create custom exception hierarchy with actionable error messages.

### Rationale
- Constitution requires generic user messages with technical details logged internally
- Custom exceptions enable programmatic error handling
- Actionable messages reduce support burden

### Exception Hierarchy

```python
class FloeStorageError(Exception):
    """Base exception for storage operations."""
    pass

class CatalogConnectionError(FloeStorageError):
    """Failed to connect to catalog."""
    pass

class CatalogAuthenticationError(FloeStorageError):
    """Authentication failed (invalid credentials or expired token)."""
    pass

class TableNotFoundError(FloeStorageError):
    """Table does not exist in catalog."""
    pass

class SchemaEvolutionError(FloeStorageError):
    """Schema evolution not possible (incompatible change)."""
    pass

class ConcurrencyConflictError(FloeStorageError):
    """Optimistic concurrency conflict during commit."""
    pass
```

### Error Message Examples

| Internal Log | User Message |
|--------------|--------------|
| `OAuth2 token request failed: 401 invalid_client for client_id=xyz` | `Authentication failed: check catalog credentials in floe.yaml` |
| `Table bronze.customers not found in catalog polaris at http://localhost:8181` | `Table 'bronze.customers' not found in catalog` |
| `Schema evolution failed: cannot change 'price' from string to int64` | `Schema mismatch: column 'price' has incompatible type` |

---

## 7. Testing Strategy

### Decision
Three-tier testing: unit tests (mocked), integration tests (testcontainers), contract tests (IOManager compliance).

### Rationale
- Unit tests ensure logic correctness with fast feedback
- Integration tests verify actual Iceberg/Polaris behavior
- Contract tests ensure Dagster IOManager compliance

### Test Infrastructure

```python
# Unit test with mocked catalog
@pytest.fixture
def mock_catalog():
    catalog = Mock(spec=Catalog)
    catalog.load_table.return_value = Mock(spec=Table)
    return catalog

# Integration test with testcontainers
@pytest.fixture(scope="module")
def polaris_catalog():
    with PolarisContainer() as container:
        catalog = load_catalog(
            "test",
            type="rest",
            uri=container.get_connection_url(),
            warehouse="test_warehouse",
        )
        yield catalog

# Dagster IOManager contract test
def test_io_manager_contract():
    io_manager = IcebergIOManager(...)
    output_context = build_output_context(...)
    input_context = build_input_context(...)

    # Round-trip test
    test_data = pa.Table.from_pydict({"id": [1, 2], "name": ["a", "b"]})
    io_manager.handle_output(output_context, test_data)
    loaded = io_manager.load_input(input_context)
    assert loaded.equals(test_data)
```

---

## 8. Configuration Schema

### Decision
Extend CatalogConfig in floe-core with retry configuration; add IcebergIOManagerConfig in floe-iceberg.

### Rationale
- CatalogConfig already exists and handles catalog connectivity
- RetryConfig is catalog-level (applies to all operations)
- IOManagerConfig is Dagster-specific (asset mapping, write modes)

### Configuration Models

```python
# In floe-core (extend CatalogConfig)
class RetryConfig(BaseModel):
    """Retry policy configuration."""
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_wait_seconds: float = Field(default=1.0, ge=0.1)
    max_wait_seconds: float = Field(default=30.0, le=300.0)
    jitter_seconds: float = Field(default=1.0)

# In floe-iceberg
class WriteMode(str, Enum):
    """Write mode for IOManager."""
    APPEND = "append"
    OVERWRITE = "overwrite"

class IcebergIOManagerConfig(BaseModel):
    """IOManager configuration."""
    model_config = ConfigDict(frozen=True)

    default_namespace: str = Field(default="public")
    write_mode: WriteMode = Field(default=WriteMode.APPEND)
    schema_evolution_enabled: bool = Field(default=True)
    column_projection_enabled: bool = Field(default=True)
```

---

## Summary

All research items resolved. Key decisions:

1. **PyIceberg RestCatalog**: Native integration with Polaris via Iceberg REST Catalog spec
2. **Tenacity retry**: Configurable exponential backoff with jitter
3. **ConfigurableIOManager**: Type-safe Dagster integration with Pydantic
4. **Schema evolution**: Enabled by default via union_by_name
5. **Observability**: structlog + OpenTelemetry consistent with floe-dagster
6. **Error handling**: Custom exceptions with actionable user messages
7. **Testing**: Unit + integration + contract tests
8. **Configuration**: Extend CatalogConfig, new IcebergIOManagerConfig
