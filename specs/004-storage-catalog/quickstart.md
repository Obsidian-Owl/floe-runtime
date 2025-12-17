# Quickstart: Storage & Catalog Layer

**Feature**: 004-storage-catalog
**Packages**: floe-polaris, floe-iceberg

This guide demonstrates the core functionality of the storage layer in 5 minutes.

---

## Prerequisites

```bash
# Install packages (from monorepo root)
pip install -e packages/floe-polaris -e packages/floe-iceberg

# Start local Polaris (optional - for integration testing)
docker run -d --name polaris -p 8181:8181 apache/polaris:latest
```

---

## 1. Connect to Polaris Catalog

```python
from floe_polaris import create_catalog, PolarisCatalogConfig

# Configure catalog connection
config = PolarisCatalogConfig(
    uri="http://localhost:8181/api/catalog",
    warehouse="quickstart_warehouse",
    client_id="root",
    client_secret="secret",  # Use SecretStr in production
)

# Create catalog client
catalog = create_catalog(config)

# Verify connection
print(f"Connected: {catalog.is_connected()}")
```

---

## 2. Manage Namespaces

```python
# Create namespace hierarchy
catalog.create_namespace_if_not_exists("bronze", {"owner": "data_team"})
catalog.create_namespace_if_not_exists("silver")
catalog.create_namespace_if_not_exists("gold")

# List namespaces
for ns in catalog.list_namespaces():
    print(f"  {ns.name}: {ns.properties}")
```

---

## 3. Create and Write to Iceberg Tables

```python
from floe_iceberg import IcebergTableManager
import pyarrow as pa

# Create table manager
manager = IcebergTableManager(catalog)

# Define schema
schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("name", pa.string()),
    pa.field("email", pa.string()),
    pa.field("created_at", pa.timestamp("us")),
])

# Create table
manager.create_table_if_not_exists("bronze.customers", schema)

# Write data
from datetime import datetime

data = pa.Table.from_pydict({
    "id": [1, 2, 3],
    "name": ["Alice", "Bob", "Charlie"],
    "email": ["alice@ex.com", "bob@ex.com", "charlie@ex.com"],
    "created_at": [datetime.now()] * 3,
})

snapshot = manager.append("bronze.customers", data)
print(f"Snapshot ID: {snapshot.snapshot_id}")
```

---

## 4. Query Data

```python
# Full scan
result = manager.scan("bronze.customers")
print(result.to_pandas())

# Column projection
result = manager.scan("bronze.customers", columns=["id", "name"])

# Row filtering
result = manager.scan("bronze.customers", row_filter="id > 1")
```

---

## 5. Dagster IOManager Integration

```python
from dagster import asset, Definitions
from floe_iceberg import create_io_manager, IcebergIOManagerConfig
import pandas as pd

# Configure IOManager
io_config = IcebergIOManagerConfig(
    catalog_uri="http://localhost:8181/api/catalog",
    warehouse="quickstart_warehouse",
    client_id="root",
    client_secret="secret",
    default_namespace="bronze",
)

@asset
def customers() -> pd.DataFrame:
    """Asset automatically stored in bronze.customers table."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
    })

@asset
def customer_count(customers: pd.DataFrame) -> pd.DataFrame:
    """Downstream asset reads from bronze.customers."""
    return pd.DataFrame({"count": [len(customers)]})

# Create Dagster Definitions
defs = Definitions(
    assets=[customers, customer_count],
    resources={"io_manager": create_io_manager(io_config)},
)
```

---

## 6. Time Travel

```python
# List all snapshots
snapshots = manager.list_snapshots("bronze.customers")
for snap in snapshots:
    print(f"{snap.snapshot_id}: {snap.timestamp}")

# Read historical data
if len(snapshots) > 1:
    old_data = manager.scan(
        "bronze.customers",
        snapshot_id=snapshots[-1].snapshot_id
    )
    print("Historical data:", old_data.to_pandas())
```

---

## 7. Schema Evolution

```python
# Add new column (automatic evolution)
data_with_status = pa.Table.from_pydict({
    "id": [4],
    "name": ["Diana"],
    "email": ["diana@ex.com"],
    "created_at": [datetime.now()],
    "status": ["active"],  # New column!
})

manager.append("bronze.customers", data_with_status, evolve_schema=True)

# Verify schema evolved
result = manager.scan("bronze.customers")
print(result.schema)  # Now includes 'status' column
```

---

## Configuration via floe.yaml

```yaml
# floe.yaml
project:
  name: my-data-project

catalog:
  type: polaris
  uri: http://localhost:8181/api/catalog
  warehouse: my_warehouse
  credential_secret_ref: polaris-credentials
  scope: "PRINCIPAL_ROLE:ALL"
  token_refresh_enabled: true
  access_delegation: vended-credentials

storage:
  default_namespace: bronze
  write_mode: append
  schema_evolution_enabled: true
```

---

## Next Steps

- [API Contract: floe-polaris](./contracts/floe-polaris-api.md)
- [API Contract: floe-iceberg](./contracts/floe-iceberg-api.md)
- [Data Model Reference](./data-model.md)
- [Research Decisions](./research.md)
