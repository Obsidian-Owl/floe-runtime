# Feature Specification: Kubernetes Demo Deployment

**Feature Branch**: `008-kubernetes-demo`
**Created**: 2025-12-22
**Status**: Draft
**Input**: User description: "Full-stack Kubernetes deployment for floe-runtime demo - DuckDB compute, Cube semantic layer, Polaris catalog, all infrastructure services"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy Complete Stack to Local Kubernetes (Priority: P1)

A Platform Engineer wants to deploy the **complete floe-runtime stack** to their local Kubernetes cluster (Docker Desktop) using a single command sequence. This validates the entire deployment automation before moving to cloud environments.

**Why this priority**: Without a working local deployment, no other testing or demo is possible. This is the foundational capability that proves all Helm charts work together.

**Independent Test**: Can be fully tested by running `make deploy-local-full` and verifying all pods reach Running state within 5 minutes.

**Acceptance Scenarios**:

1. **Given** Docker Desktop Kubernetes is running, **When** the Platform Engineer runs `make deploy-local-full`, **Then** all 8 services (PostgreSQL, MinIO, Polaris, Dagster webserver, Dagster daemon, Cube API, Cube Store, Jaeger) reach Running state within 5 minutes
2. **Given** the stack is deployed, **When** the Platform Engineer runs `kubectl get pods -n floe`, **Then** all pods show 1/1 READY status
3. **Given** the stack is deployed, **When** the Platform Engineer port-forwards to Dagster UI, **Then** the Dagster UI is accessible at localhost:3000

---

### User Story 2 - Query Data via Cube Semantic Layer (Priority: P2)

A Data Analyst wants to query the demo data through Cube's REST API and SQL API to verify the complete data flow from Iceberg tables to consumption APIs.

**Why this priority**: The semantic layer is the primary value proposition - proving data flows from storage through Cube validates the entire architecture.

**Independent Test**: Can be tested by hitting Cube's /cubejs-api/v1/load endpoint and receiving JSON response with order data.

**Acceptance Scenarios**:

1. **Given** the demo data has been seeded, **When** the Analyst queries `GET /cubejs-api/v1/load` with Orders measures, **Then** they receive a JSON response with order counts and totals
2. **Given** Cube SQL API is exposed on port 15432, **When** the Analyst connects with psycopg2, **Then** they can execute `SELECT MEASURE(count) FROM Orders` and receive results
3. **Given** Cube is configured with DuckDB, **When** querying Iceberg tables via Polaris, **Then** DuckDB reads data from MinIO storage without errors

---

### User Story 3 - Generate Demo Data On-Demand (Priority: P3)

A Solutions Architect wants to generate synthetic ecommerce data to demonstrate the pipeline during a live stakeholder presentation.

**Why this priority**: Live data generation shows the platform's real-time capabilities, but static demo works as fallback.

**Independent Test**: Can be tested by triggering the Dagster job via GraphQL mutation and observing new data in Cube queries.

**Acceptance Scenarios**:

1. **Given** the stack is deployed with empty tables, **When** the Architect triggers the seed job via Dagster UI, **Then** synthetic ecommerce data (customers, orders, products) is generated within 2 minutes
2. **Given** demo data exists, **When** the 5-minute schedule fires, **Then** new orders are appended to the orders table (row count increases)
3. **Given** a live demo in progress, **When** the Architect manually triggers data generation via API, **Then** additional data appears in Cube queries within 30 seconds

---

### User Story 4 - View Observability Data (Priority: P4)

A DevOps Engineer wants to see traces in Jaeger and lineage in Marquez to verify observability instrumentation is working.

**Why this priority**: Observability proves enterprise-grade architecture but is not required for core demo functionality.

**Independent Test**: Can be tested by viewing traces in Jaeger UI after running a data generation job.

**Acceptance Scenarios**:

1. **Given** a Dagster job has run, **When** the DevOps Engineer opens Jaeger UI at localhost:16686, **Then** they see traces for the job execution with spans for dbt and Iceberg operations
2. **Given** dbt models have materialized, **When** the DevOps Engineer opens Marquez UI at localhost:5001, **Then** they see data lineage showing model dependencies

---

### Edge Cases

- What happens when Docker Desktop has insufficient memory (< 4GB)? → Pods crash with OOMKilled, documented in troubleshooting
- What happens when Polaris initialization fails? → Dagster and Cube pods enter CrashLoopBackOff, Helm hook retries 3 times
- What happens when MinIO is unavailable during query? → Cube returns 500 error with clear message about storage unavailability
- What happens when port 3000/4000/15432 is already in use? → Port-forward fails with clear error, document alternative ports

## Requirements *(mandatory)*

### Functional Requirements

**Infrastructure Helm Chart**

- **FR-001**: System MUST provide a `charts/floe-infrastructure/` Helm chart for shared infrastructure services
- **FR-002**: Infrastructure chart MUST deploy PostgreSQL (Dagster/Marquez metadata), MinIO (Iceberg storage), Polaris (catalog), Jaeger (traces)
- **FR-003**: Infrastructure chart MUST use official Helm charts as dependencies (Bitnami PostgreSQL, MinIO, Jaeger)
- **FR-004**: All stateful services MUST use `emptyDir` for Docker Desktop compatibility (no PVC)
- **FR-005**: Polaris MUST be initialized via Helm `post-install` hook Job (create catalog, namespace, OAuth2 credentials)

**DuckDB Compute Integration**

- **FR-006**: Dagster workers MUST use dbt-duckdb adapter for transformations
- **FR-007**: DuckDB MUST connect to Polaris REST catalog using OAuth2 secrets
- **FR-008**: DuckDB MUST read Iceberg tables from MinIO via HTTPFS extension
- **FR-009**: Cube MUST use built-in DuckDB for query execution (no separate compute service)
- **FR-010**: Cube SQL API MUST be exposed on port 15432 for BI tool connections

**Demo Data Pipeline**

- **FR-011**: Dagster sensor MUST detect empty Iceberg tables and trigger seed job automatically
- **FR-012**: Dagster schedule MUST generate new orders every 5 minutes (configurable)
- **FR-013**: Manual data generation MUST be triggerable via Dagster GraphQL API
- **FR-014**: Generated data MUST use floe-synthetic EcommerceGenerator with realistic patterns

**Deployment Automation**

- **FR-015**: System MUST provide Make targets: `deploy-local-full`, `deploy-local-infra`, `undeploy-local`
- **FR-016**: Deployment MUST wait for infrastructure readiness before deploying application charts
- **FR-017**: All services MUST have fast health checks (< 30s detection, not 5-minute timeouts)
- **FR-018**: Port-forward commands MUST be documented for all UI/API access points

### Key Entities

- **HelmRelease**: Represents a deployed Helm chart with values and status
- **DuckDBCatalogConnection**: Configuration for DuckDB to connect to Polaris via REST catalog
- **CubeDataSource**: Cube configuration linking DuckDB to Iceberg tables
- **SeedJob**: Dagster job that generates initial demo data
- **GenerationSchedule**: Dagster schedule for continuous data generation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Platform engineers can deploy the complete stack with `make deploy-local-full` in under 5 minutes
- **SC-002**: All 8 pods reach Running state without manual intervention
- **SC-003**: Cube REST API responds to queries within 100ms for demo-size data
- **SC-004**: Data flows from generation through dbt to Cube queries in under 60 seconds
- **SC-005**: Port-forward commands provide access to all 6 UIs/APIs (Dagster, Cube REST, Cube SQL, Jaeger, Marquez, MinIO)
- **SC-006**: Helm charts pass `helm lint` and `helm template` validation without errors

## Assumptions

1. **Docker Desktop**: Users have Docker Desktop with Kubernetes enabled and at least 4GB RAM allocated
2. **Helm 3.x**: Users have Helm 3 installed for chart management
3. **kubectl**: Users have kubectl configured to talk to Docker Desktop cluster
4. **No Cloud Dependencies**: Demo runs entirely locally without cloud services
5. **Existing Charts**: `charts/floe-dagster/` and `charts/floe-cube/` exist from Feature 007

## Clarifications

### Session 2025-12-22

- Q: Should we have a standalone DuckDB server for ad-hoc queries? A: No - Cube SQL API (port 15432) provides enterprise ad-hoc access. DuckDB is embedded only.
- Q: How should DuckDB connect to Iceberg? A: Via Polaris REST catalog using OAuth2 secrets (not direct S3 access)
- Q: What Helm chart strategy for infrastructure? A: Subchart dependencies using official charts (Bitnami, MinIO, Jaeger)
- Q: How should initial data be seeded? A: Dagster sensor detects empty tables and triggers seed job automatically
- Q: How should Polaris be initialized? A: Helm `post-install` hook Job creates catalog, namespace, and OAuth2 credentials
