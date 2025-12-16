# Tasks: CLI Interface

**Input**: Design documents from `/specs/002-cli-interface/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included - >80% coverage required per Constitution Principle VI.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Monorepo package**: `packages/floe-cli/src/floe_cli/`, `packages/floe-cli/tests/`
- Test fixtures: `packages/floe-cli/tests/fixtures/`
- Templates: `packages/floe-cli/src/floe_cli/templates/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 [P] Update `packages/floe-cli/pyproject.toml` - Add rich-click>=1.7, jinja2>=3.1 dependencies
- [ ] T002 [P] Create `packages/floe-cli/src/floe_cli/py.typed` - PEP 561 marker file
- [ ] T003 [P] Create `packages/floe-cli/tests/conftest.py` - CliRunner fixtures, temp directory helpers
- [ ] T004 [P] Create `packages/floe-cli/tests/fixtures/valid_floe.yaml` - Valid test configuration
- [ ] T005 [P] Create `packages/floe-cli/tests/fixtures/invalid_floe.yaml` - Invalid test configuration (schema violations)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**Dependencies from floe-core**: FloeSpec, Compiler, CompiledArtifacts, ValidationError, CompilationError, export_floe_spec_schema, export_compiled_artifacts_schema

- [ ] T006 Implement `packages/floe-cli/src/floe_cli/output.py` - Rich console output utilities (success/error/warning formatting, NO_COLOR support)
- [ ] T007 Implement `packages/floe-cli/src/floe_cli/errors.py` - CLI error handling (wrap FloeError, user-friendly messages, exit codes)
- [ ] T008 Update `packages/floe-cli/src/floe_cli/main.py` - LazyGroup implementation for fast --help, --version, --no-color options
- [ ] T009 [P] Create `packages/floe-cli/tests/unit/test_output.py` - Unit tests for output utilities
- [ ] T010 [P] Create `packages/floe-cli/tests/unit/test_errors.py` - Unit tests for error handling

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 7 - Get Help and Version (Priority: P1)

**Goal**: Developers can quickly understand available commands and check installed version

**Independent Test**: Run `floe --help` and `floe --version`, verify output format and performance

**Why First**: This story validates the LazyGroup pattern and CLI entry point work correctly before implementing other commands.

### Tests for User Story 7

- [ ] T011 [P] [US7] Create `packages/floe-cli/tests/unit/test_main.py` - Test --help output format and content
- [ ] T012 [P] [US7] Create `packages/floe-cli/tests/integration/test_help_performance.py` - Test --help completes in <500ms

### Implementation for User Story 7

- [ ] T013 [US7] Verify `packages/floe-cli/src/floe_cli/main.py` - Root @click.group with --version, --help, --no-color
- [ ] T014 [US7] Register all commands in `packages/floe-cli/src/floe_cli/commands/__init__.py` using lazy loading pattern

**Checkpoint**: `floe --help` and `floe --version` work correctly

---

## Phase 4: User Story 1 - Validate Configuration (Priority: P1)

**Goal**: Developers can verify floe.yaml is syntactically correct and follows the schema

**Independent Test**: Create valid/invalid floe.yaml files and verify correct success/error output

### Tests for User Story 1

- [ ] T015 [P] [US1] Create `packages/floe-cli/tests/unit/test_validate.py` - Unit tests for validate command (valid file, invalid file, missing file, custom path)

### Implementation for User Story 1

- [ ] T016 [US1] Implement `packages/floe-cli/src/floe_cli/commands/validate.py` - floe validate with --file option
- [ ] T017 [US1] Integrate FloeSpec.from_yaml() from floe-core for validation
- [ ] T018 [US1] Add user-friendly error messages for YAML syntax errors (show line numbers)
- [ ] T019 [US1] Add user-friendly error messages for schema validation errors (show field paths)

**Checkpoint**: `floe validate` works for all acceptance scenarios

---

## Phase 5: User Story 2 - Compile Configuration to Artifacts (Priority: P1)

**Goal**: Developers can transform validated floe.yaml into CompiledArtifacts JSON

**Independent Test**: Compile valid configurations and verify output JSON structure

### Tests for User Story 2

- [ ] T020 [P] [US2] Create `packages/floe-cli/tests/unit/test_compile.py` - Unit tests for compile command (valid file, invalid file, custom output, target selection)

### Implementation for User Story 2

- [ ] T021 [US2] Implement `packages/floe-cli/src/floe_cli/commands/compile.py` - floe compile with --file, --output, --target options
- [ ] T022 [US2] Integrate Compiler().compile() from floe-core
- [ ] T023 [US2] Implement --target validation (verify target exists in spec before compilation)
- [ ] T024 [US2] Add output directory creation and permission checking
- [ ] T025 [US2] Add progress spinner during compilation using Rich

**Checkpoint**: `floe compile` works for all acceptance scenarios

---

## Phase 6: User Story 3 - Export JSON Schema (Priority: P2)

**Goal**: Developers can export JSON Schema for floe.yaml to enable IDE autocomplete

**Independent Test**: Export schema and validate against JSON Schema Draft 2020-12

### Tests for User Story 3

- [ ] T026 [P] [US3] Create `packages/floe-cli/tests/unit/test_schema.py` - Unit tests for schema export (floe-spec type, compiled-artifacts type, stdout, file output)

### Implementation for User Story 3

- [ ] T027 [US3] Create `packages/floe-cli/src/floe_cli/commands/schema.py` - floe schema subgroup
- [ ] T028 [US3] Implement floe schema export with --output, --type options
- [ ] T029 [US3] Integrate export_floe_spec_schema() and export_compiled_artifacts_schema() from floe-core

**Checkpoint**: `floe schema export` works for all acceptance scenarios

---

## Phase 7: User Story 4 - Initialize New Project (Priority: P2)

**Goal**: Developers can quickly scaffold a new floe project with sensible defaults

**Independent Test**: Run init in empty directory and verify created files match templates

### Tests for User Story 4

- [ ] T030 [P] [US4] Create `packages/floe-cli/tests/unit/test_init.py` - Unit tests for init command (empty dir, custom name, custom target, existing file, --force)

### Implementation for User Story 4

- [ ] T031 [US4] Create `packages/floe-cli/src/floe_cli/templates/floe.yaml.jinja2` - Default project template
- [ ] T032 [US4] Create `packages/floe-cli/src/floe_cli/templates/README.md.jinja2` - Project README template
- [ ] T033 [US4] Implement `packages/floe-cli/src/floe_cli/commands/init.py` - floe init with --name, --target, --force options
- [ ] T034 [US4] Implement SandboxedEnvironment template rendering (security-first)
- [ ] T035 [US4] Implement Pydantic validation for template context (prevent injection)
- [ ] T036 [US4] Add file existence checking and --force handling

**Checkpoint**: `floe init` works for all acceptance scenarios

---

## Phase 8: User Story 5 - Run Pipeline (Priority: P3 - Stub)

**Goal**: Stub command that displays helpful message about floe-dagster dependency

**Independent Test**: Verify stub displays proper error about missing floe-dagster

### Tests for User Story 5

- [ ] T037 [P] [US5] Create `packages/floe-cli/tests/unit/test_run.py` - Unit tests for run command stub

### Implementation for User Story 5

- [ ] T038 [US5] Implement `packages/floe-cli/src/floe_cli/commands/run.py` - Stub with floe-dagster dependency message
- [ ] T039 [US5] Add --file and --select options (for future compatibility)

**Checkpoint**: `floe run` displays proper stub message

---

## Phase 9: User Story 6 - Start Development Environment (Priority: P3 - Stub)

**Goal**: Stub command that displays helpful message about floe-dagster dependency

**Independent Test**: Verify stub displays proper error about missing floe-dagster

### Tests for User Story 6

- [ ] T040 [P] [US6] Create `packages/floe-cli/tests/unit/test_dev.py` - Unit tests for dev command stub

### Implementation for User Story 6

- [ ] T041 [US6] Implement `packages/floe-cli/src/floe_cli/commands/dev.py` - Stub with floe-dagster dependency message
- [ ] T042 [US6] Add --file and --port options (for future compatibility)

**Checkpoint**: `floe dev` displays proper stub message

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, documentation, and quality assurance

- [ ] T043 [P] Create `packages/floe-cli/tests/integration/test_cli_workflow.py` - End-to-end workflow tests (init -> validate -> compile)
- [ ] T044 [P] Create `packages/floe-cli/tests/integration/test_error_handling.py` - Error message quality tests (no stack traces, actionable messages)
- [ ] T045 Update `packages/floe-cli/README.md` - Package documentation with examples
- [ ] T046 Run `uv run pytest packages/floe-cli/tests --cov=floe_cli --cov-report=term-missing` - Verify >80% coverage
- [ ] T047 Run `uv run mypy packages/floe-cli/src --strict` - Verify type safety
- [ ] T048 Run `uv run ruff check packages/floe-cli/src` - Verify linting
- [ ] T049 Run quickstart.md validation - Verify all documented commands work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 7 (Phase 3)**: Depends on Foundational - validates CLI entry point
- **User Stories 1-2 (Phases 4-5)**: Depend on Phase 3 completion (P1 priority)
- **User Stories 3-4 (Phases 6-7)**: Can start after Phase 5 (P2 priority)
- **User Stories 5-6 (Phases 8-9)**: Can start after Phase 7 (P3 stubs)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 7 (Help/Version)**: Foundation only - validates LazyGroup pattern
- **User Story 1 (Validate)**: Foundation + US7 - uses FloeSpec.from_yaml()
- **User Story 2 (Compile)**: Foundation + US1 - uses Compiler, depends on validation
- **User Story 3 (Schema Export)**: Foundation + US7 - standalone feature
- **User Story 4 (Init)**: Foundation + US7 - standalone feature
- **User Story 5 (Run Stub)**: Foundation + US7 - stub only
- **User Story 6 (Dev Stub)**: Foundation + US7 - stub only

### Within Each User Story

- Tests written and FAIL before implementation
- Core implementation before edge cases
- Error handling last
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tests marked [P] can run in parallel
- After Phase 3: US1 and US3 can start in parallel (different commands)
- After Phase 5: US3 and US4 can start in parallel (P2 stories)
- After Phase 7: US5 and US6 can start in parallel (P3 stubs)
- All integration tests marked [P] can run in parallel

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 7 (Help/Version)
4. Complete Phase 4: User Story 1 (Validate)
5. Complete Phase 5: User Story 2 (Compile)
6. **STOP and VALIDATE**: Test MVP independently
7. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational + US7 → CLI entry point works
2. Add US1 (Validate) → Test independently → Deploy/Demo (MVP!)
3. Add US2 (Compile) → Test independently → Deploy/Demo
4. Add US3 (Schema Export) → Test independently
5. Add US4 (Init) → Test independently
6. Add US5/US6 (Stubs) → Document future capability
7. Polish phase → Complete package

### Success Criteria Mapping

| Criterion | Tasks | Phase |
|-----------|-------|-------|
| SC-001: Help <500ms | T011, T012 | Phase 3 |
| SC-002: Validate <2s | T015 | Phase 4 |
| SC-003: Readable errors | T018, T019, T044 | Phase 4, 10 |
| SC-004: Init <1min | T030 | Phase 7 |
| SC-005: Actionable errors | T007, T044 | Phase 2, 10 |
| SC-006: Cross-platform | T043 | Phase 10 |
| SC-007: No stack traces | T044 | Phase 10 |
| SC-008: Schema + IDE | T026-T029 | Phase 6 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- P3 commands (run, dev) are stubs only - full implementation requires floe-dagster package
