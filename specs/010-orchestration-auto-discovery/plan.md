# Implementation Plan: Orchestration Auto-Discovery

**Branch**: `010-orchestration-auto-discovery` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-orchestration-auto-discovery/spec.md`

## Summary

Implement orchestration auto-discovery that eliminates 200+ LOC of boilerplate by auto-loading dbt models as individual assets with per-model observability, enabling declarative orchestration configuration in floe.yaml, and supporting production patterns (partitions, schedules, sensors, backfills). The same floe.yaml works across dev/staging/prod environments via environment variable overrides. Includes demo refactoring to serve as acceptance tests.

## Technical Context

**Language/Version**: Python 3.10+ (compatible with Dagster 1.6+, dbt-core 1.7+)
**Primary Dependencies**: Pydantic v2, pydantic-settings, PyYAML, Dagster, dbt-core, dagster-dbt
**Storage**: Iceberg tables via Polaris REST catalog; S3-compatible backends (MinIO, AWS S3)
**Testing**: pytest with pytest-cov (>80% coverage), mypy --strict, ruff, black (100 char)
**Target Platform**: macOS (Apple Silicon, Intel), Linux (x86_64, ARM64), Windows (WSL2)
**Project Type**: Monorepo with 7 packages (floe-core, floe-dagster, floe-dbt, floe-cube, floe-polaris, floe-iceberg, floe-cli)
**Performance Goals**: `floe validate` < 2s, `floe compile` < 5s, asset loading < 1s
**Constraints**: Standalone-first (no SaaS dependencies), pure Python only, secrets via SecretStr
**Scale/Scope**: 6 User Stories (3 P1, 2 P2, 1 P3), 48 Functional Requirements, Demo refactoring included

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Standalone-First** | ✅ PASS | Feature explicitly requires environment variable fallbacks (FR-045, FR-048), no SaaS dependencies. Works standalone with local Polaris/MinIO. |
| **II. Type Safety Everywhere** | ✅ PASS | All orchestration config models will use Pydantic v2 with strict validation (FR-046, FR-047). Partitions, jobs, schedules, sensors as typed models. |
| **III. Technology Ownership** | ✅ PASS | Dagster owns orchestration (load_assets_from_modules, @dbt_assets, schedules, sensors). dbt owns SQL (unchanged). Polaris owns catalog (unchanged). |
| **IV. Contract-Driven Integration** | ✅ PASS | CompiledArtifacts remains the sole integration contract. Orchestration config flows through artifacts dict. FloeSpec extended with OrchestrationConfig section. |
| **V. Security First** | ✅ PASS | Zero secrets in floe.yaml (orchestration config). All credentials via platform.yaml with secret_ref pattern. No eval/exec in config loading. |
| **VI. Quality Standards** | ✅ PASS | 100% requirement traceability required (FR-001 through FR-048 testable). pytest markers, >80% coverage, mypy --strict, ruff, black all enforced. |

**Gate Result**: ✅ PASS - All constitution principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/010-orchestration-auto-discovery/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
│   ├── orchestration-config.schema.json
│   ├── floe-spec-v2.schema.json
│   └── compiled-artifacts-v2.schema.json
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/
├── floe-core/
│   └── src/floe_core/
│       └── schemas/
│           ├── orchestration_config.py      # NEW: OrchestrationConfig model
│           ├── partition_definition.py      # NEW: Partition types (time_window, static, multi, dynamic)
│           ├── job_definition.py            # NEW: JobDefinition (batch, ops)
│           ├── schedule_definition.py       # NEW: ScheduleDefinition
│           ├── sensor_definition.py         # NEW: SensorDefinition
│           ├── asset_config.py              # NEW: AssetConfig for pattern matching
│           ├── backfill_definition.py       # NEW: BackfillDefinition
│           └── floe_spec.py                 # MODIFIED: Add orchestration: OrchestrationConfig field
├── floe-dagster/
│   └── src/floe_dagster/
│       ├── definitions.py                   # MODIFIED: Enhance from_compiled_artifacts() to auto-load assets/dbt
│       ├── loaders/
│       │   ├── __init__.py
│       │   ├── asset_loader.py              # NEW: load_assets_from_modules wrapper
│       │   ├── dbt_loader.py                # NEW: dbt manifest → @dbt_assets with per-model observability
│       │   ├── partition_loader.py          # NEW: Convert PartitionDefinition → DailyPartitionsDefinition etc
│       │   ├── job_loader.py                # NEW: Convert JobDefinition → JobDefinition (Dagster)
│       │   ├── schedule_loader.py           # NEW: Convert ScheduleDefinition → ScheduleDefinition (Dagster)
│       │   └── sensor_loader.py             # NEW: Convert SensorDefinition → SensorDefinition (Dagster)
│       └── assets.py                        # MODIFIED: Wire create_dbt_assets_with_per_model_observability to loader
├── floe-cli/
│   └── src/floe_cli/
│       └── commands/
│           └── orchestration.py             # NEW: `floe orchestration list-jobs`, `list-schedules` (optional)
demo/
└── data_engineering/
    ├── orchestration/
    │   ├── definitions.py                   # MODIFIED: Simplified to just call FloeDefinitions.from_compiled_artifacts()
    │   ├── assets/                          # NEW: Organized asset modules
    │   │   ├── __init__.py
    │   │   └── bronze.py                    # NEW: Bronze assets moved from definitions.py
    │   └── constants.py                     # KEPT: Table constants
    ├── dbt/                                 # UNCHANGED: dbt project
    └── floe.yaml                            # MODIFIED: Add orchestration section

tests/
├── unit/
│   ├── test_orchestration_config.py         # NEW: OrchestrationConfig validation tests
│   ├── test_partition_definition.py         # NEW: Partition type tests
│   ├── test_asset_loader.py                 # NEW: Asset module loading tests
│   ├── test_dbt_loader.py                   # NEW: dbt manifest loading tests
│   └── test_floe_definitions_auto_load.py   # NEW: FloeDefinitions.from_compiled_artifacts() auto-load tests
├── integration/
│   ├── test_orchestration_end_to_end.py     # NEW: Full orchestration workflow test
│   └── test_demo_refactored.py              # NEW: Validate demo works with auto-discovery
└── contract/
    ├── orchestration-config.schema.json     # NEW: JSON Schema for OrchestrationConfig
    └── floe-spec-v2.schema.json             # NEW: JSON Schema for FloeSpec v2 with orchestration
```

**Structure Decision**: Monorepo with 7 focused packages. New orchestration models added to floe-core/schemas (schema owner). Asset/job/schedule loaders in floe-dagster/loaders (orchestration runtime owner). Demo refactored to separate assets by layer (bronze.py) and simplified definitions.py to single factory call.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Post-Design Constitution Re-Check

*Completed after Phase 1 design artifacts were generated.*

| Principle | Status | Post-Design Evidence |
|-----------|--------|---------------------|
| **I. Standalone-First** | ✅ PASS | All loaders work with local config files, no SaaS dependencies. Environment variable interpolation (${VAR:default}) provides fallback defaults. |
| **II. Type Safety Everywhere** | ✅ PASS | All schemas use Pydantic v2 with ConfigDict(frozen=True, extra="forbid"). SecretStr not needed (no secrets in orchestration config). JSON Schema export for IDE support. |
| **III. Technology Ownership** | ✅ PASS | Dagster owns orchestration (loaders → Dagster objects). dbt owns SQL (manifest consumed, not parsed). No SQL validation in Python. |
| **IV. Contract-Driven Integration** | ✅ PASS | CompiledArtifacts extended with orchestration config. Contract version remains stable (additive change only). JSON Schema published. |
| **V. Security First** | ✅ PASS | Zero secrets in orchestration config. All module paths validated before import. No eval/exec in loaders. |
| **VI. Quality Standards** | ✅ PASS | All FR-001 through FR-048 mapped to test files. pytest markers applied. mypy --strict, ruff, black enforced. >80% coverage target. |

**Post-Design Gate Result**: ✅ PASS - All design artifacts comply with constitution.

---

## Phase 0: Research Summary

**Research Topics Covered**: 10 design decisions with rationale and alternatives

1. Dagster Asset Loading Patterns - `load_assets_from_modules()`
2. dbt Integration Strategy - Existing `create_dbt_assets_with_per_model_observability()`
3. Orchestration Config Schema Design - Pydantic v2 with Union types
4. Asset Module Organization - Separate files by layer
5. FloeDefinitions Factory Enhancement - Enhance existing method
6. Partition Definition Mapping - Type-safe conversion
7. Schedule/Sensor Loading Strategy - Dedicated loaders in `floe_dagster/loaders/`
8. Demo Refactoring Scope - Included in feature deliverables
9. Environment Variable Interpolation - `${VAR:default}` syntax
10. Error Handling Strategy - Pydantic validation with clear context

**Output**: [research.md](./research.md) (14.6 KB)

---

## Phase 1: Design & Contracts Summary

**Artifacts Generated**:

| Artifact | Status | Size | Description |
|----------|--------|------|-------------|
| [research.md](./research.md) | ✅ Complete | 14.6 KB | 10 design decisions with code examples |
| [data-model.md](./data-model.md) | ✅ Complete | 22.8 KB | 8 entities with relationships, validation rules, examples, ER diagram |
| [contracts/orchestration-config.schema.json](./contracts/orchestration-config.schema.json) | ✅ Complete | 22.3 KB | Comprehensive JSON Schema with discriminated unions |
| [contracts/floe-spec-v2.schema.json](./contracts/floe-spec-v2.schema.json) | ✅ Complete | 8.6 KB | Extended FloeSpec maintaining backward compatibility |
| [contracts/compiled-artifacts-v2.schema.json](./contracts/compiled-artifacts-v2.schema.json) | ✅ Complete | 13.5 KB | Extended CompiledArtifacts v2.0.0 |
| [contracts/README.md](./contracts/README.md) | ✅ Complete | 5.8 KB | Schema usage documentation |
| [quickstart.md](./quickstart.md) | ✅ Complete | 20.7 KB | 8-section guide with examples |

**Key Design Highlights**:
- ✅ Two-tier architecture strictly enforced (platform.yaml vs floe.yaml separation)
- ✅ All platform concerns (endpoints, credentials) removed from data engineering config
- ✅ Discriminated unions for partition types, job types, sensor types
- ✅ Environment variable interpolation with `${VAR:default}` syntax
- ✅ Comprehensive validation patterns (cron, identifiers, module paths)
- ✅ Entity relationship diagram showing all connections
- ✅ Backward compatibility maintained for existing floe.yaml files

**Agent Context Updated**:
- ✅ CLAUDE.md updated with Dagster 1.6+, dagster-dbt, orchestration patterns

**Architecture Compliance**:
- ✅ Standalone-first: No SaaS dependencies, works with local Polaris/MinIO
- ✅ Type safety: All Pydantic v2 models with frozen=True, extra="forbid"
- ✅ Technology ownership: Dagster owns orchestration, dbt owns SQL
- ✅ Contract-driven: CompiledArtifacts remains sole integration contract
- ✅ Security first: Zero secrets in orchestration config, local paths only for sensors
- ✅ Quality standards: All FR-001 through FR-048 mapped to implementation

**Ready for**: `/speckit.tasks` to generate implementation tasks.
