# E2E Tests for Deployment Automation

End-to-end validation tests for the floe-runtime deployment automation feature.

## Overview

These tests validate the complete data flow from synthetic data generation
through dbt transformations to Cube semantic layer queries.

## Test Coverage

| Test | Requirement | Description |
|------|-------------|-------------|
| `test_synthetic_data_in_cube` | 007-FR-029 | Synthetic data appears in Cube queries |
| `test_cube_preaggregation_refresh` | 007-FR-032 | Cube pre-aggregations refresh correctly |

## Prerequisites

Tests require the full demo profile running:

```bash
# Start demo infrastructure
cd testing/docker
docker compose --profile demo up -d

# Wait for services to be ready
./scripts/wait-for-services.sh
```

## Running Tests

```bash
# Run all E2E tests
pytest testing/e2e/ -v --tb=short

# Run with requirement markers
pytest testing/e2e/ -v -m "requirement"

# Run specific test
pytest testing/e2e/test_demo_flow.py::test_synthetic_data_in_cube -v
```

## Test Structure

```
testing/e2e/
├── __init__.py          # Package initialization
├── conftest.py          # Shared fixtures (Docker services, Cube client)
├── test_demo_flow.py    # E2E data flow tests
└── README.md            # This file
```

## Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `cube_client` | session | REST client for Cube API |
| `demo_services` | session | Docker Compose demo profile services |
| `wait_for_data` | function | Wait for synthetic data to propagate |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CUBE_API_URL` | `http://localhost:4000` | Cube API endpoint |
| `DEMO_TIMEOUT` | `300` | Timeout for data propagation (seconds) |
