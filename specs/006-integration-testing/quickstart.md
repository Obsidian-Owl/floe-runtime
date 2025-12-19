# Quickstart: Adding Integration Tests

**Feature**: 006-integration-testing
**Audience**: Developers adding new integration tests to floe-runtime
**Time**: ~30 minutes for first test

## Prerequisites

- Docker and Docker Compose installed
- `uv` package manager installed
- Repository cloned locally

## TL;DR

```bash
# 1. Start test infrastructure
./testing/docker/scripts/run-integration-tests.sh --profile storage --up-only

# 2. Write your test with requirement marker
# packages/floe-{package}/tests/integration/test_my_feature.py

# 3. Run tests in Docker
./testing/docker/scripts/run-integration-tests.sh -k test_my_feature

# 4. Stop infrastructure
docker compose -f testing/docker/docker-compose.yml --profile storage down
```

## Step 1: Understand Test Categories

| Category | Location | Runs On | Purpose |
|----------|----------|---------|---------|
| Unit | `tests/unit/` | Host | Fast, isolated, mock dependencies |
| Contract | `tests/contract/` | Host | API contract validation |
| **Integration** | `tests/integration/` | **Docker** | Component interactions |
| E2E | `tests/e2e/` | Docker | Full workflows |

**Key Rule**: Integration tests MUST run inside Docker via `test-runner` container.

## Step 2: Choose Your Profile

| Profile | Services | Use When |
|---------|----------|----------|
| (base) | PostgreSQL, Jaeger | dbt-postgres tests |
| storage | + LocalStack, Polaris | Iceberg/Polaris tests |
| compute | + Trino, Spark | Compute engine tests |
| full | + Cube, Marquez | Semantic layer tests |

```bash
# Start storage profile
./testing/docker/scripts/run-integration-tests.sh --profile storage --up-only

# Verify services are healthy
docker compose -f testing/docker/docker-compose.yml ps
```

## Step 3: Write Your Test

### 3.1 Create Test File

```python
# packages/floe-polaris/tests/integration/test_my_feature.py
"""Integration tests for my new feature.

These tests require Docker infrastructure (storage profile).
"""
from __future__ import annotations

import pytest

from floe_polaris import PolarisCatalog


class TestMyFeature:
    """Tests for my feature covering FR-012."""

    @pytest.mark.integration
    @pytest.mark.requirement("FR-012")
    def test_catalog_connection(
        self,
        polaris_catalog: PolarisCatalog,
    ) -> None:
        """Test that we can connect to Polaris catalog.

        Covers: FR-012 (floe-polaris MUST have integration tests covering
        catalog connection, namespace operations, and table operations)
        """
        # Test implementation
        namespaces = polaris_catalog.list_namespaces()
        assert isinstance(namespaces, list)
```

### 3.2 Use Shared Fixtures

Add to your package's `conftest.py`:

```python
# packages/floe-polaris/tests/conftest.py
from __future__ import annotations

import os
import pytest

from testing.fixtures.services import (
    DockerServices,
    ensure_polaris_credentials_in_env,
)


@pytest.fixture(scope="session", autouse=True)
def load_credentials() -> None:
    """Load Polaris credentials into environment."""
    ensure_polaris_credentials_in_env()


@pytest.fixture
def polaris_catalog() -> PolarisCatalog:
    """Create a Polaris catalog client for testing."""
    from floe_polaris import PolarisCatalog, PolarisConfig

    config = PolarisConfig(
        uri=os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        credential=os.environ.get("POLARIS_CLIENT_ID", ""),
        secret=os.environ.get("POLARIS_CLIENT_SECRET", ""),
    )
    return PolarisCatalog(config)
```

### 3.3 Available Fixtures

From `testing/fixtures/`:

| Fixture | Purpose |
|---------|---------|
| `make_compiled_artifacts(target)` | Create CompiledArtifacts for any compute target |
| `DockerServices` | Manage Docker Compose lifecycle |
| `load_polaris_credentials()` | Load auto-generated Polaris credentials |
| `docker_services_storage` | Pre-configured DockerServices for storage profile |

## Step 4: Add Requirement Markers

Link tests to requirements for traceability:

```python
import pytest

# Single requirement
@pytest.mark.requirement("FR-012")
def test_polaris_connection():
    ...

# Multiple requirements
@pytest.mark.requirements(["FR-032", "FR-033"])
def test_contract_boundary():
    ...

# With integration marker
@pytest.mark.integration
@pytest.mark.requirement("FR-012")
def test_with_docker():
    ...
```

## Step 5: Run Your Test

### 5.1 Via Test Runner Script (Recommended)

```bash
# Run all integration tests
./testing/docker/scripts/run-integration-tests.sh

# Run specific test
./testing/docker/scripts/run-integration-tests.sh -k test_my_feature

# Run with verbose output
./testing/docker/scripts/run-integration-tests.sh -v --tb=short

# Run for specific package
./testing/docker/scripts/run-integration-tests.sh packages/floe-polaris/tests/integration/
```

### 5.2 Via Docker Compose Manually

```bash
cd testing/docker

# Start services
docker compose --profile storage up -d

# Wait for initialization
docker compose logs -f polaris-init  # Wait for "Catalog initialization complete"

# Run tests inside Docker
docker compose --profile test run --rm test-runner \
    uv run pytest packages/floe-polaris/tests/integration/test_my_feature.py -v

# Stop services
docker compose --profile storage down
```

## Step 6: Debug Failures

### Check Service Logs

```bash
# View all logs
docker compose -f testing/docker/docker-compose.yml logs

# View specific service
docker compose -f testing/docker/docker-compose.yml logs polaris

# Follow logs
docker compose -f testing/docker/docker-compose.yml logs -f jaeger
```

### Check Service Health

```bash
# List services with health status
docker compose -f testing/docker/docker-compose.yml ps

# Verify Polaris is healthy
curl http://localhost:8181/api/catalog/v1/config

# Verify LocalStack is healthy
curl http://localhost:4566/_localstack/health
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Could not resolve host: localstack` | Running from host, not Docker | Use `run-integration-tests.sh` |
| `401 Unauthorized` to Polaris | Credentials not loaded | Wait for polaris-init to complete |
| Test skipped | Infrastructure not available | Tests should FAIL, not skip - check setup |
| Timeout on health check | Service slow to start | Increase `start_period` in docker-compose.yml |

## Step 7: Verify Traceability

After adding your test, verify it's tracked:

```bash
# Generate traceability report (when available)
./testing/docker/scripts/run-traceability.sh

# Check that your requirement is covered
# Output should show FR-012: COVERED
```

## Best Practices

### DO

- ✅ Use `@pytest.mark.integration` marker
- ✅ Add `@pytest.mark.requirement("FR-XXX")` for traceability
- ✅ Use shared fixtures from `testing/fixtures/`
- ✅ Use unique names (UUID) for test resources
- ✅ Clean up created resources in fixtures

### DON'T

- ❌ Skip tests when infrastructure is unavailable (FAIL instead)
- ❌ Hardcode credentials (use environment variables)
- ❌ Run integration tests from host machine
- ❌ Share state between tests (use fresh resources)
- ❌ Use `localhost` in Docker tests (use service names)

## Example: Complete Integration Test

```python
# packages/floe-iceberg/tests/integration/test_table_operations.py
"""Integration tests for Iceberg table operations.

Covers: FR-013 (floe-iceberg MUST have integration tests covering
table CRUD, data operations, schema evolution, and Dagster IOManager)
"""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from pyiceberg.catalog import Catalog
from pyiceberg.exceptions import NoSuchTableError


class TestIcebergTableOperations:
    """Integration tests for Iceberg table CRUD operations."""

    @pytest.fixture
    def test_namespace(self, catalog: Catalog) -> str:
        """Create a unique namespace for test isolation."""
        namespace = f"test_{uuid.uuid4().hex[:8]}"
        catalog.create_namespace(namespace)
        yield namespace
        # Cleanup
        for table in catalog.list_tables(namespace):
            catalog.drop_table(f"{namespace}.{table}")
        catalog.drop_namespace(namespace)

    @pytest.mark.integration
    @pytest.mark.requirement("FR-013")
    def test_create_table(
        self,
        catalog: Catalog,
        test_namespace: str,
    ) -> None:
        """Test creating an Iceberg table.

        Covers: FR-013 table CRUD operations
        """
        from pyiceberg.schema import Schema
        from pyiceberg.types import IntegerType, NestedField, StringType

        schema = Schema(
            NestedField(1, "id", IntegerType(), required=True),
            NestedField(2, "name", StringType(), required=False),
        )

        table = catalog.create_table(
            f"{test_namespace}.test_table",
            schema=schema,
        )

        assert table is not None
        assert table.schema() == schema

    @pytest.mark.integration
    @pytest.mark.requirement("FR-013")
    def test_load_nonexistent_table_fails(
        self,
        catalog: Catalog,
        test_namespace: str,
    ) -> None:
        """Test that loading nonexistent table raises error.

        Covers: FR-013 table CRUD operations (error handling)
        """
        with pytest.raises(NoSuchTableError):
            catalog.load_table(f"{test_namespace}.does_not_exist")
```

## Next Steps

1. Read [research.md](./research.md) for infrastructure details
2. Review [data-model.md](./data-model.md) for traceability schema
3. Check existing tests in `packages/floe-iceberg/tests/integration/` for patterns
4. Run `./testing/docker/scripts/run-integration-tests.sh` to verify setup
