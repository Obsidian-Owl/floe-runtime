# Feature Specification: Consumption Layer (floe-cube)

**Feature Branch**: `005-consumption-layer`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "Create the consumption layer (floe-cube) that generates Cube configuration from CompiledArtifacts, syncs dbt models to Cube cubes via cube_dbt package, implements row-level security via security context, emits OpenLineage events for query lineage, and exposes REST, GraphQL, and SQL (Postgres wire) APIs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Cube Semantic Layer (Priority: P1)

A data platform operator enables the Cube semantic layer for their floe-runtime project by specifying consumption settings in floe.yaml. The system generates all required Cube configuration files from CompiledArtifacts, ready for deployment.

**Why this priority**: This is the foundation that all other features depend on. Without configuration generation, no other consumption layer functionality can work.

**Independent Test**: Can be fully tested by compiling a floe.yaml with consumption enabled and verifying the generated Cube configuration files are valid and complete.

**Acceptance Scenarios**:

1. **Given** a floe.yaml with consumption.enabled=true and a valid database_type, **When** the system compiles the configuration, **Then** it generates a valid cube.js configuration file with correct database driver settings.

2. **Given** CompiledArtifacts with pre_aggregations.refresh_schedule configured, **When** Cube configuration is generated, **Then** the refresh schedule is correctly applied to pre-aggregation definitions.

3. **Given** an api_secret_ref pointing to a Kubernetes secret, **When** Cube configuration is generated, **Then** it references the secret for API authentication instead of embedding credentials.

---

### User Story 2 - Sync dbt Models to Cube Cubes (Priority: P1)

A data engineer has dbt models that define business logic. The system automatically syncs these models to Cube cubes using the cube_dbt package, exposing measures, dimensions, and joins based on dbt manifest metadata.

**Why this priority**: This core functionality enables the semantic layer to surface dbt models through unified APIs. Without dbt-to-Cube sync, the consumption layer has no data to expose.

**Independent Test**: Can be fully tested by providing a dbt manifest.json and verifying that corresponding Cube cube definitions are generated with correct measures, dimensions, and relationships.

**Acceptance Scenarios**:

1. **Given** a dbt manifest.json containing model definitions with columns and descriptions, **When** model sync runs, **Then** Cube cubes are created with dimensions for each column and proper types inferred from dbt metadata.

2. **Given** dbt models with measures defined via meta tags (e.g., meta.cube.measures), **When** model sync runs, **Then** corresponding Cube measures are created with correct aggregation types.

3. **Given** dbt models with relationships defined via refs and joins, **When** model sync runs, **Then** Cube joins are created preserving the relationship cardinality.

4. **Given** a dbt model is updated and manifest regenerated, **When** model sync runs again, **Then** the Cube cube definition is updated to reflect changes without duplicating cubes.

---

### User Story 3 - Query Data via REST API (Priority: P2)

An application developer queries transformed data through the Cube REST API using JSON-formatted queries. The system returns results with proper pagination and filtering.

**Why this priority**: REST API is the most common integration pattern for web applications and provides the foundation for programmatic data access.

**Independent Test**: Can be fully tested by starting Cube with synced cubes and executing REST API queries, verifying correct response structure and data.

**Acceptance Scenarios**:

1. **Given** a Cube deployment with synced models and valid API credentials, **When** a client sends a REST query with dimensions and measures, **Then** the API returns correctly aggregated data in JSON format.

2. **Given** a query requesting more than 10,000 rows, **When** the client queries via REST, **Then** results are paginated with appropriate continuation tokens.

3. **Given** invalid API credentials, **When** a client attempts to query, **Then** the API returns a 401 Unauthorized response without exposing internal details.

---

### User Story 4 - Query Data via GraphQL API (Priority: P2)

A front-end developer uses GraphQL to query data with type-safe schema introspection. The system exposes cubes as GraphQL types with proper relationships.

**Why this priority**: GraphQL provides type safety and efficient querying that modern front-end frameworks expect, complementing REST for different use cases.

**Independent Test**: Can be fully tested by executing GraphQL queries against the Cube GraphQL endpoint and validating response schema matches introspected types.

**Acceptance Scenarios**:

1. **Given** a Cube deployment with synced models, **When** a client introspects the GraphQL schema, **Then** all cubes appear as types with their dimensions and measures as fields.

2. **Given** a GraphQL query with nested cube relationships, **When** executed, **Then** joined data is returned respecting the defined cube joins.

---

### User Story 5 - Query Data via SQL (Postgres Wire Protocol) (Priority: P2)

A BI tool connects to Cube using the Postgres wire protocol. The system accepts standard SQL queries and returns results compatible with Postgres client libraries.

**Why this priority**: SQL connectivity enables integration with existing BI tools (Tableau, Metabase, Superset) without requiring those tools to implement custom APIs.

**Independent Test**: Can be fully tested by connecting a Postgres client (psql) to the Cube SQL endpoint and executing SELECT queries.

**Acceptance Scenarios**:

1. **Given** Cube SQL API enabled on a configured port, **When** a Postgres client connects, **Then** authentication succeeds using Cube credentials.

2. **Given** a valid SQL SELECT query against a cube, **When** executed via Postgres wire protocol, **Then** results are returned with correct column types and data.

3. **Given** an unsupported SQL statement (e.g., UPDATE, DELETE), **When** executed, **Then** a clear error message is returned indicating the operation is not supported.

---

### User Story 6 - Enforce Row-Level Security (Priority: P3)

A data platform operator configures row-level security to control data access based on user-defined attributes (e.g., organization_id, department, region). The system filters all queries based on security context claims from JWT tokens, using user-configurable filter columns.

**Note on Security Model**: Row-level security in floe-cube is **role-based and user-managed**. Users define which columns to filter on and what claims to extract from JWT tokens. This is distinct from SaaS tenant isolation - the future Floe SaaS Control Plane provides infrastructure-level isolation (separate environments per customer), not data-level filtering within a single deployment.

**Why this priority**: Row-level security is critical for organizations with multiple user groups accessing shared data, but requires the query APIs to be working first.

**Independent Test**: Can be fully tested by executing identical queries with different security contexts and verifying different result sets are returned.

**Acceptance Scenarios**:

1. **Given** security.row_level=true and security.filter_column="organization_id", **When** a query is executed with security_context containing organization_id="org_a", **Then** only rows where organization_id="org_a" are returned.

2. **Given** row-level security enabled, **When** a query is executed without a valid security context, **Then** the query is rejected with an appropriate authorization error.

3. **Given** a cube with the configured filter column and row-level security enabled, **When** multiple queries execute concurrently with different security contexts, **Then** each query receives only its authorized data without cross-context leakage.

---

### User Story 7 - Monitor Query Performance via OpenTelemetry (Priority: P3)

A platform operations team monitors Cube query performance and latency. The system emits OpenTelemetry traces for every query, enabling performance analysis and troubleshooting in observability tools (Jaeger, Grafana Tempo, etc.).

**Note on Observability Model**: OpenTelemetry and OpenLineage serve **complementary purposes**:
- **OpenTelemetry**: Operational observability - "How is the system performing?" (traces, latency, errors)
- **OpenLineage**: Data lineage - "What data is being accessed?" (datasets, jobs, provenance)

**Why this priority**: Operational observability is important for production monitoring but requires query APIs to be working first.

**Independent Test**: Can be fully tested by executing queries and verifying OpenTelemetry traces appear in a configured collector with correct span hierarchy and metadata.

**Acceptance Scenarios**:

1. **Given** observability.traces_enabled=true with an OTel collector endpoint configured, **When** a query executes, **Then** an OpenTelemetry trace is emitted with spans for query parsing, execution, and response.

2. **Given** a client request with W3C Trace Context headers, **When** a query executes, **Then** the query trace is correlated with the parent trace via propagated context.

3. **Given** OpenTelemetry disabled, **When** queries execute, **Then** no traces are emitted and query performance is not impacted.

4. **Given** a query with row-level security filters, **When** a trace is emitted, **Then** the trace includes filter count but NOT filter values or JWT claims.

---

### User Story 8 - Emit OpenLineage Events for Query Audit (Priority: P3)

A data governance team tracks which applications query which datasets. The system emits OpenLineage events for each query execution, enabling audit trails and query lineage.

**Why this priority**: OpenLineage integration enables governance and audit capabilities but is not required for core query functionality.

**Independent Test**: Can be fully tested by executing queries and verifying OpenLineage events are emitted to the configured endpoint with correct metadata.

**Acceptance Scenarios**:

1. **Given** observability.openlineage_enabled=true with an endpoint configured, **When** a query executes successfully, **Then** an OpenLineage RUN event is emitted with job name, run ID, and input datasets.

2. **Given** a query that fails, **When** execution completes, **Then** an OpenLineage FAIL event is emitted with error details (without exposing sensitive information).

3. **Given** OpenLineage disabled, **When** queries execute, **Then** no OpenLineage events are emitted and query performance is not impacted.

---

### User Story 9 - Leverage Pre-Aggregations for Performance (Priority: P3)

A platform operator configures pre-aggregations to cache frequently-queried data. The system builds and refreshes pre-aggregations according to the configured schedule.

**Why this priority**: Pre-aggregations provide performance optimization but require the core query functionality to be operational first.

**Independent Test**: Can be fully tested by defining pre-aggregations, triggering a build, and verifying subsequent queries use the pre-aggregated data.

**Acceptance Scenarios**:

1. **Given** a cube with pre-aggregations defined and a refresh schedule, **When** the refresh interval passes, **Then** Cube automatically rebuilds the pre-aggregation.

2. **Given** a query that matches a pre-aggregation definition, **When** executed after the pre-aggregation is built, **Then** the query uses cached data and responds faster than querying raw tables.

---

### Edge Cases

- What happens when the dbt manifest.json path doesn't exist or is invalid? → System logs error and skips sync; existing cubes remain unchanged
- How does the system handle dbt models without any columns defined? → System skips model, logs warning
- What happens when Cube configuration references a database_type not supported? → System fails at startup with clear error message
- How does the system behave when the OpenLineage endpoint is unreachable? → Logs warning and continues query execution (non-blocking)
- What happens when the configured filter column doesn't exist in a cube's underlying table? → System logs error at sync time; cube excluded from row-level security enforcement
- How are queries handled when pre-aggregation build fails? → Queries fall back to raw tables; system logs pre-aggregation failure
- What happens when multiple floe-cube instances sync the same dbt models concurrently? → Last-write-wins; recommend single sync coordinator in production

## Requirements *(mandatory)*

### Functional Requirements

**Configuration Generation**

- **FR-001**: System MUST generate Cube configuration from ConsumptionConfig in CompiledArtifacts
- **FR-002**: System MUST support all database_type values: postgres, snowflake, bigquery, databricks, trino
- **FR-003**: System MUST reference Kubernetes secrets for API credentials (never embed secrets)
- **FR-004**: System MUST generate valid cube.js configuration file format

**Model Sync**

- **FR-005**: System MUST sync dbt models to Cube cubes using the cube_dbt package
- **FR-006**: System MUST infer Cube dimensions from dbt model columns
- **FR-007**: System MUST create Cube measures from dbt meta.cube.measures tags
- **FR-008**: System MUST preserve dbt model relationships as Cube joins
- **FR-009**: System MUST handle incremental sync (update existing cubes, not duplicate)
- **FR-010**: System MUST validate dbt manifest.json exists before sync
- **FR-028**: System MUST automatically trigger model sync when manifest.json changes are detected

**Query APIs**

- **FR-011**: System MUST expose REST API for JSON-formatted queries
- **FR-012**: System MUST expose GraphQL API with schema introspection
- **FR-013**: System MUST expose SQL API using Postgres wire protocol
- **FR-014**: System MUST support pagination for large result sets
- **FR-015**: System MUST return appropriate HTTP error codes for failed requests

**Row-Level Security**

- **FR-016**: System MUST implement row-level security via security context extracted from user-defined JWT token claims
- **FR-017**: System MUST filter all queries by configured filter_column (e.g., organization_id, department, region) when row-level security enabled
- **FR-018**: System MUST reject queries without valid JWT token (or missing required filter claim) when row-level security required
- **FR-019**: System MUST prevent cross-context data access in concurrent query scenarios
- **FR-027**: System MUST verify JWT signature before extracting security context claims
- **FR-030**: System MUST update floe-core CubeSecurityConfig schema to rename `tenant_column` to `filter_column` and change default from `"tenant_id"` to `"organization_id"`

**Observability: OpenTelemetry (Operational Tracing)**

OpenTelemetry provides **operational observability** - tracing query execution, measuring latency, and capturing performance metrics. This is about "how is the system performing?"

- **FR-031**: System MUST emit OpenTelemetry traces for query execution with span hierarchy (query → database → response)
- **FR-032**: System MUST include query metadata in trace spans (cube name, measures, dimensions, filter count)
- **FR-033**: System MUST propagate trace context from incoming requests (W3C Trace Context)
- **FR-034**: System MUST export traces to configured OpenTelemetry collector endpoint
- **FR-035**: System MUST NOT include sensitive data (filter values, JWT claims, row data) in trace spans
- **FR-036**: System MUST support disabling OpenTelemetry tracing via configuration

**Observability: OpenLineage (Data Lineage)**

OpenLineage provides **data lineage** - tracking which datasets are queried, by whom, and for what purpose. This is about "what data is being accessed and how does it flow?"

- **FR-020**: System MUST emit OpenLineage START events when query execution begins
- **FR-021**: System MUST emit OpenLineage COMPLETE events for successful queries
- **FR-022**: System MUST emit OpenLineage FAIL events for failed queries
- **FR-023**: System MUST NOT emit OpenLineage events when integration is disabled
- **FR-024**: System MUST NOT expose sensitive data in OpenLineage events
- **FR-029**: System MUST log a warning and continue query execution when OpenLineage endpoint is unreachable (non-blocking, best-effort)

**Pre-Aggregations**

- **FR-025**: System MUST support pre-aggregation refresh schedules (cron format)
- **FR-026**: System MUST automatically use pre-aggregated data when queries match definitions

### Key Entities

- **CubeConfig**: Runtime configuration for Cube deployment including API ports, database connection, and security settings
- **CubeSchema**: Generated cube definitions derived from dbt models, containing dimensions, measures, and joins
- **SecurityContext**: Request-scoped context containing user-defined filter claims (e.g., organization_id, department) and other security attributes for row-level filtering
- **QueryLineageEvent**: OpenLineage event capturing query execution metadata including job name, inputs, outputs, and timing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Data engineers can expose dbt models through REST/GraphQL/SQL APIs within 5 minutes of enabling consumption in floe.yaml
- **SC-002**: System supports 100 concurrent query clients without degradation
- **SC-003**: Pre-aggregated queries respond in under 1 second for 95% of requests
- **SC-004**: Row-level security filtering adds less than 100ms latency to queries
- **SC-005**: 100% of query executions emit OpenLineage events when integration is enabled
- **SC-006**: Zero cross-context data leakage when row-level security is enabled (verified via security tests)
- **SC-007**: All three API interfaces (REST, GraphQL, SQL) are functional and return consistent results for equivalent queries
- **SC-008**: 100% of query executions emit OpenTelemetry traces when tracing is enabled, with < 10ms overhead per query

## Clarifications

### Session 2025-12-18

- Q: How should the security context (containing filter claims for row-level security) be provided to Cube queries? → A: JWT tokens with user-defined claims (e.g., organization_id, department, region) verified by Cube
- Q: When should dbt models be synced to Cube cubes? → A: Automatic on manifest.json change detection (file watcher or post-dbt hook)
- Q: What should happen when the OpenLineage endpoint is unreachable during query execution? → A: Log warning and continue query execution (non-blocking, best-effort lineage)
- Q: What is the security model for row-level security vs SaaS tenant isolation? → A: Row-level security in floe-cube is role-based and user-managed (users configure filter columns like organization_id, department). This is distinct from the future Floe SaaS Control Plane which provides infrastructure-level tenant isolation (separate environments per customer).
- Q: What is the difference between OpenTelemetry and OpenLineage? → A: **OpenTelemetry** provides operational observability (traces, metrics, latency) - "how is the system performing?" **OpenLineage** provides data lineage (datasets, jobs, provenance) - "what data is being accessed?" Both are complementary standards per the floe-runtime architecture.

## Assumptions

- The cube_dbt package provides reliable dbt manifest parsing and Cube schema generation
- Cube's built-in row-level security (queryRewrite) is sufficient for user-managed filtering without custom implementation
- The existing Docker test infrastructure (testing/docker/) with the "full" profile provides Cube for integration testing
- dbt models will include appropriate meta tags for Cube measure definitions (meta.cube.measures)
- OpenLineage events follow the standard OpenLineage specification for SQL job facets

## Dependencies

- **floe-core**: Provides CompiledArtifacts with ConsumptionConfig, CubeSecurityConfig, and PreAggregationConfig schemas
- **floe-dagster**: Orchestrates dbt runs that produce manifest.json consumed by floe-cube
- **floe-iceberg**: Provides underlying table storage that Cube queries via configured database driver
- **cube_dbt**: NPM package for syncing dbt models to Cube cubes
- **OpenLineage**: Standard event format for query lineage emission (data lineage - "what data is accessed")
- **OpenTelemetry**: Standard for operational observability (traces, metrics - "how the system performs")
