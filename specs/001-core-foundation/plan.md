# Implementation Plan: Core Foundation Package (floe-core)

**Branch**: `001-core-foundation` | **Date**: 2025-12-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-core-foundation/spec.md`

## Summary

Create the foundational `floe-core` package that defines:
1. **FloeSpec** - Pydantic v2 schema for floe.yaml validation with 7 compute targets
2. **CompiledArtifacts** - Immutable contract consumed by all runtime packages (floe-dagster, floe-dbt, floe-cube, floe-polaris)
3. **Compiler** - Stateless service transforming FloeSpec → CompiledArtifacts with dbt classification extraction
4. **JSON Schema Export** - Draft 2020-12 schemas for IDE autocomplete and cross-language validation

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution: Dagster/dbt minimum)
**Primary Dependencies**: Pydantic v2, pydantic-settings, PyYAML, structlog
**Storage**: N/A (floe-core is schema/compiler only - no runtime storage)
**Testing**: pytest, pytest-cov, hypothesis (property-based), mypy --strict
**Target Platform**: macOS (Apple Silicon, Intel), Linux (x86_64, ARM64), Windows (WSL2)
**Project Type**: Single Python package (library)
**Performance Goals**: Validation <100ms (SC-001), Compilation <500ms for 200 models (SC-003)
**Constraints**: >80% test coverage (SC-004), standalone-first (no SaaS dependencies)
**Scale/Scope**: Single package, ~15 Pydantic models, 1 Compiler class, 2 JSON Schema exports

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | ✅ PASS | SaaS fields (lineage_namespace, environment_context) are Optional with None defaults per FR-013 |
| II. Type Safety Everywhere | ✅ PASS | All models use Pydantic v2, frozen=True, extra="forbid" per FR-001, FR-009 |
| III. Technology Ownership | ✅ PASS | dbt owns SQL (FR-018 extracts from manifest.json, doesn't parse SQL); Compiler delegates to dbt |
| IV. Contract-Driven Integration | ✅ PASS | CompiledArtifacts is sole contract (FR-009-015), 3-version backward compatibility (FR-015) |
| V. Security First | ✅ PASS | Secret refs validated via regex (Clarification), secrets not resolved at compile time (Assumption 4) |
| VI. Quality Standards | ✅ PASS | >80% coverage (SC-004), strict type checking (SC-005), JSON Schema export (FR-021-024) |

**Gate Result**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-foundation/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON Schema files)
│   ├── floe-spec.schema.json
│   └── compiled-artifacts.schema.json
├── checklists/          # Quality validation
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/floe-core/
├── pyproject.toml           # Package metadata, dependencies
├── src/
│   └── floe_core/
│       ├── __init__.py      # Public API exports
│       ├── py.typed         # PEP 561 marker
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── floe_spec.py      # FloeSpec + nested configs
│       │   ├── compiled.py       # CompiledArtifacts contract
│       │   ├── compute.py        # ComputeTarget, ComputeConfig
│       │   ├── transforms.py     # TransformConfig
│       │   ├── consumption.py    # ConsumptionConfig, CubeSecurityConfig, PreAggregationConfig
│       │   ├── governance.py     # GovernanceConfig, ColumnClassification
│       │   ├── observability.py  # ObservabilityConfig
│       │   └── catalog.py        # CatalogConfig
│       ├── compiler/
│       │   ├── __init__.py
│       │   ├── compiler.py       # Compiler class
│       │   └── extractors.py     # Classification extraction from dbt manifest
│       ├── errors.py             # FloeError, ValidationError, CompilationError
│       └── export.py             # JSON Schema export utilities
└── tests/
    ├── conftest.py               # Shared fixtures
    ├── unit/
    │   ├── schemas/              # Model validation tests
    │   ├── compiler/             # Compiler unit tests
    │   └── test_export.py        # JSON Schema export tests
    ├── integration/
    │   └── test_compile_flow.py  # End-to-end compilation
    └── contract/
        └── test_artifacts_contract.py  # Contract stability tests
```

**Structure Decision**: Single Python package in `packages/floe-core/` following the monorepo pattern established in architecture docs. Uses `src/` layout for proper package isolation. Test pyramid: unit → integration → contract tests.

## Complexity Tracking

> **No violations - Constitution Check passed all gates.**

---

## Post-Design Constitution Re-Check

*Verified after Phase 1 design artifacts generated.*

| Principle | Status | Post-Design Evidence |
|-----------|--------|----------------------|
| I. Standalone-First | ✅ PASS | data-model.md confirms EnvironmentContext is Optional; JSON Schema has null defaults |
| II. Type Safety Everywhere | ✅ PASS | All 15 entities in data-model.md have full type definitions; JSON Schema exports type metadata |
| III. Technology Ownership | ✅ PASS | research.md confirms dbt manifest.json parsing (not SQL); Compiler extracts, doesn't transform |
| IV. Contract-Driven Integration | ✅ PASS | contracts/compiled-artifacts.schema.json is sole cross-package contract; additionalProperties: false |
| V. Security First | ✅ PASS | Secret ref regex pattern in JSON Schema; FloeError hierarchy logs internally, returns generic messages |
| VI. Quality Standards | ✅ PASS | Test structure in plan defines unit/integration/contract pyramid; >80% coverage requirement |

**Post-Design Gate Result**: PASS - Design artifacts align with Constitution principles.

---

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Research | [research.md](research.md) | Technology decisions and patterns |
| Data Model | [data-model.md](data-model.md) | Entity definitions and relationships |
| FloeSpec Schema | [contracts/floe-spec.schema.json](contracts/floe-spec.schema.json) | JSON Schema for IDE autocomplete |
| CompiledArtifacts Schema | [contracts/compiled-artifacts.schema.json](contracts/compiled-artifacts.schema.json) | JSON Schema for cross-language validation |
| Quickstart | [quickstart.md](quickstart.md) | Usage examples and API reference |

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks (Phase 2)
2. Implement floe-core package per task breakdown
3. Run tests: `pytest packages/floe-core/tests/ --cov`
4. Verify type checking: `mypy --strict packages/floe-core/`
