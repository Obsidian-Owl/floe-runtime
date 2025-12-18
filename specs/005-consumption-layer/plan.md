# Implementation Plan: Consumption Layer (floe-cube)

**Branch**: `005-consumption-layer` | **Date**: 2025-12-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-consumption-layer/spec.md`

## Summary

Implement the floe-cube package to provide a semantic consumption layer over dbt models using Cube. The package generates Cube configuration from CompiledArtifacts, syncs dbt models to Cube cubes via YAML/Jinja templates, implements JWT-based row-level security, emits OpenLineage events for query audit, and exposes REST, GraphQL, and SQL (Postgres wire protocol) APIs.

**Key Technical Decisions** (from research.md):
- Use Cube's native YAML/Jinja template approach for dbt integration (not a separate Python cube_dbt package)
- Generate JavaScript cube.js configuration with environment variable references for secrets
- JWT-based security with Cube's queryRewrite for user-managed, role-based filtering (distinct from SaaS tenant isolation)
- openlineage-python SDK with non-blocking emission pattern
- watchdog library for manifest.json change detection

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution: Dagster/dbt minimum)
**Primary Dependencies**:
- floe-core (CompiledArtifacts, ConsumptionConfig schemas)
- openlineage-python >=1.24 (query lineage emission)
- pydantic >=2.0 (data models)
- pydantic-settings (configuration)
- structlog (logging)
- watchdog (file system monitoring for manifest sync)
- PyJWT (JWT token validation)

**Storage**: File-based configuration generation (.floe/cube/), S3 for pre-aggregations
**Testing**: pytest, testcontainers, hypothesis (property-based)
**Target Platform**: Linux server, macOS (Apple Silicon, Intel), Windows (WSL2)
**Project Type**: Python package (monorepo member)
**Performance Goals**:
- Pre-aggregated queries < 1s (95th percentile)
- RLS filtering adds < 100ms latency
- 100 concurrent query clients without degradation
**Constraints**:
- No SaaS dependencies (standalone-first)
- Cube owns semantic layer (no custom query engine)
- dbt owns SQL (no SQL parsing in Python)
**Scale/Scope**: Supports 100 concurrent clients, arbitrary number of cubes/models

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | PASS | Uses local Cube deployment, no SaaS endpoints, OpenLineage is optional |
| II. Type Safety Everywhere | PASS | All models use Pydantic v2, mypy --strict required |
| III. Technology Ownership | PASS | Cube owns semantic layer/APIs, dbt owns SQL, Python generates config only |
| IV. Contract-Driven Integration | PASS | Consumes CompiledArtifacts, exports JSON Schema for CubeConfig/CubeSchema |
| V. Security First | PASS | JWT validation, SecretStr for credentials, queryRewrite for RLS, no sensitive data in logs |
| VI. Quality Standards | PASS | >80% coverage target, Google-style docstrings, Black/isort/ruff/bandit |

### Quality Gates (Pre-Implementation)

- [x] Technical approach respects technology ownership boundaries
- [x] No new SaaS dependencies introduced
- [x] Security context uses JWT (not plain headers)
- [x] OpenLineage emission is non-blocking
- [x] All configuration uses environment variables (no embedded secrets)

## Project Structure

### Documentation (this feature)

```text
specs/005-consumption-layer/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data models
├── quickstart.md        # Phase 1 developer guide
├── contracts/           # Phase 1 JSON schemas
│   ├── cube-config.schema.json
│   ├── cube-schema.schema.json
│   └── openlineage-event.schema.json
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
packages/floe-cube/
├── pyproject.toml           # Package definition (exists, needs update)
├── README.md                # Package documentation
├── src/
│   └── floe_cube/
│       ├── __init__.py      # Package exports
│       ├── py.typed         # PEP 561 marker
│       ├── models.py        # Pydantic models (CubeConfig, CubeSchema, etc.)
│       ├── config.py        # cube.js configuration generator
│       ├── model_sync.py    # dbt manifest → Cube schema sync
│       ├── security.py      # JWT validation, SecurityContext
│       ├── lineage.py       # OpenLineage event emitter
│       └── watcher.py       # Manifest file watcher
└── tests/
    ├── conftest.py          # Shared fixtures
    ├── unit/
    │   ├── test_models.py
    │   ├── test_config.py
    │   ├── test_model_sync.py
    │   ├── test_security.py
    │   └── test_lineage.py
    ├── integration/
    │   ├── test_cube_api.py       # REST/GraphQL/SQL API tests
    │   ├── test_row_level_security.py
    │   └── test_openlineage.py
    └── contract/
        └── test_schema_stability.py  # JSON schema backward compatibility
```

### Generated Artifacts (runtime)

```text
.floe/cube/
├── cube.js              # Generated Cube configuration
└── schema/
    ├── Orders.yaml      # Generated cube schemas (one per dbt model)
    └── Customers.yaml
```

**Structure Decision**: Extends existing floe-cube package stub with full implementation. Uses monorepo package pattern consistent with floe-core, floe-dagster, floe-iceberg, floe-polaris.

## Complexity Tracking

No constitution violations requiring justification.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| dbt Integration | YAML/Jinja templates | Native Cube approach, no custom parsing |
| Security | JWT + queryRewrite | Built-in Cube feature, standard auth pattern |
| Lineage | openlineage-python | Official SDK, already in dependencies |
| File Watching | watchdog library | Mature, cross-platform |

## Implementation Phases

### Phase 0: Research (COMPLETE)
- [x] Research cube_dbt integration patterns
- [x] Research Cube configuration structure
- [x] Research OpenLineage Python SDK
- [x] Document findings in research.md

### Phase 1: Design (COMPLETE)
- [x] Define data models (data-model.md)
- [x] Create JSON Schema contracts (contracts/)
- [x] Write quickstart guide (quickstart.md)

### Phase 2: Tasks (PENDING - /speckit.tasks)
- [ ] Generate implementation tasks in tasks.md
- [ ] Break down into testable units
- [ ] Assign priorities based on user story dependencies

## Dependencies

### Internal (floe-runtime packages)
- **floe-core**: CompiledArtifacts, ConsumptionConfig, CubeSecurityConfig, PreAggregationConfig

**Note**: The existing `CubeSecurityConfig` in floe-core uses `tenant_column` field name. Per FR-030, this will be renamed to `filter_column` with the default changed from `"tenant_id"` to `"organization_id"` to align with the user-managed, role-based security model.

### External (Python packages)
- openlineage-python >=1.24 (data lineage - "what data is accessed")
- opentelemetry-api >=1.27 (operational observability - "how is system performing")
- opentelemetry-sdk >=1.27 (OTel SDK)
- opentelemetry-exporter-otlp >=1.27 (OTLP exporter)
- pydantic >=2.0
- pydantic-settings >=2.0
- structlog >=24.0
- watchdog >=4.0
- PyJWT >=2.8

### Test Infrastructure
- testing/docker/docker-compose.yml (--profile full)
- Cube container (cubejs/cube:v0.36)
- Marquez container (OpenLineage backend)
- Trino container (Cube database backend)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| cube_dbt package not available as pip | Use YAML/Jinja templates directly (confirmed in research) |
| OpenLineage endpoint unreachable | Non-blocking emission with warning logs (per spec clarification) |
| JWT validation failures | Clear error messages, reject queries without exposing internals |
| Concurrent manifest sync | Document single-coordinator recommendation |

## Next Steps

1. Run `/speckit.tasks` to generate implementation task breakdown
2. Implement models.py with Pydantic v2 models
3. Implement config.py for cube.js generation
4. Implement model_sync.py for dbt manifest parsing
5. Implement security.py for JWT handling
6. Implement lineage.py for OpenLineage emission
7. Write unit tests (>80% coverage)
8. Write integration tests using Docker test infrastructure
