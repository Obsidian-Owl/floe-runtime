# floe-iceberg API Contract

**Package**: floe-iceberg
**Version**: 0.1.0
**Date**: 2025-12-17

## Overview

This document defines the public API contract for the floe-iceberg package. The package provides Dagster IOManager for reading/writing assets to Iceberg tables, plus table management utilities.

---

## Public API

### Module: `floe_iceberg`

#### `create_io_manager`

Factory function to create a configured Iceberg IOManager for Dagster.

```python
def create_io_manager(
    config: IcebergIOManagerConfig,
    catalog: PolarisCatalog | None = None,
) -> IcebergIOManager:
    """Create an Iceberg IOManager for Dagster assets.

    Args:
        config: IOManager configuration.
        catalog: Optional pre-configured catalog. If not provided,
            creates one from config.catalog_config.

    Returns:
        IcebergIOManager: Configured IOManager for Dagster Definitions.

    Example:
        >>> from floe_iceberg import create_io_manager, IcebergIOManagerConfig
        >>> config = IcebergIOManagerConfig(
        ...     catalog_uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     default_namespace="bronze",
        ... )
        >>> io_manager = create_io_manager(config)
        >>> defs = Definitions(
        ...     assets=[my_asset],
        ...     resources={"io_manager": io_manager},
        ... )
    """
```

---

### Class: `IcebergIOManager`

Dagster IOManager for reading and writing PyArrow/Pandas data to Iceberg tables.

#### Constructor

```python
class IcebergIOManager(ConfigurableIOManager):
    """Iceberg-backed IOManager for Dagster assets.

    Maps Dagster asset keys to Iceberg table identifiers:
    - ["customers"] → {default_namespace}.customers
    - ["bronze", "raw_events"] → bronze.raw_events
    - ["gold", "metrics", "daily"] → gold.metrics_daily

    Supports:
    - PyArrow Table and Pandas DataFrame outputs
    - Partitioned assets via Dagster partition keys
    - Automatic schema evolution (configurable)
    - Multiple write modes (append, overwrite)

    Attributes:
        catalog_uri: Polaris REST API endpoint.
        warehouse: Warehouse name.
        default_namespace: Namespace for single-part asset keys.
        write_mode: Default write mode (append or overwrite).
        schema_evolution_enabled: Enable automatic schema evolution.
    """

    catalog_uri: str
    warehouse: str
    client_id: str | None = None
    client_secret: SecretStr | None = None
    default_namespace: str = "public"
    write_mode: WriteMode = WriteMode.APPEND
    schema_evolution_enabled: bool = True
```

#### Core Methods

```python
def handle_output(
    self,
    context: OutputContext,
    obj: pa.Table | pd.DataFrame,
) -> None:
    """Write asset output to Iceberg table.

    Args:
        context: Dagster output context with asset key and metadata.
        obj: Data to write (PyArrow Table or Pandas DataFrame).

    Raises:
        TableNotFoundError: If table doesn't exist and auto-create disabled.
        SchemaEvolutionError: If schema change is incompatible.
        WriteError: If write operation fails.

    Side Effects:
        - Attaches metadata to context: table, num_rows, snapshot_id
        - Creates table if it doesn't exist (when auto_create=True)
        - Evolves schema if new columns present (when enabled)

    Example:
        >>> @asset
        ... def customers() -> pd.DataFrame:
        ...     return pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        >>> # IOManager automatically writes to {namespace}.customers
    """

def load_input(
    self,
    context: InputContext,
) -> pa.Table:
    """Read asset input from Iceberg table.

    Args:
        context: Dagster input context with asset key.

    Returns:
        PyArrow Table with requested data.

    Raises:
        TableNotFoundError: If table doesn't exist.

    Note:
        For partitioned assets, reads only the requested partition.
        Column projection is applied when type hints specify columns.

    Example:
        >>> @asset
        ... def downstream(customers: pa.Table) -> pa.Table:
        ...     # customers is loaded from Iceberg table
        ...     return customers.filter(...)
    """
```

#### Configuration Methods

```python
def get_table_identifier(
    self,
    context: OutputContext | InputContext,
) -> str:
    """Map asset key to Iceberg table identifier.

    Args:
        context: Dagster context with asset key.

    Returns:
        Fully qualified table identifier (namespace.table).

    Mapping Rules:
        - ["customers"] → "{default_namespace}.customers"
        - ["bronze", "raw"] → "bronze.raw"
        - ["gold", "metrics", "daily"] → "gold.metrics_daily"
    """
```

---

### Class: `IcebergTableManager`

Utility class for direct Iceberg table operations.

#### Constructor

```python
class IcebergTableManager:
    """Manage Iceberg tables directly (outside Dagster context).

    Use this class for:
    - Creating tables with specific schemas
    - Dropping or purging tables
    - Registering external tables
    - Table maintenance operations

    Note:
        For Dagster asset storage, use IcebergIOManager instead.

    Attributes:
        catalog: PolarisCatalog instance.
    """

    def __init__(
        self,
        catalog: PolarisCatalog,
        *,
        tracer: Tracer | None = None,
        logger: BoundLogger | None = None,
    ) -> None: ...
```

#### Table Operations

```python
def create_table(
    self,
    identifier: str | TableIdentifier,
    schema: pa.Schema | Schema,
    partition_spec: PartitionSpec | None = None,
    properties: dict[str, str] | None = None,
) -> Table:
    """Create a new Iceberg table.

    Args:
        identifier: Table identifier (namespace.table).
        schema: Table schema (PyArrow or Iceberg Schema).
        partition_spec: Optional partition specification.
        properties: Optional table properties.

    Returns:
        Created PyIceberg Table object.

    Raises:
        TableExistsError: If table already exists.
        NamespaceNotFoundError: If namespace doesn't exist.

    Example:
        >>> import pyarrow as pa
        >>> schema = pa.schema([
        ...     pa.field("id", pa.int64()),
        ...     pa.field("name", pa.string()),
        ...     pa.field("created_at", pa.timestamp("us")),
        ... ])
        >>> table = manager.create_table("bronze.customers", schema)
    """

def create_table_if_not_exists(
    self,
    identifier: str | TableIdentifier,
    schema: pa.Schema | Schema,
    partition_spec: PartitionSpec | None = None,
    properties: dict[str, str] | None = None,
) -> Table:
    """Create table if it doesn't exist (idempotent).

    Args:
        identifier: Table identifier.
        schema: Table schema.
        partition_spec: Optional partition specification.
        properties: Optional table properties.

    Returns:
        Table object (created or existing).
    """

def load_table(
    self,
    identifier: str | TableIdentifier,
) -> Table:
    """Load an existing Iceberg table.

    Args:
        identifier: Table identifier.

    Returns:
        PyIceberg Table object.

    Raises:
        TableNotFoundError: If table doesn't exist.
    """

def drop_table(
    self,
    identifier: str | TableIdentifier,
    purge: bool = False,
) -> None:
    """Drop an Iceberg table.

    Args:
        identifier: Table identifier.
        purge: If True, also delete data files. If False, only
            removes metadata (data files remain).

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
        List of table names (without namespace prefix).
    """
```

#### Data Operations

```python
def append(
    self,
    identifier: str | TableIdentifier,
    data: pa.Table | pd.DataFrame,
    *,
    evolve_schema: bool = True,
) -> SnapshotInfo:
    """Append data to an Iceberg table.

    Args:
        identifier: Table identifier.
        data: Data to append.
        evolve_schema: If True, automatically add new columns.

    Returns:
        SnapshotInfo with new snapshot details.

    Raises:
        TableNotFoundError: If table doesn't exist.
        SchemaEvolutionError: If schema evolution fails.

    Example:
        >>> data = pa.Table.from_pydict({"id": [1, 2], "name": ["a", "b"]})
        >>> snapshot = manager.append("bronze.customers", data)
        >>> print(f"Created snapshot {snapshot.snapshot_id}")
    """

def overwrite(
    self,
    identifier: str | TableIdentifier,
    data: pa.Table | pd.DataFrame,
    *,
    evolve_schema: bool = True,
) -> SnapshotInfo:
    """Overwrite table data (replace all rows).

    Args:
        identifier: Table identifier.
        data: New data to write.
        evolve_schema: If True, automatically add new columns.

    Returns:
        SnapshotInfo with new snapshot details.

    Raises:
        TableNotFoundError: If table doesn't exist.
    """

def scan(
    self,
    identifier: str | TableIdentifier,
    columns: list[str] | None = None,
    row_filter: str | None = None,
    snapshot_id: int | None = None,
    limit: int | None = None,
) -> pa.Table:
    """Scan table data with optional filtering.

    Args:
        identifier: Table identifier.
        columns: Columns to project (None = all).
        row_filter: Row filter expression (Iceberg expression syntax).
        snapshot_id: Read from specific snapshot (time travel).
        limit: Maximum rows to return.

    Returns:
        PyArrow Table with scan results.

    Example:
        >>> # Read specific columns
        >>> data = manager.scan("bronze.customers", columns=["id", "name"])

        >>> # Time travel to previous snapshot
        >>> data = manager.scan("bronze.customers", snapshot_id=123456789)

        >>> # Filter rows
        >>> data = manager.scan("bronze.customers", row_filter="status = 'active'")
    """
```

#### Snapshot Operations

```python
def list_snapshots(
    self,
    identifier: str | TableIdentifier,
    limit: int | None = None,
) -> list[SnapshotInfo]:
    """List table snapshots.

    Args:
        identifier: Table identifier.
        limit: Maximum snapshots to return.

    Returns:
        List of SnapshotInfo objects (newest first).
    """

def get_current_snapshot(
    self,
    identifier: str | TableIdentifier,
) -> SnapshotInfo | None:
    """Get current snapshot info.

    Args:
        identifier: Table identifier.

    Returns:
        Current SnapshotInfo, or None if table has no snapshots.
    """

def expire_snapshots(
    self,
    identifier: str | TableIdentifier,
    older_than: datetime | None = None,
    retain_last: int | None = None,
) -> int:
    """Expire old snapshots.

    Args:
        identifier: Table identifier.
        older_than: Expire snapshots older than this timestamp.
        retain_last: Always retain at least this many snapshots.

    Returns:
        Number of snapshots expired.

    Example:
        >>> from datetime import datetime, timedelta
        >>> # Expire snapshots older than 7 days, keep at least 5
        >>> expired = manager.expire_snapshots(
        ...     "bronze.customers",
        ...     older_than=datetime.now() - timedelta(days=7),
        ...     retain_last=5,
        ... )
    """
```

---

### Class: `IcebergIOManagerConfig`

```python
class IcebergIOManagerConfig(BaseModel):
    """IOManager configuration.

    Attributes:
        catalog_uri: Polaris REST API endpoint.
        warehouse: Warehouse name.
        client_id: OAuth2 client ID (optional if using token).
        client_secret: OAuth2 client secret.
        token: Pre-fetched bearer token.
        default_namespace: Namespace for single-part asset keys.
        write_mode: Default write mode (append or overwrite).
        schema_evolution_enabled: Enable automatic schema evolution.
        auto_create_tables: Create tables automatically on first write.
        partition_column: Default partition column for time-based partitioning.
    """

    model_config = ConfigDict(frozen=True)

    catalog_uri: str
    warehouse: str
    client_id: str | None = None
    client_secret: SecretStr | None = None
    token: SecretStr | None = None
    default_namespace: str = "public"
    write_mode: WriteMode = WriteMode.APPEND
    schema_evolution_enabled: bool = True
    auto_create_tables: bool = True
    partition_column: str | None = None
```

---

### Enums

```python
class WriteMode(str, Enum):
    """Write mode for table operations."""
    APPEND = "append"
    OVERWRITE = "overwrite"
```

---

### Data Classes

```python
class SnapshotInfo(BaseModel):
    """Information about an Iceberg snapshot.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        timestamp_ms: Snapshot creation timestamp (milliseconds).
        operation: Operation that created snapshot (append, overwrite, delete).
        summary: Snapshot summary statistics.
        manifest_list: Path to manifest list file.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_id: int
    timestamp_ms: int
    operation: str
    summary: dict[str, str]
    manifest_list: str | None = None

    @property
    def timestamp(self) -> datetime:
        """Snapshot creation time as datetime."""
        return datetime.fromtimestamp(self.timestamp_ms / 1000)


class TableIdentifier(BaseModel):
    """Iceberg table identifier.

    Attributes:
        namespace: Namespace (can be nested, e.g., "bronze.raw").
        name: Table name.
    """

    model_config = ConfigDict(frozen=True)

    namespace: str
    name: str

    def __str__(self) -> str:
        return f"{self.namespace}.{self.name}"

    @classmethod
    def from_string(cls, identifier: str) -> TableIdentifier:
        """Parse identifier from string.

        Args:
            identifier: Table identifier string (namespace.table).

        Returns:
            TableIdentifier instance.

        Raises:
            ValueError: If identifier format is invalid.
        """
        parts = identifier.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid identifier: {identifier}")
        return cls(namespace=parts[0], name=parts[1])
```

---

### Exceptions

```python
class FloeStorageError(Exception):
    """Base exception for storage operations."""

class TableNotFoundError(FloeStorageError):
    """Table not found in catalog."""

class TableExistsError(FloeStorageError):
    """Table already exists."""

class SchemaEvolutionError(FloeStorageError):
    """Schema evolution not possible (incompatible change)."""

class WriteError(FloeStorageError):
    """Write operation failed."""

class ScanError(FloeStorageError):
    """Scan operation failed."""
```

---

## Usage Examples

### Basic Dagster Integration

```python
from dagster import asset, Definitions
from floe_iceberg import create_io_manager, IcebergIOManagerConfig
import pandas as pd

# Configure IOManager
config = IcebergIOManagerConfig(
    catalog_uri="http://localhost:8181/api/catalog",
    warehouse="my_warehouse",
    client_id="my_client",
    client_secret="my_secret",
    default_namespace="bronze",
)

# Define assets
@asset
def raw_customers() -> pd.DataFrame:
    """Load raw customer data."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "email": ["alice@example.com", "bob@example.com", "charlie@example.com"],
    })

@asset
def customers(raw_customers: pd.DataFrame) -> pd.DataFrame:
    """Transform customer data."""
    return raw_customers.assign(
        name_upper=raw_customers["name"].str.upper()
    )

# Create Definitions
defs = Definitions(
    assets=[raw_customers, customers],
    resources={"io_manager": create_io_manager(config)},
)
```

### Partitioned Assets

```python
from dagster import asset, DailyPartitionsDefinition
import pyarrow as pa

daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")

@asset(partitions_def=daily_partitions)
def daily_events(context) -> pa.Table:
    """Load events for a specific day."""
    partition_date = context.partition_key
    # IOManager writes to partition based on partition_key
    return load_events_for_date(partition_date)
```

### Direct Table Management

```python
from floe_polaris import create_catalog, PolarisCatalogConfig
from floe_iceberg import IcebergTableManager
import pyarrow as pa

# Create catalog connection
catalog_config = PolarisCatalogConfig(
    uri="http://localhost:8181/api/catalog",
    warehouse="my_warehouse",
    client_id="my_client",
    client_secret="my_secret",
)
catalog = create_catalog(catalog_config)

# Create table manager
manager = IcebergTableManager(catalog)

# Define schema
schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("name", pa.string()),
    pa.field("created_at", pa.timestamp("us")),
])

# Create table
table = manager.create_table_if_not_exists("bronze.customers", schema)

# Append data
data = pa.Table.from_pydict({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "created_at": [datetime.now()] * 3,
})
snapshot = manager.append("bronze.customers", data)
print(f"Created snapshot: {snapshot.snapshot_id}")

# Query data
result = manager.scan("bronze.customers", columns=["id", "name"])
print(result.to_pandas())
```

### Time Travel

```python
# List snapshots
snapshots = manager.list_snapshots("bronze.customers")
for snap in snapshots:
    print(f"{snap.snapshot_id}: {snap.timestamp} - {snap.operation}")

# Read from previous snapshot
old_data = manager.scan(
    "bronze.customers",
    snapshot_id=snapshots[1].snapshot_id
)

# Expire old snapshots
expired_count = manager.expire_snapshots(
    "bronze.customers",
    older_than=datetime.now() - timedelta(days=30),
    retain_last=10,
)
```

### From floe-core CompiledArtifacts

```python
from floe_core.schemas import CompiledArtifacts
from floe_iceberg import create_io_manager_from_artifacts

# Load CompiledArtifacts
artifacts = CompiledArtifacts.from_json_file(".floe/compiled_artifacts.json")

# Create IOManager from artifacts
io_manager = create_io_manager_from_artifacts(artifacts)
```
