# Feature Specification: Deployment Automation

**Feature Branch**: `007-deployment-automation`
**Created**: 2025-12-21
**Status**: Draft
**Input**: User description: "Implement deployment automation with GitOps, Helm charts, production Dockerfiles, and pre-deployment validation for floe-runtime"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy floe-runtime to Kubernetes (Priority: P1)

A Platform Engineer needs to deploy floe-runtime (Dagster orchestration layer) to their cloud Kubernetes cluster (EKS, GKE, or AKS). They want to use standard Kubernetes tooling (Helm) and leverage the official Dagster Helm chart with floe-specific customizations.

**Why this priority**: Without container images and Helm charts, no Kubernetes deployment is possible. This is the foundational capability that enables all production use cases.

**Independent Test**: Can be fully tested by running `helm install floe-runtime charts/floe-dagster` against a local Kubernetes cluster (Docker Desktop or kind) and verifying Dagster webserver becomes accessible.

**Acceptance Scenarios**:

1. **Given** a Kubernetes cluster with `kubectl` access, **When** the Platform Engineer runs `helm install floe-runtime charts/floe-dagster --values values.yaml`, **Then** Dagster webserver, daemon, and worker pods are created and reach Running state within 5 minutes
2. **Given** a deployed floe-runtime, **When** the Platform Engineer accesses the Dagster UI endpoint, **Then** they see the Dagster asset graph with dbt models from CompiledArtifacts
3. **Given** a values.yaml with custom configuration, **When** the Platform Engineer provides compute target credentials, **Then** dbt can successfully connect to the configured compute engine

---

### User Story 2 - Automate Deployments via GitOps (Priority: P2)

A DevOps Engineer wants to implement a fully automated deployment pipeline where pushing to a Git repository automatically deploys changes to the appropriate environment. They use either ArgoCD or Flux for GitOps-style deployments.

**Why this priority**: GitOps automation reduces manual deployment steps and enables consistent, auditable infrastructure changes. Depends on Helm charts (P1) being available.

**Independent Test**: Can be tested by creating an ArgoCD Application pointing to the Helm chart, making a values.yaml change, and verifying the cluster automatically reconciles.

**Acceptance Scenarios**:

1. **Given** an ArgoCD installation and a floe-runtime Application resource, **When** the DevOps Engineer pushes a new image tag to the values file, **Then** ArgoCD automatically syncs and deploys the new version within 3 minutes
2. **Given** a Flux HelmRelease resource configured for floe-runtime, **When** a new Helm chart version is tagged, **Then** Flux automatically reconciles and upgrades the release
3. **Given** multiple environments (dev, staging, prod), **When** the DevOps Engineer promotes changes through environment folders, **Then** each environment deploys independently with its own configuration

---

### User Story 3 - Validate Environment Before Deployment (Priority: P3)

A Data Engineer needs to verify that all external services (compute engine, storage, catalog, database) are accessible and properly configured before deploying floe-runtime. This prevents deployment failures due to misconfigured infrastructure.

**Why this priority**: Pre-flight validation reduces troubleshooting time and catches misconfigurations early. Can be used standalone but provides most value when integrated with deployment automation.

**Independent Test**: Can be tested by running `floe preflight` command against a configured environment and verifying it reports connectivity status for each service.

**Acceptance Scenarios**:

1. **Given** a configured floe.yaml with compute target settings, **When** the Data Engineer runs `floe preflight --check-compute`, **Then** the system reports whether the compute engine (Trino/Snowflake/BigQuery) is reachable
2. **Given** storage credentials in environment variables, **When** the Data Engineer runs `floe preflight --check-storage`, **Then** the system verifies bucket access and reports read/write permissions
3. **Given** Polaris catalog credentials, **When** the Data Engineer runs `floe preflight --check-catalog`, **Then** the system authenticates via OAuth2 and lists available namespaces
4. **Given** a missing or invalid credential, **When** the Data Engineer runs preflight checks, **Then** the system clearly reports which service failed and suggests remediation steps

---

### User Story 4 - Manage Secrets Securely (Priority: P4)

A Security Engineer needs to deploy floe-runtime with credentials (database passwords, API keys, OAuth2 secrets) without exposing them in Git or Helm values. They want to use their organization's preferred secrets management approach.

**Why this priority**: Secure secrets management is essential for production but multiple valid approaches exist. Documenting options enables users to choose based on their infrastructure.

**Independent Test**: Can be tested by deploying with External Secrets Operator configured and verifying credentials are injected into pods without appearing in Helm values.

**Acceptance Scenarios**:

1. **Given** External Secrets Operator installed, **When** the Security Engineer deploys using ExternalSecret resources, **Then** Kubernetes Secrets are automatically created from AWS Secrets Manager/Vault
2. **Given** Sealed Secrets installed, **When** the Security Engineer commits encrypted secrets to Git, **Then** the cluster controller decrypts and creates Kubernetes Secrets
3. **Given** SOPS-encrypted values files, **When** ArgoCD or Flux processes the Helm release, **Then** secrets are decrypted at deploy time and injected into the workload

---

### User Story 5 - Deploy Cube Semantic Layer (Priority: P5)

A Data Platform Lead wants to deploy the optional Cube semantic layer alongside Dagster to provide REST, GraphQL, and SQL APIs for data consumption.

**Why this priority**: Cube is optional and adds complexity. Core Dagster deployment should work first before adding semantic layer.

**Independent Test**: Can be tested by deploying floe-cube chart alongside floe-dagster and verifying Cube API responds to queries.

**Acceptance Scenarios**:

1. **Given** floe-dagster is deployed and running, **When** the Platform Lead installs floe-cube chart, **Then** Cube API, refresh worker, and store pods are created
2. **Given** Cube is configured with Trino as compute engine, **When** a user sends a query to the Cube REST API, **Then** the query is executed against Trino and results are returned
3. **Given** pre-aggregations are enabled, **When** the refresh worker builds aggregations, **Then** subsequent queries are served from cached data

---

### User Story 6 - E2E Deployment Demo with Live Data (Priority: P6)

A Solutions Architect wants to demonstrate floe-runtime's capabilities to stakeholders using a fully deployed environment with continuously updating "live" data. The demo should showcase the complete data flow: synthetic data generation → Dagster orchestration → dbt transformations → Iceberg tables → Cube API consumption.

**Why this priority**: E2E demos serve dual purposes: (1) internal deployment validation and regression testing for confidence, and (2) external stakeholder showcases demonstrating real-world capabilities. The demo must be polished enough for external presentations while providing rigorous validation. Depends on core deployment (P1-P5) being functional.

**Independent Test**: Can be tested by deploying the full stack, enabling scheduled synthetic data generation, and verifying data appears in Cube queries within the configured interval.

**Acceptance Scenarios**:

1. **Given** a deployed floe-runtime with demo mode enabled, **When** the Dagster schedule triggers, **Then** new ecommerce orders are generated and appended to the Iceberg orders table
2. **Given** synthetic data generation is running, **When** the Solutions Architect queries the Cube REST API, **Then** they see row counts increasing over time reflecting new data
3. **Given** demo mode with temporal patterns enabled, **When** data is generated throughout the day, **Then** order volumes follow realistic intraday patterns (morning peak, lunch dip, evening surge)
4. **Given** a demo environment, **When** the Solutions Architect opens the Dagster UI, **Then** they see scheduled runs, asset materializations, and lineage graphs showing end-to-end data flow
5. **Given** a demo has been running for multiple intervals, **When** querying the Cube API with time-based filters, **Then** data shows realistic growth and distribution patterns across regions and statuses

---

### Edge Cases

- What happens when the compute engine is temporarily unavailable during Dagster startup? (Graceful degradation with retries and clear error messaging in Dagster UI)
- How does the system handle Helm upgrade during an active pipeline run? (Use PodDisruptionBudgets to prevent data loss; running jobs complete before pod termination)
- What happens when credentials expire during a long-running job? (Dagster daemon detects credential failure and marks run as failed with actionable error)
- How does the system behave with multiple floe-runtime deployments in the same cluster? (Namespace isolation ensures independent operation)
- What happens when preflight passes but deployment fails? (Common causes documented: network policies, resource limits, image pull failures)
- What happens when synthetic data generation fails mid-demo? (Schedule retries with backoff; Dagster UI shows failed run with error details; demo continues with existing data)
- How does the demo handle disk space exhaustion from continuous data generation? (Configurable retention policies; demo mode generates reasonable data volumes; monitoring alerts before exhaustion)
- What happens when Cube pre-aggregation refresh overlaps with data generation? (Cube refresh worker handles concurrent writes gracefully; pre-aggregations eventually consistent)

## Requirements *(mandatory)*

### Functional Requirements

**Container Images**

- **FR-001**: System MUST provide a production Dockerfile for Dagster components (webserver, daemon, worker)
- **FR-002**: System MUST provide a production Dockerfile for Cube components (api, refresh-worker, store)
- **FR-003**: Container images MUST include floe-runtime packages and dbt with configured adapters
- **FR-004**: Container images MUST support configuration via environment variables for all credentials

**Helm Charts**

- **FR-005**: System MUST provide a Helm chart for floe-dagster that depends on the official Dagster Helm chart
- **FR-006**: System MUST provide a Helm chart for floe-cube for semantic layer deployment
- **FR-007**: Helm charts MUST support mounting CompiledArtifacts.json as a ConfigMap
- **FR-008**: Helm charts MUST support external secret references for credentials
- **FR-009**: Helm charts MUST provide values files for dev and production configurations
- **FR-010**: Umbrella chart MUST allow deploying all components together or individually

**GitOps Examples**

- **FR-011**: System MUST provide ArgoCD Application and ApplicationSet examples
- **FR-012**: System MUST provide Flux HelmRelease and Kustomization examples
- **FR-013**: Examples MUST demonstrate environment-based deployment (dev/staging/prod)
- **FR-014**: Examples MUST integrate with at least one secrets management approach

**Pre-Deployment Validation**

- **FR-015**: CLI MUST provide a `floe preflight` command for infrastructure validation
- **FR-016**: Preflight MUST validate compute engine connectivity (Trino, Snowflake, BigQuery, DuckDB)
- **FR-017**: Preflight MUST validate object storage access (S3, GCS, ADLS)
- **FR-018**: Preflight MUST validate Iceberg catalog authentication (Polaris OAuth2)
- **FR-019**: Preflight MUST validate PostgreSQL connection for Dagster metadata
- **FR-020**: Preflight MUST provide clear error messages with remediation suggestions

**Documentation**

- **FR-021**: System MUST update docs/06-deployment-view.md to reflect metadata-driven architecture
- **FR-022**: System MUST create docs/07-infrastructure-provisioning.md for external service setup
- **FR-023**: Documentation MUST clearly separate what floe deploys vs. external service requirements
- **FR-024**: Documentation MUST provide multi-target compute examples (Trino, Snowflake, BigQuery, DuckDB)

**E2E Demo and Testing Infrastructure**

- **FR-025**: System MUST provide a demo mode Helm values configuration that enables continuous synthetic data generation
- **FR-026**: Dagster deployment MUST include schedules for synthetic data generation at configurable intervals (default: 5 minutes for demo visibility)
- **FR-026a**: Demo MUST provide an on-demand API/trigger to generate additional data batches during live presentations
- **FR-027**: Synthetic data generators MUST use floe-synthetic package (EcommerceGenerator, SaaSGenerator) with realistic patterns
- **FR-027a**: Ecommerce generator MUST include order_items table enabling product-level joins (orders → order_items → products)
- **FR-027b**: Generators MUST support configurable data quality scenarios (nulls, duplicates, late-arriving data) for dbt validation demos
- **FR-027c**: Demo MUST include full medallion dbt project (staging → intermediate → marts) with metrics, exposures, and Cube semantic layer integration
- **FR-028**: Demo mode MUST append data to Iceberg tables (not overwrite) to show accumulating "live" data
- **FR-029**: System MUST include E2E validation tests that verify complete data flow from generation to Cube API consumption
- **FR-030**: Demo infrastructure MUST support configurable data generation rates (burst mode for quick demos, realistic mode for extended showcases)
- **FR-031**: System MUST provide a Docker Compose demo profile that runs continuously with scheduled data generation
- **FR-032**: E2E tests MUST validate that Cube pre-aggregations refresh correctly as new data arrives
- **FR-033**: Demo MUST expose Marquez UI for data lineage visualization between assets
- **FR-034**: Demo MUST expose Jaeger UI for distributed tracing of pipeline executions

### Key Entities

- **CompiledArtifacts**: The metadata contract generated by `floe compile` containing dbt configuration, compute targets, and observability settings. Mounted as ConfigMap in Kubernetes.
- **Helm Values**: Configuration for each deployment environment (dev, staging, prod) specifying replica counts, resource limits, and external service endpoints.
- **ExternalSecret/SealedSecret**: Kubernetes-native representations of credentials that reference external secrets stores without exposing values in Git.
- **ArgoCD Application**: Custom resource defining a GitOps deployment source, destination, and sync policy for floe-runtime.
- **Demo Schedule**: Dagster schedule resource that triggers synthetic data generation at configured intervals, using floe-synthetic generators with temporal patterns.
- **E2E Test Suite**: Integration tests that validate complete data flow from synthetic generation through Dagster, dbt, Iceberg, to Cube API consumption.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Platform engineers can deploy floe-runtime to any Kubernetes cluster in under 30 minutes using Helm charts
- **SC-002**: GitOps deployments automatically reconcile within 5 minutes of a Git push
- **SC-003**: Pre-flight validation identifies 100% of connectivity issues before deployment attempt
- **SC-004**: Zero credentials are exposed in Git repositories or Helm values
- **SC-005**: Documentation enables a new user to understand the deployment architecture and make their first deployment without support escalation
- **SC-006**: Helm charts pass `helm lint` and `helm template` validation without errors
- **SC-007**: Container images support at least 3 compute targets (Trino, Snowflake, and one cloud warehouse)
- **SC-008**: E2E demo shows data flowing from synthetic generation to Cube API within 10 minutes of deployment
- **SC-009**: Demo environment can run continuously for 24+ hours without intervention, generating realistic data patterns
- **SC-010**: E2E tests achieve 100% pass rate for complete data flow validation before each release

## Assumptions

The following assumptions are made based on industry standards and the analysis in the plan file:

1. **Official Dagster Helm Chart**: We will extend the official dagster/dagster Helm chart rather than creating a custom chart from scratch. This leverages Dagster team's maintenance and expertise.

2. **Container Registry**: Documentation will cover multiple registry options (ghcr.io, DockerHub, ECR/GCR/ACR) without prescribing a single choice.

3. **Secrets Management**: Documentation will cover multiple approaches (External Secrets Operator, Sealed Secrets, SOPS) with pros/cons for each.

4. **Target Environments**: Primary focus is cloud Kubernetes (EKS/GKE/AKS) with local Kubernetes (Docker Desktop, kind) for development testing.

5. **Cube Licensing**: Cube is deployed as self-hosted open-source version. Cube Cloud integration is out of scope for this feature.

6. **Infrastructure Separation**: External services (compute engines, storage, catalog, PostgreSQL) are provisioned separately. This feature covers application deployment, not infrastructure provisioning.

7. **Existing Synthetic Data Package**: The floe-synthetic package already exists with EcommerceGenerator, SaaSGenerator, IcebergLoader, and Dagster asset definitions (daily_ecommerce_orders, daily_saas_events). Demo mode will leverage these existing components.

8. **Existing Test Infrastructure**: The Docker Compose test infrastructure (testing/docker/) provides LocalStack, Polaris, Trino, Cube, and Marquez services. E2E demo will extend this with a new "demo" profile for continuous operation.

9. **Enhanced Demo Data Model**: The floe-synthetic package will be enhanced with: (a) `order_items` table to enable product-level joins (customers → orders → order_items → products) for star schema demonstrations, and (b) configurable data quality scenarios (nulls, duplicates, late-arriving data) to demonstrate dbt data validation tests and cleaning transformations.

## Clarifications

### Session 2025-12-21

- Q: Should the demo data model be enhanced to support complex transformations? → A: Add order_items table AND data quality scenarios (nulls, duplicates, late-arriving data) to demo data validation
- Q: What dbt model complexity should the demo showcase? → A: Full analytics - Medallion layers (staging → intermediate → marts) + metrics, exposures, and semantic layer integration with Cube
- Q: How should continuous "live" data generation work in the demo? → A: 5-minute Dagster schedule as default, plus on-demand API trigger for generating additional data during presentations
- Q: What is the primary audience for the E2E demo? → A: Both internal validation AND external showcase - polished enough for stakeholders while serving as deployment confidence testing
- Q: Should the demo expose lineage and tracing UIs for stakeholder visibility? → A: Both - Expose Marquez (lineage) AND Jaeger (traces) for full observability showcase
