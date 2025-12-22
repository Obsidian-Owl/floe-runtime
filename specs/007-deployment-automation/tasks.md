# Tasks: Deployment Automation

**Input**: Design documents from `/specs/007-deployment-automation/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/preflight-api.yaml

**Tests**: E2E tests included per FR-029 (E2E validation tests required by spec).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **docker/**: Production Dockerfiles
- **charts/**: Helm charts (floe-dagster, floe-cube, floe-runtime umbrella)
- **examples/**: GitOps and secrets management examples
- **demo/**: dbt project with medallion architecture
- **packages/floe-cli/**: CLI extension (preflight command)
- **packages/floe-synthetic/**: Synthetic data enhancements
- **testing/**: E2E test infrastructure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and base files for all deployment components

- [ ] T001 Create docker/ directory structure per plan.md
- [ ] T002 [P] Create charts/floe-dagster/ directory with Chart.yaml skeleton
- [ ] T003 [P] Create charts/floe-cube/ directory with Chart.yaml skeleton
- [ ] T004 [P] Create charts/floe-runtime/ umbrella chart directory
- [ ] T005 [P] Create examples/gitops/argocd/ directory structure
- [ ] T006 [P] Create examples/gitops/flux/ directory structure
- [ ] T007 [P] Create examples/secrets/ directory with external-secrets/, sealed-secrets/, sops/ subdirs
- [ ] T008 [P] Create examples/environments/ with dev/, staging/, prod/ subdirs
- [ ] T009 Create demo/ dbt project directory structure per plan.md
- [ ] T010 [P] Create testing/e2e/ directory for E2E tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 Create docker/Dockerfile.dagster with multi-stage build pattern per research.md in docker/Dockerfile.dagster
- [ ] T012 [P] Create docker/Dockerfile.cube with multi-stage build pattern in docker/Dockerfile.cube
- [ ] T013 Add OrderItem schema to floe-synthetic in packages/floe-synthetic/src/floe_synthetic/schemas/ecommerce.py
- [ ] T014 Add order_items generation to EcommerceGenerator in packages/floe-synthetic/src/floe_synthetic/generators/ecommerce.py
- [ ] T015 [P] Create data quality defects module in packages/floe-synthetic/src/floe_synthetic/quality/__init__.py
- [ ] T016 Implement null/duplicate/late-arriving injection in packages/floe-synthetic/src/floe_synthetic/quality/defects.py

**Checkpoint**: Foundation ready - Dockerfiles built, synthetic data enhanced. User story implementation can now begin.

---

## Phase 3: User Story 1 - Deploy floe-runtime to Kubernetes (Priority: P1)

**Goal**: Platform Engineer can deploy floe-runtime to any Kubernetes cluster using Helm

**Independent Test**: Run `helm install floe-runtime charts/floe-dagster` against kind cluster, verify Dagster UI accessible

### Implementation for User Story 1

- [ ] T017 [US1] Create Chart.yaml with dagster/dagster dependency in charts/floe-dagster/Chart.yaml
- [ ] T018 [US1] Create default values.yaml with image, resources, replicas in charts/floe-dagster/values.yaml
- [ ] T019 [P] [US1] Create values-dev.yaml with development overrides in charts/floe-dagster/values-dev.yaml
- [ ] T020 [P] [US1] Create values-prod.yaml with production resource limits in charts/floe-dagster/values-prod.yaml
- [ ] T021 [US1] Create configmap.yaml template for CompiledArtifacts mount in charts/floe-dagster/templates/configmap.yaml
- [ ] T022 [P] [US1] Create ingress.yaml template in charts/floe-dagster/templates/ingress.yaml
- [ ] T023 [US1] Create _helpers.tpl with common template functions in charts/floe-dagster/templates/_helpers.tpl
- [ ] T024 [US1] Run helm lint on floe-dagster chart and fix any errors
- [ ] T025 [US1] Run helm template to verify chart renders correctly

**Checkpoint**: User Story 1 complete - Helm chart deployable to Kubernetes

---

## Phase 4: User Story 2 - Automate Deployments via GitOps (Priority: P2)

**Goal**: DevOps Engineer can automate deployments using ArgoCD or Flux

**Independent Test**: Create ArgoCD Application, push values change, verify auto-sync within 3 minutes

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create ArgoCD Application example in examples/gitops/argocd/application.yaml
- [ ] T027 [P] [US2] Create ArgoCD ApplicationSet for multi-env in examples/gitops/argocd/applicationset.yaml
- [ ] T028 [P] [US2] Create Flux HelmRelease example in examples/gitops/flux/helmrelease.yaml
- [ ] T029 [P] [US2] Create Flux Kustomization example in examples/gitops/flux/kustomization.yaml
- [ ] T030 [US2] Create dev environment values in examples/environments/dev/values.yaml
- [ ] T031 [P] [US2] Create staging environment values in examples/environments/staging/values.yaml
- [ ] T032 [P] [US2] Create prod environment values in examples/environments/prod/values.yaml

**Checkpoint**: User Story 2 complete - GitOps examples for ArgoCD and Flux available

---

## Phase 5: User Story 3 - Validate Environment Before Deployment (Priority: P3)

**Goal**: Data Engineer can validate infrastructure connectivity with `floe preflight`

**Independent Test**: Run `floe preflight --all` and verify status table output for each service

### Implementation for User Story 3

- [ ] T033 [US3] Create PreflightConfig Pydantic model in packages/floe-cli/src/floe_cli/commands/preflight.py
- [ ] T034 [US3] Create PreflightResult and PreflightReport models per contracts/preflight-api.yaml
- [ ] T035 [US3] Implement compute engine check (Trino via trino-python-client) in preflight.py
- [ ] T036 [P] [US3] Implement compute check for Snowflake (snowflake-connector-python)
- [ ] T037 [P] [US3] Implement compute check for BigQuery (google-cloud-bigquery)
- [ ] T038 [P] [US3] Implement compute check for DuckDB (duckdb)
- [ ] T039 [US3] Implement storage check for S3 (boto3 head_bucket) in preflight.py
- [ ] T040 [P] [US3] Implement storage check for GCS (google-cloud-storage)
- [ ] T041 [P] [US3] Implement storage check for ADLS (azure-storage-blob)
- [ ] T042 [US3] Implement catalog check for Polaris (OAuth2 + /v1/config) in preflight.py
- [ ] T043 [US3] Implement PostgreSQL check (psycopg2) in preflight.py
- [ ] T044 [US3] Implement Rich table output formatting in preflight.py
- [ ] T045 [US3] Implement JSON output mode (--json flag) in preflight.py
- [ ] T046 [US3] Register preflight command in floe-cli in packages/floe-cli/src/floe_cli/main.py
- [ ] T047 [US3] Add preflight dependencies to pyproject.toml in packages/floe-cli/pyproject.toml

**Checkpoint**: User Story 3 complete - `floe preflight` validates all infrastructure

---

## Phase 6: User Story 4 - Manage Secrets Securely (Priority: P4)

**Goal**: Security Engineer can deploy with credentials without exposing them in Git

**Independent Test**: Deploy with External Secrets configured, verify secrets injected into pods

### Implementation for User Story 4

- [ ] T048 [US4] Create ExternalSecret template in charts/floe-dagster/templates/externalsecret.yaml
- [ ] T049 [US4] Add externalSecrets values section to charts/floe-dagster/values.yaml
- [ ] T050 [P] [US4] Create External Secrets example for AWS in examples/secrets/external-secrets/aws-secretsmanager.yaml
- [ ] T051 [P] [US4] Create External Secrets example for Vault in examples/secrets/external-secrets/hashicorp-vault.yaml
- [ ] T052 [P] [US4] Create Sealed Secrets example in examples/secrets/sealed-secrets/example.yaml
- [ ] T053 [P] [US4] Create SOPS example with age key in examples/secrets/sops/example.yaml
- [ ] T054 [US4] Document secrets management options in examples/secrets/README.md

**Checkpoint**: User Story 4 complete - Multiple secrets management patterns documented

---

## Phase 7: User Story 5 - Deploy Cube Semantic Layer (Priority: P5)

**Goal**: Data Platform Lead can deploy Cube alongside Dagster for data consumption APIs

**Independent Test**: Deploy floe-cube chart, verify Cube API responds to query

### Implementation for User Story 5

- [ ] T055 [US5] Create Chart.yaml for floe-cube in charts/floe-cube/Chart.yaml
- [ ] T056 [US5] Create values.yaml with Cube configuration in charts/floe-cube/values.yaml
- [ ] T057 [US5] Create deployment.yaml template for Cube API in charts/floe-cube/templates/deployment.yaml
- [ ] T058 [P] [US5] Create service.yaml template in charts/floe-cube/templates/service.yaml
- [ ] T059 [P] [US5] Create configmap.yaml for Cube schema in charts/floe-cube/templates/configmap.yaml
- [ ] T060 [US5] Create refresh-worker deployment in charts/floe-cube/templates/refresh-worker.yaml
- [ ] T061 [US5] Create floe-runtime umbrella Chart.yaml in charts/floe-runtime/Chart.yaml
- [ ] T062 [US5] Create umbrella values.yaml referencing sub-charts in charts/floe-runtime/values.yaml
- [ ] T063 [US5] Run helm lint on floe-cube and floe-runtime charts

**Checkpoint**: User Story 5 complete - Cube deployable alongside Dagster

---

## Phase 8: User Story 6 - E2E Deployment Demo with Live Data (Priority: P6)

**Goal**: Solutions Architect can demonstrate live data flow from generation to Cube API

**Independent Test**: Deploy demo profile, wait 10 minutes, verify data in Cube queries

### E2E Tests for User Story 6

- [ ] T064 [P] [US6] Create E2E test fixtures in testing/e2e/conftest.py
- [ ] T065 [P] [US6] Create test_demo_flow.py with @pytest.mark.requirement("007-FR-029") in testing/e2e/test_demo_flow.py
- [ ] T066 [US6] Implement test for synthetic data appears in Cube (FR-029)
- [ ] T067 [P] [US6] Implement test for Cube pre-aggregation refresh (FR-032)

### Demo dbt Project Implementation

- [ ] T068 [US6] Create dbt_project.yml with demo configuration in demo/dbt_project.yml
- [ ] T069 [P] [US6] Create sources.yml defining Iceberg sources in demo/models/sources.yml
- [ ] T070 [P] [US6] Create stg_customers.sql staging model in demo/models/staging/stg_customers.sql
- [ ] T071 [P] [US6] Create stg_orders.sql staging model in demo/models/staging/stg_orders.sql
- [ ] T072 [P] [US6] Create stg_order_items.sql staging model in demo/models/staging/stg_order_items.sql
- [ ] T073 [P] [US6] Create stg_products.sql staging model in demo/models/staging/stg_products.sql
- [ ] T074 [US6] Create int_order_items_enriched.sql intermediate model in demo/models/intermediate/int_order_items_enriched.sql
- [ ] T075 [P] [US6] Create int_customer_orders.sql intermediate model in demo/models/intermediate/int_customer_orders.sql
- [ ] T076 [P] [US6] Create int_product_performance.sql intermediate model in demo/models/intermediate/int_product_performance.sql
- [ ] T077 [US6] Create mart_revenue.sql mart model in demo/models/marts/mart_revenue.sql
- [ ] T078 [P] [US6] Create mart_customer_segments.sql mart model in demo/models/marts/mart_customer_segments.sql
- [ ] T079 [P] [US6] Create mart_product_analytics.sql mart model in demo/models/marts/mart_product_analytics.sql

### Demo Cube Schema Implementation

- [ ] T080 [P] [US6] Create Orders.js Cube schema in demo/cube/schema/Orders.js
- [ ] T081 [P] [US6] Create Customers.js Cube schema in demo/cube/schema/Customers.js
- [ ] T082 [P] [US6] Create Products.js Cube schema in demo/cube/schema/Products.js

### Demo Infrastructure Implementation

- [ ] T083 [US6] Create values-demo.yaml with demo configuration in charts/floe-dagster/values-demo.yaml
- [ ] T084 [US6] Create demo Dagster schedule for synthetic data generation in packages/floe-synthetic/src/floe_synthetic/assets/demo.py
- [ ] T085 [US6] Implement on-demand generation API endpoint (FR-026a) in demo asset
- [ ] T086 [US6] Update docker-compose.yml with demo profile in testing/docker/docker-compose.yml
- [ ] T087 [US6] Create run-demo.sh script for continuous demo in testing/docker/scripts/run-demo.sh
- [ ] T088 [US6] Add Marquez service to demo profile (FR-033) in testing/docker/docker-compose.yml
- [ ] T089 [US6] Add Jaeger service to demo profile (FR-034) in testing/docker/docker-compose.yml

**Checkpoint**: User Story 6 complete - Full E2E demo with live data flow operational

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and validation across all user stories

- [ ] T090 [P] Update docs/06-deployment-view.md with metadata-driven architecture (FR-021)
- [ ] T091 [P] Create docs/07-infrastructure-provisioning.md for external services (FR-022)
- [ ] T092 [P] Add multi-target compute examples to documentation (FR-024)
- [ ] T093 Run quickstart.md validation against deployed demo
- [ ] T094 Run helm lint on all charts
- [ ] T095 Run mypy --strict on preflight command
- [ ] T096 Run ruff check on all new Python code
- [ ] T097 Verify all E2E tests pass with @pytest.mark.requirement markers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5 → P6)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 (needs Helm charts to reference)
- **User Story 3 (P3)**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (P4)**: Depends on US1 (needs Helm chart templates)
- **User Story 5 (P5)**: Can start after Foundational - No dependencies on other stories
- **User Story 6 (P6)**: Depends on US1, US5 (needs Helm charts and Cube)

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, independent user stories can start in parallel:
  - US1, US3, US5 can all start simultaneously
  - US2, US4 wait for US1; US6 waits for US1 and US5
- All tasks within a story marked [P] can run in parallel

---

## Parallel Example: User Story 6 (Demo)

```bash
# Launch all staging models together:
Task: "Create stg_customers.sql staging model in demo/models/staging/stg_customers.sql"
Task: "Create stg_orders.sql staging model in demo/models/staging/stg_orders.sql"
Task: "Create stg_order_items.sql staging model in demo/models/staging/stg_order_items.sql"
Task: "Create stg_products.sql staging model in demo/models/staging/stg_products.sql"

# Launch all Cube schemas together:
Task: "Create Orders.js Cube schema in demo/cube/schema/Orders.js"
Task: "Create Customers.js Cube schema in demo/cube/schema/Customers.js"
Task: "Create Products.js Cube schema in demo/cube/schema/Products.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Helm charts)
4. **STOP and VALIDATE**: Deploy to kind cluster, verify Dagster UI
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Helm deployment works!)
3. Add User Story 3 → Test independently → Deploy/Demo (Preflight validates!)
4. Add User Story 2 → Test independently → Deploy/Demo (GitOps works!)
5. Add User Story 4 → Test independently → Deploy/Demo (Secrets secured!)
6. Add User Story 5 → Test independently → Deploy/Demo (Cube deployed!)
7. Add User Story 6 → Test independently → Deploy/Demo (Full E2E demo!)
8. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Helm charts)
   - Developer B: User Story 3 (Preflight CLI)
   - Developer C: User Story 5 (Cube chart)
3. After US1 completes:
   - Developer A: User Story 2 (GitOps)
   - Developer D: User Story 4 (Secrets)
4. After US1 + US5 complete:
   - Team: User Story 6 (E2E Demo)

---

## Task Summary

| Phase | User Story | Task Count | Parallel Tasks |
|-------|------------|------------|----------------|
| 1 | Setup | 10 | 8 |
| 2 | Foundational | 6 | 2 |
| 3 | US1 - K8s Deploy | 9 | 3 |
| 4 | US2 - GitOps | 7 | 5 |
| 5 | US3 - Preflight | 15 | 6 |
| 6 | US4 - Secrets | 7 | 4 |
| 7 | US5 - Cube | 9 | 3 |
| 8 | US6 - E2E Demo | 26 | 15 |
| 9 | Polish | 8 | 3 |
| **Total** | | **97** | **49** |

**MVP Scope**: Complete Phases 1-3 (25 tasks) for deployable Helm charts

**Full Feature**: Complete all 97 tasks for complete deployment automation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- FR-XXX references map to functional requirements in spec.md
