# floe-iceberg

Apache Iceberg integration for floe-runtime.

## Overview

floe-iceberg provides:

- **Table management**: Create and manage Iceberg tables
- **IOManager**: Dagster IOManager for Iceberg storage
- **Partitioning**: Apply partitioning strategies
- **Snapshots**: Time travel and snapshot management

## Installation

```bash
pip install floe-iceberg
```

## Usage

```python
from floe_iceberg import IcebergTableManager
from pyiceberg.catalog import load_catalog

catalog = load_catalog("default")
manager = IcebergTableManager(catalog, "my_namespace")

# List tables
tables = manager.list_tables()
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#6-floe-iceberg) for details.

### Component Ownership

Per `.claude/rules/component-ownership.md`:
- **Iceberg owns storage format** - ACID transactions, time travel, schema evolution
- We wrap PyIceberg, never implement Iceberg logic ourselves

## License

Apache 2.0
