# floe-runtime Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-18

## Active Technologies
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Pydantic v2, pydantic-settings, PyYAML, structlog (001-core-foundation)
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts) (002-cli-interface)
- File-based (floe.yaml input, compiled_artifacts.json output to `.floe/`) (002-cli-interface)
- File-based (profiles.yml generated to `.floe/profiles/`, reads dbt manifest.json) (003-orchestration-layer)
- Apache Iceberg tables via Polaris REST catalog (file-based metadata, Parquet data files) (004-storage-catalog)
- PyIceberg 0.9+ for Iceberg table operations (004-storage-catalog)
- Apache Polaris REST catalog for Iceberg metadata management (004-storage-catalog)
- File-based configuration generation (.floe/cube/), S3 for pre-aggregations (005-consumption-layer)

## Project Structure

```text
packages/
├── floe-cli/        # CLI entry point (Click + Rich)
├── floe-core/       # Schemas, validation, compilation (Pydantic)
├── floe-cube/       # Semantic layer (Cube integration)
├── floe-dagster/    # Orchestration, assets (Dagster)
├── floe-dbt/        # SQL transformations (dbt)
├── floe-iceberg/    # Storage layer (PyIceberg)
└── floe-polaris/    # Catalog management (Polaris REST)

testing/
├── docker/          # E2E test infrastructure (Docker Compose)
│   ├── docker-compose.yml
│   ├── Dockerfile.test-runner
│   ├── scripts/
│   │   └── run-integration-tests.sh
│   ├── init-scripts/
│   ├── trino-config/
│   ├── cube-schema/
│   └── README.md
└── fixtures/        # Shared test fixtures
    ├── artifacts.py # CompiledArtifacts factories
    └── services.py  # Docker service lifecycle
```

## Commands

```bash
# Run unit tests
uv run pytest packages/<package>/tests/

# Run storage integration tests (62 tests - Polaris, Iceberg)
./testing/docker/scripts/run-integration-tests.sh

# Run Cube integration tests (21 tests - requires full profile)
cd testing/docker && docker compose --profile full up -d
uv run pytest packages/floe-cube/tests/integration/ -v

# Run specific integration tests
./testing/docker/scripts/run-integration-tests.sh -k "test_append"
./testing/docker/scripts/run-integration-tests.sh -v --tb=short

# Linting
uv run ruff check packages/

# Type checking
uv run mypy --strict packages/
```

## Code Style

Python 3.10+ (per Constitution: Dagster/dbt minimum): Follow standard conventions

## Packages

### floe-polaris (004-storage-catalog)
- `PolarisCatalog`: Thread-safe catalog wrapper with retry logic
- `PolarisConfig`: Pydantic configuration for Polaris connection
- Observability: structlog logging, OTel tracing support
- Integration tests: `pytest -m integration packages/floe-polaris/tests/`

### floe-iceberg (004-storage-catalog)
- `IcebergTableManager`: Table creation, schema evolution, data operations
- `IcebergIOManager`: Dagster IOManager for Iceberg table assets
- Arrow/Polars/Pandas DataFrame support
- Integration tests: `pytest -m integration packages/floe-iceberg/tests/`

## Test Infrastructure

### Zero-Config Integration Tests

The recommended way to run integration tests is via the test runner script:

```bash
# Run all integration tests (62 tests total)
./testing/docker/scripts/run-integration-tests.sh
```

This script:
1. Starts test infrastructure (LocalStack, Polaris)
2. Waits for Polaris initialization to complete
3. Loads dynamically-generated credentials
4. Builds and runs tests inside Docker network
5. Handles all hostname resolution automatically

### Docker Compose Profiles

Docker Compose profiles for local testing:
- `(none)`: PostgreSQL, Jaeger (unit tests, dbt-postgres)
- `storage`: + LocalStack (S3+STS+IAM), Polaris, polaris-init (62 Iceberg storage tests)
- `compute`: + Trino 479, Spark (compute engine tests)
- `full`: + Cube v0.36, cube-init, Marquez (21 Cube tests, semantic layer)

```bash
# Manual service startup (if needed)
cd testing/docker
docker compose --profile storage up -d

# Check service health
curl http://localhost:8181/api/catalog/v1/config  # Polaris
curl http://localhost:4566/_localstack/health     # LocalStack
curl http://localhost:4000/readyz                 # Cube
```

### floe-cube (005-consumption-layer)
- `CubeConfig`: Pydantic configuration for Cube connection
- `CubeRESTClient`: REST API client for Cube queries
- Integration tests: 21 tests (T036-T039)
- Pre-aggregations: Uses `external: false` for Trino storage (GCS not available)

## Recent Changes
- 005-consumption-layer: Added floe-cube with 21 integration tests passing
- 005-consumption-layer: Cube pre-aggregations using internal Trino storage
- 005-consumption-layer: Trino 479 with OAuth2 authentication to Polaris
- 004-storage-catalog: Zero-config Docker test runner (62 integration tests passing)
- 004-storage-catalog: Added floe-polaris, floe-iceberg packages with full integration tests


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
