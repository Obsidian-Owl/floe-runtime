# Feature Specification: Orchestration Layer

**Feature Branch**: `003-orchestration-layer`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Create the orchestration layer (floe-dagster + floe-dbt) that generates dbt profiles.yml from CompiledArtifacts, creates Dagster Software-Defined Assets from dbt models, emits OpenLineage events for data lineage, and creates OpenTelemetry spans for observability"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute dbt Transformations via Dagster (Priority: P1)

As a data engineer, I want to run my dbt transformations through Dagster so that I get orchestration, scheduling, and asset management without manual dbt CLI invocation.

**Why this priority**: This is the core value proposition - connecting dbt transformations to Dagster orchestration. Without this, there is no orchestration layer.

**Independent Test**: Can be fully tested by providing a compiled floe.yaml and dbt project, then materializing assets through Dagster UI or CLI. Delivers working data pipeline execution.

**Acceptance Scenarios**:

1. **Given** a valid CompiledArtifacts file with dbt transform configuration, **When** I start the Dagster development server, **Then** I see all dbt models represented as Software-Defined Assets in the Dagster UI
2. **Given** dbt models with dependencies (refs), **When** I view the asset graph, **Then** the dependency relationships match the dbt DAG
3. **Given** a dbt model asset, **When** I trigger materialization, **Then** the dbt model is executed and the asset shows as materialized with success/failure status
4. **Given** a failed dbt run, **When** I view the asset run, **Then** I see the dbt error messages in the Dagster logs

---

### User Story 2 - Generate dbt Profiles from Configuration (Priority: P1)

As a data engineer, I want dbt profiles.yml automatically generated from my floe.yaml configuration so that I don't need to manually maintain connection settings across environments.

**Why this priority**: dbt cannot execute without profiles.yml. This is a prerequisite for Story 1.

**Independent Test**: Can be fully tested by compiling floe.yaml and verifying profiles.yml is generated with correct connection parameters. Delivers consistent configuration management.

**Acceptance Scenarios**:

1. **Given** a CompiledArtifacts with DuckDB compute target, **When** profiles are generated, **Then** the profiles.yml contains a valid DuckDB profile with the configured database path
2. **Given** a CompiledArtifacts with Snowflake compute target, **When** profiles are generated, **Then** the profiles.yml contains environment variable references for credentials (never hardcoded secrets)
3. **Given** a CompiledArtifacts with any of the 7 supported targets (DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark), **When** profiles are generated, **Then** a valid dbt profile is created with target-appropriate settings
4. **Given** custom properties in compute configuration, **When** profiles are generated, **Then** the custom properties override default values

---

### User Story 3 - Track Data Lineage with OpenLineage (Priority: P2)

As a data governance lead, I want data lineage events emitted during pipeline execution so that I can trace data flow through the system for compliance and debugging.

**Why this priority**: Lineage provides critical governance and debugging capabilities but is not required for basic pipeline execution.

**Independent Test**: Can be tested by running a pipeline with a lineage endpoint configured and verifying events appear in the lineage backend. Delivers audit trail and data flow visibility.

**Acceptance Scenarios**:

1. **Given** observability.lineage is enabled in configuration, **When** a dbt model starts executing, **Then** an OpenLineage START event is emitted with job and run identifiers
2. **Given** a dbt model execution completes successfully, **When** the asset materializes, **Then** an OpenLineage COMPLETE event is emitted with input/output dataset information
3. **Given** a dbt model execution fails, **When** the error occurs, **Then** an OpenLineage FAIL event is emitted with error details
4. **Given** column classifications exist in dbt meta tags, **When** lineage events are emitted, **Then** the classification metadata is included in dataset facets

---

### User Story 4 - Monitor Execution with OpenTelemetry (Priority: P2)

As a platform operator, I want execution traces and metrics exported via OpenTelemetry so that I can monitor pipeline performance and troubleshoot issues in my observability stack.

**Why this priority**: Observability is essential for production operations but not required for basic development workflows.

**Independent Test**: Can be tested by running a pipeline with OTLP endpoint configured and verifying spans appear in the trace backend. Delivers performance monitoring and debugging.

**Acceptance Scenarios**:

1. **Given** observability.traces is enabled with an OTLP endpoint, **When** an asset materializes, **Then** a trace span is created with asset name and execution duration
2. **Given** trace spans are created, **When** I view them in the observability backend, **Then** I see attributes including asset name, compute target, and tenant context
3. **Given** structured logging is enabled, **When** logs are emitted during execution, **Then** trace_id and span_id are included for correlation
4. **Given** observability is disabled (standalone mode), **When** the pipeline executes, **Then** no external telemetry calls are made and execution completes normally

---

### User Story 5 - Configure Multiple Environments (Priority: P3)

As a data engineer, I want to run the same pipeline against different environments (dev, staging, prod) by changing configuration so that I can test changes safely before production deployment.

**Why this priority**: Multi-environment support is a production need but not required for initial development or single-environment deployments.

**Independent Test**: Can be tested by generating profiles with different target configurations and verifying each connects to the correct environment. Delivers safe promotion workflow.

**Acceptance Scenarios**:

1. **Given** different floe.yaml configurations for dev and prod, **When** I compile each, **Then** separate profiles.yml files are generated with environment-specific connections
2. **Given** environment-specific secret references, **When** profiles are generated, **Then** the correct environment variables are referenced for each target

---

### Edge Cases

- What happens when dbt manifest.json doesn't exist? System provides clear error message instructing user to run `dbt compile` first
- What happens when dbt execution fails mid-pipeline? Dagster marks affected assets as failed, unaffected assets remain unchanged, lineage FAIL event is emitted
- What happens when OpenLineage/OTel endpoints are unreachable? Pipeline execution continues (observability is non-blocking), warning is logged
- What happens with circular dbt refs? dbt itself catches this error; system surfaces dbt's error message
- What happens when profiles.yml already exists? System overwrites it (generated artifact, not user-managed)
- What happens with unsupported compute target? Validation fails at compile time with clear error listing supported targets

## Requirements *(mandatory)*

### Functional Requirements

**Profile Generation (floe-dbt)**:

- **FR-001**: System MUST generate valid dbt profiles.yml from CompiledArtifacts compute configuration
- **FR-002**: System MUST support all 7 compute targets: DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark
- **FR-003**: System MUST use environment variable references for all credentials (never hardcoded secrets)
- **FR-004**: System MUST allow properties override via FloeSpec compute.properties
- **FR-005**: System MUST write profiles to the path specified in CompiledArtifacts.dbt_profiles_path

**Asset Creation (floe-dagster)**:

- **FR-006**: System MUST create Dagster Software-Defined Assets from dbt manifest.json
- **FR-007**: System MUST preserve dbt model dependencies as Dagster asset dependencies
- **FR-008**: System MUST configure DbtCliResource with generated profiles directory
- **FR-009**: System MUST stream dbt execution events to Dagster event log
- **FR-010**: System MUST attach metadata from dbt models (description, tags, owner) to Dagster assets

**OpenLineage Integration** (custom emission via floe-dagster for orchestrator portability):

- **FR-011**: System MUST emit OpenLineage START event when dbt execution begins
- **FR-012**: System MUST emit OpenLineage COMPLETE event with schema facets on successful execution
- **FR-013**: System MUST emit OpenLineage FAIL event with error details on failed execution
- **FR-014**: System MUST include input/output dataset information in lineage events
- **FR-015**: System MUST include column classifications from governance config in dataset facets
- **FR-024**: System MUST implement OpenLineage emission in floe-dagster code (not via Dagster sensor) for standards-based portability

**OpenTelemetry Integration**:

- **FR-016**: System MUST create trace spans for each asset materialization
- **FR-017**: System MUST include asset name, duration, and status as span attributes
- **FR-018**: System MUST propagate tenant context from CompiledArtifacts.observability.attributes
- **FR-019**: System MUST inject trace_id and span_id into structured logs
- **FR-020**: System MUST support OTLP export when endpoint is configured

**Standalone Operation**:

- **FR-021**: System MUST function without OpenLineage endpoint (lineage disabled gracefully)
- **FR-022**: System MUST function without OTLP endpoint (traces disabled gracefully)
- **FR-023**: System MUST not require any SaaS dependencies for core execution

### Key Entities

- **Profile**: Generated dbt connection configuration for a specific compute target. Contains authentication method, connection parameters, and target-specific settings.
- **DbtAsset**: A Dagster Software-Defined Asset representing a dbt model. Contains model name, dependencies, metadata, and materialization logic.
- **LineageEvent**: An OpenLineage RunEvent capturing job execution state. Contains job identity, run identity, input/output datasets, and facets.
- **TraceSpan**: An OpenTelemetry span representing a unit of work. Contains operation name, timing, attributes, and parent relationship.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can execute dbt models through Dagster UI within 5 minutes of initial setup
- **SC-002**: Profile generation supports all 7 compute targets with 100% test coverage
- **SC-003**: Asset dependencies match dbt DAG structure with 100% accuracy
- **SC-004**: OpenLineage events are emitted within 1 second of execution state changes
- **SC-005**: Trace spans capture 100% of asset materializations when observability is enabled
- **SC-006**: System operates in standalone mode (no external dependencies) with zero degradation in core functionality
- **SC-007**: All secrets remain in environment variables - zero hardcoded credentials in generated files
- **SC-008**: Users can correlate logs, traces, and lineage events using shared identifiers

## Assumptions

- dbt project already exists with valid models and dbt_project.yml
- User has run `dbt compile` to generate manifest.json before using floe-dagster
- Environment variables for credentials are set in the execution environment
- OpenLineage and OTLP backends are accessible when enabled (graceful degradation when not)
- Users are familiar with Dagster concepts (assets, runs, schedules)
- Iceberg table format is handled by dbt adapters (via `file_format='iceberg'` config), not by floe-dagster
- Polaris catalog registration is deferred to floe-iceberg package (next feature), keeping orchestration layer storage-agnostic

## Dependencies

- **floe-core**: Provides CompiledArtifacts contract, FloeSpec schema, ComputeTarget enum
- **dagster 1.9+**: Orchestration framework with Software-Defined Assets
- **dagster-dbt 0.25+**: dbt integration providing @dbt_assets decorator and DbtCliResource
- **dbt-core 1.9+**: Data transformation framework
- **openlineage-python 1.24+**: OpenLineage event emission
- **opentelemetry-sdk**: Tracing and metrics
- **opentelemetry-exporter-otlp**: OTLP export capability

## Out of Scope

- dbt Cloud integration (standalone/self-hosted only)
- Custom Python transformations (dbt models only in this feature)
- Dagster schedules and sensors (future feature)
- Iceberg table management (separate floe-iceberg package)
- Cube semantic layer (separate floe-cube package)
- Web UI for configuration (CLI-only in this feature)

## Clarifications

### Session 2025-12-16

- Q: OpenLineage event source - use Dagster native lineage only, custom OpenLineage emission, or wrapper? → A: Option B - Emit OpenLineage events via custom floe-dagster code (standards-based portability for future orchestrator flexibility)
- Q: Iceberg/Polaris relationship to orchestration layer - agnostic, include hooks, or defer? → A: Option A - Orchestration layer is Iceberg-agnostic (clean separation; dbt adapters handle storage format, floe-iceberg handles Polaris registration)
