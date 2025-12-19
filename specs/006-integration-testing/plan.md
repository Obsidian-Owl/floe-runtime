# Implementation Plan: Robust Integration Testing with Traceability

**Branch**: `006-integration-testing` | **Date**: 2025-12-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-integration-testing/spec.md`

## Summary

Establish comprehensive integration testing requirements across all 7 floe-runtime packages to ensure full traceability between feature specifications (001-005) and their corresponding integration tests. This includes:
- Traceability matrix generation tool mapping FR-XXX requirements to test files
- Gap closure for missing integration tests (floe-cli, floe-dbt, floe-dagster, floe-cube)
- Contract boundary testing verifying CompiledArtifacts flows correctly between packages
- Observability verification via Jaeger/Marquez API queries
- Standalone-first validation ensuring core functionality works without optional services

## Technical Context

**Language/Version**: Python 3.10+ (Constitution: Dagster/dbt minimum)
**Primary Dependencies**: pytest 8.0+, structlog, requests, PyIceberg 0.9+, Dagster 1.6+, dbt-core 1.7+, Cube v0.36
**Storage**: Apache Iceberg tables via Polaris REST catalog, LocalStack S3 emulation
**Testing**: pytest (unit/contract on host), pytest in Docker test-runner (integration/E2E)
**Target Platform**: Linux/macOS (Docker Compose), CI/CD (GitHub Actions)
**Project Type**: Monorepo with 7 packages (packages/floe-*)
**Performance Goals**: Storage profile starts < 2 min, full profile < 5 min, integration tests < 5 min per package
**Constraints**: "Tests FAIL, Never Skip" philosophy, 80%+ coverage, standalone-first
**Scale/Scope**: 35 functional requirements, 7 packages, ~200+ integration tests target

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | ✅ PASS | FR-029 to FR-031 explicitly require graceful degradation tests when optional services (Jaeger, Marquez) unavailable |
| II. Type Safety Everywhere | ✅ PASS | All test fixtures use Pydantic models (CompiledArtifacts), type hints required |
| III. Technology Ownership | ✅ PASS | Tests respect boundaries: dbt owns SQL (profile validation), Dagster owns orchestration (asset tests), etc. |
| IV. Contract-Driven Integration | ✅ PASS | FR-032 to FR-035 explicitly require contract boundary tests verifying CompiledArtifacts flows |
| V. Security First | ✅ PASS | Credentials via environment variables (polaris-credentials.env), SecretStr for secrets |
| VI. Quality Standards | ✅ PASS | 80%+ coverage target, "Tests FAIL, Never Skip" philosophy enforced |

**Constitution Check Result**: ✅ ALL PASS - Ready for Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/006-integration-testing/
├── plan.md                    # This file
├── research.md                # Phase 0: Testing infrastructure analysis
├── data-model.md              # Phase 1: Traceability matrix schema
├── quickstart.md              # Phase 1: Developer guide for adding tests
├── contracts/                 # Phase 1: Test contract schemas
│   ├── traceability-matrix.schema.json
│   └── test-report.schema.json
└── tasks.md                   # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
# Existing structure - enhancements marked with [NEW]
packages/
├── floe-cli/
│   └── tests/
│       ├── integration/        # [ENHANCE] Add command execution tests
│       │   └── test_commands.py
│       └── unit/
├── floe-core/
│   └── tests/
│       ├── integration/        # Existing - comprehensive
│       └── unit/
├── floe-dbt/
│   └── tests/
│       ├── integration/        # [ENHANCE] Add 6 more compute targets
│       │   ├── test_duckdb.py  # Existing
│       │   ├── test_snowflake.py  # [NEW]
│       │   ├── test_bigquery.py   # [NEW]
│       │   ├── test_redshift.py   # [NEW]
│       │   ├── test_databricks.py # [NEW]
│       │   ├── test_postgres.py   # [NEW]
│       │   └── test_spark.py      # [NEW]
│       └── unit/
├── floe-dagster/
│   └── tests/
│       ├── integration/        # [ENHANCE] Add materialization & observability
│       │   ├── test_manifest.py    # Existing
│       │   ├── test_assets.py      # [NEW] Asset materialization
│       │   ├── test_openlineage.py # [NEW] Lineage verification
│       │   └── test_otel.py        # [NEW] Trace verification
│       └── unit/
├── floe-polaris/
│   └── tests/
│       ├── integration/        # Existing - 42 tests comprehensive
│       └── unit/
├── floe-iceberg/
│   └── tests/
│       ├── integration/        # Existing - 62 tests comprehensive
│       └── unit/
└── floe-cube/
    └── tests/
        ├── integration/        # [ENHANCE] Add RLS and pre-agg tests
        │   ├── test_rest_api.py      # Existing
        │   ├── test_graphql_api.py   # Existing
        │   ├── test_sql_api.py       # Existing
        │   ├── test_rls.py           # [NEW] Row-level security
        │   └── test_preagg.py        # [NEW] Pre-aggregation refresh
        └── unit/

testing/
├── docker/
│   ├── docker-compose.yml      # Existing - 4 profiles, 9 services
│   ├── scripts/
│   │   ├── run-integration-tests.sh  # Existing
│   │   └── run-traceability.sh       # [NEW] Traceability report
│   └── init-scripts/           # Existing - idempotent initialization
├── fixtures/
│   ├── artifacts.py            # Existing - CompiledArtifacts factories
│   ├── services.py             # Existing - Docker service lifecycle
│   └── observability.py        # [NEW] Jaeger/Marquez API helpers
├── traceability/               # [NEW] Traceability tooling
│   ├── __init__.py
│   ├── parser.py               # Parse spec requirements
│   ├── mapper.py               # Map requirements to tests
│   └── reporter.py             # Generate coverage reports
└── contracts/                  # [NEW] Contract test utilities
    ├── __init__.py
    └── boundary_tests.py       # CompiledArtifacts boundary validation
```

**Structure Decision**: Monorepo with 7 packages under `packages/`. Integration tests run inside Docker via `test-runner` container. New tooling for traceability and contract testing added under `testing/`.

## Complexity Tracking

> **No violations identified** - Implementation follows established patterns

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Traceability Tool | Python module in `testing/` | Reuses existing pytest infrastructure, no new dependencies |
| Contract Tests | Extend existing `testing/fixtures/artifacts.py` | Leverages existing CompiledArtifacts factories |
| Observability Tests | Query Jaeger/Marquez HTTP APIs | Standard REST API testing, no new infrastructure |

## Phase 0: Research Summary

### Existing Infrastructure Analysis

**Docker Compose Profiles** (from `testing/docker/docker-compose.yml`):

| Profile | Services | Use Case |
|---------|----------|----------|
| (base) | PostgreSQL, Jaeger | Unit tests, dbt-postgres |
| storage | + LocalStack, Polaris, polaris-init | 62 Iceberg/Polaris integration tests |
| compute | + Trino 479, Spark | Compute engine tests |
| full | + Cube v0.36, Marquez, cube-init | 21 Cube tests, semantic layer |

**Current Test Counts** (from spec.md Gap Analysis):

| Package | Integration Tests | Status |
|---------|-------------------|--------|
| floe-core | 2 files | ✅ Comprehensive |
| floe-cli | 1 file (perf only) | ⚠️ Gaps: validate, compile, init commands |
| floe-dbt | 1 file (DuckDB only) | ⚠️ Gaps: 6 other compute targets |
| floe-dagster | 1 file (manifest only) | ⚠️ Gaps: materialization, observability |
| floe-polaris | 42 tests | ✅ Comprehensive |
| floe-iceberg | 62 tests | ✅ Comprehensive |
| floe-cube | ~100 tests | ⚠️ Gaps: RLS JWT, pre-agg refresh |

**Shared Test Fixtures** (from `testing/fixtures/`):

- `artifacts.py`: `make_compiled_artifacts()` factory for all 7 compute targets
- `services.py`: `DockerServices` class with health checks, URL resolution, credential loading

### Contract Boundary Analysis

**CompiledArtifacts Flow** (from spec.md FR-032 to FR-035):

```
floe.yaml → floe-core (Compiler) → CompiledArtifacts
                                        ↓
    ┌───────────────────────────────────┴───────────────────────────────────┐
    ↓                                   ↓                                   ↓
floe-dbt                           floe-dagster                        floe-polaris
(profiles.yml)                     (asset creation)                    (catalog init)
    ↓
manifest.json → floe-cube (model sync)
```

**Contract Test Strategy**:
1. **Core → Dagster**: Verify CompiledArtifacts creates valid assets
2. **Core → dbt**: Verify CompiledArtifacts generates valid profiles.yml
3. **dbt → Cube**: Verify manifest.json syncs models correctly
4. **Core → Polaris**: Verify catalog config initializes connections

### Observability Verification Strategy

**Jaeger API** (FR-024):
- Endpoint: `http://jaeger:16686/api/traces`
- Query by service name and operation
- Verify span attributes and parent-child relationships

**Marquez API** (FR-025):
- Endpoint: `http://marquez:5000/api/v1/lineage`
- Query by job name
- Verify START/COMPLETE/FAIL events with correct facets

### Standalone-First Verification Strategy

**Test Categories** (FR-029 to FR-031):
1. **Core Functionality**: Works when Jaeger/Marquez unavailable
2. **Warning Logs**: Missing services emit warnings, not failures
3. **Optional Fields**: CompiledArtifacts without EnvironmentContext executes correctly

## Phase 1: Design Artifacts

### Data Model: Traceability Matrix Schema

See `contracts/traceability-matrix.schema.json` for full schema.

Key entities:
- **Requirement**: FR-XXX from spec, with file path and line number
- **Test**: Test file path, function name, markers
- **Mapping**: Requirement ↔ Test relationship with coverage status

### Contract Schemas

See `contracts/` directory for:
- `test-report.schema.json`: Coverage report format for CI
- `traceability-matrix.schema.json`: Requirement-to-test mapping

### Quickstart Guide

See `quickstart.md` for:
- Adding a new integration test
- Using shared fixtures
- Running tests in Docker
- Understanding traceability markers

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks from this plan
2. Tasks will be created in dependency order
3. Implementation follows "Tests FAIL, Never Skip" philosophy
