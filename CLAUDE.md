# floe-runtime Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-17

## Active Technologies
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Pydantic v2, pydantic-settings, PyYAML, structlog (001-core-foundation)
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts) (002-cli-interface)
- File-based (floe.yaml input, compiled_artifacts.json output to `.floe/`) (002-cli-interface)
- File-based (profiles.yml generated to `.floe/profiles/`, reads dbt manifest.json) (003-orchestration-layer)
- Apache Iceberg tables via Polaris REST catalog (file-based metadata, Parquet data files) (004-storage-catalog)
- PyIceberg 0.9+ for Iceberg table operations (004-storage-catalog)
- Apache Polaris REST catalog for Iceberg metadata management (004-storage-catalog)

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
# Run tests
pytest packages/<package>/tests/

# Run integration tests (requires Docker)
cd testing/docker && docker compose --profile storage up -d
pytest -m integration packages/floe-polaris/tests/
pytest -m integration packages/floe-iceberg/tests/

# Linting
ruff check packages/

# Type checking
mypy --strict packages/
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

Docker Compose profiles for local testing:
- `(none)`: PostgreSQL, Jaeger (unit tests, dbt-postgres)
- `storage`: + LocalStack (S3+STS+IAM), Polaris (Iceberg storage tests)
- `compute`: + Trino, Spark (compute engine tests)
- `full`: + Cube, Marquez (E2E tests, semantic layer)

```bash
# Start storage profile
cd testing/docker
docker compose --profile storage up -d

# Check service health
curl http://localhost:8181/api/catalog/v1/config  # Polaris
curl http://localhost:4566/_localstack/health     # LocalStack
```

## Recent Changes
- 004-storage-catalog: Added floe-polaris, floe-iceberg packages with full integration tests
- 004-storage-catalog: Added Docker Compose E2E test infrastructure
- 003-orchestration-layer: Added floe-dagster, floe-dbt packages
- 002-cli-interface: Added floe-cli with Click 8.1+, Rich 13.9+
- 001-core-foundation: Added floe-core with Pydantic v2 schemas


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
