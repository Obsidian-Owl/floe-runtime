# floe-cube

Cube semantic layer integration for floe-runtime.

## Overview

floe-cube provides integration with Cube for semantic layer and consumption APIs:

- **Configuration**: Cube configuration generation
- **Model Sync**: Sync dbt models to Cube

## Installation

```bash
pip install floe-cube
```

## Usage

```python
from floe_cube import sync_models

# Sync dbt models to Cube semantic layer
sync_models(dbt_manifest_path="target/manifest.json")
```

## Architecture

floe-cube bridges dbt models with Cube semantic layer:

- Generates Cube data model from dbt manifest
- Configures Cube connections
- Exposes REST/GraphQL/SQL APIs via Cube

## Development

```bash
uv sync
uv run pytest packages/floe-cube/tests/
```

## Integration Testing

Integration tests require Docker infrastructure with the `full` profile:

```bash
# Start infrastructure (includes Cube, Trino, Polaris, LocalStack)
cd testing/docker
docker compose --profile full up -d

# Wait for services to be ready (cube-init creates test data)
docker compose logs -f cube-init

# Run integration tests (21 tests: T036-T039)
uv run pytest packages/floe-cube/tests/integration/ -v
```

### Test Infrastructure

- **Trino 479**: Query engine with OAuth2 authentication to Polaris
- **Cube v0.36**: Semantic layer with Trino driver
- **Test data**: 15,500 rows in `iceberg.default.orders` table

### Test Coverage (T036-T039)

| Test | Description |
|------|-------------|
| T036 | REST API returns valid JSON responses |
| T037 | Authentication requirements (dev mode accepts all) |
| T038 | Pagination for large result sets (15,500 rows) |
| T039 | Pre-aggregations build and accelerate queries |

### Pre-aggregation Configuration

Cube pre-aggregations use `external: false` to store in Trino/Iceberg instead of requiring GCS (the Trino driver only supports GCS for external bucket, not S3/LocalStack).

## License

Apache 2.0
