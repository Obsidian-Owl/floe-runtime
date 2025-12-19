# Testing Guide for floe-runtime

This document describes the testing strategy, patterns, and workflows for floe-runtime.

## Quick Start

```bash
# Run unit tests (fast, no Docker required)
make test-unit

# Run integration tests in Docker (zero-config, recommended)
make test-integration

# Run all CI checks (lint, type, security, test)
make check

# See all available commands
make help
```

### Manual pytest Commands

```bash
# Run ALL unit tests across all packages
uv run pytest packages/floe-core/tests/ packages/floe-dbt/tests/unit/ packages/floe-dagster/tests/unit/ tests/contract/ -v

# Run all unit tests for a single package
uv run pytest packages/floe-core/tests/ -v

# Run adapter profile tests
uv run pytest packages/floe-dbt/tests/unit/test_profiles/ -v

# Run with specific markers
uv run pytest -m "not slow and not integration" -v

# Run tests for a specific adapter
uv run pytest -k "snowflake" -v
```

## Important: No `__init__.py` in Test Directories

**CRITICAL**: Test directories (`packages/*/tests/`) must NOT contain `__init__.py` files.

pytest uses `--import-mode=importlib` which causes namespace collisions when multiple
packages have `tests/__init__.py` files (all resolve to `tests.conftest` module name).

```
# CORRECT - No __init__.py in test directories
packages/floe-core/tests/conftest.py     # OK - namespace package
packages/floe-dbt/tests/conftest.py      # OK - namespace package

# WRONG - __init__.py causes collision
packages/floe-core/tests/__init__.py     # BAD - causes "tests.conftest" collision
```

This is why `floe-core` tests work correctly (no `__init__.py`) while other packages
previously had issues.

## Test Structure

```
floe-runtime/
├── testing/                           # Shared testing infrastructure
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── artifacts.py               # CompiledArtifacts factory
│   │   └── services.py                # Docker service lifecycle
│   ├── base_classes/
│   │   ├── __init__.py
│   │   └── adapter_test_base.py       # Base test classes
│   ├── markers/
│   │   └── __init__.py                # Marker documentation
│   └── docker/                        # Docker Compose E2E infrastructure
│       ├── docker-compose.yml         # Multi-profile service definitions
│       ├── init-scripts/              # Database initialization
│       ├── trino-config/              # Trino catalog configs
│       ├── cube-schema/               # Cube semantic layer schemas
│       └── README.md                  # Infrastructure documentation
├── tests/                             # Root-level tests
│   └── conftest.py
└── packages/
    ├── floe-core/tests/
    │   ├── unit/                      # Fast, isolated tests
    │   └── contract/                  # Schema stability tests
    ├── floe-dbt/tests/
    │   ├── unit/                      # Profile generator tests
    │   │   └── test_profiles/         # Adapter-specific tests
    │   └── integration/               # Real dbt execution tests
    ├── floe-dagster/tests/
    │   ├── unit/                      # Asset factory tests
    │   └── integration/               # Real Dagster tests
    ├── floe-polaris/tests/
    │   ├── unit/                      # Catalog wrapper tests
    │   └── integration/               # Real Polaris catalog tests
    └── floe-iceberg/tests/
        ├── unit/                      # Table manager tests
        └── integration/               # Real Iceberg table tests
```

## Testing Pyramid

```
        /\          E2E (5-10%): Full pipeline with containers
       /  \
      /____\        Integration (20-30%): Real dbt, testcontainers
     /      \
    /________\      Contract (10%): Cross-package validation
   /          \
  /____________\    Unit (60%): Mocks, fast feedback
```

## Test Execution Model (CRITICAL)

**Understanding where tests run is essential for reliable testing.**

| Test Type | Location | Execution Environment | Why |
|-----------|----------|----------------------|-----|
| Unit tests | `packages/*/tests/unit/` | Host (`uv run pytest`) | Fast, no external deps |
| Contract tests | `packages/*/tests/contract/` | Host (`uv run pytest`) | Fast, no external deps |
| **Integration tests** | `packages/*/tests/integration/` | **Docker (test-runner)** | Requires S3, Polaris, etc. |
| **E2E tests** | `packages/*/tests/e2e/` | **Docker (test-runner)** | Full pipeline testing |

### Why Integration Tests MUST Run Inside Docker

Integration tests interact with services using Docker internal hostnames:
- **LocalStack** (S3, STS, IAM) at `localstack:4566`
- **Polaris** (Iceberg catalog) at `polaris:8181`
- **PostgreSQL** at `postgres:5432`
- **Trino** at `trino:8080`
- **Cube** at `cube:4000`

These hostnames only resolve inside the Docker network. Running integration tests
from the host will fail with errors like:

```
Could not resolve host: localstack
AWS Error NETWORK_CONNECTION during CreateMultipartUpload operation
```

### Correct Test Execution

```bash
# ✅ Unit tests - OK to run from host
uv run pytest packages/floe-core/tests/unit/ -v

# ✅ Integration tests - MUST run inside Docker
./testing/docker/scripts/run-integration-tests.sh
# Or:
make test-integration

# ❌ WRONG - Will fail for S3/Polaris tests
uv run pytest packages/floe-iceberg/tests/integration/ -v
```

### CI/Local Parity

Both CI and local development use the same execution model:

| Environment | Unit/Contract Tests | Integration Tests |
|-------------|---------------------|-------------------|
| **Local** | `uv run pytest` on host | `make test-integration` (Docker) |
| **CI (GitHub Actions)** | `uv run pytest` on runner | Docker test-runner container |

This ensures tests behave identically everywhere.

## pytest Markers

Available markers (defined in `pyproject.toml`):

| Marker | Description | Example |
|--------|-------------|---------|
| `slow` | Tests taking > 1 second | `@pytest.mark.slow` |
| `integration` | Require external services | `@pytest.mark.integration` |
| `contract` | Cross-package validation | `@pytest.mark.contract` |
| `e2e` | End-to-end pipeline tests | `@pytest.mark.e2e` |
| `adapter` | Specific compute adapter | `@pytest.mark.adapter("snowflake")` |
| `requires_dbt` | Require dbt-core installed | `@pytest.mark.requires_dbt` |
| `requires_container` | Require Docker | `@pytest.mark.requires_container` |

### Running by Marker

```bash
# Skip slow tests
uv run pytest -m "not slow" -v

# Only integration tests
uv run pytest -m integration -v

# Only contract tests
uv run pytest -m contract -v

# Exclude integration and slow
uv run pytest -m "not integration and not slow" -v
```

## Base Test Classes

### BaseProfileGeneratorTests

All profile generator adapter tests inherit from `BaseProfileGeneratorTests`:

```python
from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests

class TestMyAdapterProfileGenerator(BaseProfileGeneratorTests):
    """Test suite for MyAdapter profile generation."""

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        from floe_dbt.profiles.myadapter import MyAdapterProfileGenerator
        return MyAdapterProfileGenerator()

    @property
    def target_type(self) -> str:
        return "myadapter"

    @property
    def required_fields(self) -> set[str]:
        return {"type", "host", "port", "threads"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        return {
            "version": "1.0.0",
            "compute": {
                "target": "myadapter",
                "properties": {"host": "localhost"},
            },
            "transforms": [],
        }

    # Adapter-specific tests go here...
    def test_myadapter_specific_feature(self, generator, config):
        ...
```

**Inherited tests** (automatically run for all adapters):
1. `test_implements_protocol` - Verifies ProfileGenerator Protocol
2. `test_generate_returns_dict` - Validates return type
3. `test_generate_includes_target_name` - Target name in output
4. `test_generate_has_correct_type` - Correct adapter type
5. `test_generate_has_required_fields` - All required fields present
6. `test_generate_uses_config_threads` - Thread configuration
7. `test_generate_custom_target_name` - Custom target naming
8. `test_generate_with_different_environments` - Environment support

### BaseCredentialProfileGeneratorTests

For adapters with credentials (user/password, API tokens):

```python
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests

class TestSnowflakeProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for Snowflake profile generation."""

    @property
    def credential_fields(self) -> set[str]:
        return {"user", "password"}  # Fields that must use env_var()

    # ... other required properties and methods
```

**Additional inherited tests**:
1. `test_credentials_use_env_var_template` - Verifies `{{ env_var(...) }}`
2. `test_never_hardcodes_credentials` - Security validation

## Fixture Factories

### make_compiled_artifacts

Create test CompiledArtifacts:

```python
from testing.fixtures.artifacts import make_compiled_artifacts

def test_something():
    artifacts = make_compiled_artifacts(
        target="snowflake",
        environment="prod",
        include_transforms=True,
    )
    # Use artifacts in test...
```

### COMPUTE_CONFIGS

Pre-defined configurations for all adapters:

```python
from testing.fixtures.artifacts import COMPUTE_CONFIGS

def test_all_adapters():
    for adapter_name, config in COMPUTE_CONFIGS.items():
        artifacts = make_compiled_artifacts(target=adapter_name)
        # Test with each adapter...
```

## Adding a New Adapter

1. **Create the generator** in `packages/floe-dbt/src/floe_dbt/profiles/`:
   ```python
   # myadapter.py
   class MyAdapterProfileGenerator:
       def generate(self, artifacts: dict, config: ProfileGeneratorConfig) -> dict:
           ...
   ```

2. **Create the test file** in `packages/floe-dbt/tests/unit/test_profiles/`:
   ```python
   # test_myadapter.py
   class TestMyAdapterProfileGenerator(BaseProfileGeneratorTests):
       # Implement required abstract methods...
   ```

3. **Add config to COMPUTE_CONFIGS** in `testing/fixtures/artifacts.py`:
   ```python
   COMPUTE_CONFIGS: dict[str, dict[str, Any]] = {
       # ... existing configs
       "myadapter": {
           "target": "myadapter",
           "properties": {"host": "localhost"},
       },
   }
   ```

4. **Run tests**:
   ```bash
   uv run pytest packages/floe-dbt/tests/unit/test_profiles/test_myadapter.py -v
   ```

## Contract Tests

Contract tests validate cross-package integration:

```python
# packages/floe-core/tests/contract/test_compiled_artifacts_stability.py

@pytest.mark.contract
def test_schema_backward_compatible():
    """Verify schema changes are backward compatible."""
    current = CompiledArtifacts.model_json_schema()
    # Compare with baseline schema...
```

## Integration Tests

Integration tests require external dependencies:

```python
@pytest.mark.integration
@pytest.mark.requires_dbt
def test_dbt_debug_with_generated_profile(tmp_path):
    """Test generated profile works with real dbt."""
    # Generate profile
    artifacts = make_compiled_artifacts(target="duckdb")
    profile = generator.generate(artifacts, config)

    # Write to file
    write_profile(profile, tmp_path / "profiles.yml")

    # Run dbt debug
    result = subprocess.run(
        ["dbt", "debug", "--profiles-dir", str(tmp_path)],
        capture_output=True,
    )
    assert result.returncode == 0
```

### Skip Patterns

```python
import pytest

try:
    import dbt.cli.main
    HAS_DBT = True
except ImportError:
    HAS_DBT = False

@pytest.mark.skipif(not HAS_DBT, reason="dbt-core not installed")
def test_requires_dbt():
    ...
```

## Docker E2E Test Infrastructure

The `testing/docker/` directory provides a complete local testing environment using Docker Compose
with layered profiles for different testing scenarios.

### Architecture

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
│                     │  (Port 8181)  │  (OAuth2 credentials via init)   │
│                     └───────┬───────┘                                  │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                      │
│         │                   │                   │                       │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐              │
│  │  PostgreSQL  │    │  LocalStack  │    │   Marquez    │  Storage &   │
│  │ (Port 5432)  │    │ (Port 4566)  │    │ (Port 5002)  │  Lineage     │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  ┌──────────────┐                                                      │
│  │   Jaeger     │  Observability                                       │
│  │ (Port 16686) │                                                      │
│  └──────────────┘                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Docker Compose Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (none) | PostgreSQL, Jaeger | Unit tests, dbt-postgres target |
| `storage` | + LocalStack (S3+STS+IAM), Polaris, polaris-init | Iceberg storage tests (62 tests) |
| `compute` | + Trino 479, Spark | Compute engine tests |
| `full` | + Cube v0.36, cube-init, Marquez | E2E tests, semantic layer (21 tests) |

### Service Versions

| Service | Version | Notes |
|---------|---------|-------|
| PostgreSQL | 16-alpine | Multi-database setup |
| LocalStack | latest | S3 + STS + IAM emulation |
| Polaris | localstack/polaris | Pre-configured for LocalStack S3 |
| Trino | 479 | OAuth2 support for Polaris authentication |
| Spark | 3.5.1 + Iceberg 1.5.0 | tabulario/spark-iceberg image |
| Cube | v0.36 | Trino driver, pre-aggregations |
| Marquez | 0.49.0 | OpenLineage backend |
| Jaeger | latest | OpenTelemetry collector |

### Zero-Config Integration Testing (Recommended)

Integration tests run inside Docker containers on the same network as the services.
This eliminates hostname resolution issues and provides a consistent, reproducible
environment on any machine.

```bash
# Run all integration tests (zero-config, works anywhere)
make test-integration

# Or use the script directly
./testing/docker/scripts/run-integration-tests.sh
```

This approach:
- **Zero configuration** - Works on any machine with Docker
- **Production parity** - Tests run in same network topology as production
- **Reproducible** - Same environment locally and in CI
- **No /etc/hosts modification** - Internal Docker hostnames resolve automatically

### Manual Testing (Alternative)

For development iteration, you can start services and run tests from your host:

```bash
# Start services
make docker-up

# Run tests (from host - may have hostname resolution limitations)
uv run pytest -m integration packages/floe-iceberg/tests/
```

**Note**: Some write operations may fail with `Could not resolve host: localstack`
when running from host. Use `make test-integration` for full compatibility.

### Quick Start

```bash
# Navigate to testing directory
cd testing/docker

# Copy environment template
cp env.example .env

# Start base services (PostgreSQL + Jaeger)
docker compose up -d

# Start with storage profile (adds LocalStack + Polaris)
docker compose --profile storage up -d

# Wait for polaris-init to complete (extracts credentials automatically)
# Credentials are written to testing/docker/config/polaris-credentials.env

# Start with compute profile (adds Trino + Spark)
docker compose --profile compute up -d

# Start all services (full profile)
docker compose --profile full up -d
```

### Service URLs

After starting services, access UIs at:

| Service | URL | Credentials |
|---------|-----|-------------|
| LocalStack Health | http://localhost:4566/_localstack/health | - |
| Polaris API | http://localhost:8181/api/catalog/v1/config | OAuth2 (auto-generated) |
| Trino UI | http://localhost:8080 | - |
| Jaeger UI | http://localhost:16686 | - |
| Spark Notebooks | http://localhost:8888 | - |
| Cube REST API | http://localhost:4000 | Dev mode (no auth) |
| Cube SQL API | localhost:15432 | Postgres wire protocol |
| Marquez API | http://localhost:5002 | - |
| Marquez UI | http://localhost:3001 | - |

### Automatic Credential Management

Polaris auto-generates OAuth2 credentials on each container startup. The `polaris-init` container:
1. Extracts credentials from Polaris logs
2. Writes `polaris-credentials.env` for Python tests
3. Writes `trino-iceberg.properties` with OAuth2 config for Trino

**Files generated by polaris-init:**

```
testing/docker/config/
├── polaris-credentials.env      # For Python tests (PyIceberg)
└── trino-iceberg.properties     # For Trino Iceberg connector
```

**For integration tests**, credentials are loaded automatically by importing from `testing.fixtures.services`:

```python
# At the top of your test file:
from testing.fixtures.services import ensure_polaris_credentials_in_env
ensure_polaris_credentials_in_env()

# Now environment variables are set:
# - POLARIS_CLIENT_ID
# - POLARIS_CLIENT_SECRET
# - POLARIS_URI
# - POLARIS_WAREHOUSE
# - AWS_ACCESS_KEY_ID (for LocalStack S3)
# - AWS_SECRET_ACCESS_KEY
```

**For manual testing**, source the file before running tests:

```bash
source testing/docker/config/polaris-credentials.env
uv run pytest -m integration packages/floe-iceberg/tests/
```

Both credential files are git-ignored and regenerated on each `docker compose up`.

### Trino-Polaris Authentication

Trino 479 requires OAuth2 authentication for the Polaris REST catalog. The `polaris-init` container
automatically generates `trino-iceberg.properties` with the correct OAuth2 credentials:

```properties
# Auto-generated by polaris-init
iceberg.rest-catalog.security=OAUTH2
iceberg.rest-catalog.oauth2.server-uri=http://polaris:8181/api/catalog/v1/oauth/tokens
iceberg.rest-catalog.oauth2.credential=<client_id>:<client_secret>
iceberg.rest-catalog.oauth2.scope=PRINCIPAL_ROLE:ALL
```

This enables Trino, Cube, and other services to authenticate with Polaris.

### Using Docker Services in Tests

#### With pytest fixtures

```python
import pytest
from testing.fixtures.services import DockerServices

@pytest.fixture(scope="module")
def docker_services():
    """Start Docker services for integration tests."""
    services = DockerServices(
        compose_file=Path("testing/docker/docker-compose.yml"),
        profile="storage",
    )
    services.start()
    yield services
    services.stop()

@pytest.mark.integration
def test_polaris_catalog(docker_services):
    """Test Polaris catalog connection."""
    config = docker_services.get_polaris_config()
    # config = {"uri": "http://localhost:8181/api/catalog", "warehouse": "warehouse"}

    from pyiceberg.catalog import load_catalog
    catalog = load_catalog("polaris", **config)
    assert catalog is not None
```

#### Auto-start fixtures

Pre-configured fixtures that automatically manage service lifecycle:

```python
from testing.fixtures.services import docker_services_storage

@pytest.mark.integration
def test_iceberg_table(docker_services_storage):
    """Test with storage profile (LocalStack + Polaris)."""
    polaris_config = docker_services_storage.get_polaris_config()
    s3_config = docker_services_storage.get_s3_config()
    # ...
```

Available fixtures:
- `docker_services_base` - PostgreSQL, Jaeger
- `docker_services_storage` - + LocalStack (S3+STS+IAM), Polaris
- `docker_services_compute` - + Trino, Spark
- `docker_services_full` - All services

### Health Checks

```bash
# Check Polaris
curl -f http://localhost:8181/api/catalog/v1/config

# Check LocalStack
curl -f http://localhost:4566/_localstack/health

# Check Trino
docker exec floe-trino trino --execute "SELECT 1"

# Check Cube
curl -f http://localhost:4000/readyz

# Check Marquez
curl -f http://localhost:5002/api/v1/namespaces
```

### Running Cube Integration Tests

The `--profile full` includes Cube with test data:

```bash
# Start full profile
cd testing/docker
docker compose --profile full up -d

# Wait for cube-init to complete (loads 15,500 test rows)
docker compose logs cube-init --tail 20

# Run Cube integration tests (21 tests, including pre-aggregations)
uv run pytest packages/floe-cube/tests/integration/ -v
```

**What cube-init does:**
1. Waits for Trino to be healthy
2. Creates `iceberg.default` namespace
3. Creates `orders` table with schema (id, customer_id, status, region, amount, created_at)
4. Loads 15,500 test rows for pagination testing

**Test coverage (T036-T039):**
- T036: REST API returns JSON for valid queries
- T037: REST API authentication handling
- T038: REST API pagination over 10k rows
- T039: Pre-aggregations (using `external: false` for Trino storage)

### Pre-configured Databases

PostgreSQL is initialized with multiple databases:

| Database | Purpose |
|----------|---------|
| polaris | Iceberg catalog metadata |
| marquez | OpenLineage data |
| floe_dev | Development/testing |
| floe_dbt | dbt compute target |

### Pre-configured S3 Buckets

LocalStack is initialized with buckets:

| Bucket | Purpose |
|--------|---------|
| warehouse | Iceberg table data |
| iceberg | Alternative Iceberg location |
| cube-preaggs | Cube pre-aggregation storage |
| dbt-artifacts | dbt artifacts storage |

### Cleanup

```bash
# Stop all containers
docker compose --profile full down

# Remove volumes (fresh start)
docker compose --profile full down -v

# Remove everything including images
docker compose --profile full down -v --rmi all
```

## Mock vs Real Services Matrix

| Service | Unit Tests | Integration | E2E |
|---------|------------|-------------|-----|
| dbt | Mock dbtRunner | Real subprocess | Real |
| DuckDB | Real (fast) | Real | Real |
| Snowflake | Mock adapter | Skip (no creds) | Skip |
| PostgreSQL | Mock adapter | Docker Compose | Real |
| Polaris | Mock catalog | Docker Compose | Real |
| LocalStack (S3) | Mock client | Docker Compose | Real |
| Iceberg | Mock PyIceberg | Docker Compose | Real |
| Trino | Mock connector | Docker Compose | Real |
| Spark | Mock session | Docker Compose | Real |
| Cube | Mock API | Docker Compose | Real |
| OpenLineage | Mock emit() | Local HTTP | Marquez |
| OpenTelemetry | InMemorySpanExporter | InMemory | Jaeger |

### OpenTelemetry Testing

Use the `in_memory_span_exporter` fixture to verify spans without requiring an external collector:

```python
def test_tracing_creates_spans(in_memory_span_exporter):
    """Test that operations create correct OTel spans."""
    exporter, provider = in_memory_span_exporter
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("transform") as span:
        span.set_attribute("model", "customers")
        span.set_attribute("status", "success")

    # Verify spans
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "transform"
    assert spans[0].attributes["model"] == "customers"

    exporter.clear()  # Clean up for next test
```

This approach:
- Requires no Docker or external collector
- Verifies span names, attributes, and parent/child relationships
- Runs fast in CI/CD
- Uses the built-in `InMemorySpanExporter` from `opentelemetry-sdk`

## CI/CD Pipeline

Tests run in stages:

1. **Lint & Type Check** (< 2 min)
   ```bash
   ruff check .
   black --check .
   mypy --strict packages/
   ```

2. **Unit Tests** (< 5 min, parallel by Python version)
   ```bash
   uv run pytest -m "not integration and not slow" --cov
   ```

3. **Contract Tests** (< 3 min)
   ```bash
   uv run pytest -m contract
   ```

4. **Integration Tests** (< 10 min)
   ```bash
   uv run pytest -m integration
   ```

5. **Adapter Tests** (parallel per adapter)
   ```bash
   uv run pytest -k duckdb
   uv run pytest -k postgres
   ```

## Coverage Requirements

- **Minimum**: 80% coverage required
- **Unit tests**: Fast, isolated, mock external dependencies
- **Integration tests**: Test component interactions
- **Contract tests**: Validate API contracts between packages

## Troubleshooting

### Missing Adapters

Some tests skip when adapters aren't installed:

```bash
# Install specific adapter for testing
uv pip install dbt-snowflake
uv run pytest -k snowflake -v
```

### OpenTelemetry Warnings

Expected when running locally without OTel collector:

```
Transient error StatusCode.UNAVAILABLE encountered while exporting traces
```

This is harmless - the NoOp tracer handles this gracefully.

## Plugin Author Checklist

For third-party plugins implementing ProfileGenerator:

- [ ] Inherits from `BaseProfileGeneratorTests` and passes all inherited tests
- [ ] Implements `ProfileGenerator` Protocol (runtime-checkable)
- [ ] Generates valid profiles.yml structure
- [ ] Uses `ProfileGeneratorConfig.get_secret_env_var()` for secrets
- [ ] Handles missing optional properties gracefully
- [ ] Includes integration test with `dbt debug` validation
- [ ] Documents required vs optional properties
