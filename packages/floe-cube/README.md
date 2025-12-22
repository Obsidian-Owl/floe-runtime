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

Cube pre-aggregations can be stored in two locations:

| Environment | `external` | Storage | Use Case |
|-------------|-----------|---------|----------|
| **Testing** | `false` | Source database (Trino/DuckDB) | No S3/GCS setup required |
| **Production** | `true` | Cube Store + S3/GCS | High concurrency, sub-second queries |

**Testing configuration** (used in Docker Compose):

```yaml
# floe.yaml
consumption:
  pre_aggregations:
    external: false  # Store in source database
```

This is the default for local testing because:
- No additional S3/GCS infrastructure required
- Pre-aggregations are stored as tables in Trino/DuckDB
- Sufficient for development and integration testing

**Production configuration** (recommended):

```yaml
# floe.yaml
consumption:
  pre_aggregations:
    external: true
    cube_store:
      enabled: true
      s3_bucket: "my-cube-preaggs"
      s3_region: "us-east-1"
    # For Trino/Snowflake with large datasets (>100k rows)
    export_bucket:
      enabled: true
      bucket_type: "s3"
      name: "my-cube-export"
      region: "us-east-1"
```

**Database-specific notes**:

- **DuckDB**: Uses batching strategy. Does NOT support export buckets.
- **Trino**: Supports S3 and GCS export buckets for large pre-aggregation builds.
- **Snowflake**: Supports S3, GCS, and Azure export buckets. Uses storage integration.

## License

Apache 2.0
