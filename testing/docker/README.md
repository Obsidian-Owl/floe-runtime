# floe-runtime E2E Test Infrastructure

Docker Compose configuration for local integration and E2E testing of the complete floe-runtime data stack.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         floe-runtime Test Stack                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Cube       │    │    Trino     │    │    Spark     │  Consumption │
│  │  (Port 4000) │    │ (Port 8080)  │    │ (Port 10000) │  & Compute   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             │                                           │
│                     ┌───────┴───────┐                                  │
│                     │    Polaris    │  Iceberg REST Catalog            │
│                     │  (Port 8181)  │                                  │
│                     └───────┬───────┘                                  │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                      │
│         │                   │                   │                       │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐              │
│  │  PostgreSQL  │    │  LocalStack  │    │   Marquez    │  Storage &   │
│  │ (Port 5432)  │    │ (Port 4566)  │    │ (Port 5000)  │  Lineage     │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  ┌──────────────┐                                                      │
│  │   Jaeger     │  Observability                                       │
│  │ (Port 16686) │                                                      │
│  └──────────────┘                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Navigate to testing directory
cd testing/docker

# Copy environment template
cp env.example .env

# Start base services (PostgreSQL + Jaeger)
docker compose up -d

# Start with storage profile (adds LocalStack + Polaris)
docker compose --profile storage up -d

# Start with compute profile (adds Trino + Spark)
docker compose --profile compute up -d

# Start all services (full profile)
docker compose --profile full up -d
```

## Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (none) | PostgreSQL, Jaeger | Unit tests, dbt-postgres target |
| storage | + LocalStack (S3+STS+IAM), Polaris | Iceberg storage tests |
| compute | + Trino, Spark | Compute engine tests |
| full | + Cube, Marquez | E2E tests, semantic layer |

## Services

### Core Infrastructure

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Relational database (catalog persistence, dbt target) |
| Jaeger | 16686 | Distributed tracing UI |

### Storage Layer (--profile storage)

| Service | Port | Description |
|---------|------|-------------|
| LocalStack | 4566 | AWS emulator (S3, STS, IAM) for production-aligned testing |
| Polaris | 8181, 8182 | Apache Polaris - Iceberg REST catalog |

### Compute Layer (--profile compute)

| Service | Port | Description |
|---------|------|-------------|
| Trino | 8080 | Distributed SQL query engine |
| Spark | 8888, 10000 | Apache Spark with Iceberg |

### Full Stack (--profile full)

| Service | Port | Description |
|---------|------|-------------|
| Cube | 4000, 3000 | Semantic layer (REST/GraphQL/SQL APIs) |
| Marquez | 5000, 5001 | OpenLineage backend for data lineage |
| Marquez Web | 3001 | Lineage visualization UI |

## Service URLs

After starting services, access UIs at:

- **LocalStack Health**: http://localhost:4566/_localstack/health
- **Polaris API**: http://localhost:8181
- **Trino UI**: http://localhost:8080
- **Jaeger UI**: http://localhost:16686
- **Spark Notebooks**: http://localhost:8888
- **Cube Playground**: http://localhost:3000
- **Marquez UI**: http://localhost:3001

## Usage in Tests

### With pytest fixtures

```python
import pytest
from testing.fixtures.services import docker_services_storage

@pytest.mark.integration
def test_polaris_catalog(docker_services_storage):
    """Test Polaris catalog connection."""
    config = docker_services_storage.get_polaris_config()
    # ... test implementation
```

### Direct service access

```python
from testing.fixtures.services import DockerServices

services = DockerServices(
    compose_file=Path("testing/docker/docker-compose.yml"),
    profile="storage",
)

# Get service URLs
polaris_url = services.get_url("polaris", 8181)
s3_config = services.get_s3_config()

# Wait for services
services.wait_for_service("polaris", timeout=60)
```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and customize:

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# LocalStack (uses test credentials by default)
# AWS_ACCESS_KEY_ID=test
# AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1

# Polaris
POLARIS_BOOTSTRAP_CREDENTIALS=POLARIS,root,s3cr3t
POLARIS_CLIENT_ID=root
POLARIS_CLIENT_SECRET=s3cr3t

# Cube
CUBEJS_API_SECRET=floe-cube-secret
```

### Custom Configurations

- **Trino catalogs**: `trino-config/catalog/`
- **Spark settings**: `spark-defaults.conf`
- **Cube schemas**: `cube-schema/`

## Operations

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f polaris
```

### Restart a service

```bash
docker compose restart polaris
```

### Clean up

```bash
# Stop all containers
docker compose --profile full down

# Remove volumes (fresh start)
docker compose --profile full down -v

# Remove everything including images
docker compose --profile full down -v --rmi all
```

### Health checks

```bash
# Check service status
docker compose ps

# Check specific service health
curl -f http://localhost:8181/api/catalog/v1/config         # Polaris
curl -f http://localhost:4566/_localstack/health            # LocalStack
curl -f http://localhost:4000/readyz                        # Cube
```

## Databases

PostgreSQL is pre-configured with multiple databases:

| Database | Purpose |
|----------|---------|
| polaris | Iceberg catalog metadata |
| marquez | OpenLineage data |
| floe_dev | Development/testing |
| floe_dbt | dbt compute target |

## S3 Buckets

LocalStack is pre-configured with buckets:

| Bucket | Purpose |
|--------|---------|
| warehouse | Iceberg table data |
| iceberg | Alternative Iceberg location |
| cube-preaggs | Cube pre-aggregation storage |
| dbt-artifacts | dbt artifacts storage |

## Security Testing with LocalStack

LocalStack provides AWS S3 + STS + IAM emulation, enabling production-aligned
credential vending testing. This allows us to test the same authentication flows
that would be used in production with real AWS.

Key features:
- **S3**: Object storage for Iceberg table data
- **STS**: Credential vending for temporary security credentials
- **IAM**: Role-based access control simulation

The `polaris-storage-role` IAM role is created automatically for credential vending.

## Troubleshooting

### Polaris won't start

Check PostgreSQL is healthy first:
```bash
docker compose logs postgres
```

### Trino can't connect to Polaris

Ensure Polaris is fully initialized (takes ~30s):
```bash
curl http://localhost:8181/api/catalog/v1/config
```

### LocalStack buckets not created

The `localstack-init` service runs once. Check logs:
```bash
docker compose logs localstack-init
```

### Out of memory

Reduce Spark memory in `spark-defaults.conf`:
```properties
spark.driver.memory=1g
spark.executor.memory=1g
```

## Integration with floe-runtime

This infrastructure is designed to test the complete floe-runtime stack:

1. **floe-core**: CompiledArtifacts validation
2. **floe-dbt**: Profile generation, dbt execution against PostgreSQL/Trino
3. **floe-dagster**: Asset materialization orchestration
4. **floe-iceberg**: Iceberg table operations via Polaris
5. **floe-polaris**: Catalog management
6. **floe-cube**: Semantic layer over Iceberg tables

Run the full test suite with:

```bash
# From repository root
pytest -m integration --profile=storage
pytest -m e2e --profile=full
```
