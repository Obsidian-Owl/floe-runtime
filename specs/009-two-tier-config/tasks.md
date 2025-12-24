# Tasks: Two-Tier Configuration Architecture

**Input**: Design documents from `/specs/009-two-tier-config/`
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete), data-model.md (complete), contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Exact file paths included in descriptions

## Path Conventions

This is a monorepo with 7 packages:
- **Core schemas**: `packages/floe-core/src/floe_core/schemas/`
- **Compiler**: `packages/floe-core/src/floe_core/compiler/`
- **Tests**: `packages/floe-core/tests/unit/`, `testing/docker/tests/`
- **Demo**: `demo/`, `platform/`
- **Docs**: `docs/`, `docs/adr/`
- **Charts**: `charts/floe-dagster/`

---

## Phase 1: Setup (Project Scaffolding)

**Purpose**: Create directory structure and placeholder files for new modules

- [x] T001 Create platform environment directories: `platform/local/`, `platform/dev/`, `platform/staging/`, `platform/prod/`
- [x] T002 [P] Create schema module structure: `packages/floe-core/src/floe_core/schemas/platform_spec.py`
- [x] T003 [P] Create schema module: `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [x] T004 [P] Create schema module: `packages/floe-core/src/floe_core/schemas/storage_profile.py`
- [x] T005 [P] Create schema module: `packages/floe-core/src/floe_core/schemas/catalog_profile.py`
- [x] T006 [P] Create schema module: `packages/floe-core/src/floe_core/schemas/compute_profile.py`
- [x] T007 [P] Create compiler module: `packages/floe-core/src/floe_core/compiler/platform_resolver.py`
- [x] T008 [P] Create compiler module: `packages/floe-core/src/floe_core/compiler/profile_resolver.py`
- [x] T009 [P] Create test directory structure: `packages/floe-core/tests/unit/schemas/`, `packages/floe-core/tests/integration/`
- [x] T010 [P] Create docs directory: `docs/adr/`, ensure `docs/` exists

---

## Phase 2: Foundational (Core Entities - Blocks All Stories)

**Purpose**: Implement core Pydantic models that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Core Entities

- [ ] T011 Implement `SecretReference` model with K8S_SECRET_PATTERN validation in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T012 Implement `CredentialMode` enum (static, oauth2, iam_role, service_account) in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T013 Implement `CredentialConfig` model with mode validation in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T014 [P] Implement `StorageType` enum and `StorageProfile` model in `packages/floe-core/src/floe_core/schemas/storage_profile.py`
- [ ] T015 [P] Implement `CatalogType` enum and `CatalogProfile` model in `packages/floe-core/src/floe_core/schemas/catalog_profile.py`
- [ ] T016 [P] Implement `ComputeProfile` model (reuse existing ComputeTarget enum) in `packages/floe-core/src/floe_core/schemas/compute_profile.py`
- [ ] T017 Implement `ObservabilityConfig` for tracing/lineage in `packages/floe-core/src/floe_core/schemas/platform_spec.py`
- [ ] T018 Implement `PlatformSpec` top-level model with `from_yaml()` class method in `packages/floe-core/src/floe_core/schemas/platform_spec.py`
- [ ] T019 Update `packages/floe-core/src/floe_core/schemas/__init__.py` to export all new schemas
- [ ] T020 [P] Create unit tests for `CredentialConfig` in `packages/floe-core/tests/unit/schemas/test_credential_config.py`
- [ ] T021 [P] Create unit tests for `StorageProfile` in `packages/floe-core/tests/unit/schemas/test_storage_profile.py`
- [ ] T022 [P] Create unit tests for `CatalogProfile` in `packages/floe-core/tests/unit/schemas/test_catalog_profile.py`
- [ ] T023 [P] Create unit tests for `PlatformSpec` in `packages/floe-core/tests/unit/schemas/test_platform_spec.py`
- [ ] T024 Run `make lint` and `make typecheck` to validate all new schemas pass mypy --strict

**Checkpoint**: All core entities implemented and tested. Profile resolution can now be built.

---

## Phase 3: User Story 1 - Platform Engineer Configures Infrastructure (Priority: P1) 🎯 MVP

**Goal**: Platform engineers can create platform.yaml files with storage, catalog, compute, and observability profiles. Credentials are referenced via secret_ref.

**Independent Test**: Create a platform.yaml with all profile types, load it with `PlatformSpec.from_yaml()`, and verify all profiles are accessible and credentials resolve from environment variables.

### Implementation for User Story 1

- [ ] T025 [US1] Implement `PlatformResolver` class with YAML loading and env var fallback in `packages/floe-core/src/floe_core/compiler/platform_resolver.py`
- [ ] T026 [US1] Add `SecretReference.resolve()` method for runtime secret retrieval in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T027 [US1] Create example `platform/local/platform.yaml` with all profile types (storage, catalog, compute, observability)
- [ ] T028 [P] [US1] Create example `platform/dev/platform.yaml` with AWS/cloud endpoints
- [ ] T029 [P] [US1] Create example `platform/staging/platform.yaml` with staging endpoints
- [ ] T030 [P] [US1] Create example `platform/prod/platform.yaml` with production endpoints (IAM role mode)
- [ ] T031 [US1] Add integration test for platform.yaml loading in `packages/floe-core/tests/integration/test_platform_resolver.py`
- [ ] T032 [US1] Add test for env var fallback when platform.yaml missing in `packages/floe-core/tests/integration/test_platform_resolver.py`
- [ ] T033 [US1] Add test for secret resolution from environment variables in `packages/floe-core/tests/unit/schemas/test_credential_config.py`

**Checkpoint**: Platform engineers can create and validate platform.yaml files. Secrets resolve at runtime.

---

## Phase 4: User Story 2 - Data Engineer Deploys Same Pipeline to Multiple Environments (Priority: P1)

**Goal**: Data engineers write floe.yaml with profile references (`catalog: default`) that resolve to environment-specific infrastructure at compile time. Same floe.yaml works across all environments.

**Independent Test**: Deploy the same floe.yaml with two different platform.yaml files and verify CompiledArtifacts contains the correct resolved configuration for each environment.

### Implementation for User Story 2

- [ ] T034 [US2] Modify `FloeSpec` to add profile reference fields (catalog, storage, compute as strings) in `packages/floe-core/src/floe_core/schemas/floe_spec.py`
- [ ] T035 [US2] Remove deprecated inline infrastructure fields from `FloeSpec` (FR-034) in `packages/floe-core/src/floe_core/schemas/floe_spec.py`
- [ ] T036 [US2] Implement `ProfileResolver` class to resolve profile names to configs in `packages/floe-core/src/floe_core/compiler/profile_resolver.py`
- [ ] T037 [US2] Update `Compiler` to merge FloeSpec + PlatformSpec into CompiledArtifacts v2.0 in `packages/floe-core/src/floe_core/compiler/compiler.py`
- [ ] T038 [US2] Update `CompiledArtifacts` schema to v2.0 with resolved profiles and platform source tracking in `packages/floe-core/src/floe_core/compiler/models.py`
- [ ] T039 [US2] Update `demo/floe.yaml` to use profile references instead of inline config
- [ ] T040 [US2] Update `demo/orchestration/config.py` to load from platform.yaml via PlatformResolver
- [ ] T041 [US2] Update `demo/orchestration/definitions.py` to use resolved profiles from CompiledArtifacts
- [ ] T042 [US2] Add integration test: same floe.yaml + different platform.yaml = correct resolved config in `packages/floe-core/tests/integration/test_profile_resolution.py`
- [ ] T043 [US2] Add unit tests for `ProfileResolver` in `packages/floe-core/tests/unit/compiler/test_profile_resolver.py`
- [ ] T044 [US2] Export JSON Schema for FloeSpec v2.0 to `packages/floe-core/schemas/floe-spec.schema.json`

**Checkpoint**: Data engineers can write environment-portable floe.yaml files. Profile resolution works correctly.

---

## Phase 5: User Story 3 - Security Team Validates Zero Secrets in Code (Priority: P2)

**Goal**: Security engineers can audit the codebase and confirm zero hardcoded credentials. Schema validation enforces secret_ref for all sensitive fields.

**Independent Test**: Run security scanner on repo and verify zero hardcoded credentials found. Attempt to create platform.yaml with plaintext client_secret and verify validation fails with clear error.

### Implementation for User Story 3

- [ ] T045 [US3] Add `validate_no_secrets()` model validator to `FloeSpec` that fails if credential patterns detected in `packages/floe-core/src/floe_core/schemas/floe_spec.py`
- [ ] T046 [US3] Add sensitive field validation to `CredentialConfig` that requires secret_ref for client_secret, passwords, etc. in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T047 [US3] Add validation that endpoint URIs support secret_ref for internal topology protection in `packages/floe-core/src/floe_core/schemas/catalog_profile.py`
- [ ] T048 [US3] Create bandit security scan configuration in `pyproject.toml` or `.bandit` to scan for hardcoded credentials
- [ ] T049 [US3] Add unit test: plaintext client_secret rejected with "use secret_ref" error in `packages/floe-core/tests/unit/schemas/test_credential_config.py`
- [ ] T050 [US3] Add unit test: credential patterns in floe.yaml rejected in `packages/floe-core/tests/unit/schemas/test_floe_spec.py`
- [ ] T051 [US3] Run `bandit -r packages/` and verify zero high/critical findings related to credentials

**Checkpoint**: Zero secrets in code. Schema validation enforces secret_ref pattern.

---

## Phase 6: User Story 5 - Platform Engineer Troubleshoots Configuration Errors (Priority: P2)

**Goal**: Platform engineers receive clear, actionable error messages when configuration is invalid. Errors include file name, field path, and available options.

**Independent Test**: Introduce deliberate errors (missing profile, invalid secret_ref, plaintext credential) and verify error messages are specific and actionable.

### Implementation for User Story 5

- [ ] T052 [US5] Implement `ConfigurationError` exception class with file/field context in `packages/floe-core/src/floe_core/errors.py`
- [ ] T053 [US5] Implement `ProfileNotFoundError` that lists available profiles in `packages/floe-core/src/floe_core/errors.py`
- [ ] T054 [US5] Implement `SecretNotFoundError` with expected location (env var, K8s secret) in `packages/floe-core/src/floe_core/errors.py`
- [ ] T055 [US5] Add profile listing to ProfileResolver errors (FR-038) in `packages/floe-core/src/floe_core/compiler/profile_resolver.py`
- [ ] T056 [US5] Add line number tracking to YAML parsing errors in `packages/floe-core/src/floe_core/compiler/platform_resolver.py`
- [ ] T057 [US5] Add unit test: missing profile error lists available profiles in `packages/floe-core/tests/unit/compiler/test_profile_resolver.py`
- [ ] T058 [US5] Add unit test: missing secret error shows expected env var name in `packages/floe-core/tests/unit/schemas/test_credential_config.py`
- [ ] T059 [US5] Add integration test: YAML syntax error shows file name and line number in `packages/floe-core/tests/integration/test_platform_resolver.py`

**Checkpoint**: All configuration errors are actionable with clear context.

---

## Phase 7: User Story 4 - DevOps Engineer Reviews Credential Modes (Priority: P3)

**Goal**: DevOps engineers can configure different credential modes (static, oauth2, iam_role, service_account) per environment. Each mode authenticates correctly.

**Independent Test**: Configure platform.yaml with each credential mode and verify authentication succeeds (mocked for IAM/service_account, real for static/oauth2 in local env).

### Implementation for User Story 4

- [ ] T060 [US4] Implement OAuth2 client credentials flow in `packages/floe-polaris/src/floe_polaris/auth.py`
- [ ] T061 [US4] Implement token refresh for OAuth2 with configurable expiry in `packages/floe-polaris/src/floe_polaris/auth.py`
- [ ] T062 [US4] Update `packages/floe-polaris/src/floe_polaris/config.py` to accept CredentialConfig
- [ ] T063 [US4] Update `packages/floe-polaris/src/floe_polaris/client.py` to support all credential modes
- [ ] T064 [US4] Update `packages/floe-iceberg/src/floe_iceberg/config.py` to use profile-based storage config
- [ ] T065 [US4] Add IAM role credential mode placeholder (future AWS integration) in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T066 [US4] Add service_account credential mode placeholder (future GCP/Azure integration) in `packages/floe-core/src/floe_core/schemas/credential_config.py`
- [ ] T067 [US4] Add integration test for OAuth2 authentication with mocked Polaris in `packages/floe-polaris/tests/integration/test_oauth2_auth.py`
- [ ] T068 [US4] Add integration test for static credential mode in `packages/floe-polaris/tests/integration/test_static_auth.py`

**Checkpoint**: All credential modes functional. OAuth2 includes automatic token refresh.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, tech debt cleanup, and final validation

### Documentation (FR-041 through FR-046)

- [ ] T069 [P] Create ADR: `docs/adr/0002-two-tier-config.md` documenting design rationale
- [ ] T070 [P] Create Platform Configuration Guide: `docs/platform-config.md` for platform engineers
- [ ] T071 [P] Create Pipeline Configuration Guide: `docs/pipeline-config.md` for data engineers
- [ ] T072 [P] Create Security Architecture document: `docs/security.md` (zero-trust model, credential flow)
- [ ] T073 Update `CLAUDE.md` with two-tier configuration patterns and references
- [ ] T074 [P] Export final JSON Schema files: `packages/floe-core/schemas/platform-spec.schema.json`, `packages/floe-core/schemas/floe-spec.schema.json`

### Helm Chart Updates

- [ ] T075 Create `charts/floe-dagster/templates/platform-configmap.yaml` for platform.yaml injection
- [ ] T076 Update `charts/floe-dagster/values.yaml` to add `platform.spec` section with profiles

### Tech Debt Cleanup (FR-047 through FR-052)

- [ ] T077 Remove deprecated inline config patterns from `packages/floe-polaris/src/floe_polaris/` (FR-047)
- [ ] T078 [P] Remove deprecated config patterns from `packages/floe-iceberg/src/floe_iceberg/` (FR-047)
- [ ] T079 Update all type hints to use new profile models in `packages/floe-dagster/src/floe_dagster/resources.py` (FR-048)
- [ ] T080 [P] Update all test fixtures to use profile-based config in `testing/fixtures/` (FR-049)
- [ ] T081 Add integration tests validating profile resolution and secret_ref injection in `testing/docker/tests/test_platform_injection.py` (FR-050)
- [ ] T082 Run `make lint` on all modified packages and fix any issues (FR-051)
- [ ] T083 Run `make typecheck` (mypy --strict) on all modified packages and fix any issues (FR-051)
- [ ] T084 Verify test coverage remains >80% with `make test` and pytest-cov (FR-052)

### CLI Command

- [ ] T085 Implement `floe platform list-profiles` command in `packages/floe-cli/src/floe_cli/commands/platform.py`

### Final Validation

- [ ] T086 Run full test suite: `make test`
- [ ] T087 Run quickstart.md validation with local platform.yaml
- [ ] T088 Verify all JSON Schemas valid and provide IDE autocomplete

---

## Phase 9: Batteries-Included floe-dagster (User Stories 6 & 7)

**Purpose**: Eliminate boilerplate in data engineer code by providing high-level abstractions that consume CompiledArtifacts. Data engineers should write pure business logic with zero observability setup, config loading, or credential handling.

**Success Metrics**:
- Demo reduced from ~1,150 to ~400 LOC (60% reduction)
- Zero observability boilerplate in data engineer code
- Same demo code works in Docker Compose and K8s

### Bead 1: ObservabilityOrchestrator (floe-runtime-5qrc)

**Priority**: P1 | **Dependencies**: None | **Blocks**: Bead 2, Bead 3

- [ ] T089 [US6] Create `packages/floe-dagster/src/floe_dagster/observability/__init__.py` module exports
- [ ] T090 [US6] Implement `ObservabilityOrchestrator` context manager in `packages/floe-dagster/src/floe_dagster/observability/orchestrator.py`
  - `from_compiled_artifacts()` factory method
  - `asset_run()` context manager combining OTel spans + OpenLineage events
  - Graceful degradation when endpoints unavailable (FR-058)
  - Exception recording to span before re-raising (FR-057)
- [ ] T091 [US6] Implement `AssetRunContext` dataclass returned by `asset_run()` context manager
  - `span: Span | None` (None if tracing unavailable)
  - `run_id: str | None` (None if lineage unavailable)
  - `set_attribute(key, value)` helper
- [ ] T092 [US6] Add unit tests for graceful degradation in `packages/floe-dagster/tests/unit/observability/test_orchestrator.py`
- [ ] T093 [US6] Add unit tests for exception handling in `packages/floe-dagster/tests/unit/observability/test_orchestrator.py`

### Bead 2: @floe_asset Decorator + Resources (floe-runtime-5u2y)

**Priority**: P1 | **Depends on**: Bead 1 (floe-runtime-5qrc)

- [ ] T094 [US6] Create `packages/floe-dagster/src/floe_dagster/resources/__init__.py` module exports
- [ ] T095 [US6] Implement `PolarisCatalogResource` (ConfigurableResource) in `packages/floe-dagster/src/floe_dagster/resources/catalog.py`
  - `from_compiled_artifacts()` factory method (FR-059)
  - Secret resolution at runtime, not compile time
  - `get_catalog()` method returning PolarisCatalog
- [ ] T096 [US6] Implement `@floe_asset` decorator in `packages/floe-dagster/src/floe_dagster/decorators.py`
  - Auto-creates OTel span with asset name (FR-055)
  - Auto-emits OpenLineage START/COMPLETE/FAIL events (FR-056)
  - Resource injection via signature inspection (FR-060)
  - Pass-through kwargs to Dagster @asset
- [ ] T097 [US6] Add unit tests for `@floe_asset` decorator in `packages/floe-dagster/tests/unit/test_decorators.py`
- [ ] T098 [US6] Add unit tests for `PolarisCatalogResource` in `packages/floe-dagster/tests/unit/resources/test_catalog.py`

### Bead 3: FloeDefinitions Factory (floe-runtime-0c7j)

**Priority**: P1 | **Depends on**: Bead 1 (floe-runtime-5qrc), Bead 2 (floe-runtime-5u2y)

- [ ] T099 [US7] Implement `FloeDefinitions.from_compiled_artifacts()` factory in `packages/floe-dagster/src/floe_dagster/definitions.py`
  - Load CompiledArtifacts from path
  - Initialize TracingManager + OpenLineageEmitter
  - Create PolarisCatalogResource
  - Wire resources into Dagster Definitions (FR-061)
- [ ] T100 [US7] Update `packages/floe-dagster/src/floe_dagster/__init__.py` to export new public API
  - `floe_asset`, `FloeDefinitions`, `PolarisCatalogResource`, `ObservabilityOrchestrator`
- [ ] T101 [US7] Add integration test for full wiring in `packages/floe-dagster/tests/integration/test_definitions_factory.py`
- [ ] T102 [US7] Add integration test verifying observability flows in `packages/floe-dagster/tests/integration/test_observability_integration.py`

### Bead 4: Demo Refactoring (floe-runtime-i43l)

**Priority**: P2 | **Depends on**: Bead 3 (floe-runtime-0c7j)

- [ ] T103 [US7] Refactor `demo/orchestration/definitions.py` to use `@floe_asset` and `FloeDefinitions.from_compiled_artifacts()` (FR-062)
- [ ] T104 [US7] Simplify `demo/orchestration/config.py` to contain only business constants (remove platform loading)
- [ ] T105 [US7] Verify demo assets contain zero observability/config boilerplate (FR-063)
- [ ] T106 [US7] Run E2E tests in Docker Compose and K8s to verify same code works in both environments

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational (Core Entities) ← BLOCKS ALL USER STORIES
    │
    ├──────────────┬──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼
Phase 3:       Phase 4:       Phase 5:       Phase 6:       Phase 7:
US1 (P1)       US2 (P1)       US3 (P2)       US5 (P2)       US4 (P3)
Platform       Pipeline       Security       Diagnostics    Credentials
Config         Portability    Validation     Errors         Modes
    │              │              │              │              │
    └──────────────┴──────────────┴──────────────┴──────────────┘
                                  │
                                  ▼
                          Phase 8: Polish
                          (Documentation, Cleanup)
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  Phase 9: Batteries-Included │
                    │  floe-dagster (US6, US7)    │
                    │                              │
                    │  Bead 1 ──► Bead 2 ──► Bead 3 ──► Bead 4 │
                    │  (5qrc)    (5u2y)    (0c7j)    (i43l)   │
                    └─────────────────────────────┘
```

### User Story Dependencies

| Story | Depends On | Can Run In Parallel With |
|-------|------------|--------------------------|
| US1 (P1) | Foundational (Phase 2) | US2 after T035 |
| US2 (P1) | Foundational + partial US1 (T025) | US3, US5, US4 |
| US3 (P2) | Foundational | US4, US5 |
| US5 (P2) | US2 (needs ProfileResolver) | US3, US4 |
| US4 (P3) | US1 + US2 | US3, US5 |
| US6 (P1) | Phase 8 (Polish) | US7 |
| US7 (P1) | US6 (Bead 1-3) | - |

### Bead Dependencies (Phase 9)

| Bead | ID | Depends On | Blocks |
|------|-----|------------|--------|
| 1. ObservabilityOrchestrator | floe-runtime-5qrc | None | Bead 2, Bead 3 |
| 2. @floe_asset + Resources | floe-runtime-5u2y | Bead 1 | Bead 3 |
| 3. FloeDefinitions Factory | floe-runtime-0c7j | Bead 1, Bead 2 | Bead 4 |
| 4. Demo Refactoring | floe-runtime-i43l | Bead 3 | None |

### Within Each User Story

1. Core implementation before integration
2. Unit tests alongside implementation
3. Integration tests after core complete
4. Story complete before moving to next priority

---

## Parallel Opportunities

### Phase 2 Parallel Group (after T013):
```bash
# Launch all profile models in parallel:
Task: T014 "Implement StorageProfile model"
Task: T015 "Implement CatalogProfile model"
Task: T016 "Implement ComputeProfile model"

# Launch all unit tests in parallel (after models):
Task: T020 "Create unit tests for CredentialConfig"
Task: T021 "Create unit tests for StorageProfile"
Task: T022 "Create unit tests for CatalogProfile"
Task: T023 "Create unit tests for PlatformSpec"
```

### Phase 3 (US1) Parallel Group:
```bash
# Launch all example platform.yaml files in parallel:
Task: T028 "Create example platform/dev/platform.yaml"
Task: T029 "Create example platform/staging/platform.yaml"
Task: T030 "Create example platform/prod/platform.yaml"
```

### Phase 8 (Polish) Parallel Group:
```bash
# Launch all documentation in parallel:
Task: T069 "Create ADR 0002-two-tier-config.md"
Task: T070 "Create Platform Configuration Guide"
Task: T071 "Create Pipeline Configuration Guide"
Task: T072 "Create Security Architecture document"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T024)
3. Complete Phase 3: User Story 1 (T025-T033) - Platform Config
4. Complete Phase 4: User Story 2 (T034-T044) - Pipeline Portability
5. **STOP and VALIDATE**: Test with `make test`, verify platform.yaml + floe.yaml integration
6. Deploy/demo if ready - MVP is complete!

### Incremental Delivery

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP | US1 + US2 | Platform engineers can configure infrastructure; Data engineers can write portable pipelines |
| Security | + US3 | Enterprise security audit passes; Zero secrets in code |
| Diagnostics | + US5 | Clear error messages for troubleshooting |
| Full | + US4 | All credential modes functional; Production-ready |
| Complete | + Polish | Full documentation; Helm integration; CLI command |

### Parallel Team Strategy

With 2 developers:

1. **Week 1**: Both complete Setup + Foundational together
2. **Week 2**:
   - Developer A: US1 (Platform Config)
   - Developer B: US2 (Pipeline Portability)
3. **Week 3**:
   - Developer A: US3 (Security)
   - Developer B: US5 (Diagnostics)
4. **Week 4**:
   - Both: US4 (Credential Modes) + Polish

---

## Task Summary

| Phase | Task Range | Count | Purpose | Bead ID |
|-------|------------|-------|---------|---------|
| Setup | T001-T010 | 10 | Directory and file scaffolding | - |
| Foundational | T011-T024 | 14 | Core Pydantic models | - |
| US1 (P1) | T025-T033 | 9 | Platform configuration | - |
| US2 (P1) | T034-T044 | 11 | Pipeline portability | - |
| US3 (P2) | T045-T051 | 7 | Security validation | - |
| US5 (P2) | T052-T059 | 8 | Error diagnostics | - |
| US4 (P3) | T060-T068 | 9 | Credential modes | - |
| Polish | T069-T088 | 20 | Documentation, cleanup, validation | - |
| US6/US7 Bead 1 | T089-T093 | 5 | ObservabilityOrchestrator | floe-runtime-5qrc |
| US6 Bead 2 | T094-T098 | 5 | @floe_asset + Resources | floe-runtime-5u2y |
| US7 Bead 3 | T099-T102 | 4 | FloeDefinitions Factory | floe-runtime-0c7j |
| US7 Bead 4 | T103-T106 | 4 | Demo Refactoring | floe-runtime-i43l |
| **TOTAL** | T001-T106 | **106** | | |

### Tasks per User Story

| User Story | Tasks | Parallel Opportunities |
|------------|-------|------------------------|
| US1 | 9 | 3 (example platform.yaml files) |
| US2 | 11 | 1 (JSON schema export) |
| US3 | 7 | 0 (sequential validation) |
| US5 | 8 | 0 (sequential errors) |
| US4 | 9 | 0 (sequential auth) |
| US6 | 10 (T089-T098) | Bead 2 depends on Bead 1 |
| US7 | 8 (T099-T106) | Bead 4 depends on Bead 3 |

---

## Notes

- All tasks include exact file paths
- [P] marks parallel opportunities
- [USn] maps task to user story for traceability
- Tests are included as per FR-049/FR-050 requirements
- Stop at any checkpoint to validate independently
- Commit after each task or logical group
