# Implementation Plan: Deployment Automation

**Branch**: `007-deployment-automation` | **Date**: 2025-12-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-deployment-automation/spec.md`

## Summary

Implement production deployment automation for floe-runtime including:
- Production Dockerfiles for Dagster and Cube components
- Helm charts extending official Dagster chart with floe-specific customizations
- GitOps examples (ArgoCD/Flux) with secrets management integration
- Pre-deployment validation CLI (`floe preflight`)
- E2E demo infrastructure with continuous synthetic data generation, full medallion dbt models, and observability (Marquez lineage + Jaeger traces)

The deployment follows a metadata-driven architecture where floe-runtime generates configuration (CompiledArtifacts) that Dagster/dbt consume, connecting to externally-provisioned compute engines, storage, and catalog services.

## Technical Context

**Language/Version**: Python 3.10+ (Dagster/dbt minimum), Helm 3.x, Docker
**Primary Dependencies**: Dagster 1.6+, dbt-core 1.7+, Cube v0.36+, Helm, Docker, ArgoCD/Flux
**Storage**: Iceberg tables (via Polaris REST catalog), PostgreSQL (Dagster metadata), S3/GCS/ADLS (object storage)
**Testing**: pytest (Python), helm lint/template (Helm), Docker Compose (integration), E2E validation suite
**Target Platform**: Kubernetes (EKS/GKE/AKS primary, Docker Desktop/kind for local dev)
**Project Type**: Infrastructure/DevOps - Dockerfiles, Helm charts, GitOps manifests, CLI command
**Performance Goals**: Deploy in <30 minutes, GitOps sync <5 minutes, preflight checks <30 seconds
**Constraints**: Zero credentials in Git, standalone-first (no SaaS dependencies), air-gapped support
**Scale/Scope**: Single-tenant deployments, 3 environments (dev/staging/prod), 24+ hour continuous demo operation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Standalone-First ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| No SaaS endpoints hardcoded | ✅ | All external services (Polaris, Trino, S3) configured via environment variables |
| Standard open formats only | ✅ | Iceberg, OpenLineage, OpenTelemetry, Polaris REST API |
| Examples run without SaaS | ✅ | Docker Compose demo uses LocalStack, self-hosted Polaris |
| SaaS fields optional | ✅ | CompiledArtifacts already has optional SaaS enrichment fields |

### Principle II: Type Safety Everywhere ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Pydantic for configuration | ✅ | PreflightConfig, DemoConfig will use Pydantic models |
| mypy --strict compliance | ✅ | All new Python code (preflight command) will pass strict mode |
| SecretStr for credentials | ✅ | All credential handling uses SecretStr |

### Principle III: Technology Ownership ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| dbt owns SQL | ✅ | Demo dbt project owns all transformations (staging/intermediate/marts) |
| Dagster owns orchestration | ✅ | Schedules, sensors, assets defined in Dagster |
| Cube owns semantic layer | ✅ | Cube defines metrics, dimensions, pre-aggregations |
| Polaris owns catalog | ✅ | All catalog operations via Polaris REST API |

### Principle IV: Contract-Driven Integration ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CompiledArtifacts as sole contract | ✅ | Helm charts mount CompiledArtifacts.json as ConfigMap |
| No direct FloeSpec passing | ✅ | Only CompiledArtifacts flows to runtime packages |
| JSON Schema exported | ✅ | CompiledArtifacts exports schema for validation |

### Principle V: Security First ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| No dangerous constructs | ✅ | No eval/exec in preflight command |
| Input validation with Pydantic | ✅ | All CLI inputs validated |
| Secrets via SecretStr | ✅ | All credentials handled securely |
| Zero credentials in Git | ✅ | External Secrets/Sealed Secrets/SOPS patterns |

### Principle VI: Quality Standards ✅ PASS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| 100% requirement traceability | ✅ | All FR-XXX will have corresponding tests |
| pytest.mark.requirement markers | ✅ | E2E tests will use 007-FR-XXX markers |
| Black/isort/ruff compliance | ✅ | All new code formatted |
| Google-style docstrings | ✅ | All public APIs documented |

**Constitution Gate: PASSED** - No violations detected. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-deployment-automation/
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Data model documentation
├── quickstart.md        # Phase 1: Quick start guide
├── contracts/           # Phase 1: API contracts (OpenAPI)
│   └── preflight-api.yaml
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
# Production Dockerfiles
docker/
├── Dockerfile.dagster           # Multi-stage Dagster (webserver, daemon, worker)
├── Dockerfile.cube              # Cube API + refresh worker
└── docker-compose.demo.yml      # Demo profile with continuous generation

# Helm Charts
charts/
├── floe-dagster/                # Dagster deployment (extends official chart)
│   ├── Chart.yaml               # Chart metadata, dependencies
│   ├── values.yaml              # Default values
│   ├── values-dev.yaml          # Development overrides
│   ├── values-prod.yaml         # Production overrides
│   ├── values-demo.yaml         # Demo mode with synthetic generation
│   └── templates/
│       ├── configmap.yaml       # CompiledArtifacts mount
│       ├── externalsecret.yaml  # External Secrets integration
│       └── ingress.yaml         # Optional ingress
├── floe-cube/                   # Cube semantic layer
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── floe-runtime/                # Umbrella chart
    ├── Chart.yaml
    └── values.yaml

# GitOps Examples
examples/
├── gitops/
│   ├── argocd/
│   │   ├── application.yaml
│   │   └── applicationset.yaml
│   └── flux/
│       ├── helmrelease.yaml
│       └── kustomization.yaml
├── secrets/
│   ├── external-secrets/
│   ├── sealed-secrets/
│   └── sops/
└── environments/
    ├── dev/
    ├── staging/
    └── prod/

# CLI Extension (preflight command)
packages/floe-cli/src/floe_cli/commands/
├── preflight.py                 # NEW: floe preflight command
└── __init__.py                  # Updated to register command

# Synthetic Data Enhancement
packages/floe-synthetic/src/floe_synthetic/
├── schemas/
│   └── ecommerce.py             # ENHANCED: Add OrderItem schema
├── generators/
│   └── ecommerce.py             # ENHANCED: Add order_items generation
└── quality/                     # NEW: Data quality injection
    ├── __init__.py
    └── defects.py               # Nulls, duplicates, late-arriving

# Demo dbt Project
demo/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   ├── stg_customers.sql
│   │   ├── stg_orders.sql
│   │   ├── stg_order_items.sql
│   │   └── stg_products.sql
│   ├── intermediate/
│   │   ├── int_order_items_enriched.sql
│   │   ├── int_customer_orders.sql
│   │   └── int_product_performance.sql
│   └── marts/
│       ├── mart_revenue.sql
│       ├── mart_customer_segments.sql
│       └── mart_product_analytics.sql
├── tests/
│   └── data_quality/
└── cube/
    └── schema/
        ├── Orders.js
        ├── Customers.js
        └── Products.js

# E2E Tests
testing/
├── docker/
│   ├── docker-compose.yml       # UPDATED: Add demo profile
│   └── scripts/
│       └── run-demo.sh          # NEW: Demo runner script
└── e2e/
    └── test_demo_flow.py        # NEW: E2E validation tests
```

**Structure Decision**: Infrastructure/DevOps project structure with:
- `docker/` for production container images
- `charts/` for Helm charts (industry standard)
- `examples/` for GitOps and secrets patterns
- `demo/` for complete dbt project showcasing medallion architecture
- CLI extension in existing `packages/floe-cli/`
- E2E tests in existing `testing/` infrastructure

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
