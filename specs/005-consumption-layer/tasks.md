# Tasks: Consumption Layer (floe-cube)

**Input**: Design documents from `/specs/005-consumption-layer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as this package requires >80% coverage per Constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Package root**: `packages/floe-cube/`
- **Source**: `packages/floe-cube/src/floe_cube/`
- **Tests**: `packages/floe-cube/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and package structure

- [x] T001 Update pyproject.toml with dependencies (openlineage-python>=1.24, opentelemetry-api>=1.27, opentelemetry-sdk>=1.27, opentelemetry-exporter-otlp>=1.27, pydantic>=2.0, pydantic-settings>=2.0, structlog>=24.0, watchdog>=4.0, PyJWT>=2.8) in packages/floe-cube/pyproject.toml
- [x] T002 [P] Create py.typed marker for PEP 561 in packages/floe-cube/src/floe_cube/py.typed
- [x] T003 [P] Configure package exports in packages/floe-cube/src/floe_cube/__init__.py
- [x] T004 [P] Create test conftest.py with shared fixtures in packages/floe-cube/tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete. This includes:
- Updating floe-core schema (FR-030)
- Base Pydantic models shared across stories

- [x] T005 Update CubeSecurityConfig in floe-core: rename `tenant_column` to `filter_column`, change default from `"tenant_id"` to `"organization_id"` (FR-030) in packages/floe-core/src/floe_core/schemas/consumption.py
- [x] T006 [P] Implement CubeConfig Pydantic model (database_type, api_port, sql_port, api_secret_ref, dev_mode, jwt_audience, jwt_issuer) in packages/floe-cube/src/floe_cube/models.py
- [x] T007 [P] Implement CubeDimension Pydantic model (name, sql, type, primary_key, description, meta) in packages/floe-cube/src/floe_cube/models.py
- [x] T008 [P] Implement CubeMeasure Pydantic model (name, sql, type, description, filters) in packages/floe-cube/src/floe_cube/models.py
- [x] T009 [P] Implement CubeJoin Pydantic model (name, relationship, sql) in packages/floe-cube/src/floe_cube/models.py
- [x] T010 Implement CubeSchema Pydantic model (name, sql_table, description, dimensions, measures, joins, pre_aggregations, filter_column) in packages/floe-cube/src/floe_cube/models.py
- [x] T011 [P] Implement CubePreAggregation Pydantic model (name, measures, dimensions, time_dimension, granularity, refresh_every, external) in packages/floe-cube/src/floe_cube/models.py
- [x] T012 Write unit tests for all foundational models (>80% coverage) in packages/floe-cube/tests/unit/test_models.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel (COMPLETE: 67 tests, 98% coverage)

---

## Phase 3: User Story 1 - Configure Cube Semantic Layer (Priority: P1)

**Goal**: Generate Cube configuration files from CompiledArtifacts for deployment

**Independent Test**: Compile a floe.yaml with consumption enabled and verify generated Cube configuration files are valid and complete

**Functional Requirements**: FR-001, FR-002, FR-003, FR-004

### Tests for User Story 1

- [x] T013 [P] [US1] Unit test: config generator creates valid cube.js for each database_type in packages/floe-cube/tests/unit/test_config.py
- [x] T014 [P] [US1] Unit test: config generator references K8s secrets (never embeds credentials) in packages/floe-cube/tests/unit/test_config.py
- [x] T015 [P] [US1] Contract test: generated config matches cube-config.schema.json in packages/floe-cube/tests/contract/test_schema_stability.py

### Implementation for User Story 1

- [x] T016 [US1] Implement database driver template selection (postgres, snowflake, bigquery, databricks, trino) in packages/floe-cube/src/floe_cube/config.py
- [x] T017 [US1] Implement cube.js configuration generator from ConsumptionConfig in packages/floe-cube/src/floe_cube/config.py
- [x] T018 [US1] Implement K8s secret reference handling (api_secret_ref environment variable mapping) in packages/floe-cube/src/floe_cube/config.py
- [x] T019 [US1] Implement config file writer (output to .floe/cube/cube.js) in packages/floe-cube/src/floe_cube/config.py
- [x] T020 [US1] Add validation for unsupported database_type with clear error messages in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: User Story 1 complete - can generate valid Cube configuration from CompiledArtifacts (COMPLETE: 25 tests passing)

---

## Phase 4: User Story 2 - Sync dbt Models to Cube Cubes (Priority: P1)

**Goal**: Parse dbt manifest.json and generate Cube schema YAML files with dimensions, measures, and joins

**Independent Test**: Provide a dbt manifest.json and verify corresponding Cube cube definitions are generated correctly

**Functional Requirements**: FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-028

### Tests for User Story 2

- [x] T021 [P] [US2] Unit test: model_sync extracts dimensions from dbt columns with correct type mapping in packages/floe-cube/tests/unit/test_model_sync.py
- [x] T022 [P] [US2] Unit test: model_sync extracts measures from meta.cube.measures tags in packages/floe-cube/tests/unit/test_model_sync.py
- [x] T023 [P] [US2] Unit test: model_sync creates joins from dbt relationships in packages/floe-cube/tests/unit/test_model_sync.py
- [x] T024 [P] [US2] Unit test: model_sync handles incremental updates without duplicating cubes in packages/floe-cube/tests/unit/test_model_sync.py
- [x] T025 [P] [US2] Contract test: generated schemas match cube-schema.schema.json in packages/floe-cube/tests/contract/test_schema_stability.py

### Implementation for User Story 2

- [x] T026 [US2] Implement dbt manifest.json parser (extract models, columns, meta tags) in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T027 [US2] Implement dbt-to-Cube type mapping (text→string, integer→number, timestamp→time, etc.) in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T028 [US2] Implement dimension extraction from dbt columns in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T029 [US2] Implement measure extraction from meta.cube.measures tags in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T030 [US2] Implement join extraction from dbt refs and meta.cube.joins in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T031 [US2] Implement CubeSchema YAML generator (output to .floe/cube/schema/*.yaml) in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T032 [US2] Implement incremental sync logic (update existing, detect removed models) in packages/floe-cube/src/floe_cube/model_sync.py
- [x] T033 [US2] Add manifest.json existence validation with clear error messages in packages/floe-cube/src/floe_cube/model_sync.py
- [ ] T034 [US2] Implement watchdog file watcher for manifest.json changes (FR-028) in packages/floe-cube/src/floe_cube/watcher.py
- [ ] T035 [P] [US2] Unit test: watcher triggers sync on manifest.json modification in packages/floe-cube/tests/unit/test_watcher.py

**Checkpoint**: User Stories 1 AND 2 core implementation complete - 118 tests passing, 91% coverage. (T034-T035 watcher deferred)

---

## Phase 5: User Story 3 - Query Data via REST API (Priority: P2)

**Goal**: Verify Cube REST API is properly configured and functional

**Independent Test**: Start Cube with synced cubes and execute REST API queries, verifying correct response structure

**Functional Requirements**: FR-011, FR-014, FR-015

**Note**: Cube owns the REST API - our work is configuration and integration testing

### Tests for User Story 3

- [ ] T036 [P] [US3] Integration test: REST API returns JSON data for valid query in packages/floe-cube/tests/integration/test_cube_api.py
- [ ] T037 [P] [US3] Integration test: REST API returns 401 for invalid credentials in packages/floe-cube/tests/integration/test_cube_api.py
- [ ] T038 [P] [US3] Integration test: REST API paginates results over 10,000 rows in packages/floe-cube/tests/integration/test_cube_api.py

### Implementation for User Story 3

- [ ] T039 [US3] Add REST API port configuration to cube.js generator (default 4000) in packages/floe-cube/src/floe_cube/config.py
- [ ] T040 [US3] Add API authentication configuration (CUBEJS_API_SECRET) in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: REST API functional - applications can query data via JSON

---

## Phase 6: User Story 4 - Query Data via GraphQL API (Priority: P2)

**Goal**: Verify Cube GraphQL API is properly configured and functional

**Independent Test**: Execute GraphQL queries against the Cube GraphQL endpoint and validate schema introspection

**Functional Requirements**: FR-012

**Note**: Cube owns the GraphQL API - our work is configuration and integration testing

### Tests for User Story 4

- [ ] T041 [P] [US4] Integration test: GraphQL schema introspection returns cube types in packages/floe-cube/tests/integration/test_cube_api.py
- [ ] T042 [P] [US4] Integration test: GraphQL query with nested relationships returns joined data in packages/floe-cube/tests/integration/test_cube_api.py

### Implementation for User Story 4

- [ ] T043 [US4] Verify GraphQL endpoint configuration in cube.js generator (same port as REST) in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: GraphQL API functional - frontend developers can use type-safe queries

---

## Phase 7: User Story 5 - Query Data via SQL (Postgres Wire Protocol) (Priority: P2)

**Goal**: Verify Cube SQL API is properly configured and functional via Postgres wire protocol

**Independent Test**: Connect a Postgres client (psql) to the Cube SQL endpoint and execute SELECT queries

**Functional Requirements**: FR-013

**Note**: Cube owns the SQL API - our work is configuration and integration testing

### Tests for User Story 5

- [ ] T044 [P] [US5] Integration test: SQL API accepts Postgres client connection in packages/floe-cube/tests/integration/test_cube_api.py
- [ ] T045 [P] [US5] Integration test: SQL SELECT query returns correct data in packages/floe-cube/tests/integration/test_cube_api.py
- [ ] T046 [P] [US5] Integration test: SQL API rejects UPDATE/DELETE with clear error in packages/floe-cube/tests/integration/test_cube_api.py

### Implementation for User Story 5

- [ ] T047 [US5] Add SQL API port configuration to cube.js generator (default 15432) in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: All three API interfaces functional - SC-007 achieved

---

## Phase 8: User Story 6 - Enforce Row-Level Security (Priority: P3)

**Goal**: Configure JWT-based row-level security with user-defined filter columns

**Independent Test**: Execute identical queries with different security contexts and verify different result sets

**Functional Requirements**: FR-016, FR-017, FR-018, FR-019, FR-027

### Tests for User Story 6

- [ ] T048 [P] [US6] Unit test: SecurityContext model validates filter_claims and expiration in packages/floe-cube/tests/unit/test_security.py
- [ ] T049 [P] [US6] Unit test: JWT validation extracts filter claims correctly in packages/floe-cube/tests/unit/test_security.py
- [ ] T050 [P] [US6] Unit test: JWT signature verification rejects tampered tokens in packages/floe-cube/tests/unit/test_security.py
- [ ] T051 [P] [US6] Integration test: queries with different security contexts return filtered data in packages/floe-cube/tests/integration/test_row_level_security.py
- [ ] T052 [P] [US6] Integration test: query without valid JWT is rejected with 401 in packages/floe-cube/tests/integration/test_row_level_security.py
- [ ] T053 [P] [US6] Integration test: concurrent queries with different contexts don't leak data (SC-006) in packages/floe-cube/tests/integration/test_row_level_security.py

### Implementation for User Story 6

- [ ] T054 [US6] Implement SecurityContext Pydantic model (filter_claims, user_id, roles, exp) in packages/floe-cube/src/floe_cube/models.py
- [ ] T055 [US6] Implement JWT token validation and claim extraction in packages/floe-cube/src/floe_cube/security.py
- [ ] T056 [US6] Implement JWT signature verification using CUBEJS_API_SECRET in packages/floe-cube/src/floe_cube/security.py
- [ ] T057 [US6] Generate cube.js checkAuth function for JWT validation in packages/floe-cube/src/floe_cube/config.py
- [ ] T058 [US6] Generate cube.js queryRewrite function for filter injection in packages/floe-cube/src/floe_cube/config.py
- [ ] T059 [US6] Add filter_column and filter_claim environment variable configuration in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: Row-level security functional - SC-004 and SC-006 achievable

---

## Phase 9: User Story 7 - Monitor Query Performance via OpenTelemetry (Priority: P3)

**Goal**: Emit OpenTelemetry traces for query execution with W3C Trace Context propagation

**Note on Observability Model**: OpenTelemetry provides **operational observability** - "how is the system performing?" (traces, latency, errors). This is complementary to OpenLineage (User Story 8) which provides **data lineage** - "what data is being accessed?"

**Independent Test**: Execute queries and verify OpenTelemetry traces appear in configured collector with correct span hierarchy

**Functional Requirements**: FR-031, FR-032, FR-033, FR-034, FR-035, FR-036

### Tests for User Story 7

- [ ] T060 [P] [US7] Unit test: QueryTraceSpan model validates required fields in packages/floe-cube/tests/unit/test_tracing.py
- [ ] T061 [P] [US7] Unit test: tracer creates span hierarchy (query → parse → execute → response) in packages/floe-cube/tests/unit/test_tracing.py
- [ ] T062 [P] [US7] Unit test: span attributes include safe metadata (cube.name, filter_count) NOT filter values in packages/floe-cube/tests/unit/test_tracing.py
- [ ] T063 [P] [US7] Unit test: W3C Trace Context is extracted from incoming headers in packages/floe-cube/tests/unit/test_tracing.py
- [ ] T064 [P] [US7] Unit test: tracing disabled produces no spans in packages/floe-cube/tests/unit/test_tracing.py
- [ ] T065 [P] [US7] Integration test: traces appear in Jaeger when collector configured in packages/floe-cube/tests/integration/test_opentelemetry.py

### Implementation for User Story 7

- [ ] T066 [US7] Implement QueryTraceSpan Pydantic model (trace_id, span_id, parent_span_id, name, kind, start_time, end_time, status, attributes) in packages/floe-cube/src/floe_cube/models.py
- [ ] T067 [US7] Implement TracerProvider initialization with OTLP exporter in packages/floe-cube/src/floe_cube/tracing.py
- [ ] T068 [US7] Implement trace_query() function with W3C context extraction in packages/floe-cube/src/floe_cube/tracing.py
- [ ] T069 [US7] Implement span hierarchy creation (cube.query, cube.parse, cube.execute, cube.response) in packages/floe-cube/src/floe_cube/tracing.py
- [ ] T070 [US7] Implement safe attribute injection (NO filter values, JWT claims, or row data) in packages/floe-cube/src/floe_cube/tracing.py
- [ ] T071 [US7] Implement record_query_result() for span status and row count in packages/floe-cube/src/floe_cube/tracing.py
- [ ] T072 [US7] Add OTel collector endpoint configuration to cube.js generator in packages/floe-cube/src/floe_cube/config.py
- [ ] T073 [US7] Add traces_enabled configuration flag for disabling tracing in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: OpenTelemetry tracing functional - SC-008 achievable

---

## Phase 10: User Story 8 - Emit OpenLineage Events for Query Audit (Priority: P3)

**Goal**: Emit OpenLineage events for query execution with non-blocking behavior

**Note on Observability Model**: OpenLineage provides **data lineage** - "what data is being accessed?" (datasets, jobs, provenance). This is complementary to OpenTelemetry (User Story 7) which provides **operational observability** - "how is the system performing?"

**Independent Test**: Execute queries and verify OpenLineage events are emitted to configured endpoint

**Functional Requirements**: FR-020, FR-021, FR-022, FR-023, FR-024, FR-029

### Tests for User Story 8

- [ ] T074 [P] [US8] Unit test: QueryLineageEvent model validates required fields in packages/floe-cube/tests/unit/test_lineage.py
- [ ] T075 [P] [US8] Unit test: emit_start creates START event with correct facets in packages/floe-cube/tests/unit/test_lineage.py
- [ ] T076 [P] [US8] Unit test: emit_complete creates COMPLETE event in packages/floe-cube/tests/unit/test_lineage.py
- [ ] T077 [P] [US8] Unit test: emit_fail sanitizes error message (no sensitive data) in packages/floe-cube/tests/unit/test_lineage.py
- [ ] T078 [P] [US8] Unit test: emission failure logs warning and continues (non-blocking) in packages/floe-cube/tests/unit/test_lineage.py
- [ ] T079 [P] [US8] Contract test: emitted events match openlineage-event.schema.json in packages/floe-cube/tests/contract/test_schema_stability.py
- [ ] T080 [P] [US8] Integration test: events appear in Marquez when endpoint configured in packages/floe-cube/tests/integration/test_openlineage.py

### Implementation for User Story 8

- [ ] T081 [US8] Implement QueryLineageEvent Pydantic model (run_id, job_name, namespace, event_type, event_time, inputs, sql, row_count, error) in packages/floe-cube/src/floe_cube/models.py
- [ ] T082 [US8] Implement QueryLineageEmitter class with OpenLineageClient in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T083 [US8] Implement emit_start() method for START events in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T084 [US8] Implement emit_complete() method for COMPLETE events in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T085 [US8] Implement emit_fail() method for FAIL events with sanitized errors in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T086 [US8] Implement error sanitization (remove credentials, PII, truncate) in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T087 [US8] Implement non-blocking emission with try/except and warning logs in packages/floe-cube/src/floe_cube/lineage.py
- [ ] T088 [US8] Add OpenLineage endpoint configuration to cube.js generator in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: OpenLineage integration functional - SC-005 achievable

---

## Phase 11: User Story 9 - Leverage Pre-Aggregations for Performance (Priority: P3)

**Goal**: Configure pre-aggregation definitions with cron-based refresh schedules

**Independent Test**: Define pre-aggregations, trigger a build, and verify subsequent queries use cached data

**Functional Requirements**: FR-025, FR-026

### Tests for User Story 9

- [ ] T089 [P] [US9] Unit test: CubePreAggregation validates cron expression in packages/floe-cube/tests/unit/test_models.py
- [ ] T090 [P] [US9] Unit test: pre-aggregation config generates correct YAML in packages/floe-cube/tests/unit/test_model_sync.py
- [ ] T091 [P] [US9] Integration test: queries use pre-aggregated data when available in packages/floe-cube/tests/integration/test_cube_api.py

### Implementation for User Story 9

- [ ] T092 [US9] Implement pre-aggregation YAML generation from PreAggregationConfig in packages/floe-cube/src/floe_cube/model_sync.py
- [ ] T093 [US9] Add refresh_schedule configuration to generated cube schemas in packages/floe-cube/src/floe_cube/model_sync.py
- [ ] T094 [US9] Add Cube Store configuration (S3 bucket, credentials) to cube.js generator in packages/floe-cube/src/floe_cube/config.py

**Checkpoint**: Pre-aggregations functional - SC-003 achievable

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T095 [P] Add package README.md with usage examples in packages/floe-cube/README.md
- [ ] T096 [P] Add Google-style docstrings to all public functions
- [ ] T097 Run mypy --strict and fix all type errors in packages/floe-cube/
- [ ] T098 Run ruff check and fix all linting issues in packages/floe-cube/
- [ ] T099 Run bandit security scan and address findings in packages/floe-cube/
- [ ] T100 Verify >80% test coverage with pytest --cov in packages/floe-cube/
- [ ] T101 Run quickstart.md validation (manual test of documented workflow)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 and can proceed in parallel
  - US3, US4, US5 (all P2) can proceed in parallel after US1+US2
  - US6, US7, US8, US9 (all P3) can proceed in parallel after US1+US2
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - generates cube.js config
- **User Story 2 (P1)**: Can start after Foundational - generates schema YAMLs
- **User Story 3 (P2)**: Depends on US1 (REST API needs config) - integration testing
- **User Story 4 (P2)**: Depends on US1 (GraphQL API needs config) - integration testing
- **User Story 5 (P2)**: Depends on US1 (SQL API needs config) - integration testing
- **User Story 6 (P3)**: Depends on US1 (security config) - can run parallel with US3-5
- **User Story 7 (P3)**: Can start after Foundational - independent OpenTelemetry tracer
- **User Story 8 (P3)**: Can start after Foundational - independent OpenLineage emitter
- **User Story 9 (P3)**: Depends on US2 (schema generation) - pre-agg config

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before configuration generators
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational model tasks (T006-T011) marked [P] can run in parallel
- Once Foundational phase completes:
  - US1 and US2 can start in parallel
  - After US1 completes: US3, US4, US5 can all run in parallel
  - US6, US7, and US8 can run in parallel (independent observability tracks)
- All tests for a user story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test: config generator creates valid cube.js for each database_type in packages/floe-cube/tests/unit/test_config.py"
Task: "Unit test: config generator references K8s secrets (never embeds credentials) in packages/floe-cube/tests/unit/test_config.py"
Task: "Contract test: generated config matches cube-config.schema.json in packages/floe-cube/tests/contract/test_schema_stability.py"
```

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Unit test: model_sync extracts dimensions from dbt columns with correct type mapping"
Task: "Unit test: model_sync extracts measures from meta.cube.measures tags"
Task: "Unit test: model_sync creates joins from dbt relationships"
Task: "Unit test: model_sync handles incremental updates without duplicating cubes"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (cube.js generation)
4. Complete Phase 4: User Story 2 (schema generation)
5. **STOP and VALIDATE**: Test US1+US2 independently - can now deploy Cube with generated config
6. Deploy/demo if ready (SC-001: expose dbt models in 5 minutes)

### Incremental Delivery

1. Complete Setup + Foundational + US1 + US2 → Foundation ready, Cube deployable
2. Add US3 + US4 + US5 → All three APIs tested → Deploy (SC-007 achieved)
3. Add US6 → Row-level security → Deploy (SC-004, SC-006 achieved)
4. Add US7 → OpenLineage integration → Deploy (SC-005 achieved)
5. Add US8 → Pre-aggregations → Deploy (SC-003 achieved)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (config generation)
   - Developer B: User Story 2 (model sync)
3. After US1+US2:
   - Developer A: User Stories 3+4+5 (API integration tests)
   - Developer B: User Story 6 (security) + User Story 8 (pre-aggs)
   - Developer C: User Story 7 (OpenLineage)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Cube owns the APIs (REST, GraphQL, SQL) - our work is configuration and integration testing
- floe-core schema update (FR-030) is in Foundational phase as it blocks security story
- **OpenTelemetry vs OpenLineage**: US7 (OTel) provides operational observability ("how is system performing?"), US8 (OpenLineage) provides data lineage ("what data is accessed?") - both are complementary

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 101 |
| **Setup Tasks** | 4 |
| **Foundational Tasks** | 8 |
| **User Story Tasks** | 82 |
| **Polish Tasks** | 7 |

### Tasks per User Story

| Story | Priority | Task Count | Description |
|-------|----------|------------|-------------|
| US1 | P1 | 8 | Configure Cube Semantic Layer |
| US2 | P1 | 15 | Sync dbt Models to Cube Cubes |
| US3 | P2 | 5 | Query Data via REST API |
| US4 | P2 | 3 | Query Data via GraphQL API |
| US5 | P2 | 4 | Query Data via SQL API |
| US6 | P3 | 12 | Enforce Row-Level Security |
| US7 | P3 | 14 | Monitor Query Performance (OpenTelemetry) |
| US8 | P3 | 15 | Emit OpenLineage Events |
| US9 | P3 | 6 | Leverage Pre-Aggregations |

### MVP Scope

**Recommended MVP**: User Stories 1 + 2 (P1)
- 23 tasks (Setup + Foundational + US1 + US2)
- Delivers: Cube configuration generation, dbt model sync
- Achieves: SC-001 (expose dbt models in 5 minutes)
- Independent test: Can deploy Cube with generated config
