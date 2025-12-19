# Research: Integration Testing Infrastructure Analysis

**Feature**: 006-integration-testing
**Date**: 2025-12-19
**Status**: Complete

## Executive Summary

This document provides a comprehensive analysis of the existing integration testing infrastructure in floe-runtime, identifying gaps against the 35 functional requirements from the specification, and recommending implementation strategies for closing those gaps.

**Key Findings**:
- Strong infrastructure exists: Docker Compose with 4 profiles, 9 services, shared fixtures
- Comprehensive coverage in storage packages (floe-polaris: 42 tests, floe-iceberg: 62 tests)
- Significant gaps in orchestration packages (floe-cli, floe-dbt, floe-dagster)
- Missing traceability tooling (no FR-XXX to test mapping)
- Missing contract boundary tests (CompiledArtifacts flows)
- Missing observability verification tests (Jaeger/Marquez API queries)

## 1. Docker Compose Infrastructure

### 1.1 Profile Structure

**Location**: `testing/docker/docker-compose.yml`

| Profile | Services | Port Mappings | Primary Use |
|---------|----------|---------------|-------------|
| (base) | postgres, jaeger | 5432, 16686, 4317, 4318 | Unit tests, dbt-postgres target |
| storage | + localstack, polaris, polaris-init | 4566, 8181 | Iceberg/Polaris integration tests |
| compute | + trino, spark-iceberg | 8080, 8888, 10000 | Compute engine tests |
| full | + cube, marquez, marquez-web, cube-init | 4000, 15432, 5001, 5002, 3001 | Semantic layer tests |

### 1.2 Service Initialization Chain

```
postgres (base) ─────────────────────────────────────────────────────►
jaeger (base) ──────────────────────────────────────────────────────►
localstack (storage) ─► localstack-init ────────────────────────────►
polaris (storage) ───────────────────────► polaris-init ────────────►
trino (compute) ◄────────────────────────── polaris-init (OAuth2) ──►
cube (full) ◄──────────────────────────────── trino (healthy) ──────►
cube-init (full) ◄──────────────────────────── trino (healthy) ─────►
marquez (full) ◄──────────────────────────── postgres (healthy) ────►
```

**Key Dependencies**:
- `polaris-init` generates OAuth2 credentials from Polaris logs
- `trino` waits for `polaris-init` to write `trino-iceberg.properties`
- `cube` waits for `trino` to be healthy

### 1.3 Health Checks

All services define health checks for startup ordering:

| Service | Health Check | Interval | Start Period |
|---------|--------------|----------|--------------|
| postgres | `pg_isready -U postgres` | 5s | 10s |
| localstack | `curl http://localhost:4566/_localstack/health` | 5s | 20s |
| polaris | `curl http://localhost:8182/q/health` | 10s | 30s |
| trino | `trino --execute "SELECT 1"` | 15s | 60s |
| cube | `curl http://localhost:4000/readyz` | 10s | 30s |
| marquez | `curl http://localhost:5001/healthcheck` | 10s | 60s |
| jaeger | `wget --spider http://localhost:16686` | 10s | 10s |

### 1.4 Startup Time Measurements

From empirical testing (macOS M2):

| Profile | Cold Start | Warm Start |
|---------|------------|------------|
| storage | ~90s | ~30s |
| compute | ~150s | ~60s |
| full | ~180s | ~90s |

**Note**: Marquez runs via Rosetta 2 on Apple Silicon, adding ~30s to startup.

## 2. Shared Test Fixtures

### 2.1 CompiledArtifacts Factory

**Location**: `testing/fixtures/artifacts.py`

```python
def make_compiled_artifacts(
    target: str = "duckdb",
    *,
    environment: str = "dev",
    observability_enabled: bool = False,
    lineage_enabled: bool = False,
    with_classifications: bool = False,
    dbt_profiles_path: str = ".floe/profiles",
    metadata: dict[str, Any] | None = None,
    compute_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

**Supported Targets**: duckdb, snowflake, bigquery, redshift, databricks, postgres, spark

### 2.2 Docker Services Manager

**Location**: `testing/fixtures/services.py`

Key classes and functions:

| Component | Purpose |
|-----------|---------|
| `DockerServices` | Manager class with start/stop, health checks, URL resolution |
| `is_running_in_docker()` | Detect if running inside Docker container |
| `get_service_host()` | Context-aware hostname resolution |
| `load_polaris_credentials()` | Load auto-generated OAuth2 credentials |
| `ensure_polaris_credentials_in_env()` | Set credentials in environment |

**Fixtures Provided**:
- `docker_services_base`: Base profile (PostgreSQL, Jaeger)
- `docker_services_storage`: Storage profile (+ LocalStack, Polaris)
- `docker_services_compute`: Compute profile (+ Trino, Spark)
- `docker_services_full`: Full profile (+ Cube, Marquez)
- `docker_services`: Alias for storage profile (most common use)

## 3. Current Integration Test Inventory

### 3.1 Package-by-Package Analysis

#### floe-core (2 files)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_compile_flow.py` | ~10 | CompiledArtifacts generation |
| `test_floe_yaml_loading.py` | ~5 | YAML parsing, validation |

**Status**: ✅ Comprehensive - Core compilation flow covered

#### floe-cli (1 file)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_help_performance.py` | 1 | Only `--help` < 500ms |

**Gaps**:
- ❌ No `floe validate` command tests
- ❌ No `floe compile` command tests
- ❌ No `floe init` command tests
- ❌ No error handling tests

#### floe-dbt (1 file)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_profile_validation.py` | ~5 | DuckDB only |

**Gaps**:
- ❌ No Snowflake profile tests
- ❌ No BigQuery profile tests
- ❌ No Redshift profile tests
- ❌ No Databricks profile tests
- ❌ No PostgreSQL profile tests (with actual DB)
- ❌ No Spark profile tests
- ❌ No manifest.json generation tests

#### floe-dagster (1 file)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_dbt_execution.py` | ~5 | dbt manifest parsing |

**Gaps**:
- ❌ No actual asset materialization tests
- ❌ No OpenLineage event emission tests
- ❌ No OpenTelemetry trace verification tests
- ❌ No asset dependency resolution tests

#### floe-polaris (1 file)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_polaris_catalog.py` | 42 | Comprehensive |

**Covered**:
- ✅ Catalog connection
- ✅ Namespace operations (create, list, delete)
- ✅ Table operations (create, load, update)
- ✅ Schema evolution
- ✅ Error handling

#### floe-iceberg (2 files)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_iceberg_tables.py` | ~40 | Table CRUD, data ops |
| `test_dagster_assets.py` | ~22 | IOManager integration |

**Covered**:
- ✅ Table creation, loading, deletion
- ✅ Data operations (append, overwrite)
- ✅ Schema evolution
- ✅ Time travel queries
- ✅ Dagster IOManager asset handling

#### floe-cube (5 files)

| File | Test Count | Coverage |
|------|------------|----------|
| `test_rest_api_integration.py` | ~25 | REST API queries |
| `test_graphql_api_integration.py` | ~25 | GraphQL queries |
| `test_sql_api_integration.py` | ~20 | SQL API (Postgres wire) |
| `test_opentelemetry.py` | ~15 | OTel trace emission |
| `test_openlineage_marquez.py` | ~15 | OpenLineage events |

**Gaps**:
- ❌ No row-level security JWT tests
- ❌ No pre-aggregation refresh tests
- ❌ No security context propagation tests

### 3.2 Summary Matrix

| Package | Integration Files | Tests | Status |
|---------|-------------------|-------|--------|
| floe-core | 2 | ~15 | ✅ |
| floe-cli | 1 | 1 | ⚠️ Critical gaps |
| floe-dbt | 1 | ~5 | ⚠️ 6 targets missing |
| floe-dagster | 1 | ~5 | ⚠️ Materialization missing |
| floe-polaris | 1 | 42 | ✅ |
| floe-iceberg | 2 | 62 | ✅ |
| floe-cube | 5 | ~100 | ⚠️ RLS missing |
| **Total** | 13 | ~230 | |

## 4. Gap Analysis Against Requirements

### 4.1 Test Traceability (FR-001 to FR-003)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-001: Traceability matrix | ❌ Missing | No tool exists to map FR-XXX to tests |
| FR-002: Coverage gap reporting | ❌ Missing | No automated gap detection |
| FR-003: Per-feature reports | ❌ Missing | No feature-specific coverage |

**Recommendation**: Create `testing/traceability/` module with:
- `parser.py`: Extract FR-XXX from spec files
- `mapper.py`: Scan test files for requirement markers
- `reporter.py`: Generate coverage reports

### 4.2 Test Execution (FR-004 to FR-007)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-004: Docker network execution | ✅ | `test-runner` container in `floe-network` |
| FR-005: FAIL not skip | ✅ | `testing/fixtures/services.py` health checks |
| FR-006: Environment-based config | ✅ | `polaris-credentials.env`, env vars |
| FR-007: UUID isolation | ✅ | Tests use `uuid.uuid4()` for namespaces |

### 4.3 Package Coverage (FR-008 to FR-014)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-008: floe-core | ✅ | Covered |
| FR-009: floe-cli | ❌ | Missing command tests |
| FR-010: floe-dbt | ⚠️ | Only DuckDB, need 6 more |
| FR-011: floe-dagster | ⚠️ | Only manifest, need materialization |
| FR-012: floe-polaris | ✅ | Covered (42 tests) |
| FR-013: floe-iceberg | ✅ | Covered (62 tests) |
| FR-014: floe-cube | ⚠️ | Missing RLS, pre-agg |

### 4.4 Infrastructure (FR-015 to FR-018)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-015: Storage profile | ✅ | `docker-compose.yml` profiles |
| FR-016: Full profile | ✅ | Includes Cube, Trino, Marquez |
| FR-017: Test runner scripts | ✅ | `run-integration-tests.sh` |
| FR-018: Idempotent init scripts | ✅ | `2>/dev/null || true` patterns |

### 4.5 Shared Fixtures (FR-019 to FR-021)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-019: CompiledArtifacts factories | ✅ | `testing/fixtures/artifacts.py` |
| FR-020: Docker lifecycle fixtures | ✅ | `testing/fixtures/services.py` |
| FR-021: Base test classes | ⚠️ | Only `adapter_test_base.py` |

### 4.6 Production Config (FR-022 to FR-023)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-022: Production-like configs | ❌ | No tests with different URIs |
| FR-023: Env var injection | ❌ | No secret_ref resolution tests |

**Recommendation**: Add `testing/fixtures/production_configs.py` with:
- Varied URI patterns (different endpoints, ports)
- Environment variable substitution tests
- Secret reference resolution tests

### 4.7 Observability Verification (FR-024 to FR-025)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-024: Jaeger API verification | ⚠️ | Partial in floe-cube |
| FR-025: Marquez API verification | ⚠️ | Partial in floe-cube |

**Current Implementation** (in `floe-cube/tests/integration/test_opentelemetry.py`):
```python
def test_rest_api_creates_traces():
    # Executes query and verifies trace exists
    # But doesn't verify span attributes deeply
```

**Recommendation**: Create `testing/fixtures/observability.py` with:
- `JaegerClient`: Query traces, verify spans, check attributes
- `MarquezClient`: Query lineage, verify events, check facets

### 4.8 Row-Level Security (FR-026 to FR-028)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-026: RLS with JWT claims | ❌ | No tests exist |
| FR-027: Security context rejection | ❌ | No tests exist |
| FR-028: Context propagation | ❌ | No tests exist |

**Recommendation**: Add `floe-cube/tests/integration/test_rls.py` with:
- JWT generation with custom claims
- Query execution with/without valid context
- Verification that data is filtered correctly

### 4.9 Standalone-First (FR-029 to FR-031)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-029: Core without observability | ❌ | No tests exist |
| FR-030: Warning logs | ❌ | No tests exist |
| FR-031: Minimal CompiledArtifacts | ❌ | No tests exist |

**Recommendation**: Add `testing/contracts/standalone_tests.py` with:
- Tests that explicitly disable Jaeger/Marquez services
- Log capture to verify warning messages
- `make_minimal_artifacts()` execution tests

### 4.10 Contract Boundary (FR-032 to FR-035)

| Requirement | Status | Gap |
|-------------|--------|-----|
| FR-032: Core → Dagster | ❌ | No boundary tests |
| FR-033: Core → dbt | ❌ | No boundary tests |
| FR-034: dbt → Cube | ❌ | No boundary tests |
| FR-035: Core → Polaris | ❌ | No boundary tests |

**Recommendation**: Create `testing/contracts/boundary_tests.py` with:
- End-to-end artifact flow tests
- Schema validation at boundaries
- Error propagation tests

## 5. Recommended Implementation Priority

### Phase 1: Foundation (P1 Requirements)

1. **Traceability Tooling** (FR-001 to FR-003)
   - Create `testing/traceability/` module
   - Add pytest markers for requirement mapping
   - Generate CI-compatible reports

2. **Contract Boundary Tests** (FR-032 to FR-035)
   - Create `testing/contracts/` module
   - Test CompiledArtifacts flows end-to-end
   - Add schema validation at package boundaries

### Phase 2: Gap Closure (P2 Requirements)

3. **floe-cli Command Tests** (FR-009)
   - Add `test_commands.py` with validate, compile, init
   - Test error handling and output formatting

4. **floe-dbt Compute Targets** (FR-010)
   - Add profile validation for 6 remaining targets
   - Mock or use actual services where available

5. **floe-dagster Materialization** (FR-011)
   - Add asset materialization tests
   - Add observability event verification

### Phase 3: Security & Observability (P3 Requirements)

6. **Row-Level Security** (FR-026 to FR-028)
   - Add JWT-based RLS tests for Cube
   - Verify security context propagation

7. **Observability Verification** (FR-024 to FR-025)
   - Create Jaeger/Marquez client helpers
   - Add deep attribute verification

8. **Standalone-First** (FR-029 to FR-031)
   - Add graceful degradation tests
   - Verify warning log emission

## 6. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total integration tests | ~230 | 300+ |
| Packages with gaps | 4 | 0 |
| Traceability coverage | 0% | 100% |
| Contract boundary tests | 0 | 10+ |
| RLS tests | 0 | 5+ |
| Standalone tests | 0 | 10+ |

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Flaky Docker tests | Medium | High | Health check improvements, retry logic |
| Slow test execution | Medium | Medium | Parallel test execution, profile caching |
| Credential management | Low | High | Existing polaris-init pattern works well |
| Cross-platform issues | Medium | Medium | Test on Linux and macOS in CI |

## 8. References

- Specification: `specs/006-integration-testing/spec.md`
- Docker Compose: `testing/docker/docker-compose.yml`
- Fixtures: `testing/fixtures/`
- Constitution: `.specify/memory/constitution.md`
