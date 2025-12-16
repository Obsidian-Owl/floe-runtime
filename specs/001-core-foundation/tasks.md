# Tasks: Core Foundation Package (floe-core)

**Input**: Design documents from `/specs/001-core-foundation/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, contracts/
**Generated**: 2025-12-15

**Tests**: Tests are included per SC-004 requirement (>80% coverage) in spec.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md, using monorepo structure:
- **Package root**: `packages/floe-core/`
- **Source**: `packages/floe-core/src/floe_core/`
- **Tests**: `packages/floe-core/tests/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create floe-core package structure and configure tooling

- [x] T001 Create package directory structure per plan.md at packages/floe-core/
- [x] T002 Create pyproject.toml with dependencies (pydantic>=2.10, pyyaml>=6.0, structlog>=24.4) at packages/floe-core/pyproject.toml
- [x] T003 [P] Create py.typed marker file at packages/floe-core/src/floe_core/py.typed
- [x] T004 [P] Create package __init__.py with public API exports at packages/floe-core/src/floe_core/__init__.py
- [x] T005 [P] Create schemas package __init__.py at packages/floe-core/src/floe_core/schemas/__init__.py
- [x] T006 [P] Create compiler package __init__.py at packages/floe-core/src/floe_core/compiler/__init__.py
- [x] T007 [P] Create tests conftest.py with shared fixtures at packages/floe-core/tests/conftest.py

**Checkpoint**: Package skeleton ready for implementation

---

## Phase 2: Foundational (Core Infrastructure)

**Purpose**: Error handling and base utilities that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T008 Implement FloeError exception hierarchy (FloeError, ValidationError, CompilationError) at packages/floe-core/src/floe_core/errors.py
- [x] T009 [P] Write unit tests for error hierarchy at packages/floe-core/tests/unit/test_errors.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Define Pipeline Configuration (Priority: P1) MVP

**Goal**: Data engineer can define entire data pipeline in a single floe.yaml with compute target, transformations, consumption layer settings, governance policies, and observability configuration.

**Independent Test**: Create a valid floe.yaml and load it via FloeSpec.from_yaml() - returns validated FloeSpec with defaults applied.

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US1] Unit tests for ComputeTarget enum at packages/floe-core/tests/unit/schemas/test_compute_target.py
- [x] T011 [P] [US1] Unit tests for ComputeConfig validation (secret ref pattern) at packages/floe-core/tests/unit/schemas/test_compute_config.py
- [x] T012 [P] [US1] Unit tests for TransformConfig validation at packages/floe-core/tests/unit/schemas/test_transform_config.py
- [x] T013 [P] [US1] Unit tests for ConsumptionConfig defaults at packages/floe-core/tests/unit/schemas/test_consumption_config.py
- [x] T014 [P] [US1] Unit tests for GovernanceConfig defaults at packages/floe-core/tests/unit/schemas/test_governance_config.py
- [x] T015 [P] [US1] Unit tests for ObservabilityConfig defaults at packages/floe-core/tests/unit/schemas/test_observability_config.py
- [x] T016 [P] [US1] Unit tests for CatalogConfig validation at packages/floe-core/tests/unit/schemas/test_catalog_config.py
- [x] T017 [P] [US1] Unit tests for FloeSpec validation (name pattern, version semver) at packages/floe-core/tests/unit/schemas/test_floe_spec.py
- [x] T018 [P] [US1] Unit tests for FloeSpec.from_yaml() loading at packages/floe-core/tests/unit/schemas/test_floe_spec_yaml.py
- [x] T019 [P] [US1] Integration test for valid floe.yaml loading at packages/floe-core/tests/integration/test_floe_yaml_loading.py

### Implementation for User Story 1

- [x] T020 [P] [US1] Implement ComputeTarget enum with 7 targets at packages/floe-core/src/floe_core/schemas/compute.py
- [x] T021 [P] [US1] Implement ComputeConfig with secret ref validation at packages/floe-core/src/floe_core/schemas/compute.py
- [x] T022 [P] [US1] Implement TransformConfig with type discriminator at packages/floe-core/src/floe_core/schemas/transforms.py
- [x] T023 [P] [US1] Implement PreAggregationConfig with defaults at packages/floe-core/src/floe_core/schemas/consumption.py
- [x] T024 [P] [US1] Implement CubeSecurityConfig with defaults at packages/floe-core/src/floe_core/schemas/consumption.py
- [x] T025 [P] [US1] Implement ConsumptionConfig with database_type and dev_mode at packages/floe-core/src/floe_core/schemas/consumption.py
- [x] T026 [P] [US1] Implement GovernanceConfig with classification_source enum at packages/floe-core/src/floe_core/schemas/governance.py
- [x] T027 [P] [US1] Implement ColumnClassification model at packages/floe-core/src/floe_core/schemas/governance.py
- [x] T028 [P] [US1] Implement ObservabilityConfig with attributes dict at packages/floe-core/src/floe_core/schemas/observability.py
- [x] T029 [P] [US1] Implement CatalogConfig with Polaris OAuth2 fields at packages/floe-core/src/floe_core/schemas/catalog.py
- [x] T030 [US1] Implement FloeSpec root model with from_yaml() method at packages/floe-core/src/floe_core/schemas/floe_spec.py
- [x] T031 [US1] Export all schema models from schemas/__init__.py at packages/floe-core/src/floe_core/schemas/__init__.py

**Checkpoint**: FloeSpec validation fully functional - users can define and validate floe.yaml

---

## Phase 4: User Story 2 - Compile Configuration to Runtime Artifacts (Priority: P1) MVP

**Goal**: Data engineer can compile validated floe.yaml into CompiledArtifacts consumed by downstream packages (floe-dagster, floe-dbt, floe-cube).

**Independent Test**: Compile a FloeSpec and verify resulting CompiledArtifacts JSON contains all expected sections with correct metadata.

**Dependencies**: Requires User Story 1 (FloeSpec models)

### Tests for User Story 2

- [ ] T032 [P] [US2] Unit tests for ArtifactMetadata model at packages/floe-core/tests/unit/schemas/test_compiled.py
- [ ] T033 [P] [US2] Unit tests for EnvironmentContext optional model at packages/floe-core/tests/unit/schemas/test_compiled.py
- [ ] T034 [P] [US2] Unit tests for CompiledArtifacts immutability at packages/floe-core/tests/unit/schemas/test_compiled.py
- [ ] T035 [P] [US2] Unit tests for CompiledArtifacts JSON round-trip at packages/floe-core/tests/unit/schemas/test_compiled.py
- [ ] T036 [P] [US2] Unit tests for classification extraction from dbt manifest at packages/floe-core/tests/unit/compiler/test_extractors.py
- [ ] T037 [P] [US2] Unit tests for Compiler.compile() at packages/floe-core/tests/unit/compiler/test_compiler.py
- [ ] T038 [US2] Integration test for full compile flow at packages/floe-core/tests/integration/test_compile_flow.py
- [ ] T039 [US2] Contract test for CompiledArtifacts stability at packages/floe-core/tests/contract/test_artifacts_contract.py

### Implementation for User Story 2

- [ ] T040 [P] [US2] Implement ArtifactMetadata model at packages/floe-core/src/floe_core/schemas/compiled.py
- [ ] T041 [P] [US2] Implement EnvironmentContext optional model at packages/floe-core/src/floe_core/schemas/compiled.py
- [ ] T042 [US2] Implement CompiledArtifacts contract model at packages/floe-core/src/floe_core/schemas/compiled.py
- [ ] T043 [US2] Implement classification extractor from dbt manifest at packages/floe-core/src/floe_core/compiler/extractors.py
- [ ] T044 [US2] Implement Compiler class with compile() method at packages/floe-core/src/floe_core/compiler/compiler.py
- [ ] T045 [US2] Export Compiler from compiler/__init__.py at packages/floe-core/src/floe_core/compiler/__init__.py

**Checkpoint**: Full compilation pipeline functional - FloeSpec compiles to CompiledArtifacts

---

## Phase 5: User Story 3 - Enable IDE Autocomplete for floe.yaml (Priority: P2)

**Goal**: Data engineer gets IDE autocomplete suggestions and validation errors while editing floe.yaml in VS Code/IntelliJ.

**Independent Test**: Export JSON Schema and verify VS Code YAML extension provides autocomplete when $schema directive points to exported schema.

**Dependencies**: Requires User Story 1 (FloeSpec models)

### Tests for User Story 3

- [ ] T046 [P] [US3] Unit tests for FloeSpec JSON Schema export at packages/floe-core/tests/unit/test_export.py
- [ ] T047 [P] [US3] Unit tests for schema field descriptions inclusion at packages/floe-core/tests/unit/test_export.py

### Implementation for User Story 3

- [ ] T048 [US3] Implement export_floe_spec_schema() function at packages/floe-core/src/floe_core/export.py
- [ ] T049 [US3] Add $schema and $id metadata to exported schema at packages/floe-core/src/floe_core/export.py

**Checkpoint**: IDE autocomplete working for floe.yaml editing

---

## Phase 6: User Story 4 - Validate Artifacts Contract for Cross-System Integration (Priority: P2)

**Goal**: Platform engineer can validate that CompiledArtifacts are compatible with Go-based Control Plane using JSON Schema.

**Independent Test**: Export CompiledArtifacts JSON Schema and validate sample artifacts against it from any language.

**Dependencies**: Requires User Story 2 (CompiledArtifacts model)

### Tests for User Story 4

- [ ] T050 [P] [US4] Unit tests for CompiledArtifacts JSON Schema export at packages/floe-core/tests/unit/test_export.py
- [ ] T051 [P] [US4] Unit tests for schema Draft 2020-12 compliance at packages/floe-core/tests/unit/test_export.py
- [ ] T052 [US4] Contract test for extra="forbid" validation at packages/floe-core/tests/contract/test_artifacts_contract.py

### Implementation for User Story 4

- [ ] T053 [US4] Implement export_compiled_artifacts_schema() function at packages/floe-core/src/floe_core/export.py
- [ ] T054 [US4] Export all export functions from export.py at packages/floe-core/src/floe_core/export.py

**Checkpoint**: Cross-language contract validation working

---

## Phase 7: User Story 5 - Support Multiple Compute Targets (Priority: P2)

**Goal**: Data engineer can use same floe.yaml structure across different compute environments (DuckDB for dev, Snowflake for prod) with target-specific properties.

**Independent Test**: Create FloeSpec configurations for each compute target and validate target-specific properties.

**Dependencies**: Requires User Story 1 (FloeSpec models)

### Tests for User Story 5

- [ ] T055 [P] [US5] Unit tests for DuckDB target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T056 [P] [US5] Unit tests for Snowflake target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T057 [P] [US5] Unit tests for BigQuery target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T058 [P] [US5] Unit tests for Redshift target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T059 [P] [US5] Unit tests for Databricks target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T060 [P] [US5] Unit tests for PostgreSQL target properties at packages/floe-core/tests/unit/schemas/test_compute.py
- [ ] T061 [P] [US5] Unit tests for Spark target properties at packages/floe-core/tests/unit/schemas/test_compute.py

### Implementation for User Story 5

- [ ] T062 [US5] Document target-specific properties in ComputeConfig docstring at packages/floe-core/src/floe_core/schemas/compute.py

**Checkpoint**: All 7 compute targets validated correctly

---

## Phase 8: User Story 6 - Configure Iceberg Catalog Integration (Priority: P2)

**Goal**: Data engineer can configure their Iceberg catalog (Polaris, Glue, Nessie) for floe-polaris and floe-iceberg packages.

**Independent Test**: Create FloeSpec configurations with different catalog types and validate catalog-specific properties.

**Dependencies**: Requires User Story 1 (FloeSpec models with CatalogConfig)

### Tests for User Story 6

- [ ] T063 [P] [US6] Unit tests for Polaris catalog properties (scope, token_refresh) at packages/floe-core/tests/unit/schemas/test_catalog.py
- [ ] T064 [P] [US6] Unit tests for Glue catalog properties (region in properties) at packages/floe-core/tests/unit/schemas/test_catalog.py
- [ ] T065 [P] [US6] Unit tests for Nessie catalog properties (branch in properties) at packages/floe-core/tests/unit/schemas/test_catalog.py
- [ ] T066 [US6] Unit tests for missing catalog graceful handling at packages/floe-core/tests/unit/schemas/test_catalog.py

### Implementation for User Story 6

- [ ] T067 [US6] Document catalog-specific properties in CatalogConfig docstring at packages/floe-core/src/floe_core/schemas/catalog.py

**Checkpoint**: All catalog types validated correctly

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final quality improvements and documentation

- [ ] T068 Update package __init__.py with complete public API exports at packages/floe-core/src/floe_core/__init__.py
- [ ] T069 [P] Run mypy --strict and fix any type errors at packages/floe-core/
- [ ] T070 [P] Run pytest with coverage report (target >80%) at packages/floe-core/tests/
- [ ] T071 [P] Run quickstart.md examples to validate documentation at specs/001-core-foundation/quickstart.md
- [ ] T072 [P] Copy JSON Schema files to package for distribution at packages/floe-core/src/floe_core/schemas/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Foundational
  - US2 (Phase 4): Depends on US1 (needs FloeSpec models)
  - US3 (Phase 5): Depends on US1 (needs FloeSpec for schema export)
  - US4 (Phase 6): Depends on US2 (needs CompiledArtifacts for schema export)
  - US5 (Phase 7): Depends on US1 (adds tests for compute targets)
  - US6 (Phase 8): Depends on US1 (adds tests for catalog config)
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies (Critical Path)

```
Setup → Foundational → US1 (FloeSpec) ─┬→ US2 (Compiler) → US4 (Contract Schema)
                                       ├→ US3 (IDE Schema)
                                       ├→ US5 (Targets)
                                       └→ US6 (Catalogs)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (T001-T007)**:
```bash
# Run in parallel after T001:
T003, T004, T005, T006, T007
```

**User Story 1 Tests (T010-T019)**:
```bash
# All can run in parallel:
T010, T011, T012, T013, T014, T015, T016, T017, T018, T019
```

**User Story 1 Implementation (T020-T031)**:
```bash
# Run in parallel (different files):
T020, T021, T022, T023, T024, T025, T026, T027, T028, T029
# Then T030, T031 (depend on above)
```

**User Story 2 Tests (T032-T039)**:
```bash
# Run in parallel:
T032, T033, T034, T035, T036, T037
# T038, T039 depend on models
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (FloeSpec)
4. **STOP and VALIDATE**: Test FloeSpec.from_yaml() works
5. Complete Phase 4: User Story 2 (Compiler)
6. **STOP and VALIDATE**: Test Compiler.compile() works
7. Deploy/demo if ready - core pipeline validation and compilation working

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. User Story 1 → Test independently → **MVP: Pipeline Definition**
3. User Story 2 → Test independently → **MVP: Compilation**
4. User Story 3 → Test independently → IDE autocomplete
5. User Story 4 → Test independently → Cross-language validation
6. User Story 5 → Test independently → Multi-target support
7. User Story 6 → Test independently → Catalog integration

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 → then User Story 2
   - Developer B (after US1 done): User Stories 3, 5, 6
   - Developer C (after US2 done): User Story 4
3. Stories complete and integrate independently

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Tasks** | 72 |
| Setup Phase | 7 |
| Foundational Phase | 2 |
| User Story 1 (P1) | 22 (10 tests + 12 impl) |
| User Story 2 (P1) | 14 (8 tests + 6 impl) |
| User Story 3 (P2) | 4 (2 tests + 2 impl) |
| User Story 4 (P2) | 5 (3 tests + 2 impl) |
| User Story 5 (P2) | 8 (7 tests + 1 impl) |
| User Story 6 (P2) | 5 (4 tests + 1 impl) |
| Polish Phase | 5 |
| **Parallelizable Tasks** | 48 (marked [P]) |

### MVP Scope

**Minimum viable delivery**: Setup + Foundational + US1 + US2 = **45 tasks**

This delivers:
- FloeSpec validation (floe.yaml parsing)
- CompiledArtifacts compilation
- Classification extraction from dbt manifest
- JSON serialization/deserialization

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All models MUST use `Field(default_factory=...)` for mutable defaults per data-model.md Implementation Notes
