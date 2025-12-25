# Implementation Tasks: Orchestration Auto-Discovery

**Feature Branch**: `010-orchestration-auto-discovery`
**Created**: 2025-12-26
**Specification**: [spec.md](./spec.md) | [plan.md](./plan.md) | [data-model.md](./data-model.md) | [research.md](./research.md)

## Feature Summary

Implement orchestration auto-discovery that eliminates 200+ LOC of boilerplate by auto-loading dbt models as individual assets with per-model observability, enabling declarative orchestration configuration in floe.yaml, and supporting production patterns (partitions, schedules, sensors, backfills). The same floe.yaml works across dev/staging/prod environments via environment variable overrides.

## Implementation Strategy

**MVP-First Approach**: Implement P1 user stories first (US1: dbt auto-discovery, US2: declarative orchestration) to deliver immediate value. P2 stories (US3: partitions, US4: Python asset auto-discovery) enable advanced patterns. P3 stories (US5: sensors, US6: ops jobs) add production features. Each user story can be tested independently.

**Key Architecture Decisions**:
- Use existing `create_dbt_assets_with_per_model_observability()` for per-model tracking
- Leverage Dagster's `load_assets_from_modules()` for Python asset discovery
- Enhance existing `FloeDefinitions.from_compiled_artifacts()` factory method
- Organize assets by layer (bronze.py, gold.py, ops.py) for scalability
- Demo refactoring serves as comprehensive acceptance tests

## Dependencies

### Story Completion DAG
```
Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US4) → Phase 6 (US5) → Phase 7 (US6)
                                     ↓
                                  Phase 8 (Polish)
```

**Critical Dependencies**:
- US1 blocks all observability testing (requires per-model spans)
- US2 blocks advanced orchestration (schedules, sensors depend on job definitions)
- Demo refactoring requires US1 + US2 completion for end-to-end validation

## Phase 1: Setup

- [ ] T001 [P] Create feature branch `010-orchestration-auto-discovery` from main branch
- [ ] T002 [P] Update dependencies in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/pyproject.toml` to include dagster-dbt compatibility
- [ ] T003 [P] Verify test infrastructure supports pytest markers for requirements tracking in `/Users/dmccarthy/Projects/floe-runtime/pyproject.toml`

## Phase 2: Foundational (Blocks All User Stories)

- [ ] T004 Create OrchestrationConfig schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/orchestration_config.py`
- [ ] T005 Create PartitionDefinition schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/partition_definition.py`
- [ ] T006 Create JobDefinition schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/job_definition.py`
- [ ] T007 Create ScheduleDefinition schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/schedule_definition.py`
- [ ] T008 Create SensorDefinition schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/sensor_definition.py`
- [ ] T009 Create AssetConfig schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/asset_config.py`
- [ ] T010 Create BackfillDefinition schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/backfill_definition.py`
- [ ] T011 Create DbtConfig schema in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/orchestration_config.py`
- [ ] T012 Extend FloeSpec with orchestration field in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/floe_spec.py`
- [ ] T013 Create schema validation tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_orchestration_config.py`
- [ ] T014 Create partition definition validation tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_partition_definition.py`

## Phase 3: User Story 1 - Eliminate dbt Wrapper Boilerplate [US1] (Priority P1)

**Independent Test Criteria**: Each dbt model (stg_customers, stg_orders, stg_products, stg_order_items, customer_orders, revenue_by_product) appears as separate asset in orchestrator UI with individual execution traces and lineage events, replacing wrapper assets.

- [ ] T015 [US1] Create dbt loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/dbt_loader.py`
- [ ] T016 [US1] Wire dbt loader to existing create_dbt_assets_with_per_model_observability in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/assets.py`
- [ ] T017 [US1] Create dbt loader tests with manifest validation in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_dbt_loader.py`
- [ ] T018 [US1] Enhance FloeDefinitions.from_compiled_artifacts for dbt auto-loading in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/definitions.py`
- [ ] T019 [US1] Test dbt auto-loading integration in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_dbt_auto_loading.py`

**US1 Validation**:
```python
@pytest.mark.requirement("010-FR-006", "010-FR-007", "010-FR-008")
def test_dbt_models_as_individual_assets():
    """Verify each dbt model appears as separate asset with observability."""
    # Load orchestration config with dbt manifest
    # Verify assets created for stg_customers, stg_orders, etc.
    # Execute pipeline and verify per-model spans exist
```

## Phase 4: User Story 2 - Configure Orchestration Declaratively [US2] (Priority P1)

**Independent Test Criteria**: Jobs, schedules, and sensors defined in configuration file appear in orchestrator UI and execute according to configuration without Python code.

- [ ] T020 [US2] Create job loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/job_loader.py`
- [ ] T021 [US2] Create schedule loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/schedule_loader.py`
- [ ] T022 [US2] Create partition loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/partition_loader.py`
- [ ] T023 [US2] [P] Create job loader tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_job_loader.py`
- [ ] T024 [US2] [P] Create schedule loader tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_schedule_loader.py`
- [ ] T025 [US2] [P] Create partition loader tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_partition_loader.py`
- [ ] T026 [US2] Enhance FloeDefinitions for job/schedule auto-loading in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/definitions.py`
- [ ] T027 [US2] Test declarative orchestration integration in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_declarative_orchestration.py`

**US2 Validation**:
```python
@pytest.mark.requirement("010-FR-018", "010-FR-024", "010-FR-025")
def test_declarative_job_schedule_execution():
    """Verify jobs and schedules from config execute correctly."""
    # Load config with job selecting bronze assets
    # Load config with schedule for the job
    # Verify job appears in UI, schedule is active
```

## Phase 5: User Story 4 - Auto-Discover Python Assets [US4] (Priority P2)

**Independent Test Criteria**: Assets defined in Python modules listed in orchestration config appear in orchestrator without explicit registration code.

- [ ] T028 [US4] Create asset loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/asset_loader.py`
- [ ] T029 [US4] Create asset loader tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_asset_loader.py`
- [ ] T030 [US4] Enhance FloeDefinitions for asset module auto-loading in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/definitions.py`
- [ ] T031 [US4] Test asset module auto-discovery integration in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_asset_auto_discovery.py`

**US4 Validation**:
```python
@pytest.mark.requirement("010-FR-001", "010-FR-002", "010-FR-003")
def test_python_asset_auto_discovery():
    """Verify assets from modules are auto-loaded."""
    # Create test module with decorated assets
    # Add module path to orchestration config
    # Verify assets appear without registration
```

## Phase 6: User Story 5 - Configure Event-Driven Execution [US5] (Priority P3)

**Independent Test Criteria**: Sensors defined in configuration trigger associated jobs when conditions are met (file arrival, asset materialization).

- [ ] T032 [US5] Create sensor loader in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/sensor_loader.py`
- [ ] T033 [US5] Create sensor loader tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_sensor_loader.py`
- [ ] T034 [US5] Enhance FloeDefinitions for sensor auto-loading in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/definitions.py`
- [ ] T035 [US5] Test event-driven sensor integration in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_event_driven_sensors.py`

**US5 Validation**:
```python
@pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
def test_event_driven_sensor_execution():
    """Verify sensors trigger jobs on condition met."""
    # Configure file_watcher sensor with local path
    # Create matching file, verify job triggers
    # Configure asset_sensor, materialize watched asset, verify trigger
```

## Phase 7: User Story 6 - Configure Ops Maintenance Jobs [US6] (Priority P3)

**Independent Test Criteria**: Ops maintenance jobs (vacuum, compact) defined in configuration execute according to schedule.

- [ ] T036 [US6] Extend job loader for ops job type in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/job_loader.py`
- [ ] T037 [US6] Create ops job tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_ops_jobs.py`
- [ ] T038 [US6] Test ops job integration in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_ops_maintenance.py`

**US6 Validation**:
```python
@pytest.mark.requirement("010-FR-021", "010-FR-022")
def test_ops_maintenance_job_execution():
    """Verify ops jobs execute maintenance operations."""
    # Configure vacuum ops job with schedule
    # Verify job executes maintenance function
    # Test with configurable parameters
```

## Phase 8: Polish

### Demo Refactoring (Acceptance Tests)

- [ ] T039 Remove wrapper assets from `/Users/dmccarthy/Projects/floe-runtime/demo/data_engineering/orchestration/definitions.py`
- [ ] T040 Create bronze assets module in `/Users/dmccarthy/Projects/floe-runtime/demo/data_engineering/orchestration/assets/bronze.py`
- [ ] T041 Create ops assets module in `/Users/dmccarthy/Projects/floe-runtime/demo/data_engineering/orchestration/assets/ops.py`
- [ ] T042 Add orchestration section to `/Users/dmccarthy/Projects/floe-runtime/demo/data_engineering/floe.yaml`
- [ ] T043 Simplify definitions.py to single factory call in `/Users/dmccarthy/Projects/floe-runtime/demo/data_engineering/orchestration/definitions.py`
- [ ] T044 Create demo refactoring test in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_demo_refactored.py`

### Cross-Cutting Concerns

- [ ] T045 [P] Create FloeDefinitions auto-loading tests in `/Users/dmccarthy/Projects/floe-runtime/tests/unit/test_floe_definitions_auto_load.py`
- [ ] T046 [P] Create orchestration end-to-end test in `/Users/dmccarthy/Projects/floe-runtime/tests/integration/test_orchestration_end_to_end.py`
- [ ] T047 [P] Update loader __init__.py files for clean imports in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-dagster/src/floe_dagster/loaders/__init__.py`
- [ ] T048 [P] Create JSON schema export for IDE support in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/orchestration_config.py`
- [ ] T049 [P] Add environment variable interpolation support in `/Users/dmccarthy/Projects/floe-runtime/packages/floe-core/src/floe_core/schemas/orchestration_config.py`
- [ ] T050 [P] Update type hints and docstrings across all new modules for mypy compliance

## Parallel Execution Examples

### Phase 2 Foundational (Tasks T004-T014)
```bash
# All schema files can be created in parallel
T004, T005, T006, T007, T008, T009, T010, T011 → T012 → T013, T014
```

### Phase 3 US1 (Tasks T015-T019)
```bash
# Loader and tests can be parallel, then integration
T015, T017 → T016 → T018 → T019
```

### Phase 4 US2 (Tasks T020-T027)
```bash
# All loaders and tests in parallel, then integration
T020, T021, T022, T023, T024, T025 → T026 → T027
```

### Phase 8 Polish (Tasks T045-T050)
```bash
# All cross-cutting tasks can be parallel
T045, T046, T047, T048, T049, T050 (fully parallel)
```

## Task Summary

| Phase | Task Count | User Story | Can Test Independently |
|-------|------------|------------|------------------------|
| Setup | 3 | - | ✅ |
| Foundational | 11 | - | ✅ Schema validation only |
| US1 (P1) | 5 | dbt auto-discovery | ✅ Per-model observability |
| US2 (P1) | 8 | Declarative orchestration | ✅ Config-driven jobs/schedules |
| US4 (P2) | 4 | Python asset discovery | ✅ Module-based loading |
| US5 (P3) | 4 | Event-driven sensors | ✅ Sensor triggering |
| US6 (P3) | 3 | Ops maintenance | ✅ Maintenance job execution |
| Polish | 12 | Demo + cross-cutting | ✅ End-to-end validation |
| **Total** | **50** | **6 User Stories** | **All independently testable** |

## Success Metrics

- **SC-001**: Demo floe.yaml under 50 lines vs current 200+ lines Python (95% reduction)
- **SC-002**: Each dbt model appears as separate asset in orchestrator UI
- **SC-003**: Complete lineage from bronze → silver models → gold models
- **SC-004**: Same floe.yaml works across dev/staging/prod via environment variables
- **SC-005**: New assets added via module files without registration code

## Requirements Coverage

All 48 functional requirements (FR-001 through FR-048) from spec.md are covered by tasks with pytest markers `@pytest.mark.requirement("010-FR-XXX")` for full traceability.