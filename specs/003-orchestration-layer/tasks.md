# Tasks: Orchestration Layer

**Input**: Design documents from `/specs/003-orchestration-layer/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md

**Tests**: REQUIRED per SC-002 (100% test coverage for profile generation)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize both packages with correct structure and dependencies

- [ ] T001 [P] Create floe-dbt package directory structure per plan.md in packages/floe-dbt/
- [ ] T002 [P] Create floe-dagster package directory structure per plan.md in packages/floe-dagster/
- [ ] T003 [P] Initialize floe-dbt pyproject.toml with dependencies (pyyaml, floe-core) in packages/floe-dbt/pyproject.toml
- [ ] T004 [P] Initialize floe-dagster pyproject.toml with dependencies (dagster 1.9+, dagster-dbt 0.25+, openlineage-python 1.24+, opentelemetry-api 1.28+, floe-core, floe-dbt) in packages/floe-dagster/pyproject.toml
- [ ] T005 [P] Create floe-dbt __init__.py with public exports in packages/floe-dbt/src/floe_dbt/__init__.py
- [ ] T006 [P] Create floe-dagster __init__.py with public exports in packages/floe-dagster/src/floe_dagster/__init__.py
- [ ] T007 Configure workspace root pyproject.toml to include new packages in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create ProfileGenerator Protocol in packages/floe-dbt/src/floe_dbt/profiles/base.py
- [ ] T009 Create ProfileGeneratorConfig model in packages/floe-dbt/src/floe_dbt/profiles/base.py
- [ ] T010 [P] Create profiles subpackage __init__.py in packages/floe-dbt/src/floe_dbt/profiles/__init__.py
- [ ] T011 [P] Create lineage subpackage __init__.py in packages/floe-dagster/src/floe_dagster/lineage/__init__.py
- [ ] T012 [P] Create observability subpackage __init__.py in packages/floe-dagster/src/floe_dagster/observability/__init__.py
- [ ] T013 Create shared test fixtures for CompiledArtifacts mocking in packages/floe-dbt/tests/conftest.py
- [ ] T014 Create shared test fixtures for Dagster testing in packages/floe-dagster/tests/conftest.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 2 - Generate dbt Profiles from Configuration (Priority: P1) 🎯 MVP

**Goal**: Automatically generate valid dbt profiles.yml from floe.yaml configuration for all 7 compute targets

**Why First**: US2 is a prerequisite for US1 - dbt cannot execute without profiles.yml

**Independent Test**: Compile floe.yaml and verify profiles.yml is generated with correct connection parameters for each target

### Tests for User Story 2 (100% coverage per SC-002)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US2] Unit tests for DuckDBProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_duckdb.py
- [ ] T016 [P] [US2] Unit tests for SnowflakeProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_snowflake.py
- [ ] T017 [P] [US2] Unit tests for BigQueryProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_bigquery.py
- [ ] T018 [P] [US2] Unit tests for RedshiftProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_redshift.py
- [ ] T019 [P] [US2] Unit tests for DatabricksProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_databricks.py
- [ ] T020 [P] [US2] Unit tests for PostgreSQLProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_postgres.py
- [ ] T021 [P] [US2] Unit tests for SparkProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_spark.py
- [ ] T022 [P] [US2] Unit tests for ProfileFactory in packages/floe-dbt/tests/unit/test_factory.py
- [ ] T023 [P] [US2] Unit tests for ProfileWriter in packages/floe-dbt/tests/unit/test_writer.py
- [ ] T024 [US2] Integration test for profile validation with dbt debug in packages/floe-dbt/tests/integration/test_profile_validation.py

### Implementation for User Story 2

- [ ] T025 [P] [US2] Implement DuckDBProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/duckdb.py
- [ ] T026 [P] [US2] Implement SnowflakeProfileGenerator with env_var templating in packages/floe-dbt/src/floe_dbt/profiles/snowflake.py
- [ ] T027 [P] [US2] Implement BigQueryProfileGenerator with service-account/oauth support in packages/floe-dbt/src/floe_dbt/profiles/bigquery.py
- [ ] T028 [P] [US2] Implement RedshiftProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/redshift.py
- [ ] T029 [P] [US2] Implement DatabricksProfileGenerator with Unity Catalog support in packages/floe-dbt/src/floe_dbt/profiles/databricks.py
- [ ] T030 [P] [US2] Implement PostgreSQLProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/postgres.py
- [ ] T031 [P] [US2] Implement SparkProfileGenerator with thrift/odbc/session/http methods in packages/floe-dbt/src/floe_dbt/profiles/spark.py
- [ ] T032 [US2] Implement ProfileFactory with target registry in packages/floe-dbt/src/floe_dbt/factory.py
- [ ] T033 [US2] Implement ProfileWriter with YAML serialization in packages/floe-dbt/src/floe_dbt/writer.py
- [ ] T034 [US2] Update profiles __init__.py to export all generators in packages/floe-dbt/src/floe_dbt/profiles/__init__.py
- [ ] T035 [US2] Update floe-dbt __init__.py with public API in packages/floe-dbt/src/floe_dbt/__init__.py

**Checkpoint**: Profile generation complete - can generate profiles.yml for all 7 targets

---

## Phase 4: User Story 1 - Execute dbt Transformations via Dagster (Priority: P1) 🎯 MVP

**Goal**: Run dbt transformations through Dagster with orchestration, scheduling, and asset management

**Depends on**: US2 (profiles must be generated before dbt can execute)

**Independent Test**: Provide compiled floe.yaml and dbt project, materialize assets through Dagster UI/CLI

### Tests for User Story 1

- [ ] T036 [P] [US1] Unit tests for FloeTranslator in packages/floe-dagster/tests/unit/test_translator.py
- [ ] T037 [P] [US1] Unit tests for FloeAssetFactory in packages/floe-dagster/tests/unit/test_assets.py
- [ ] T038 [P] [US1] Unit tests for DbtModelMetadata.from_manifest_node in packages/floe-dagster/tests/unit/test_metadata.py
- [ ] T039 [US1] Integration test for dbt asset execution in packages/floe-dagster/tests/integration/test_dbt_execution.py

### Implementation for User Story 1

- [ ] T040 [P] [US1] Create DbtModelMetadata model in packages/floe-dagster/src/floe_dagster/models.py
- [ ] T041 [P] [US1] Create ColumnMetadata model in packages/floe-dagster/src/floe_dagster/models.py
- [ ] T042 [P] [US1] Create AssetMaterializationResult model in packages/floe-dagster/src/floe_dagster/models.py
- [ ] T043 [US1] Implement FloeTranslator (extends DagsterDbtTranslator) in packages/floe-dagster/src/floe_dagster/translator.py
- [ ] T044 [US1] Implement FloeAssetFactory.create_dbt_assets using @dbt_assets decorator in packages/floe-dagster/src/floe_dagster/assets.py
- [ ] T045 [US1] Implement DbtCliResource configuration in packages/floe-dagster/src/floe_dagster/resources.py
- [ ] T046 [US1] Implement FloeAssetFactory.create_definitions in packages/floe-dagster/src/floe_dagster/assets.py
- [ ] T047 [US1] Create Dagster definitions entry point in packages/floe-dagster/src/floe_dagster/definitions.py
- [ ] T048 [US1] Update floe-dagster __init__.py with public API (create_dbt_definitions) in packages/floe-dagster/src/floe_dagster/__init__.py

**Checkpoint**: Core orchestration complete - dbt models visible as Dagster assets, can materialize via UI

---

## Phase 5: User Story 3 - Track Data Lineage with OpenLineage (Priority: P2)

**Goal**: Emit OpenLineage events during pipeline execution for data flow tracing and compliance

**Independent Test**: Run pipeline with lineage endpoint configured, verify events appear in backend

### Tests for User Story 3

- [ ] T049 [P] [US3] Unit tests for LineageEvent model in packages/floe-dagster/tests/unit/test_lineage/test_events.py
- [ ] T050 [P] [US3] Unit tests for LineageDataset model in packages/floe-dagster/tests/unit/test_lineage/test_events.py
- [ ] T051 [P] [US3] Unit tests for OpenLineageConfig model in packages/floe-dagster/tests/unit/test_lineage/test_config.py
- [ ] T052 [P] [US3] Unit tests for OpenLineageEmitter in packages/floe-dagster/tests/unit/test_lineage/test_client.py
- [ ] T053 [P] [US3] Unit tests for LineageDatasetBuilder in packages/floe-dagster/tests/unit/test_lineage/test_builder.py
- [ ] T054 [US3] Unit tests for ColumnClassification facet generation in packages/floe-dagster/tests/unit/test_lineage/test_facets.py

### Implementation for User Story 3

- [ ] T055 [P] [US3] Create OpenLineageConfig model in packages/floe-dagster/src/floe_dagster/lineage/config.py
- [ ] T056 [P] [US3] Create LineageEventType enum in packages/floe-dagster/src/floe_dagster/lineage/events.py
- [ ] T057 [P] [US3] Create LineageDataset model in packages/floe-dagster/src/floe_dagster/lineage/events.py
- [ ] T058 [P] [US3] Create LineageEvent model in packages/floe-dagster/src/floe_dagster/lineage/events.py
- [ ] T059 [P] [US3] Create ColumnClassification model in packages/floe-dagster/src/floe_dagster/lineage/facets.py
- [ ] T060 [US3] Implement LineageDatasetBuilder.build_from_dbt_node in packages/floe-dagster/src/floe_dagster/lineage/builder.py
- [ ] T061 [US3] Implement LineageDatasetBuilder.build_classification_facet in packages/floe-dagster/src/floe_dagster/lineage/builder.py
- [ ] T062 [US3] Implement OpenLineageEmitter.emit_start in packages/floe-dagster/src/floe_dagster/lineage/client.py
- [ ] T063 [US3] Implement OpenLineageEmitter.emit_complete with schema facets in packages/floe-dagster/src/floe_dagster/lineage/client.py
- [ ] T064 [US3] Implement OpenLineageEmitter.emit_fail with error details in packages/floe-dagster/src/floe_dagster/lineage/client.py
- [ ] T065 [US3] Implement graceful degradation (NoOp) when endpoint unavailable in packages/floe-dagster/src/floe_dagster/lineage/client.py
- [ ] T066 [US3] Integrate OpenLineageEmitter into FloeAssetFactory asset execution in packages/floe-dagster/src/floe_dagster/assets.py
- [ ] T067 [US3] Update lineage __init__.py with public exports in packages/floe-dagster/src/floe_dagster/lineage/__init__.py

**Checkpoint**: Lineage tracking complete - OpenLineage events emitted during execution

---

## Phase 6: User Story 4 - Monitor Execution with OpenTelemetry (Priority: P2)

**Goal**: Export execution traces and metrics via OpenTelemetry for performance monitoring

**Independent Test**: Run pipeline with OTLP endpoint configured, verify spans appear in trace backend

### Tests for User Story 4

- [ ] T068 [P] [US4] Unit tests for TracingConfig model in packages/floe-dagster/tests/unit/test_tracing/test_config.py
- [ ] T069 [P] [US4] Unit tests for TracingManager in packages/floe-dagster/tests/unit/test_tracing/test_manager.py
- [ ] T070 [US4] Unit tests for structured logging with trace injection in packages/floe-dagster/tests/unit/test_tracing/test_logging.py

### Implementation for User Story 4

- [ ] T071 [P] [US4] Create TracingConfig model in packages/floe-dagster/src/floe_dagster/observability/config.py
- [ ] T072 [US4] Implement TracingManager.configure with OTLP exporter in packages/floe-dagster/src/floe_dagster/observability/tracing.py
- [ ] T073 [US4] Implement TracingManager.start_span with asset attributes in packages/floe-dagster/src/floe_dagster/observability/tracing.py
- [ ] T074 [US4] Implement NoOpTracerProvider for graceful degradation in packages/floe-dagster/src/floe_dagster/observability/tracing.py
- [ ] T075 [US4] Implement structured logging with trace_id/span_id injection in packages/floe-dagster/src/floe_dagster/observability/logging.py
- [ ] T076 [US4] Integrate TracingManager into FloeAssetFactory asset execution in packages/floe-dagster/src/floe_dagster/assets.py
- [ ] T077 [US4] Update observability __init__.py with public exports in packages/floe-dagster/src/floe_dagster/observability/__init__.py

**Checkpoint**: Observability complete - traces and structured logs with correlation IDs

---

## Phase 7: User Story 5 - Configure Multiple Environments (Priority: P3)

**Goal**: Run same pipeline against different environments by changing configuration

**Independent Test**: Generate profiles with different target configurations, verify each connects to correct environment

### Tests for User Story 5

- [ ] T078 [P] [US5] Unit tests for multi-environment profile generation in packages/floe-dbt/tests/unit/test_profiles/test_environments.py
- [ ] T079 [US5] Integration test for dev/prod profile switching in packages/floe-dbt/tests/integration/test_multi_env.py

### Implementation for User Story 5

- [ ] T080 [US5] Add environment-aware target name generation to ProfileFactory in packages/floe-dbt/src/floe_dbt/factory.py
- [ ] T081 [US5] Add environment-specific secret reference support in packages/floe-dbt/src/floe_dbt/profiles/base.py
- [ ] T082 [US5] Document environment variable naming conventions in packages/floe-dbt/README.md

**Checkpoint**: Multi-environment support complete - can generate separate profiles per environment

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T083 [P] Validate all profile generators against dbt-profile.schema.json contract
- [ ] T084 [P] Validate OpenLineage events against openlineage-event.schema.json contract
- [ ] T085 [P] Add comprehensive docstrings to all public APIs
- [ ] T086 [P] Run ruff check and black formatting on both packages
- [ ] T087 [P] Run mypy --strict on both packages
- [ ] T088 [P] Run bandit security scan on both packages
- [ ] T089 Validate quickstart.md workflow end-to-end
- [ ] T090 Update floe-cli run.py stub to call floe-dagster in packages/floe-cli/src/floe_cli/commands/run.py
- [ ] T091 Update floe-cli dev.py stub to call dagster dev in packages/floe-cli/src/floe_cli/commands/dev.py
- [ ] T092 Verify >80% test coverage for both packages

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────────────────────────────────────────────►
                                                                              │
Phase 2: Foundational ◄───────────────────────────────────────────────────────┘
         │
         ▼ (BLOCKS all user stories)
         │
Phase 3: US2 (Profile Generation) ◄────────────────────────────────────────────
         │                                                                     │
         ▼ (US1 depends on US2)                                               │
         │                                                                     │
Phase 4: US1 (Dagster Assets) ◄────────────────────────────────────────────────
         │
         ├──────────────────────────────────────────────────────────────────────
         │                                                                     │
         ▼ (can run in parallel)                                              │
         │                                                                     │
Phase 5: US3 (OpenLineage) ────────────────────────────────────────────────────┤
                                                                              │
Phase 6: US4 (OpenTelemetry) ──────────────────────────────────────────────────┤
                                                                              │
Phase 7: US5 (Multi-Environment) ──────────────────────────────────────────────┤
                                                                              │
Phase 8: Polish ◄──────────────────────────────────────────────────────────────┘
```

### User Story Dependencies

- **US2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **US1 (P1)**: DEPENDS ON US2 - dbt cannot execute without profiles.yml
- **US3 (P2)**: Can start after US1 - integrates with asset execution
- **US4 (P2)**: Can start after US1 - integrates with asset execution
- **US5 (P3)**: Can start after US2 - extends profile generation

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services/managers
- Services/managers before integration points
- Core implementation before integration with assets.py
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks (T001-T007 marked [P]) can run in parallel
- All Foundational tasks marked [P] can run in parallel (T010-T012)
- All 7 profile generator implementations (T025-T031) can run in parallel
- All profile generator tests (T015-T021) can run in parallel
- All model classes (T040-T042, T055-T059, T071) can run in parallel
- US3 and US4 can run in parallel after US1 completes

---

## Parallel Example: User Story 2 (Profile Generation)

```bash
# Launch all profile generator tests together:
Task: "Unit tests for DuckDBProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_duckdb.py"
Task: "Unit tests for SnowflakeProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_snowflake.py"
Task: "Unit tests for BigQueryProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_bigquery.py"
Task: "Unit tests for RedshiftProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_redshift.py"
Task: "Unit tests for DatabricksProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_databricks.py"
Task: "Unit tests for PostgreSQLProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_postgres.py"
Task: "Unit tests for SparkProfileGenerator in packages/floe-dbt/tests/unit/test_profiles/test_spark.py"

# Then launch all profile generator implementations together:
Task: "Implement DuckDBProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/duckdb.py"
Task: "Implement SnowflakeProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/snowflake.py"
Task: "Implement BigQueryProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/bigquery.py"
Task: "Implement RedshiftProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/redshift.py"
Task: "Implement DatabricksProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/databricks.py"
Task: "Implement PostgreSQLProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/postgres.py"
Task: "Implement SparkProfileGenerator in packages/floe-dbt/src/floe_dbt/profiles/spark.py"
```

---

## Implementation Strategy

### MVP First (US2 + US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US2 - Profile Generation
4. **CHECKPOINT**: Test profile generation for all 7 targets
5. Complete Phase 4: US1 - Dagster Asset Execution
6. **STOP and VALIDATE**: Test asset materialization via Dagster UI
7. Deploy/demo if ready - **This is MVP!**

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US2 → Test profile generation → **First milestone**
3. Add US1 → Test asset execution → Deploy/Demo (**MVP!**)
4. Add US3 → Test lineage events → Deploy/Demo (governance-ready)
5. Add US4 → Test traces → Deploy/Demo (observable)
6. Add US5 → Test multi-env → Deploy/Demo (production-ready)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US2 (Profile Generation) - **PRIORITY**
   - Wait for US2 to complete
   - Developer A: US1 (Dagster Assets)
   - Developer B: US3 (OpenLineage) - starts after US1
   - Developer C: US4 (OpenTelemetry) - starts after US1
3. Developer D: US5 (Multi-Environment) - can start after US2

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US2 MUST complete before US1 (profile generation is prerequisite)
- All observability features (US3, US4) degrade gracefully when endpoints unavailable
