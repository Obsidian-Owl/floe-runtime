# Data Model: Storage & Catalog Layer

**Feature**: 004-storage-catalog
**Date**: 2025-12-17

## Overview

This document defines the data models for floe-polaris and floe-iceberg packages. All models use Pydantic v2 with frozen immutability and strict validation.

---

## 1. Configuration Models (floe-polaris)

### RetryConfig

Configurable retry policy for catalog operations.

```python
class RetryConfig(BaseModel):
    """Retry policy configuration for catalog operations.

    Implements exponential backoff with jitter per enterprise best practices.

    Attributes:
        max_attempts: Maximum number of retry attempts (1-10).
        initial_wait_seconds: Initial wait time before first retry.
        max_wait_seconds: Maximum wait time cap.
        jitter_seconds: Random jitter added to prevent thundering herd.
        circuit_breaker_threshold: Failures before circuit opens (0 = disabled).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_wait_seconds: float = Field(default=1.0, ge=0.1, le=30.0)
    max_wait_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    jitter_seconds: float = Field(default=1.0, ge=0.0, le=10.0)
    circuit_breaker_threshold: int = Field(default=5, ge=0)
```

**Validation Rules**:
- max_attempts: 1-10 (prevent infinite retries)
- initial_wait_seconds: 0.1-30s (reasonable starting point)
- max_wait_seconds: 1-300s (cap at 5 minutes)
- jitter_seconds: 0-10s (prevent synchronized retries)

---

### PolarisCatalogConfig

Extended configuration for Polaris catalog connection (extends CatalogConfig from floe-core).

```python
class PolarisCatalogConfig(BaseModel):
    """Polaris-specific catalog configuration.

    Extends base CatalogConfig with retry and observability settings.

    Attributes:
        uri: Polaris REST API endpoint.
        warehouse: Warehouse name in Polaris.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret (SecretStr).
        scope: OAuth2 scope for token request.
        token_refresh_enabled: Enable automatic token refresh.
        access_delegation: Iceberg access delegation mode.
        retry: Retry policy configuration.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str = Field(..., description="Polaris REST API endpoint")
    warehouse: str = Field(..., description="Warehouse name")
    client_id: str | None = Field(default=None, description="OAuth2 client ID")
    client_secret: SecretStr | None = Field(default=None, description="OAuth2 client secret")
    token: SecretStr | None = Field(default=None, description="Pre-fetched bearer token")
    scope: str = Field(default="PRINCIPAL_ROLE:ALL", description="OAuth2 scope")
    token_refresh_enabled: bool = Field(default=True, description="Enable token refresh")
    access_delegation: str = Field(
        default="vended-credentials",
        description="Iceberg access delegation header"
    )
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry policy")

    @model_validator(mode="after")
    def validate_auth(self) -> Self:
        """Ensure either client credentials or token is provided."""
        has_credentials = self.client_id is not None and self.client_secret is not None
        has_token = self.token is not None
        if not has_credentials and not has_token:
            raise ValueError("Either (client_id + client_secret) or token must be provided")
        return self
```

**Validation Rules**:
- Must have either (client_id + client_secret) or token
- uri is required
- warehouse is required
- scope defaults to "PRINCIPAL_ROLE:ALL"

---

### NamespaceInfo

Information about a catalog namespace.

```python
class NamespaceInfo(BaseModel):
    """Information about a catalog namespace.

    Attributes:
        name: Namespace name (may be nested: "bronze.raw").
        properties: Custom namespace properties.
        tables: List of table names in this namespace.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Namespace name")
    properties: dict[str, str] = Field(default_factory=dict)
    tables: list[str] = Field(default_factory=list)
```

---

## 2. Configuration Models (floe-iceberg)

### WriteMode

Enum for IOManager write behavior.

```python
class WriteMode(str, Enum):
    """Write mode for Iceberg IOManager.

    APPEND: Add new data to existing table data.
    OVERWRITE: Replace all data in table (or partition).
    """
    APPEND = "append"
    OVERWRITE = "overwrite"
```

---

### IcebergIOManagerConfig

Configuration for the Dagster IOManager.

```python
class IcebergIOManagerConfig(BaseModel):
    """Configuration for IcebergIOManager.

    Attributes:
        catalog_uri: Polaris catalog endpoint.
        warehouse: Warehouse name.
        default_namespace: Default namespace for tables without explicit namespace.
        write_mode: Default write mode (append/overwrite).
        schema_evolution_enabled: Enable automatic schema evolution.
        column_projection_enabled: Enable column projection on reads.
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        retry: Retry policy configuration.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_uri: str = Field(..., description="Polaris catalog URI")
    warehouse: str = Field(..., description="Warehouse name")
    default_namespace: str = Field(default="public", description="Default namespace")
    write_mode: WriteMode = Field(default=WriteMode.APPEND, description="Write mode")
    schema_evolution_enabled: bool = Field(default=True)
    column_projection_enabled: bool = Field(default=True)
    client_id: str | None = Field(default=None)
    client_secret: SecretStr | None = Field(default=None)
    token: SecretStr | None = Field(default=None)
    scope: str = Field(default="PRINCIPAL_ROLE:ALL")
    retry: RetryConfig = Field(default_factory=RetryConfig)
```

---

### TableIdentifier

Represents an Iceberg table location.

```python
class TableIdentifier(BaseModel):
    """Iceberg table identifier.

    Attributes:
        namespace: Namespace path (e.g., ["bronze", "raw"]).
        name: Table name.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: tuple[str, ...] = Field(..., description="Namespace path")
    name: str = Field(..., description="Table name")

    @property
    def full_name(self) -> str:
        """Return dot-separated full name (e.g., 'bronze.raw.events')."""
        return ".".join([*self.namespace, self.name])

    @classmethod
    def from_string(cls, identifier: str) -> "TableIdentifier":
        """Parse from dot-separated string."""
        parts = identifier.split(".")
        return cls(namespace=tuple(parts[:-1]), name=parts[-1])

    @classmethod
    def from_asset_key(cls, asset_key: list[str], default_namespace: str = "public") -> "TableIdentifier":
        """Create from Dagster asset key path."""
        if len(asset_key) >= 2:
            return cls(namespace=(asset_key[0],), name="_".join(asset_key[1:]))
        return cls(namespace=(default_namespace,), name=asset_key[0])
```

**Examples**:
- `TableIdentifier(namespace=("bronze",), name="customers")` → `"bronze.customers"`
- `TableIdentifier.from_string("gold.metrics.daily")` → namespace=("gold", "metrics"), name="daily"
- `TableIdentifier.from_asset_key(["bronze", "raw_events"])` → `"bronze.raw_events"`

---

### PartitionTransform

Configuration for partition transforms.

```python
class PartitionTransformType(str, Enum):
    """Iceberg partition transform types."""
    IDENTITY = "identity"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    HOUR = "hour"
    BUCKET = "bucket"
    TRUNCATE = "truncate"

class PartitionTransform(BaseModel):
    """Partition transform specification.

    Attributes:
        source_column: Column to partition on.
        transform_type: Type of transform to apply.
        num_buckets: Number of buckets (for BUCKET transform).
        width: Truncation width (for TRUNCATE transform).
        name: Custom partition field name (defaults to auto-generated).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_column: str = Field(..., description="Source column name")
    transform_type: PartitionTransformType = Field(..., description="Transform type")
    num_buckets: int | None = Field(default=None, ge=1, description="Buckets for BUCKET")
    width: int | None = Field(default=None, ge=1, description="Width for TRUNCATE")
    name: str | None = Field(default=None, description="Custom partition field name")

    @model_validator(mode="after")
    def validate_transform_params(self) -> Self:
        """Validate transform-specific parameters."""
        if self.transform_type == PartitionTransformType.BUCKET and self.num_buckets is None:
            raise ValueError("num_buckets required for BUCKET transform")
        if self.transform_type == PartitionTransformType.TRUNCATE and self.width is None:
            raise ValueError("width required for TRUNCATE transform")
        return self
```

---

### SnapshotInfo

Information about a table snapshot.

```python
class SnapshotInfo(BaseModel):
    """Information about an Iceberg table snapshot.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        timestamp_ms: Snapshot creation timestamp (milliseconds since epoch).
        operation: Operation that created snapshot (append, overwrite, delete).
        summary: Snapshot summary statistics.
        parent_snapshot_id: Parent snapshot ID (None for first snapshot).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: int = Field(..., description="Snapshot ID")
    timestamp_ms: int = Field(..., description="Creation timestamp (ms)")
    operation: str = Field(..., description="Operation type")
    summary: dict[str, str] = Field(default_factory=dict)
    parent_snapshot_id: int | None = Field(default=None)

    @property
    def timestamp(self) -> datetime:
        """Return timestamp as datetime."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.timestamp_ms / 1000, tz=timezone.utc)
```

---

### MaterializationMetadata

Metadata attached to Dagster asset materializations.

```python
class MaterializationMetadata(BaseModel):
    """Metadata for Dagster asset materialization.

    Attached via context.add_output_metadata() after writes.

    Attributes:
        table: Full table identifier.
        num_rows: Number of rows written.
        snapshot_id: New snapshot ID after write.
        write_mode: Write mode used (append/overwrite).
        partition_key: Partition key if partitioned write.
        schema_evolved: Whether schema was evolved.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    table: str = Field(..., description="Table identifier")
    num_rows: int = Field(..., ge=0, description="Rows written")
    snapshot_id: int = Field(..., description="New snapshot ID")
    write_mode: WriteMode = Field(..., description="Write mode used")
    partition_key: str | None = Field(default=None, description="Partition key")
    schema_evolved: bool = Field(default=False, description="Schema was evolved")
```

---

## 3. Error Models

### StorageErrorDetail

Structured error information for logging and debugging.

```python
class StorageErrorDetail(BaseModel):
    """Detailed error information for storage operations.

    Used for internal logging; user messages are sanitized.

    Attributes:
        error_type: Error classification.
        operation: Operation that failed.
        table: Table identifier (if applicable).
        namespace: Namespace (if applicable).
        message: Detailed error message (internal only).
        retryable: Whether operation can be retried.
        retry_count: Number of retries attempted.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    error_type: str = Field(..., description="Error classification")
    operation: str = Field(..., description="Failed operation")
    table: str | None = Field(default=None)
    namespace: str | None = Field(default=None)
    message: str = Field(..., description="Internal error message")
    retryable: bool = Field(default=False)
    retry_count: int = Field(default=0, ge=0)
```

---

## 4. Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      floe-core                                  │
│  ┌─────────────────┐     ┌─────────────────────────────────┐   │
│  │  CatalogConfig  │────▶│      CompiledArtifacts          │   │
│  └─────────────────┘     └─────────────────────────────────┘   │
└──────────┬──────────────────────────────────────────────────────┘
           │ extends
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     floe-polaris                                │
│  ┌─────────────────────┐     ┌─────────────────┐               │
│  │PolarisCatalogConfig │────▶│   RetryConfig   │               │
│  └─────────────────────┘     └─────────────────┘               │
│            │                                                    │
│            │ creates                                            │
│            ▼                                                    │
│  ┌─────────────────────┐     ┌─────────────────┐               │
│  │  PolarisCatalog     │────▶│  NamespaceInfo  │               │
│  │  (PyIceberg)        │     └─────────────────┘               │
│  └─────────────────────┘                                       │
└──────────┬──────────────────────────────────────────────────────┘
           │ used by
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     floe-iceberg                                │
│  ┌─────────────────────┐     ┌─────────────────────┐           │
│  │IcebergIOManagerConfig│────▶│  TableIdentifier    │           │
│  └─────────────────────┘     └─────────────────────┘           │
│            │                          │                         │
│            │                          │ references              │
│            ▼                          ▼                         │
│  ┌─────────────────────┐     ┌─────────────────────┐           │
│  │  IcebergIOManager   │────▶│    Table (PyIceberg)│           │
│  └─────────────────────┘     └─────────────────────┘           │
│            │                          │                         │
│            │ produces                 │ contains                │
│            ▼                          ▼                         │
│  ┌─────────────────────┐     ┌─────────────────────┐           │
│  │MaterializationMeta  │     │    SnapshotInfo     │           │
│  └─────────────────────┘     └─────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. State Transitions

### Catalog Connection States

```
                 ┌───────────────┐
                 │  Disconnected │
                 └───────┬───────┘
                         │ connect()
                         ▼
                 ┌───────────────┐
          ┌──────│ Authenticating│──────┐
          │      └───────┬───────┘      │
   auth   │              │ success     │ failure
   error  │              ▼              │
          │      ┌───────────────┐      │
          │      │  Connected    │      │
          │      └───────┬───────┘      │
          │              │              │
          │   ┌──────────┼──────────┐   │
          │   │          │          │   │
          │   ▼          ▼          ▼   │
          │ ┌───┐     ┌───┐     ┌───┐   │
          │ │op │     │op │     │op │   │
          │ └─┬─┘     └─┬─┘     └─┬─┘   │
          │   │         │         │     │
          │   └─────────┴─────────┘     │
          │              │              │
          │       token expired         │
          │              │              │
          │              ▼              │
          │      ┌───────────────┐      │
          └─────▶│  Reconnecting │◀─────┘
                 └───────┬───────┘
                         │ retry with backoff
                         ▼
                 (back to Authenticating)
```

### Write Operation States

```
┌────────────┐
│  Pending   │
└─────┬──────┘
      │ handle_output()
      ▼
┌────────────┐     schema      ┌────────────────┐
│  Validating│───mismatch─────▶│ Evolving Schema│
└─────┬──────┘                 └───────┬────────┘
      │ valid                          │ evolved
      ▼                                │
┌────────────┐                         │
│  Writing   │◀────────────────────────┘
└─────┬──────┘
      │
      ├─── success ──▶ ┌────────────┐
      │                │ Committed  │
      │                └────────────┘
      │
      └─── conflict ──▶ ┌────────────┐
                        │  Retrying  │
                        └─────┬──────┘
                              │ max retries
                              ▼
                        ┌────────────┐
                        │   Failed   │
                        └────────────┘
```

---

## Summary

This data model provides:

1. **Type-safe configuration** via Pydantic models for catalog and IOManager settings
2. **Immutable data structures** using `frozen=True` for thread safety
3. **Rich validation** with field constraints and cross-field validators
4. **Clear entity relationships** between floe-core, floe-polaris, and floe-iceberg
5. **State machine documentation** for connection and write operation lifecycle
