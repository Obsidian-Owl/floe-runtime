# floe-polaris

Apache Polaris catalog integration for floe-runtime.

## Overview

floe-polaris provides integration with Apache Polaris for catalog management:

- **PolarisClient**: Wrapper for Polaris REST API
- **Catalog Factory**: Create catalog clients from configuration

## Installation

```bash
pip install floe-polaris
```

## Usage

```python
from floe_polaris import create_catalog_client

catalog = create_catalog_client(
    uri="http://localhost:8181",
    warehouse="my_warehouse"
)
```

## Architecture

floe-polaris integrates with Polaris via the standard Iceberg REST catalog API:

- Namespace management
- Principal and role management
- Access control policies
- Metadata storage

## Development

```bash
uv sync
uv run pytest packages/floe-polaris/tests/
```

## License

Apache 2.0
