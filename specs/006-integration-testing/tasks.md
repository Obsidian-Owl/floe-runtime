# Tasks: Robust Integration Testing with Traceability

**Input**: Design documents from `/specs/006-integration-testing/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: This feature is ABOUT testing infrastructure - tasks create integration tests as the primary deliverable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a monorepo with packages under `packages/` and shared testing infrastructure under `testing/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create foundational testing infrastructure modules

- [ ] T001 Create `testing/traceability/__init__.py` with module exports
- [ ] T002 [P] Create `testing/traceability/models.py` with Pydantic models (Requirement, Test, TraceabilityMapping, TraceabilityMatrix) per data-model.md
- [ ] T003 [P] Create `testing/contracts/__init__.py` with module exports
- [ ] T004 [P] Create `testing/fixtures/observability.py` with JaegerClient and MarquezClient helper classes
- [ ] T005 [P] Register custom pytest markers (`requirement`, `requirements`) in root `conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement `testing/traceability/parser.py` with `parse_requirements(spec_path)` function to extract FR-XXX from spec.md files
- [ ] T007 Implement `testing/traceability/scanner.py` with `scan_tests(test_dirs)` function to discover tests and their requirement markers
- [ ] T008 Implement `testing/traceability/mapper.py` with `map_requirements_to_tests(requirements, tests)` function to create TraceabilityMapping entries
- [ ] T009 Implement `testing/fixtures/observability.py` JaegerClient class with `get_traces(service, operation)` and `verify_span_attributes(trace, expected)` methods
- [ ] T010 Implement `testing/fixtures/observability.py` MarquezClient class with `get_lineage_events(job_name)` and `verify_event_facets(event, expected)` methods
- [ ] T011 Add unit tests for traceability parser in `testing/traceability/tests/test_parser.py`
- [ ] T012 Add unit tests for traceability scanner in `testing/traceability/tests/test_scanner.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Validates Feature Coverage (Priority: P1) 🎯 MVP

**Goal**: Provide traceability matrix generation and gap reporting so developers can verify requirement coverage

**Independent Test**: Run `python -m testing.traceability.reporter --spec specs/006-integration-testing/spec.md` and verify it outputs a matrix showing FR-XXX to test mappings with coverage percentages

### Implementation for User Story 1

- [ ] T013 [US1] Implement `testing/traceability/reporter.py` with `generate_matrix(spec_files, test_dirs)` function returning TraceabilityMatrix
- [ ] T014 [US1] Implement `testing/traceability/reporter.py` `format_console_report(matrix)` function for terminal output with coverage percentages
- [ ] T015 [US1] Implement `testing/traceability/reporter.py` `format_json_report(matrix)` function for CI-compatible JSON output
- [ ] T016 [US1] Add CLI entry point in `testing/traceability/__main__.py` with argparse for `--spec`, `--test-dirs`, `--format` options
- [ ] T017 [US1] Create `testing/docker/scripts/run-traceability.sh` wrapper script to run traceability report inside Docker
- [ ] T018 [US1] Add requirement markers to existing floe-polaris integration tests in `packages/floe-polaris/tests/integration/test_polaris_catalog.py`
- [ ] T019 [US1] Add requirement markers to existing floe-iceberg integration tests in `packages/floe-iceberg/tests/integration/test_iceberg_tables.py`
- [ ] T020 [US1] Add requirement markers to existing floe-iceberg Dagster tests in `packages/floe-iceberg/tests/integration/test_dagster_assets.py`
- [ ] T021 [US1] Add integration test for traceability report generation in `testing/traceability/tests/test_integration.py`

**Checkpoint**: User Story 1 complete - developers can generate traceability reports and identify gaps

---

## Phase 4: User Story 2 - CI Pipeline Validates Integration Tests (Priority: P1)

**Goal**: Ensure CI runs all integration tests in Docker with FAIL not skip behavior

**Independent Test**: Trigger CI pipeline on a PR with a breaking change and verify tests FAIL with clear error messages (not skip)

### Implementation for User Story 2

- [ ] T022 [US2] Create `testing/contracts/boundary_tests.py` with `test_core_to_dagster_boundary()` verifying CompiledArtifacts → asset creation
- [ ] T023 [P] [US2] Add `test_core_to_dbt_boundary()` in `testing/contracts/boundary_tests.py` verifying CompiledArtifacts → profiles.yml
- [ ] T024 [P] [US2] Add `test_dbt_to_cube_boundary()` in `testing/contracts/boundary_tests.py` verifying manifest.json → Cube model sync
- [ ] T025 [P] [US2] Add `test_core_to_polaris_boundary()` in `testing/contracts/boundary_tests.py` verifying catalog config → connection
- [ ] T026 [US2] Create `packages/floe-cli/tests/integration/test_commands.py` with `test_validate_command()` integration test
- [ ] T027 [P] [US2] Add `test_compile_command()` in `packages/floe-cli/tests/integration/test_commands.py`
- [ ] T028 [P] [US2] Add `test_init_command()` in `packages/floe-cli/tests/integration/test_commands.py`
- [ ] T029 [US2] Create `packages/floe-dagster/tests/integration/test_assets.py` with asset materialization tests
- [ ] T030 [P] [US2] Create `packages/floe-dagster/tests/integration/test_openlineage.py` with Marquez API verification tests using MarquezClient fixture
- [ ] T031 [P] [US2] Create `packages/floe-dagster/tests/integration/test_otel.py` with Jaeger API verification tests using JaegerClient fixture
- [ ] T032 [US2] Update `.github/workflows/ci.yml` to run integration tests in Docker via `run-integration-tests.sh`
- [ ] T033 [US2] Add CI job for traceability report generation with coverage threshold check (>= 80%)

**Checkpoint**: User Story 2 complete - CI validates all integration tests with proper FAIL behavior

---

## Phase 5: User Story 3 - Package Maintainer Adds Integration Tests (Priority: P2)

**Goal**: Provide clear guidance and patterns for adding new integration tests

**Independent Test**: New developer follows quickstart.md to add an integration test that runs successfully in Docker

### Implementation for User Story 3

- [ ] T034 [US3] Create `packages/floe-dbt/tests/integration/test_postgres.py` with PostgreSQL profile validation tests using Docker postgres service
- [ ] T035 [P] [US3] Create `packages/floe-dbt/tests/integration/test_snowflake.py` with Snowflake profile structure validation (mock credentials)
- [ ] T036 [P] [US3] Create `packages/floe-dbt/tests/integration/test_bigquery.py` with BigQuery profile structure validation (mock credentials)
- [ ] T037 [P] [US3] Create `packages/floe-dbt/tests/integration/test_redshift.py` with Redshift profile structure validation (mock credentials)
- [ ] T038 [P] [US3] Create `packages/floe-dbt/tests/integration/test_databricks.py` with Databricks profile structure validation (mock credentials)
- [ ] T039 [P] [US3] Create `packages/floe-dbt/tests/integration/test_spark.py` with Spark profile structure validation
- [ ] T040 [US3] Create `testing/base_classes/integration_test_base.py` with IntegrationTestBase class providing common fixtures and patterns
- [ ] T041 [US3] Update `testing/fixtures/artifacts.py` to add `make_production_artifacts()` factory for production-like config testing (FR-022)
- [ ] T042 [US3] Create `packages/floe-cube/tests/integration/test_rls.py` with row-level security JWT tests (FR-026 to FR-028)
- [ ] T043 [US3] Validate and update `specs/006-integration-testing/quickstart.md` with real working examples from implemented tests

**Checkpoint**: User Story 3 complete - developers have patterns and documentation for adding tests

---

## Phase 6: User Story 4 - Architect Reviews Test Coverage by Feature (Priority: P2)

**Goal**: Provide per-feature coverage reports for release decisions

**Independent Test**: Run `python -m testing.traceability.reporter --feature 004 --format json` and verify output shows all FR-XXX from spec 004 with test status

### Implementation for User Story 4

- [ ] T044 [US4] Extend `testing/traceability/reporter.py` with `--feature` flag to filter by feature number
- [ ] T045 [US4] Implement `generate_feature_report(feature_id)` function that loads spec from `specs/{feature_id}-*/spec.md`
- [ ] T046 [P] [US4] Add `format_markdown_report(matrix)` function for PR comment integration
- [ ] T047 [US4] Create GitHub Actions workflow step to post traceability report as PR comment
- [ ] T048 [US4] Add acceptance scenario test coverage tracking (which scenarios are tested vs not)

**Checkpoint**: User Story 4 complete - architects can review per-feature coverage

---

## Phase 7: User Story 5 - DevOps Engineer Maintains Test Infrastructure (Priority: P3)

**Goal**: Provide clear documentation for infrastructure maintenance

**Independent Test**: DevOps engineer follows documentation to add a new service to Docker Compose and verifies it integrates with health checks

### Implementation for User Story 5

- [ ] T049 [US5] Create `testing/docker/docs/adding-services.md` with step-by-step guide for adding new Docker services
- [ ] T050 [P] [US5] Create `testing/docker/docs/profiles.md` documenting all 4 profiles and their use cases
- [ ] T051 [P] [US5] Create `testing/docker/docs/troubleshooting.md` with common issues and solutions
- [ ] T052 [US5] Add `testing/docker/scripts/health-check.sh` for manual infrastructure verification
- [ ] T053 [US5] Create `testing/contracts/standalone_tests.py` with graceful degradation tests (FR-029 to FR-031)
- [ ] T054 [P] [US5] Add test that verifies core functionality when Jaeger/Marquez unavailable
- [ ] T055 [P] [US5] Add test that verifies warning logs emitted for missing optional services

**Checkpoint**: User Story 5 complete - DevOps can maintain infrastructure with documentation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T056 [P] Update `testing/docker/README.md` with comprehensive overview linking to all docs
- [ ] T057 [P] Add type hints and docstrings to all new modules for mypy --strict compliance
- [ ] T058 Run `uv run ruff check` and `uv run black` on all new files
- [ ] T059 Run `uv run mypy --strict` on testing/ module and fix any type errors
- [ ] T060 Validate all integration tests pass via `./testing/docker/scripts/run-integration-tests.sh`
- [ ] T061 Generate final traceability report and verify >= 80% coverage of FR-001 to FR-035
- [ ] T062 Update CLAUDE.md with new testing patterns and traceability command

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Independent, but shares observability fixtures with US1
- **User Story 3 (P2)**: Can start after Foundational - Uses patterns from US1/US2 tests as examples
- **User Story 4 (P2)**: Depends on US1 (reporter infrastructure) - Extends reporter functionality
- **User Story 5 (P3)**: Can start after Foundational - Uses contract tests from US2

### Within Each User Story

- Models/infrastructure before dependent code
- Core implementation before integration
- Tests validate the implementation
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (5 parallel tasks):**
- T002, T003, T004, T005 can all run in parallel

**Foundational Phase (2 parallel groups):**
- Group 1: T006 → T007 → T008 (sequential: parser → scanner → mapper)
- Group 2: T009, T010 can run in parallel with Group 1
- Group 3: T011, T012 after their respective implementations

**User Story 1 (3 parallel tasks):**
- T018, T019, T020 (adding markers to existing tests) can run in parallel

**User Story 2 (7 parallel tasks):**
- T023, T024, T025 (boundary tests) can run in parallel
- T027, T028 (CLI commands) can run in parallel
- T030, T031 (observability tests) can run in parallel

**User Story 3 (5 parallel tasks):**
- T035, T036, T037, T038, T039 (dbt target profiles) can all run in parallel

**User Story 5 (4 parallel tasks):**
- T050, T051 (docs) can run in parallel
- T054, T055 (standalone tests) can run in parallel

---

## Parallel Example: User Story 2 Contract Boundary Tests

```bash
# Launch all boundary tests in parallel:
Task: "[US2] Add test_core_to_dbt_boundary() in testing/contracts/boundary_tests.py"
Task: "[US2] Add test_dbt_to_cube_boundary() in testing/contracts/boundary_tests.py"
Task: "[US2] Add test_core_to_polaris_boundary() in testing/contracts/boundary_tests.py"
```

## Parallel Example: User Story 3 dbt Profile Tests

```bash
# Launch all dbt target profile tests in parallel:
Task: "[US3] Create packages/floe-dbt/tests/integration/test_snowflake.py"
Task: "[US3] Create packages/floe-dbt/tests/integration/test_bigquery.py"
Task: "[US3] Create packages/floe-dbt/tests/integration/test_redshift.py"
Task: "[US3] Create packages/floe-dbt/tests/integration/test_databricks.py"
Task: "[US3] Create packages/floe-dbt/tests/integration/test_spark.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run traceability report, verify it shows coverage gaps
5. Deploy/demo traceability tooling

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test traceability report → Demo (MVP!)
3. Add User Story 2 → Test CI integration → Enable CI checks
4. Add User Story 3 → Validate developer experience → Publish guide
5. Add User Story 4 → Test per-feature reports → Enable architecture reviews
6. Add User Story 5 → Validate documentation → Complete infrastructure docs

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (traceability)
   - Developer B: User Story 2 (CI + boundary tests)
   - Developer C: User Story 3 (dbt profiles + patterns)
3. Stories complete and integrate independently
4. Developer A continues to US4 (extends US1)
5. Developer B/C handle US5 (documentation)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- This feature IS about testing, so test files ARE the primary deliverable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All new code must follow Constitution: type hints, Pydantic v2, mypy --strict

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 62 |
| Setup Phase | 5 tasks |
| Foundational Phase | 7 tasks |
| User Story 1 (P1) | 9 tasks |
| User Story 2 (P1) | 12 tasks |
| User Story 3 (P2) | 10 tasks |
| User Story 4 (P2) | 5 tasks |
| User Story 5 (P3) | 7 tasks |
| Polish Phase | 7 tasks |
| Parallel Opportunities | 26 tasks marked [P] |
| MVP Scope | Phases 1-3 (21 tasks) |
