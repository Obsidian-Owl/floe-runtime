# Implementation Plan: Kubernetes Demo Deployment

**Branch**: `008-kubernetes-demo` | **Date**: 2025-12-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-kubernetes-demo/spec.md`

## Summary

Deploy the complete floe-runtime stack to Kubernetes (Docker Desktop) as a production-quality demo with:
- DuckDB as embedded compute engine (in Cube and Dagster)
- Polaris REST catalog for Iceberg table metadata
- Modular Helm chart architecture with official subchart dependencies
- Automated data seeding and 5-minute scheduled generation

## Technical Context

**Language/Version**: Helm 3.x (chart templates), Python 3.10+ (Dagster, dbt), YAML (Kubernetes manifests)
**Primary Dependencies**:
- Bitnami PostgreSQL chart (Dagster/Marquez metadata)
- MinIO chart (Iceberg storage)
- Apache Polaris (REST catalog)
- Dagster Helm chart (orchestration)
- Cube (semantic layer with built-in DuckDB)
- Jaeger (tracing)
**Storage**: MinIO (S3-compatible) for Iceberg Parquet files, PostgreSQL for metadata
**Testing**: `helm lint`, `helm template`, `kubectl get pods`, integration tests
**Target Platform**: Docker Desktop Kubernetes (1.25+)
**Project Type**: Infrastructure-as-code (Helm charts) + configuration updates
**Performance Goals**: All pods Running within 5 minutes, Cube query response < 100ms
**Constraints**:
- No PVCs (Docker Desktop hostpath provisioner issues) - use emptyDir
- Minimal resources (100m CPU, 256Mi RAM requests)
- Fast health checks (< 30s failure detection)
**Scale/Scope**: 8 services, local demo environment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | ✅ PASS | No SaaS dependencies; runs entirely on local K8s |
| II. Type Safety | ✅ PASS | Helm values use typed schema; Python configs use Pydantic |
| III. Technology Ownership | ✅ PASS | dbt owns SQL, Dagster owns orchestration, Cube owns semantic layer |
| IV. Contract-Driven | ✅ PASS | Helm values files are the contract between charts |
| V. Security First | ✅ PASS | OAuth2 secrets for Polaris; no hardcoded credentials |
| VI. Quality Standards | ✅ PASS | Helm lint validation; documented troubleshooting |

## Project Structure

### Documentation (this feature)

```text
specs/008-kubernetes-demo/
├── plan.md              # This file
├── research.md          # Phase 0 output (DuckDB+Iceberg, Helm patterns)
├── data-model.md        # Phase 1 output (Helm values schema)
├── quickstart.md        # Phase 1 output (local deployment guide)
├── contracts/           # Phase 1 output (Helm values contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
charts/
├── floe-infrastructure/     # NEW - Shared infrastructure
│   ├── Chart.yaml           # Dependencies: postgresql, minio, polaris
│   ├── values.yaml          # Default values
│   ├── values-local.yaml    # Docker Desktop optimized
│   └── templates/
│       ├── _helpers.tpl     # Helm helpers
│       ├── polaris-init-job.yaml  # Helm hook for Polaris setup
│       └── NOTES.txt        # Post-install instructions
├── floe-dagster/            # EXISTS - Update for DuckDB
│   ├── values-local.yaml    # NEW - Local K8s values
│   └── (existing templates)
├── floe-cube/               # EXISTS - Update for DuckDB + Polaris
│   ├── values-local.yaml    # NEW - Local K8s values
│   └── (existing templates)
└── floe-runtime/            # EXISTS - Umbrella (optional)

demo/
├── profiles.yml             # UPDATE - Add dbt-duckdb profile
└── orchestration/
    └── definitions.py       # UPDATE - Add seed sensor

Makefile                     # UPDATE - Add deploy targets
```

**Structure Decision**: Modular Helm charts with subchart dependencies. Each chart is independently deployable. Infrastructure chart provides shared services.

## Complexity Tracking

> No Constitution violations requiring justification.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Subchart dependencies | Use official charts | Community-maintained, tested, minimal custom code |
| DuckDB embedded | No standalone server | DuckDB not designed as server; Cube SQL API provides access |
| emptyDir storage | Bypass PVC issues | Docker Desktop hostpath unreliable; acceptable for demo |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    FLOE-RUNTIME: KUBERNETES DEPLOYMENT                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        INFRASTRUCTURE LAYER                              │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  MinIO (S3)              Polaris (Catalog)        PostgreSQL            │    │
│  │  ├─► Iceberg data        ├─► Table metadata       ├─► Dagster state    │    │
│  │  │   (Parquet files)     │   (schemas, snapshots) │   (runs, logs)      │    │
│  │  │                       │                        │                      │    │
│  │  └─► Cube pre-aggs       └─► OAuth2 tokens        └─► Marquez lineage  │    │
│  │      (Cube Store)            for DuckDB                                 │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        ORCHESTRATION LAYER                               │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  Dagster Webserver        Dagster Daemon          Dagster Worker        │    │
│  │  ├─► UI/API               ├─► Scheduler           ├─► Job execution    │    │
│  │  │                        │   (5-min schedule)    │                      │    │
│  │  │                        │                       └─► dbt + DuckDB      │    │
│  │  │                        │                            (embedded)        │    │
│  │  │                        │                            └─► Polaris      │    │
│  │  │                        │                                └─► MinIO    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        SEMANTIC LAYER (Cube)                             │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  Cube API                 Cube Refresh Worker     Cube Store            │    │
│  │  ├─► REST/GraphQL/SQL     ├─► Pre-agg builder     ├─► Pre-agg storage  │    │
│  │  │                        │                        │   (router+workers) │    │
│  │  └─► DuckDB (built-in) ←──┴─► DuckDB (built-in)   └─► MinIO S3 bucket  │    │
│  │       └─► Polaris REST catalog for Iceberg queries                      │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        OBSERVABILITY LAYER                               │    │
│  ├─────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                          │    │
│  │  Jaeger                   Marquez                                        │    │
│  │  ├─► Traces (OTel)        ├─► Lineage (OpenLineage)                     │    │
│  │  │   - Dagster spans      │   - Asset dependencies                      │    │
│  │  │   - dbt spans          │   - dbt model lineage                       │    │
│  │  │   - Cube spans         │                                              │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Decisions

| Question | Decision |
|----------|----------|
| Compute Engine | **DuckDB** - embedded in Cube and Dagster workers |
| Pre-aggregations | **Cube Store (dedicated)** - production-like |
| Data Generation | **All 3**: Initial seed + 5-min schedule + manual trigger |
| Deployment Approach | **Modular charts** with Make targets, not umbrella |
| Storage for Local | **emptyDir** - no PVC issues on Docker Desktop |
| Standalone DuckDB Server | **No** - Cube SQL API (port 15432) provides enterprise ad-hoc access |
| DuckDB-Iceberg Connection | **Polaris REST catalog** - DuckDB uses `ATTACH` with OAuth2 secrets |
| Infrastructure Helm Strategy | **Subchart dependencies** - Use official charts (Bitnami, MinIO, Jaeger) |
| Initial Data Seeding | **Dagster sensor** - Detect empty tables, trigger seed job automatically |
| Polaris Initialization | **Helm hook Job** - `post-install` hook creates catalog, namespace, OAuth2 creds |

## Port-Forward Commands

```bash
# Dagster UI
kubectl port-forward svc/floe-dagster-webserver 3000:80 -n floe

# Cube REST/GraphQL API
kubectl port-forward svc/floe-cube 4000:4000 -n floe

# Cube SQL API (for BI tools: Tableau, Looker, Metabase, psycopg2)
kubectl port-forward svc/floe-cube-sql 15432:15432 -n floe

# Jaeger UI
kubectl port-forward svc/floe-jaeger 16686:16686 -n floe

# Marquez UI
kubectl port-forward svc/floe-marquez 5001:5000 -n floe

# MinIO Console
kubectl port-forward svc/floe-minio-console 9001:9001 -n floe
```

## Implementation Phases

### Phase 1: Infrastructure Chart
1. Create `charts/floe-infrastructure/` structure
2. Add PostgreSQL, MinIO, Polaris, Jaeger as subchart dependencies
3. Create `values-local.yaml` with Docker Desktop optimizations (emptyDir, minimal resources)
4. Add Polaris init hook Job
5. Test: `helm install` + verify pods running

### Phase 2: Update Dagster Chart for DuckDB
1. Create `charts/floe-dagster/values-local.yaml`
2. Configure dbt-duckdb profile in demo/profiles.yml
3. Add Polaris connection config (OAuth2 secrets)
4. Test: Dagster UI accessible

### Phase 3: Update Cube Chart for DuckDB
1. Create `charts/floe-cube/values-local.yaml`
2. Configure DuckDB data source with Polaris endpoint
3. Configure Cube Store for pre-aggregations
4. Enable SQL API on port 15432
5. Test: Cube API responds, can query Iceberg

### Phase 4: Demo Pipeline
1. Add Dagster sensor for empty table detection → seed job trigger
2. Configure 5-minute generation schedule
3. Test: Full data flow from generation to Cube API

### Phase 5: Deployment Automation
1. Add Makefile targets: `deploy-local-full`, `undeploy-local`
2. Add health check waiting between chart deployments
3. Document troubleshooting in quickstart.md

## Risks and Resolution Strategy

| Risk | Resolution Approach |
|------|---------------------|
| DuckDB Iceberg extension issues | Test DuckDB ↔ Polaris connection **first** before building other integrations |
| Cube DuckDB + Iceberg integration | Validate Cube can execute queries via DuckDB; work through configuration step-by-step |
| Docker Desktop resource limits | Use minimal resource requests; ensure 4GB+ RAM allocated |
| Polaris Helm chart complexity | Reference existing `helm/polaris/ci/` fixtures for proven patterns |
| PVC provisioning issues | Already solved - use `emptyDir` for all stateful services |

**Philosophy**: Work through issues first. No premature fallbacks - resolve problems at the source.
