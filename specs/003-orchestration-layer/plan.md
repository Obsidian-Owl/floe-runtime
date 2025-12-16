# Implementation Plan: Orchestration Layer

**Branch**: `003-orchestration-layer` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-orchestration-layer/spec.md`

## Summary

Implement the orchestration layer comprising two packages (floe-dagster, floe-dbt) that:
1. Generate dbt profiles.yml from CompiledArtifacts for all 7 compute targets
2. Create Dagster Software-Defined Assets from dbt manifest.json
3. Emit OpenLineage events (START/COMPLETE/FAIL) for data lineage via custom floe-dagster code
4. Create OpenTelemetry spans for each asset materialization

The implementation follows the standalone-first principle - all observability features degrade gracefully when endpoints are unavailable.

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution: Dagster/dbt minimum)
**Primary Dependencies**:
- dagster 1.9+ (orchestration, Software-Defined Assets)
- dagster-dbt 0.25+ (@dbt_assets decorator, DbtCliResource, DbtProject)
- dbt-core 1.9+ (SQL transformation framework)
- openlineage-python 1.24+ (OpenLineage event emission)
- opentelemetry-api 1.28+ (trace spans)
- opentelemetry-exporter-otlp (OTLP export)
- floe-core (CompiledArtifacts contract)

**Storage**: File-based (profiles.yml generated to `.floe/profiles/`, reads dbt manifest.json)
**Testing**: pytest with pytest-cov (>80% coverage required), hypothesis for property-based tests
**Target Platform**: macOS (Apple Silicon/Intel), Linux (x86_64/ARM64), Windows (WSL2)
**Project Type**: Monorepo with workspace packages (packages/floe-dagster, packages/floe-dbt)
**Performance Goals**:
- `floe run` startup < 10s
- Profile generation < 1s
- OpenLineage events emitted within 1s of state changes

**Constraints**:
- Pure Python only (no compiled extensions)
- Standalone-first: no SaaS dependencies for core execution
- Technology ownership: dbt owns SQL, Dagster owns orchestration
- Contract-driven: CompiledArtifacts is the sole integration point
- Secrets via environment variables (never hardcoded)

**Scale/Scope**:
- 7 compute targets (DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark)
- 2 packages (floe-dagster, floe-dbt)
- ~24 functional requirements
- ~8 success criteria

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | ✅ PASS | FR-021/022/023 require graceful degradation without OTel/OpenLineage endpoints |
| II. Type Safety | ✅ PASS | All models use Pydantic v2, CompiledArtifacts is typed contract |
| III. Technology Ownership | ✅ PASS | dbt owns SQL (FR-001–005), Dagster owns orchestration (FR-006–010) |
| IV. Contract-Driven | ✅ PASS | CompiledArtifacts is sole input to floe-dagster/floe-dbt |
| V. Security First | ✅ PASS | FR-003/SC-007 require env var refs for secrets, never hardcoded |
| VI. Quality Standards | ✅ PASS | SC-002 requires 100% test coverage for profile generation |

**Gate Result**: ✅ PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/003-orchestration-layer/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT this command)
```

### Source Code (repository root)

```text
packages/
├── floe-core/           # EXISTING - Provides CompiledArtifacts contract
│   └── src/floe_core/
│       ├── compiler/models.py    # CompiledArtifacts, EnvironmentContext
│       └── schemas/              # ComputeConfig, ObservabilityConfig, etc.
│
├── floe-dagster/        # THIS FEATURE - Dagster orchestration
│   ├── src/floe_dagster/
│   │   ├── __init__.py
│   │   ├── assets.py             # @dbt_assets factory, asset definitions
│   │   ├── resources.py          # DbtCliResource configuration
│   │   ├── lineage/              # OpenLineage integration
│   │   │   ├── __init__.py
│   │   │   ├── client.py         # OpenLineageClient
│   │   │   └── events.py         # RunEvent builders (START/COMPLETE/FAIL)
│   │   ├── observability/        # OpenTelemetry integration
│   │   │   ├── __init__.py
│   │   │   ├── tracing.py        # Span creation, context propagation
│   │   │   └── logging.py        # Structured logging with trace injection
│   │   └── definitions.py        # Dagster Definitions factory
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_assets.py
│   │   │   ├── test_lineage.py
│   │   │   └── test_tracing.py
│   │   └── integration/
│   │       └── test_dbt_execution.py
│   └── pyproject.toml
│
├── floe-dbt/            # THIS FEATURE - dbt profile generation
│   ├── src/floe_dbt/
│   │   ├── __init__.py
│   │   ├── profiles/             # Profile generators
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # ProfileGenerator base class
│   │   │   ├── duckdb.py         # DuckDB profile
│   │   │   ├── snowflake.py      # Snowflake profile
│   │   │   ├── bigquery.py       # BigQuery profile
│   │   │   ├── redshift.py       # Redshift profile
│   │   │   ├── databricks.py     # Databricks profile
│   │   │   ├── postgres.py       # PostgreSQL profile
│   │   │   └── spark.py          # Spark profile
│   │   ├── factory.py            # ProfileFactory (target → generator)
│   │   └── writer.py             # profiles.yml file writer
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_profiles/    # One test file per target
│   │   │   ├── test_factory.py
│   │   │   └── test_writer.py
│   │   └── integration/
│   │       └── test_profile_validation.py
│   └── pyproject.toml
│
└── floe-cli/            # EXISTING - Entry point (run/dev stubs to be activated)
    └── src/floe_cli/commands/
        ├── run.py                # Stub → calls floe-dagster
        └── dev.py                # Stub → calls dagster dev
```

**Structure Decision**: Monorepo workspace with two new packages:
- **floe-dbt**: Focused on profile generation (5 FRs) - no orchestration logic
- **floe-dagster**: Focused on orchestration + observability (19 FRs) - depends on floe-dbt

This separation maintains technology ownership boundaries (Constitution Principle III).

## Complexity Tracking

> No violations to justify. Design follows constitution exactly.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Phase 0: Research Needed

### Technology Research Tasks

1. **dagster-dbt 0.25+ patterns**: Verify @dbt_assets decorator, DbtCliResource, DbtProject usage
2. **dbt profiles.yml structure**: Document exact YAML structure for all 7 targets with env var templating
3. **OpenLineage Python SDK**: Research RunEvent creation, facets, client configuration
4. **OpenTelemetry Python SDK**: Research span creation, OTLP export, context propagation
5. **dbt manifest.json structure**: Document model extraction, dependency parsing, metadata access

### Integration Research Tasks

1. **dagster-dbt + custom lineage**: Verify hook points for OpenLineage emission during dbt execution
2. **Structured logging with OTel**: Research trace_id/span_id injection into structlog
3. **Graceful degradation patterns**: Research best practices for optional observability

## Phase 1: Design Outputs (After Research)

- **data-model.md**: Profile, DbtAsset, LineageEvent, TraceSpan entities
- **contracts/**: OpenAPI/JSON Schema for any internal APIs
- **quickstart.md**: 5-minute getting started guide
