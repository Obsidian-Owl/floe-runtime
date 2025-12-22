# Research: Deployment Automation

**Feature**: 007-deployment-automation
**Date**: 2025-12-21
**Status**: Complete

## Overview

This document consolidates research findings for implementing production deployment automation for floe-runtime. All NEEDS CLARIFICATION items from the Technical Context have been resolved.

---

## 1. Dagster Helm Chart Integration

### Decision: Extend Official Dagster Helm Chart via Umbrella Chart

Use the official `dagster/dagster` Helm chart as a dependency in a custom `floe-dagster` umbrella chart.

### Rationale

1. **Maintenance leverage**: Official chart is maintained by Dagster team with regular updates
2. **Tested patterns**: Production-tested configurations for webserver, daemon, workers
3. **PostgreSQL integration**: Built-in support for PostgreSQL subchart or external DB
4. **Extension points**: `extraManifests` field allows adding custom ConfigMaps/Secrets

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Fork official chart | High maintenance burden, divergence risk |
| Custom chart from scratch | Duplicates extensive Dagster configuration work |
| Kustomize overlays | Less portable than Helm, harder for users to customize |

### Implementation Pattern

```yaml
# charts/floe-dagster/Chart.yaml
apiVersion: v2
name: floe-dagster
version: 0.1.0
dependencies:
  - name: dagster
    version: "1.9.x"
    repository: "https://dagster-io.github.io/helm"
```

Key customization points:
- **ConfigMap for CompiledArtifacts**: Mount via `extraManifests` or custom template
- **External Secrets**: Reference via `dagster.global.postgresqlSecretName` pattern
- **Custom workspace**: Override `dagster.workspace` to point to floe-runtime definitions
- **Resource limits**: Provide production defaults in `values-prod.yaml`

---

## 2. Production Dockerfile Patterns

### Decision: Multi-Stage Build with Python Slim Base

Use multi-stage Dockerfile with `python:3.10-slim` as production base, with separate build stage for dependencies.

### Rationale

1. **Image size**: Slim base is ~150MB vs ~1GB for full Python image
2. **Security**: Fewer packages = smaller attack surface
3. **Build caching**: Separate dependency installation from code copy
4. **Multi-arch**: Official Python images support amd64 and arm64

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Alpine base | musl libc compatibility issues with scientific Python packages |
| Distroless | No shell for debugging, limited Python ecosystem support |
| Full Python image | 5-6x larger image size |
| Dagster official image | Doesn't include floe-runtime packages or dbt adapters |

### Implementation Pattern

```dockerfile
# Dockerfile.dagster
# Stage 1: Build dependencies
FROM python:3.10-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Stage 2: Production image
FROM python:3.10-slim AS production
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 dagster

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY packages/ ./packages/
COPY demo/ ./demo/

# Switch to non-root user
USER dagster

# Dagster webserver entrypoint
ENTRYPOINT ["dagster", "webserver", "-h", "0.0.0.0", "-p", "3000"]
```

Security requirements:
- Non-root user (UID 1000)
- No secrets in build layers
- Minimal installed packages
- Read-only root filesystem compatible

---

## 3. GitOps Patterns (ArgoCD/Flux)

### Decision: Support Both ArgoCD and Flux with Examples

Provide working examples for both ArgoCD (Application/ApplicationSet) and Flux (HelmRelease/Kustomization).

### Rationale

1. **User choice**: Both tools have significant adoption
2. **ArgoCD strengths**: UI, RBAC, app-of-apps pattern
3. **Flux strengths**: Native Kubernetes, better multi-tenancy
4. **Low effort**: Examples are documentation, not runtime code

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| ArgoCD only | Excludes Flux users |
| Flux only | Excludes ArgoCD users (more common) |
| Neither | Reduces deployment automation value |

### Implementation Patterns

**ArgoCD Application**:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: floe-runtime-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/floe-deploy
    targetRevision: HEAD
    path: environments/dev
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: floe-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Flux HelmRelease**:
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: floe-runtime
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: ./charts/floe-dagster
      sourceRef:
        kind: GitRepository
        name: floe-deploy
  values:
    # Environment-specific values
  valuesFrom:
    - kind: Secret
      name: floe-secrets
```

### Environment Promotion Pattern

```
environments/
├── dev/
│   ├── values.yaml          # Dev-specific values
│   └── kustomization.yaml   # Optional overlays
├── staging/
│   ├── values.yaml
│   └── kustomization.yaml
└── prod/
    ├── values.yaml
    └── kustomization.yaml
```

Promotion flow: Update image tag in dev → PR to staging → PR to prod

---

## 4. Secrets Management Integration

### Decision: Document External Secrets Operator as Primary, with Sealed Secrets and SOPS Alternatives

Provide working examples for all three approaches with pros/cons.

### Rationale

1. **External Secrets Operator**: Most flexible, supports AWS/GCP/Azure/Vault
2. **Sealed Secrets**: Simple, GitOps-native, no external dependencies
3. **SOPS**: Works with ArgoCD/Flux, encrypts at rest
4. **User choice**: Different organizations have different infrastructure

### Comparison Matrix

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| External Secrets Operator | Multi-cloud, centralized secrets | Requires operator deployment | Cloud-native orgs |
| Sealed Secrets | Simple, GitOps-native | Cluster-specific encryption | Simple setups |
| SOPS | Works with existing KMS | Requires key management | AWS/GCP KMS users |

### Implementation Pattern (External Secrets)

```yaml
# charts/floe-dagster/templates/externalsecret.yaml
{{- if .Values.externalSecrets.enabled }}
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: {{ .Release.Name }}-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: {{ .Values.externalSecrets.secretStoreName }}
  target:
    name: {{ .Release.Name }}-secrets
  data:
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: {{ .Values.externalSecrets.postgresKey }}
    - secretKey: POLARIS_CLIENT_SECRET
      remoteRef:
        key: {{ .Values.externalSecrets.polarisKey }}
{{- end }}
```

---

## 5. Preflight Validation Command

### Decision: Click-based CLI with Structured Output and Rich Formatting

Implement `floe preflight` as a Click command with JSON and human-readable output modes.

### Rationale

1. **Click integration**: Consistent with existing floe-cli commands
2. **Rich output**: Table formatting for human readability
3. **JSON mode**: Machine-parseable for CI/CD integration
4. **Pydantic validation**: Type-safe configuration handling

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Separate binary | Inconsistent with floe-cli |
| Python script | No CLI ergonomics |
| Helm hook | Can't run before Helm install |

### Implementation Pattern

```python
# packages/floe-cli/src/floe_cli/commands/preflight.py
from __future__ import annotations

import click
from pydantic import BaseModel, SecretStr
from rich.console import Console
from rich.table import Table

class PreflightResult(BaseModel):
    """Result of a preflight check."""
    service: str
    status: str  # "ok", "warning", "error"
    message: str
    remediation: str | None = None

class PreflightConfig(BaseModel):
    """Configuration for preflight checks."""
    compute_type: str  # trino, snowflake, bigquery, duckdb
    compute_host: str | None = None
    storage_bucket: str | None = None
    catalog_uri: str | None = None
    postgres_host: str | None = None

@click.command("preflight")
@click.option("--check-compute", is_flag=True, help="Validate compute engine")
@click.option("--check-storage", is_flag=True, help="Validate object storage")
@click.option("--check-catalog", is_flag=True, help="Validate Iceberg catalog")
@click.option("--check-postgres", is_flag=True, help="Validate PostgreSQL")
@click.option("--all", "check_all", is_flag=True, help="Run all checks")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def preflight_command(
    check_compute: bool,
    check_storage: bool,
    check_catalog: bool,
    check_postgres: bool,
    check_all: bool,
    json_output: bool,
) -> None:
    """Validate infrastructure connectivity before deployment."""
    # Implementation
```

### Check Implementations

| Check | Method | Success Criteria |
|-------|--------|------------------|
| Compute (Trino) | JDBC connection | `SELECT 1` returns |
| Compute (Snowflake) | snowflake-connector | `SELECT 1` returns |
| Storage (S3) | boto3 head_bucket | Bucket exists and accessible |
| Catalog (Polaris) | REST API /v1/config | OAuth2 token obtained |
| PostgreSQL | psycopg2 | Connection established |

### Error Messages

Format: `[SERVICE] [STATUS]: [MESSAGE]. Remediation: [SUGGESTION]`

Example:
```
[CATALOG] ERROR: OAuth2 authentication failed (401 Unauthorized).
Remediation: Verify POLARIS_CLIENT_ID and POLARIS_CLIENT_SECRET environment variables.
```

---

## 6. Demo Mode Configuration

### Decision: Helm Values Flag with Dagster Schedule

Enable demo mode via `values-demo.yaml` with configurable synthetic data schedule.

### Rationale

1. **Simple enablement**: Single values file to enable demo mode
2. **Dagster-native**: Uses Dagster schedules (5-minute default)
3. **Configurable**: Rate and volume adjustable via values

### Implementation Pattern

```yaml
# charts/floe-dagster/values-demo.yaml
demo:
  enabled: true
  schedule:
    interval: "*/5 * * * *"  # Every 5 minutes
    batchSize: 100           # Orders per batch
  dataQuality:
    nullRate: 0.02           # 2% null values
    duplicateRate: 0.01      # 1% duplicates
    lateArrivalRate: 0.05    # 5% late-arriving data
```

### Dagster Schedule Asset

```python
@asset
def demo_orders(
    context: AssetExecutionContext,
    generator: EcommerceGenerator,
    loader: IcebergLoader,
) -> None:
    """Generate demo orders on schedule."""
    batch = generator.generate_orders(batch_size=100)
    loader.append(table="orders", data=batch)
    context.log.info(f"Generated {len(batch)} demo orders")

demo_schedule = ScheduleDefinition(
    job=define_asset_job("demo_generation", selection=[demo_orders]),
    cron_schedule="*/5 * * * *",
)
```

---

## 7. E2E Test Strategy

### Decision: pytest with Docker Compose Demo Profile

Run E2E tests using pytest against Docker Compose demo profile with full stack.

### Rationale

1. **Existing infrastructure**: Extends testing/docker/ setup
2. **pytest integration**: Consistent with other tests
3. **Traceability**: Uses @pytest.mark.requirement markers

### Implementation Pattern

```python
# testing/e2e/test_demo_flow.py
import pytest
from floe_cube import CubeRESTClient

@pytest.mark.requirement("007-FR-029")
class TestDemoDataFlow:
    """E2E tests for demo data flow."""

    def test_synthetic_data_appears_in_cube(
        self,
        cube_client: CubeRESTClient,
        trigger_demo_generation: None,
    ) -> None:
        """Verify synthetic data flows from generation to Cube API."""
        # Wait for data to flow through
        initial_count = cube_client.query("Orders", measures=["count"])

        # Trigger generation
        # Wait for processing

        final_count = cube_client.query("Orders", measures=["count"])
        assert final_count > initial_count, "Data should increase after generation"
```

---

## 8. Documentation Structure

### Decision: Update Existing Docs + New Provisioning Guide

Update `docs/06-deployment-view.md` and create `docs/07-infrastructure-provisioning.md`.

### Rationale

1. **Existing structure**: arc42 documentation already established
2. **Clear separation**: Deployment (what floe deploys) vs. Provisioning (external services)
3. **User journey**: Provisioning first, then deployment

### Documentation Outline

**06-deployment-view.md (Updated)**:
1. Overview (metadata-driven architecture)
2. Prerequisites (external services required)
3. Local Development (Docker Compose)
4. Kubernetes Deployment (Helm charts)
5. GitOps Integration (ArgoCD/Flux)
6. Demo Mode (E2E showcase)
7. Pre-deployment Validation (`floe preflight`)

**07-infrastructure-provisioning.md (New)**:
1. Overview (what to provision)
2. Object Storage (S3/GCS/ADLS)
3. Iceberg Catalog (Polaris)
4. Compute Engines (Trino/Snowflake/BigQuery)
5. PostgreSQL (Dagster metadata)
6. Observability (OTel Collector, Marquez)

---

## Summary of Decisions

| Topic | Decision | Key Benefit |
|-------|----------|-------------|
| Helm Charts | Extend official Dagster chart | Maintenance leverage |
| Dockerfiles | Multi-stage with python:3.10-slim | Small, secure images |
| GitOps | Support ArgoCD + Flux | User choice |
| Secrets | External Secrets primary | Cloud-native, flexible |
| Preflight | Click CLI with Rich output | Consistent, readable |
| Demo Mode | Helm values + Dagster schedule | Simple enablement |
| E2E Tests | pytest + Docker Compose | Existing infrastructure |
| Docs | Update + new provisioning guide | Clear separation |
