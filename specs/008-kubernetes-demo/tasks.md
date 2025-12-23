# Tasks: Kubernetes Demo Deployment

**Input**: Design documents from `/specs/008-kubernetes-demo/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: No automated tests requested for this infrastructure feature. Validation is via `helm lint`, `helm template`, and manual deployment verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Helm charts**: `charts/` at repository root
- **Demo assets**: `demo/` at repository root
- **Makefile**: Root `Makefile`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Helm chart structure

- [ ] T001 Create chart directory structure at charts/floe-infrastructure/
- [ ] T002 [P] Create Chart.yaml with subchart dependencies in charts/floe-infrastructure/Chart.yaml
- [ ] T003 [P] Create default values.yaml in charts/floe-infrastructure/values.yaml
- [ ] T004 Create Helm helpers template in charts/floe-infrastructure/templates/_helpers.tpl
- [ ] T005 Run `helm dependency update charts/floe-infrastructure` to fetch subcharts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create values-local.yaml with emptyDir storage in charts/floe-infrastructure/values-local.yaml
- [ ] T007 [P] Create Polaris init hook Job template in charts/floe-infrastructure/templates/polaris-init-job.yaml
- [ ] T008 [P] Create NOTES.txt with post-install instructions in charts/floe-infrastructure/templates/NOTES.txt
- [ ] T009 Validate chart with `helm lint charts/floe-infrastructure`
- [ ] T010 Validate chart templates with `helm template floe-infra charts/floe-infrastructure -f charts/floe-infrastructure/values-local.yaml`

**Checkpoint**: Infrastructure chart validated - user story implementation can now begin

---

## Phase 3: User Story 1 - Deploy Complete Stack to Local Kubernetes (Priority: P1)

**Goal**: Platform Engineer deploys complete floe-runtime stack with single command sequence

**Independent Test**: Run `make deploy-local-full` and verify all 8+ pods reach Running state within 5 minutes

### Implementation for User Story 1

- [ ] T011 [US1] Create values-local.yaml for floe-dagster in charts/floe-dagster/values-local.yaml
- [ ] T012 [P] [US1] Create values-local.yaml for floe-cube in charts/floe-cube/values-local.yaml
- [ ] T013 [US1] Add deploy-local-infra target to Makefile
- [ ] T014 [US1] Add deploy-local-dagster target to Makefile
- [ ] T015 [US1] Add deploy-local-cube target to Makefile
- [ ] T016 [US1] Add deploy-local-full target with wait logic to Makefile
- [ ] T017 [US1] Add undeploy-local target to Makefile
- [ ] T018 [US1] Add port-forward-all target to Makefile
- [ ] T019 [US1] Deploy infrastructure chart with `helm install floe-infra charts/floe-infrastructure -n floe --create-namespace -f charts/floe-infrastructure/values-local.yaml`
- [ ] T020 [US1] Verify PostgreSQL, MinIO, Polaris, Jaeger pods reach Running state
- [ ] T021 [US1] Deploy Dagster chart with `helm install floe-dagster charts/floe-dagster -n floe -f charts/floe-dagster/values-local.yaml`
- [ ] T022 [US1] Deploy Cube chart with `helm install floe-cube charts/floe-cube -n floe -f charts/floe-cube/values-local.yaml`
- [ ] T023 [US1] Verify all 8+ pods show 1/1 READY status with `kubectl get pods -n floe`
- [ ] T024 [US1] Verify Dagster UI accessible via port-forward at localhost:3000

**Checkpoint**: User Story 1 complete - full stack deploys with single command

---

## Phase 4: User Story 2 - Query Data via Cube Semantic Layer (Priority: P2)

**Goal**: Data Analyst queries demo data through Cube REST API and SQL API

**Independent Test**: Hit Cube's /cubejs-api/v1/load endpoint and receive JSON response

### Implementation for User Story 2

- [ ] T025 [US2] Configure DuckDB data source in charts/floe-cube/values-local.yaml (CUBEJS_DB_TYPE: duckdb)
- [ ] T026 [US2] Configure Polaris endpoint in Cube values (CUBEJS_DB_DUCKDB_S3_ENDPOINT)
- [ ] T027 [US2] Enable SQL API on port 15432 in charts/floe-cube/values-local.yaml
- [ ] T028 [US2] Configure Cube Store for pre-aggregations in charts/floe-cube/values-local.yaml
- [ ] T029 [US2] Update Cube schema to use DuckDB + Iceberg SQL in demo/cube/schema/Orders.js
- [ ] T030 [US2] Verify Cube REST API responds at localhost:4000/readyz
- [ ] T031 [US2] Test query via REST API: curl localhost:4000/cubejs-api/v1/load with Orders measures
- [ ] T032 [US2] Verify SQL API connection via psycopg2 on port 15432
- [ ] T033 [US2] Test MEASURE() syntax query: SELECT MEASURE(count) FROM Orders

**Checkpoint**: User Story 2 complete - Cube queries work with DuckDB + Iceberg

---

## Phase 5: User Story 3 - Generate Demo Data On-Demand (Priority: P3)

**Goal**: Solutions Architect generates synthetic ecommerce data during live demos

**Independent Test**: Trigger Dagster job via UI and see new data in Cube queries

### Implementation for User Story 3

- [ ] T034 [US3] Add dbt-duckdb profile to demo/profiles.yml
- [ ] T035 [US3] Implement empty_tables_sensor in demo/orchestration/definitions.py
- [ ] T036 [US3] Implement seed_demo_data_job in demo/orchestration/definitions.py
- [ ] T037 [US3] Add 5-minute generation schedule to demo/orchestration/definitions.py
- [ ] T038 [US3] Configure Polaris connection (OAuth2 secrets) in demo/orchestration/config.py
- [ ] T039 [US3] Deploy updated Dagster image with new definitions
- [ ] T040 [US3] Verify sensor detects empty tables and triggers seed job
- [ ] T041 [US3] Verify seed job generates customers, products, orders data
- [ ] T042 [US3] Verify 5-minute schedule triggers and appends new orders
- [ ] T043 [US3] Test manual trigger via Dagster GraphQL API

**Checkpoint**: User Story 3 complete - data generation works on-demand and scheduled

---

## Phase 6: User Story 4 - View Observability Data (Priority: P4)

**Goal**: DevOps Engineer views traces in Jaeger and lineage in Marquez

**Independent Test**: View traces in Jaeger UI after running a data generation job

### Implementation for User Story 4

- [ ] T044 [US4] Configure OpenTelemetry exporter to Jaeger in demo/orchestration/config.py
- [ ] T045 [US4] Configure OpenLineage exporter to Marquez in demo/orchestration/config.py
- [ ] T046 [US4] Verify Jaeger UI accessible at localhost:16686
- [ ] T047 [US4] Run data generation job and verify traces appear in Jaeger
- [ ] T048 [US4] Verify Marquez UI accessible at localhost:5001
- [ ] T049 [US4] Verify dbt model lineage appears in Marquez

**Checkpoint**: User Story 4 complete - observability working for all pipeline operations

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and validation

- [ ] T050 [P] Update quickstart.md with deployment verification steps in specs/008-kubernetes-demo/quickstart.md
- [ ] T051 [P] Add troubleshooting section to quickstart.md
- [ ] T052 Run full validation: make deploy-local-full from clean state
- [ ] T053 Verify all success criteria from spec.md (SC-001 through SC-006)
- [ ] T054 Clean up any temporary files or test artifacts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 must complete first (provides running cluster for US2-4)
  - US2-4 can then proceed in priority order
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: MUST complete first - provides the deployed cluster
- **User Story 2 (P2)**: Depends on US1 (needs running Cube + infrastructure)
- **User Story 3 (P3)**: Depends on US1 (needs running Dagster + Polaris)
- **User Story 4 (P4)**: Depends on US1 and US3 (needs traces from running jobs)

### Within Each User Story

- Configuration files before deployment
- Deployment before verification
- Core functionality before integration

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T007 and T008 can run in parallel (different templates)
- T011 and T012 can run in parallel (different charts)
- T044 and T045 can run in parallel (different exporters)
- T050 and T051 can run in parallel (different doc sections)

---

## Parallel Example: Phase 1 Setup

```bash
# Launch chart creation tasks together:
Task: "Create Chart.yaml with subchart dependencies in charts/floe-infrastructure/Chart.yaml"
Task: "Create default values.yaml in charts/floe-infrastructure/values.yaml"
```

## Parallel Example: Foundational Templates

```bash
# Launch template tasks together:
Task: "Create Polaris init hook Job template in charts/floe-infrastructure/templates/polaris-init-job.yaml"
Task: "Create NOTES.txt with post-install instructions in charts/floe-infrastructure/templates/NOTES.txt"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Deploy Complete Stack)
4. **STOP and VALIDATE**: Verify all pods running with `kubectl get pods -n floe`
5. Demo/validate if ready

### Incremental Delivery

1. Complete Setup + Foundational → Infrastructure chart ready
2. Add User Story 1 → Test deployment → Demo (MVP!)
3. Add User Story 2 → Test Cube queries → Demo
4. Add User Story 3 → Test data generation → Demo
5. Add User Story 4 → Test observability → Demo
6. Each story adds value without breaking previous stories

### Sequential Execution (Single Developer)

1. Setup (T001-T005): ~30 minutes
2. Foundational (T006-T010): ~30 minutes
3. User Story 1 (T011-T024): ~2 hours
4. User Story 2 (T025-T033): ~1 hour
5. User Story 3 (T034-T043): ~2 hours
6. User Story 4 (T044-T049): ~1 hour
7. Polish (T050-T054): ~30 minutes

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently verifiable once complete
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

## Files Created/Modified

### New Files

| File | Phase | Description |
|------|-------|-------------|
| `charts/floe-infrastructure/Chart.yaml` | Setup | Chart with subchart dependencies |
| `charts/floe-infrastructure/values.yaml` | Setup | Default values |
| `charts/floe-infrastructure/values-local.yaml` | Foundational | Docker Desktop optimized |
| `charts/floe-infrastructure/templates/_helpers.tpl` | Setup | Helm helpers |
| `charts/floe-infrastructure/templates/polaris-init-job.yaml` | Foundational | Polaris initialization |
| `charts/floe-infrastructure/templates/NOTES.txt` | Foundational | Post-install instructions |
| `charts/floe-dagster/values-local.yaml` | US1 | Local K8s values |
| `charts/floe-cube/values-local.yaml` | US1/US2 | DuckDB + Polaris config |

### Modified Files

| File | Phase | Description |
|------|-------|-------------|
| `Makefile` | US1 | Deploy targets |
| `demo/profiles.yml` | US3 | dbt-duckdb profile |
| `demo/orchestration/definitions.py` | US3 | Sensor and schedule |
| `demo/orchestration/config.py` | US3/US4 | Polaris + observability config |
| `demo/cube/schema/Orders.js` | US2 | DuckDB + Iceberg SQL |
