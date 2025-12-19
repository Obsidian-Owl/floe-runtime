# Feature Specification: Robust Integration Testing with Traceability

**Feature Branch**: `006-integration-testing`
**Created**: 2025-12-19
**Status**: Draft
**Input**: User description: "We need to ensure we have robust integration tests for all components and packages that utilise our test infrastructure. Analyse the existing specs and ensure we have full traceability and validation of integration tests on all features."

## Executive Summary

This specification establishes comprehensive integration testing requirements across all floe-runtime packages to ensure full traceability between feature specifications and their corresponding integration tests. The goal is to verify that every feature requirement from specs 001-005 has corresponding integration test coverage, identify gaps, and define the infrastructure improvements needed to close those gaps.

## Clarifications

### Session 2025-12-19

- Q: Should integration tests explicitly validate that configuration patterns used in Docker translate correctly to production deployment scenarios? → A: Yes - add tests verifying CompiledArtifacts work with production-like configs (different URIs, env vars)
- Q: How should integration tests verify observability event emission (traces, lineage events)? → A: Backend verification - query Jaeger/Marquez APIs to confirm events arrived with correct structure
- Q: Should integration tests validate multi-tenant isolation patterns? → A: Multi-tenant isolation is SaaS concern (out of scope for OSS runtime), but row-level security via JWT/IAM is a standalone capability that must be tested as configurable security
- Q: Should integration tests validate graceful degradation when optional services are unavailable? → A: Yes - test that features work when optional services (Marquez, Jaeger, Control Plane context) are unavailable to ensure standalone-first philosophy
- Q: Should integration tests include explicit contract validation at package boundaries? → A: Yes - add contract boundary tests verifying outputs from one package are valid inputs to consuming packages (especially CompiledArtifacts)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Validates Feature Coverage (Priority: P1)

A developer working on floe-runtime needs confidence that all feature requirements from specifications 001-005 have corresponding integration tests. They want to run a traceability check that maps requirements to tests and reports coverage gaps.

**Why this priority**: Without traceability, the team cannot verify that implemented features are properly tested. This is the foundation for all other testing work.

**Independent Test**: Can be tested by running a traceability report command that outputs a matrix of requirements vs test coverage, showing pass/fail for each mapping.

**Acceptance Scenarios**:

1. **Given** a developer has access to the specs directory, **When** they run the traceability analysis, **Then** they receive a report showing each functional requirement (FR-XXX) from specs 001-005 mapped to corresponding integration test files
2. **Given** a requirement has no corresponding integration test, **When** the traceability report is generated, **Then** the gap is clearly flagged with the requirement ID, spec file, and suggested test file location
3. **Given** all requirements are covered, **When** the traceability report is generated, **Then** it shows 100% coverage with green status indicators

---

### User Story 2 - CI Pipeline Validates Integration Tests (Priority: P1)

The CI/CD pipeline needs to run integration tests against Docker infrastructure and report results with clear pass/fail status. Failed tests must provide actionable error messages, not silent skips.

**Why this priority**: Integration tests are the primary quality gate for features that interact with external services. If tests silently skip, bugs ship to production.

**Independent Test**: Can be tested by triggering CI pipeline on a PR that introduces a breaking change, and verifying the pipeline fails with a clear error message pointing to the specific test and infrastructure issue.

**Acceptance Scenarios**:

1. **Given** the CI pipeline is configured with Docker infrastructure, **When** integration tests are triggered, **Then** all 7 packages' integration tests execute within the Docker network
2. **Given** an integration test fails due to missing infrastructure, **When** the test executes, **Then** the test FAILs with an error message (not skips) indicating which service is unavailable
3. **Given** all infrastructure is healthy, **When** integration tests run, **Then** all tests pass and the CI reports success with test count and duration

---

### User Story 3 - Package Maintainer Adds Integration Tests (Priority: P2)

A developer adding a new feature to a package needs clear guidance on how to write integration tests that follow project patterns, use shared fixtures, and integrate with the test infrastructure.

**Why this priority**: Consistent test patterns reduce cognitive load and ensure new tests integrate properly with existing infrastructure.

**Independent Test**: Can be tested by a new developer following the testing guide to add an integration test for a new package method, and the test runs successfully in Docker.

**Acceptance Scenarios**:

1. **Given** a developer needs to add an integration test for floe-polaris, **When** they follow the testing documentation, **Then** they can create a test that uses the shared fixtures (catalog, test_namespace) and runs in Docker
2. **Given** a new test requires infrastructure not in the current Docker Compose, **When** the developer reviews the infrastructure documentation, **Then** they can determine which profile to use or how to add new services
3. **Given** a test uses shared fixtures from testing/fixtures/, **When** the test executes, **Then** it properly connects to services using environment-based configuration

---

### User Story 4 - Architect Reviews Test Coverage by Feature (Priority: P2)

A technical architect needs to review integration test coverage for a specific feature (e.g., 004-storage-catalog) to assess quality before release.

**Why this priority**: Feature-level visibility into test coverage enables informed release decisions.

**Independent Test**: Can be tested by generating a feature-specific coverage report that shows all requirements from spec 004 and their test status.

**Acceptance Scenarios**:

1. **Given** an architect wants to review coverage for feature 004, **When** they run the coverage report with --feature 004, **Then** they see all FR-XXX requirements from spec 004 mapped to test files with pass/fail status
2. **Given** feature 004 has 62 integration tests, **When** the report is generated, **Then** it shows the test count, coverage percentage, and any untested requirements
3. **Given** a requirement is partially covered, **When** the report is generated, **Then** it indicates which acceptance scenarios are covered and which are not

---

### User Story 5 - DevOps Engineer Maintains Test Infrastructure (Priority: P3)

A DevOps engineer maintaining the test infrastructure needs clear documentation on Docker Compose profiles, service dependencies, and initialization scripts.

**Why this priority**: Infrastructure maintenance is essential but less frequent than development activities.

**Independent Test**: Can be tested by following the infrastructure documentation to add a new service to Docker Compose and verify it integrates with existing health checks.

**Acceptance Scenarios**:

1. **Given** a DevOps engineer needs to upgrade Polaris version, **When** they review the docker-compose.yml, **Then** they can identify the service, its dependencies, and health check configuration
2. **Given** a new service is added to Docker Compose, **When** the engineer runs docker compose --profile full up, **Then** the service starts and passes health checks
3. **Given** initialization scripts need modification, **When** the engineer updates init-scripts/, **Then** the changes take effect on next container restart

---

### Edge Cases

- What happens when a Docker service fails health check during test run? Tests FAIL with clear error message identifying the unhealthy service
- How does the system handle tests that require credentials not in environment? Tests FAIL with error indicating missing environment variable
- What happens when LocalStack S3 is slow to respond? Tests have configurable timeout (default 30s) and FAIL on timeout with service name
- How does the system handle concurrent test runs in CI? Each test run uses isolated namespaces/tables with UUID suffixes

## Requirements *(mandatory)*

### Functional Requirements

#### Test Traceability

- **FR-001**: System MUST provide a traceability matrix mapping functional requirements (FR-XXX) from specs 001-005 to integration test files
- **FR-002**: System MUST report coverage gaps where requirements have no corresponding integration tests
- **FR-003**: System MUST generate coverage reports per feature (001, 002, 003, 004, 005) showing test status

#### Test Execution

- **FR-004**: Integration tests MUST execute inside Docker network to resolve internal hostnames (localstack, polaris, trino, cube)
- **FR-005**: Integration tests MUST FAIL (not skip) when required infrastructure is unavailable
- **FR-006**: Integration tests MUST use environment-based configuration for all service URLs and credentials
- **FR-007**: Integration tests MUST use unique identifiers (UUID) for test isolation to enable concurrent execution

#### Package Coverage Requirements

- **FR-008**: floe-core MUST have integration tests covering YAML loading, compilation flow, and round-trip serialization
- **FR-009**: floe-cli MUST have integration tests covering command execution (validate, compile) with real files
- **FR-010**: floe-dbt MUST have integration tests covering profile generation for all 7 compute targets with actual dbt validation
- **FR-011**: floe-dagster MUST have integration tests covering asset creation from manifest and materialization workflow
- **FR-012**: floe-polaris MUST have integration tests covering catalog connection, namespace operations, and table operations
- **FR-013**: floe-iceberg MUST have integration tests covering table CRUD, data operations, schema evolution, and Dagster IOManager
- **FR-014**: floe-cube MUST have integration tests covering REST API, GraphQL API, SQL API, security, and observability

#### Infrastructure Requirements

- **FR-015**: Docker Compose MUST provide storage profile with LocalStack, Polaris, and polaris-init
- **FR-016**: Docker Compose MUST provide full profile with Cube, Trino, Marquez, and cube-init
- **FR-017**: Test runner scripts MUST handle service startup, health checks, and credential loading automatically
- **FR-018**: Initialization scripts MUST be idempotent - safe to run multiple times without side effects

#### Shared Test Fixtures

- **FR-019**: System MUST provide CompiledArtifacts factory fixtures for all 7 compute targets
- **FR-020**: System MUST provide Docker service lifecycle fixtures with health checks
- **FR-021**: System MUST provide base test classes for common patterns (e.g., dbt profile generator tests)

#### Production Configuration Validation

- **FR-022**: Integration tests MUST validate that CompiledArtifacts generated in Docker environments work correctly with production-like configurations (different URIs, environment variable patterns)
- **FR-023**: Integration tests MUST verify environment variable injection patterns match production deployment expectations (secret_ref resolution, catalog URI substitution)

#### Observability Verification

- **FR-024**: Integration tests MUST verify OpenTelemetry trace emission by querying Jaeger API to confirm traces arrived with correct span names, attributes, and parent-child relationships
- **FR-025**: Integration tests MUST verify OpenLineage event emission by querying Marquez API to confirm START/COMPLETE/FAIL events arrived with correct job names, datasets, and facets

#### Row-Level Security Testing

- **FR-026**: Integration tests MUST verify Cube row-level security filters work correctly with configurable JWT claims or IAM-based security contexts
- **FR-027**: Integration tests MUST verify that queries without valid security context are rejected appropriately
- **FR-028**: Integration tests MUST verify security context propagation through the query pipeline (no data leakage across security boundaries)

#### Standalone-First / Graceful Degradation Testing

- **FR-029**: Integration tests MUST verify core functionality works when optional observability services (Jaeger, Marquez) are unavailable
- **FR-030**: Integration tests MUST verify that missing optional services emit appropriate warning logs but do not cause failures
- **FR-031**: Integration tests MUST verify CompiledArtifacts without optional EnvironmentContext fields still execute correctly (standalone mode)

#### Contract Boundary Testing

- **FR-032**: Integration tests MUST verify CompiledArtifacts output from floe-core is valid input for floe-dagster asset creation
- **FR-033**: Integration tests MUST verify CompiledArtifacts output from floe-core generates valid dbt profiles via floe-dbt
- **FR-034**: Integration tests MUST verify dbt manifest.json output is valid input for floe-cube model sync
- **FR-035**: Integration tests MUST verify Polaris catalog configuration in CompiledArtifacts correctly initializes floe-polaris connections

### Key Entities

- **Traceability Matrix**: Mapping between requirement IDs (FR-XXX) and test file paths, with coverage status
- **Test Profile**: Docker Compose profile grouping (base, storage, compute, full) with service list
- **Test Fixture**: Reusable test setup/teardown code in testing/fixtures/ or conftest.py
- **Integration Test**: Test that requires external services (Docker) to execute
- **Coverage Gap**: Requirement without corresponding integration test

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of functional requirements from specs 001-005 have corresponding integration tests documented in traceability matrix
- **SC-002**: All 7 packages have integration test directories with at least one test file that executes in Docker
- **SC-003**: Integration test suite executes successfully in CI with zero skipped tests (all tests either pass or fail)
- **SC-004**: Test infrastructure starts within 2 minutes for storage profile and 5 minutes for full profile
- **SC-005**: Each package's integration tests complete within 5 minutes for normal runs
- **SC-006**: Traceability report generation completes within 30 seconds
- **SC-007**: New developer can add an integration test following documentation within 30 minutes

## Gap Analysis: Current State vs Requirements

Based on analysis of existing specs (001-005) and current integration tests, the following gaps have been identified:

### Coverage Gaps by Package

#### floe-core (Spec 001)
**Current**: 2 integration test files covering YAML loading and compilation
**Gap**: None identified - comprehensive coverage of core functionality

#### floe-cli (Spec 002)
**Current**: 1 integration test file covering only performance (help --500ms)
**Gap**:
- Missing: Command execution tests for `validate`, `compile`, `init`
- Missing: Error handling tests for invalid input files
- Missing: End-to-end workflow tests (validate then compile)

#### floe-dbt (Spec 003)
**Current**: 1 integration test file covering DuckDB profile validation only
**Gap**:
- Missing: Profile validation for Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark
- Missing: Manifest.json generation and parsing
- Missing: Multi-environment profile generation

#### floe-dagster (Spec 003)
**Current**: 1 integration test file covering manifest parsing
**Gap**:
- Missing: Actual asset materialization execution
- Missing: OpenLineage event emission verification
- Missing: OpenTelemetry trace span verification
- Missing: Asset dependency resolution tests

#### floe-polaris (Spec 004)
**Current**: 1 integration test file with approximately 42 tests
**Gap**: None identified - comprehensive namespace and table operation coverage

#### floe-iceberg (Spec 004)
**Current**: 2 integration test files with approximately 62 tests total
**Gap**: None identified - comprehensive table and IOManager coverage

#### floe-cube (Spec 005)
**Current**: 5 integration test files with approximately 100 tests
**Gap**:
- Missing: Pre-aggregation refresh testing
- Missing: Row-level security JWT validation tests

### Infrastructure Gaps

- **Gap-INFRA-001**: No test runner script for floe-dbt integration tests with PostgreSQL target
- **Gap-INFRA-002**: No test runner script for floe-dagster integration tests with Marquez
- **Gap-INFRA-003**: Missing documentation for adding new services to Docker Compose
- **Gap-INFRA-004**: No automated traceability matrix generation tool

### Traceability Gaps

- **Gap-TRACE-001**: No formal mapping between spec requirements and test files
- **Gap-TRACE-002**: No coverage report generation tool
- **Gap-TRACE-003**: No CI job to validate traceability on PR

## Assumptions

1. **Test Philosophy**: The project follows "Tests FAIL, Never Skip" philosophy - all infrastructure issues cause test failures, not skips
2. **Docker Availability**: CI environment has Docker and Docker Compose available
3. **Credential Management**: Polaris credentials are auto-generated and extracted by init scripts; no manual credential setup required
4. **Test Isolation**: Tests use UUID-based naming for concurrent execution safety
5. **Service Health**: All Docker services define health checks for startup ordering
6. **Documentation Location**: Test documentation resides in testing/docker/README.md and package-level README files

## Dependencies

- **Depends on 001-core-foundation**: CompiledArtifacts contract and FloeSpec schema
- **Depends on 003-orchestration-layer**: dbt manifest.json generation for Dagster tests
- **Depends on 004-storage-catalog**: Polaris and Iceberg infrastructure for storage tests
- **Depends on 005-consumption-layer**: Cube infrastructure for semantic layer tests

## Out of Scope

- **E2E Testing**: End-to-end tests spanning multiple packages are deferred to a future specification
- **Performance Testing**: Load testing and performance benchmarks are not included
- **Security Penetration Testing**: Security testing beyond basic authentication is not included
- **Cloud Provider Testing**: Tests against actual AWS/GCP/Azure services (uses LocalStack for S3/STS/IAM)
- **Multi-Tenant Isolation**: Tenant namespace isolation is a SaaS Control Plane concern, not OSS runtime (row-level security IS in scope as a standalone capability)
