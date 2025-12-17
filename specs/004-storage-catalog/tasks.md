# Tasks: Storage & Catalog Layer

**Input**: Design documents from `/specs/004-storage-catalog/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as this is a foundational package requiring >80% coverage per Constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Monorepo**: `packages/floe-polaris/src/floe_polaris/`, `packages/floe-iceberg/src/floe_iceberg/`
- **Tests**: `packages/floe-polaris/tests/`, `packages/floe-iceberg/tests/`

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Initialize the two packages with dependencies and structure

- [ ] T001 Create floe-polaris package structure in packages/floe-polaris/
- [ ] T002 Create floe-iceberg package structure in packages/floe-iceberg/
- [ ] T003 [P] Configure pyproject.toml for floe-polaris with dependencies (pyiceberg>=0.8, tenacity, structlog, opentelemetry-api)
- [ ] T004 [P] Configure pyproject.toml for floe-iceberg with dependencies (pyiceberg>=0.8, dagster>=1.9, pyarrow, pandas)
- [ ] T005 [P] Create __init__.py with public API exports in packages/floe-polaris/src/floe_polaris/__init__.py
- [ ] T006 [P] Create __init__.py with public API exports in packages/floe-iceberg/src/floe_iceberg/__init__.py
- [ ] T007 [P] Configure pytest and coverage for floe-polaris in packages/floe-polaris/pyproject.toml
- [ ] T008 [P] Configure pytest and coverage for floe-iceberg in packages/floe-iceberg/pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### Shared Exception Hierarchy

- [ ] T009 [P] Implement FloeStorageError base exception in packages/floe-polaris/src/floe_polaris/errors.py
- [ ] T010 [P] Implement catalog exceptions (CatalogConnectionError, CatalogAuthenticationError, NamespaceExistsError, NamespaceNotFoundError, NamespaceNotEmptyError, TableNotFoundError) in packages/floe-polaris/src/floe_polaris/errors.py
- [ ] T011 [P] Implement storage exceptions (TableExistsError, SchemaEvolutionError, WriteError, ScanError) in packages/floe-iceberg/src/floe_iceberg/errors.py

### Configuration Models

- [ ] T012 [P] Implement RetryConfig Pydantic model in packages/floe-polaris/src/floe_polaris/config.py
- [ ] T013 [P] Implement PolarisCatalogConfig Pydantic model with validation in packages/floe-polaris/src/floe_polaris/config.py
- [ ] T014 [P] Implement WriteMode enum in packages/floe-iceberg/src/floe_iceberg/config.py
- [ ] T015 [P] Implement IcebergIOManagerConfig Pydantic model in packages/floe-iceberg/src/floe_iceberg/config.py
- [ ] T016 [P] Implement TableIdentifier model with from_string and from_asset_key methods in packages/floe-iceberg/src/floe_iceberg/config.py
- [ ] T017 [P] Implement PartitionTransform and PartitionTransformType in packages/floe-iceberg/src/floe_iceberg/partitions.py
- [ ] T018 [P] Implement SnapshotInfo model in packages/floe-iceberg/src/floe_iceberg/config.py
- [ ] T019 [P] Implement MaterializationMetadata model in packages/floe-iceberg/src/floe_iceberg/config.py
- [ ] T020 [P] Implement NamespaceInfo model in packages/floe-polaris/src/floe_polaris/config.py

### Observability Infrastructure

- [ ] T021 [P] Implement structured logging setup in packages/floe-polaris/src/floe_polaris/observability.py
- [ ] T022 [P] Implement OpenTelemetry span helpers in packages/floe-polaris/src/floe_polaris/observability.py
- [ ] T023 [P] Implement observability module for floe-iceberg in packages/floe-iceberg/src/floe_iceberg/observability.py

### Retry Infrastructure

- [ ] T024 Implement tenacity retry decorator factory in packages/floe-polaris/src/floe_polaris/retry.py

### Unit Tests for Foundation

- [ ] T025 [P] Write unit tests for RetryConfig validation in packages/floe-polaris/tests/unit/test_config.py
- [ ] T026 [P] Write unit tests for PolarisCatalogConfig validation in packages/floe-polaris/tests/unit/test_config.py
- [ ] T027 [P] Write unit tests for TableIdentifier parsing in packages/floe-iceberg/tests/unit/test_config.py
- [ ] T028 [P] Write unit tests for PartitionTransform validation in packages/floe-iceberg/tests/unit/test_partitions.py
- [ ] T029 [P] Write unit tests for retry decorator in packages/floe-polaris/tests/unit/test_retry.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Connect to Polaris Catalog (Priority: P1) MVP

**Goal**: Enable data engineers to connect to Apache Polaris REST catalog with OAuth2 authentication

**Independent Test**: Configure catalog credentials, verify connection succeeds, list namespaces

### Tests for User Story 1

- [ ] T030 [P] [US1] Write unit tests for PolarisCatalog client initialization in packages/floe-polaris/tests/unit/test_client.py
- [ ] T031 [P] [US1] Write unit tests for OAuth2 authentication handling in packages/floe-polaris/tests/unit/test_client.py
- [ ] T032 [P] [US1] Write unit tests for create_catalog factory function in packages/floe-polaris/tests/unit/test_factory.py

### Implementation for User Story 1

- [ ] T033 [US1] Implement PolarisCatalog class wrapping PyIceberg RestCatalog in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T034 [US1] Implement OAuth2 client credentials flow in PolarisCatalog in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T035 [US1] Implement bearer token authentication in PolarisCatalog in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T036 [US1] Implement automatic token refresh logic in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T037 [US1] Implement is_connected() and reconnect() methods in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T038 [US1] Implement create_catalog() factory function in packages/floe-polaris/src/floe_polaris/factory.py
- [ ] T039 [US1] Add retry decorator to connection operations in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T040 [US1] Add OpenTelemetry spans for authentication in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T041 [US1] Add structured logging for connection events in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T042 [US1] Implement CatalogConfig to PolarisCatalogConfig conversion in packages/floe-polaris/src/floe_polaris/factory.py
- [ ] T043 [US1] Update __init__.py exports for US1 in packages/floe-polaris/src/floe_polaris/__init__.py

### Integration Tests for User Story 1

- [ ] T044 [US1] Write integration test for catalog connection with mock Polaris in packages/floe-polaris/tests/integration/test_polaris_catalog.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Create and Manage Namespaces (Priority: P2)

**Goal**: Enable data engineers to create and manage hierarchical namespaces

**Independent Test**: Create namespaces, list them, verify properties persist

### Tests for User Story 2

- [ ] T045 [P] [US2] Write unit tests for create_namespace in packages/floe-polaris/tests/unit/test_namespaces.py
- [ ] T046 [P] [US2] Write unit tests for list_namespaces in packages/floe-polaris/tests/unit/test_namespaces.py
- [ ] T047 [P] [US2] Write unit tests for create_namespace_if_not_exists in packages/floe-polaris/tests/unit/test_namespaces.py
- [ ] T048 [P] [US2] Write unit tests for nested namespace handling in packages/floe-polaris/tests/unit/test_namespaces.py

### Implementation for User Story 2

- [ ] T049 [US2] Implement create_namespace method in PolarisCatalog in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T050 [US2] Implement create_namespace_if_not_exists method in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T051 [US2] Implement list_namespaces method in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T052 [US2] Implement load_namespace method in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T053 [US2] Implement drop_namespace method in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T054 [US2] Implement update_namespace_properties method in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T055 [US2] Implement automatic parent namespace creation (create_parents=True) in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T056 [US2] Add retry decorators to namespace operations in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T057 [US2] Add OpenTelemetry spans for namespace operations in packages/floe-polaris/src/floe_polaris/client.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Create and Load Iceberg Tables (Priority: P2)

**Goal**: Enable data engineers to create Iceberg tables with schemas and partition specifications

**Independent Test**: Create table with schema, load it back, verify schema matches

### Tests for User Story 3

- [ ] T058 [P] [US3] Write unit tests for IcebergTableManager initialization in packages/floe-iceberg/tests/unit/test_tables.py
- [ ] T059 [P] [US3] Write unit tests for create_table in packages/floe-iceberg/tests/unit/test_tables.py
- [ ] T060 [P] [US3] Write unit tests for load_table in packages/floe-iceberg/tests/unit/test_tables.py
- [ ] T061 [P] [US3] Write unit tests for partition spec building in packages/floe-iceberg/tests/unit/test_partitions.py

### Implementation for User Story 3

- [ ] T062 [US3] Implement IcebergTableManager class in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T063 [US3] Implement create_table method in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T064 [US3] Implement create_table_if_not_exists method in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T065 [US3] Implement load_table method in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T066 [US3] Implement table_exists method in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T067 [US3] Implement list_tables method in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T068 [US3] Implement drop_table method with purge option in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T069 [US3] Implement partition spec builder for Iceberg hidden partitioning in packages/floe-iceberg/src/floe_iceberg/partitions.py
- [ ] T070 [US3] Add table operations to PolarisCatalog (load_table, table_exists, list_tables) in packages/floe-polaris/src/floe_polaris/client.py
- [ ] T071 [US3] Add OpenTelemetry spans for table operations in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T072 [US3] Update __init__.py exports for US3 in packages/floe-iceberg/src/floe_iceberg/__init__.py

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work independently

---

## Phase 6: User Story 4 - Write Data via Dagster IOManager (Priority: P1) MVP

**Goal**: Enable Dagster assets to automatically write outputs to Iceberg tables

**Independent Test**: Define Dagster asset, materialize it, verify data in Iceberg table

### Tests for User Story 4

- [ ] T073 [P] [US4] Write unit tests for IcebergIOManager handle_output in packages/floe-iceberg/tests/unit/test_io_manager.py
- [ ] T074 [P] [US4] Write unit tests for asset key to table identifier mapping in packages/floe-iceberg/tests/unit/test_io_manager.py
- [ ] T075 [P] [US4] Write unit tests for append operation in packages/floe-iceberg/tests/unit/test_operations.py
- [ ] T076 [P] [US4] Write unit tests for overwrite operation in packages/floe-iceberg/tests/unit/test_operations.py

### Implementation for User Story 4

- [ ] T077 [US4] Implement append function in packages/floe-iceberg/src/floe_iceberg/operations.py
- [ ] T078 [US4] Implement overwrite function in packages/floe-iceberg/src/floe_iceberg/operations.py
- [ ] T079 [US4] Implement IcebergIOManager class extending ConfigurableIOManager in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T080 [US4] Implement get_table_identifier mapping in IcebergIOManager in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T081 [US4] Implement handle_output method for PyArrow Table in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T082 [US4] Implement handle_output method for Pandas DataFrame in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T083 [US4] Implement partitioned write support in handle_output in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T084 [US4] Implement schema evolution in handle_output in packages/floe-iceberg/src/floe_iceberg/schema.py
- [ ] T085 [US4] Implement materialization metadata attachment in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T086 [US4] Implement create_io_manager factory function in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T087 [US4] Add OpenTelemetry spans for write operations in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T088 [US4] Update __init__.py exports for US4 in packages/floe-iceberg/src/floe_iceberg/__init__.py

### Integration Tests for User Story 4

- [ ] T089 [US4] Write integration test for Dagster asset materialization in packages/floe-iceberg/tests/integration/test_dagster_assets.py

**Checkpoint**: At this point, User Story 4 (IOManager write) should be fully functional

---

## Phase 7: User Story 5 - Read Data via Dagster IOManager (Priority: P2)

**Goal**: Enable Dagster assets to automatically read inputs from Iceberg tables

**Independent Test**: Define upstream/downstream assets, materialize both, verify data flows

### Tests for User Story 5

- [ ] T090 [P] [US5] Write unit tests for IcebergIOManager load_input in packages/floe-iceberg/tests/unit/test_io_manager.py
- [ ] T091 [P] [US5] Write unit tests for scan operation in packages/floe-iceberg/tests/unit/test_operations.py
- [ ] T092 [P] [US5] Write unit tests for column projection in packages/floe-iceberg/tests/unit/test_operations.py
- [ ] T093 [P] [US5] Write unit tests for row filtering in packages/floe-iceberg/tests/unit/test_operations.py

### Implementation for User Story 5

- [ ] T094 [US5] Implement scan function in packages/floe-iceberg/src/floe_iceberg/operations.py
- [ ] T095 [US5] Implement load_input method in IcebergIOManager in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T096 [US5] Implement column projection support in load_input in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T097 [US5] Implement row filter support in load_input in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T098 [US5] Implement partitioned read support in load_input in packages/floe-iceberg/src/floe_iceberg/io_manager.py
- [ ] T099 [US5] Add OpenTelemetry spans for read operations in packages/floe-iceberg/src/floe_iceberg/io_manager.py

### Integration Tests for User Story 5

- [ ] T100 [US5] Write integration test for multi-asset pipeline in packages/floe-iceberg/tests/integration/test_dagster_assets.py

**Checkpoint**: At this point, User Stories 4 AND 5 (full IOManager) should work together

---

## Phase 8: User Story 6 - Time Travel Queries (Priority: P3)

**Goal**: Enable querying historical versions of data for debugging and auditing

**Independent Test**: Write data twice, query previous snapshot, verify historical data

### Tests for User Story 6

- [ ] T101 [P] [US6] Write unit tests for list_snapshots in packages/floe-iceberg/tests/unit/test_snapshots.py
- [ ] T102 [P] [US6] Write unit tests for get_current_snapshot in packages/floe-iceberg/tests/unit/test_snapshots.py
- [ ] T103 [P] [US6] Write unit tests for time travel scan in packages/floe-iceberg/tests/unit/test_snapshots.py

### Implementation for User Story 6

- [ ] T104 [US6] Implement list_snapshots in IcebergTableManager in packages/floe-iceberg/src/floe_iceberg/snapshots.py
- [ ] T105 [US6] Implement get_current_snapshot in IcebergTableManager in packages/floe-iceberg/src/floe_iceberg/snapshots.py
- [ ] T106 [US6] Implement snapshot_id parameter in scan function in packages/floe-iceberg/src/floe_iceberg/operations.py
- [ ] T107 [US6] Add snapshot operations to IcebergTableManager in packages/floe-iceberg/src/floe_iceberg/tables.py

**Checkpoint**: At this point, User Story 6 (time travel) should work independently

---

## Phase 9: User Story 7 - Table Maintenance Operations (Priority: P3)

**Goal**: Enable maintenance operations like snapshot expiration for cost control

**Independent Test**: Create snapshots, expire old ones, verify removal

### Tests for User Story 7

- [ ] T108 [P] [US7] Write unit tests for expire_snapshots in packages/floe-iceberg/tests/unit/test_maintenance.py
- [ ] T109 [P] [US7] Write unit tests for retention policy in packages/floe-iceberg/tests/unit/test_maintenance.py

### Implementation for User Story 7

- [ ] T110 [US7] Implement expire_snapshots in packages/floe-iceberg/src/floe_iceberg/maintenance.py
- [ ] T111 [US7] Implement retain_last parameter in expire_snapshots in packages/floe-iceberg/src/floe_iceberg/maintenance.py
- [ ] T112 [US7] Add maintenance operations to IcebergTableManager in packages/floe-iceberg/src/floe_iceberg/tables.py
- [ ] T113 [US7] Add OpenTelemetry spans for maintenance operations in packages/floe-iceberg/src/floe_iceberg/maintenance.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T114 [P] Add Google-style docstrings to all public APIs in packages/floe-polaris/src/floe_polaris/
- [ ] T115 [P] Add Google-style docstrings to all public APIs in packages/floe-iceberg/src/floe_iceberg/
- [ ] T116 [P] Run mypy --strict and fix type errors in packages/floe-polaris/
- [ ] T117 [P] Run mypy --strict and fix type errors in packages/floe-iceberg/
- [ ] T118 [P] Run ruff and black formatting in packages/floe-polaris/
- [ ] T119 [P] Run ruff and black formatting in packages/floe-iceberg/
- [ ] T120 [P] Run bandit security scan in packages/floe-polaris/
- [ ] T121 [P] Run bandit security scan in packages/floe-iceberg/
- [ ] T122 Verify >80% test coverage for floe-polaris
- [ ] T123 Verify >80% test coverage for floe-iceberg
- [ ] T124 Validate quickstart.md examples work end-to-end
- [ ] T125 Update CLAUDE.md with new packages and technologies

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - MVP
- **User Story 2 (Phase 4)**: Depends on Foundational, can run parallel to US1
- **User Story 3 (Phase 5)**: Depends on Foundational, can run parallel to US1/US2
- **User Story 4 (Phase 6)**: Depends on US1 (catalog connection) and US3 (table operations) - MVP
- **User Story 5 (Phase 7)**: Depends on US4 (IOManager base)
- **User Story 6 (Phase 8)**: Depends on US3 (table operations)
- **User Story 7 (Phase 9)**: Depends on US6 (snapshot management)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

```
                    ┌──────────────────────────────────────────────────┐
                    │              Foundational (Phase 2)               │
                    └──────────────────┬───────────────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
    ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
    │ US1: Catalog │           │ US2: Namespace│          │ US3: Tables  │
    │ Connection   │           │ Management   │           │ (Create/Load)│
    │ (P1) MVP     │           │ (P2)         │           │ (P2)         │
    └──────┬───────┘           └──────────────┘           └──────┬───────┘
           │                                                      │
           └────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ US4: IOManager│
                        │ Write (P1) MVP│
                        └──────┬───────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ US5: IOManager│
                        │ Read (P2)    │
                        └──────────────┘
                                              ┌──────────────┐
                                              │ US6: Time    │
                                              │ Travel (P3)  │
                                              └──────┬───────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │ US7: Maint.  │
                                              │ (P3)         │
                                              └──────────────┘
```

### Parallel Opportunities

- **Phase 1**: T003-T008 can all run in parallel (different files)
- **Phase 2**: T009-T020 can mostly run in parallel (different files, same config modules grouped)
- **Phase 3 (US1)**: T030-T032 tests in parallel, then T033-T043 implementation
- **Phase 4 (US2)**: T045-T048 tests in parallel, then T049-T057 implementation
- **Phase 5 (US3)**: T058-T061 tests in parallel, then T062-T072 implementation
- **Phase 6 (US4)**: T073-T076 tests in parallel, then T077-T088 implementation
- **Phase 7 (US5)**: T090-T093 tests in parallel, then T094-T099 implementation
- **Phase 10**: T114-T121 can all run in parallel

---

## Parallel Example: Phase 2 Foundation

```bash
# Launch all config models in parallel:
Task T012: "Implement RetryConfig Pydantic model"
Task T013: "Implement PolarisCatalogConfig Pydantic model"
Task T014: "Implement WriteMode enum"
Task T015: "Implement IcebergIOManagerConfig Pydantic model"
Task T016: "Implement TableIdentifier model"
Task T018: "Implement SnapshotInfo model"
Task T19: "Implement MaterializationMetadata model"
Task T020: "Implement NamespaceInfo model"

# Launch all unit tests for config in parallel:
Task T025: "Write unit tests for RetryConfig validation"
Task T026: "Write unit tests for PolarisCatalogConfig validation"
Task T027: "Write unit tests for TableIdentifier parsing"
Task T028: "Write unit tests for PartitionTransform validation"
```

---

## Parallel Example: User Story 4

```bash
# Launch all US4 tests in parallel:
Task T073: "Write unit tests for IcebergIOManager handle_output"
Task T074: "Write unit tests for asset key to table identifier mapping"
Task T075: "Write unit tests for append operation"
Task T076: "Write unit tests for overwrite operation"

# After tests fail, launch parallel implementation:
Task T077: "Implement append function"
Task T078: "Implement overwrite function"
# Then sequential:
Task T079: "Implement IcebergIOManager class"
Task T080-T088: Sequential IOManager implementation
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 4)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T029)
3. Complete Phase 3: User Story 1 - Catalog Connection (T030-T044)
4. Complete Phase 5: User Story 3 - Tables (T058-T072) - needed for IOManager
5. Complete Phase 6: User Story 4 - IOManager Write (T073-T089)
6. **STOP and VALIDATE**: Test MVP independently - can connect, create tables, write data
7. Deploy/demo if ready

### Incremental Delivery

1. MVP: US1 + US3 + US4 → Can connect and write data
2. Add US2 (Namespace management) → Better organization
3. Add US5 (IOManager read) → Full pipeline support
4. Add US6 (Time travel) → Data governance
5. Add US7 (Maintenance) → Production readiness

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Catalog) + User Story 4 (IOManager Write)
   - Developer B: User Story 2 (Namespaces) + User Story 3 (Tables)
   - Developer C: User Story 5 (IOManager Read) after US4 complete
3. P3 stories (US6, US7) can be done by anyone after dependencies complete

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Both packages (floe-polaris, floe-iceberg) should achieve >80% test coverage
- All public APIs must have type hints and Google-style docstrings
