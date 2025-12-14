# 09. Control Plane Integration

This document describes how floe-runtime integrates with the optional Floe SaaS Control Plane.

---

## 1. Integration Overview

floe-runtime is designed to work **standalone** without any external dependencies. The Control Plane integration is **optional** and provides enhanced capabilities for teams and enterprises.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTEGRATION MODES                                     │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MODE 1: STANDALONE (Default)                                         │  │
│  │                                                                        │  │
│  │  User ──► floe-cli ──► CompiledArtifacts ──► Runtime                  │  │
│  │                                                                        │  │
│  │  • No Control Plane required                                          │  │
│  │  • User manages infrastructure                                        │  │
│  │  • Full open-source experience                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  MODE 2: MANAGED (SaaS Integration)                                   │  │
│  │                                                                        │  │
│  │  User ──► Git push ──► Control Plane ──► CompiledArtifacts           │  │
│  │                              │                                         │  │
│  │                              ├──► Provision namespace                  │  │
│  │                              ├──► Deploy Runtime                       │  │
│  │                              └──► Configure observability              │  │
│  │                                                                        │  │
│  │  • Control Plane manages lifecycle                                    │  │
│  │  • Automated deployments                                              │  │
│  │  • Enhanced observability                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CompiledArtifacts Contract

The `CompiledArtifacts` JSON structure is the **interface contract** between Control Plane and Runtime.

### 2.1 Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CompiledArtifacts",
  "type": "object",
  "required": ["version", "metadata", "compute", "transforms", "observability"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Schema version for compatibility checking",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "metadata": {
      "$ref": "#/definitions/ArtifactMetadata"
    },
    "compute": {
      "$ref": "#/definitions/ComputeConfig"
    },
    "transforms": {
      "type": "array",
      "items": { "$ref": "#/definitions/TransformConfig" }
    },
    "observability": {
      "$ref": "#/definitions/ObservabilityConfig"
    },
    "dbt_manifest_path": {
      "type": "string",
      "description": "Path to compiled dbt manifest.json"
    },
    "dbt_project_path": {
      "type": "string",
      "description": "Path to dbt project directory"
    },
    "dbt_profiles_path": {
      "type": "string",
      "description": "Path to generated profiles.yml"
    }
  }
}
```

### 2.2 Full Example

```json
{
  "version": "1.0.0",
  "metadata": {
    "compiled_at": "2024-12-10T10:30:00Z",
    "floe_core_version": "0.1.0",
    "source_hash": "abc123def456"
  },
  "environment_context": {
    "tenant_id": "tenant-uuid-123",
    "tenant_slug": "acme-corp",
    "project_id": "project-uuid-456",
    "project_slug": "my-project",
    "environment_id": "env-uuid-789",
    "environment_type": "preview",
    "governance_category": "non_production"
  },
  "compute": {
    "target": "snowflake",
    "connection_secret_ref": "floe-secrets/snowflake-credentials",
    "properties": {
      "warehouse": "COMPUTE_WH",
      "database": "ANALYTICS",
      "schema": "PUBLIC"
    }
  },
  "transforms": [
    {
      "type": "dbt",
      "path": "models/",
      "target": "prod"
    }
  ],
  "observability": {
    "traces": true,
    "metrics": true,
    "lineage": true,
    "otlp_endpoint": "http://otel-collector.floe-system:4317",
    "lineage_endpoint": "http://marquez.floe-system:5000",
    "attributes": {
      "floe.tenant.id": "tenant-uuid-123",
      "floe.project.id": "project-uuid-456",
      "floe.environment.id": "env-uuid-789",
      "floe.environment.type": "preview"
    }
  },
  "dbt_manifest_path": "/app/target/manifest.json",
  "dbt_project_path": "/app",
  "dbt_profiles_path": "/app/.floe"
}
```

### 2.3 Version Compatibility

| Artifacts Version | Runtime Version | Compatibility |
|-------------------|-----------------|---------------|
| 1.0.x | 0.1.x+ | Full |
| 1.1.x | 0.2.x+ | Full |
| 2.0.x | 1.0.x+ | Breaking changes |

**Compatibility Rules:**
- Minor version bumps: New optional fields only
- Major version bumps: May have breaking changes
- Runtime checks artifacts version on load

---

## 3. Integration Patterns

### 3.1 Pull Mode

Runtime periodically polls Control Plane for updated artifacts.

```
┌─────────────────┐                    ┌─────────────────┐
│    Runtime      │                    │  Control Plane  │
│                 │                    │                 │
│  ┌───────────┐  │     GET /api/v1    │  ┌───────────┐  │
│  │  Loader   │──┼───────────────────►│  │ Artifacts │  │
│  │           │  │   /environments/   │  │    API    │  │
│  │           │◄─┼───────────────────│  │           │  │
│  └───────────┘  │   {artifacts}      │  └───────────┘  │
│                 │                    │                 │
│  Poll every     │                    │                 │
│  30 seconds     │                    │                 │
└─────────────────┘                    └─────────────────┘
```

**Implementation:**

```python
# floe_dagster/loader.py
import httpx
import time
from pathlib import Path
from floe_core import CompiledArtifacts

class ArtifactsLoader:
    """Load artifacts from Control Plane API."""

    def __init__(
        self,
        api_url: str,
        environment_id: str,
        api_key: str,
        poll_interval: int = 30,
    ):
        self.api_url = api_url
        self.environment_id = environment_id
        self.api_key = api_key
        self.poll_interval = poll_interval
        self._cached_artifacts: CompiledArtifacts | None = None
        self._cached_hash: str | None = None

    def load(self) -> CompiledArtifacts:
        """Load artifacts, using cache if unchanged."""
        response = httpx.get(
            f"{self.api_url}/api/v1/environments/{self.environment_id}/artifacts",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response.raise_for_status()

        data = response.json()
        source_hash = data["metadata"]["source_hash"]

        if source_hash != self._cached_hash:
            self._cached_artifacts = CompiledArtifacts.model_validate(data)
            self._cached_hash = source_hash

        return self._cached_artifacts

    def watch(self, callback: callable):
        """Watch for artifact changes and call callback."""
        while True:
            try:
                artifacts = self.load()
                if artifacts != self._cached_artifacts:
                    callback(artifacts)
            except Exception as e:
                logger.error(f"Failed to load artifacts: {e}")

            time.sleep(self.poll_interval)
```

### 3.2 Push Mode

Control Plane triggers runtime deployments via Kubernetes API.

```
┌─────────────────┐                    ┌─────────────────┐
│  Control Plane  │                    │   Kubernetes    │
│                 │                    │                 │
│  ┌───────────┐  │  kubectl apply     │  ┌───────────┐  │
│  │Provisioner│──┼───────────────────►│  │ Namespace │  │
│  │           │  │                    │  │           │  │
│  │           │──┼───────────────────►│  │ ConfigMap │  │
│  │           │  │  (artifacts.json)  │  │           │  │
│  │           │──┼───────────────────►│  │Deployment │  │
│  └───────────┘  │  helm upgrade      │  └───────────┘  │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘
```

**Helm Values Injection:**

```yaml
# values.yaml generated by Control Plane
floe:
  artifacts:
    # Embedded or ConfigMap reference
    source: configmap
    configMapName: floe-artifacts

  compute:
    target: snowflake
    secretRef: tenant-123-snowflake-creds

  observability:
    otlpEndpoint: http://otel-collector.floe-system:4317
    attributes:
      floe.tenant.id: tenant-123
      floe.project.id: project-456
```

### 3.3 Hybrid Mode

Local development with Control Plane artifacts.

```
┌─────────────────┐                    ┌─────────────────┐
│  Local Machine  │                    │  Control Plane  │
│                 │                    │                 │
│  ┌───────────┐  │    floe pull       │  ┌───────────┐  │
│  │ floe-cli  │──┼───────────────────►│  │ Artifacts │  │
│  │           │◄─┼───────────────────│  │    API    │  │
│  └───────────┘  │  {artifacts.json}  │  └───────────┘  │
│       │         │                    │                 │
│       ▼         │                    │                 │
│  .floe/         │                    │                 │
│  artifacts.json │                    │                 │
│       │         │                    │                 │
│       ▼         │                    │                 │
│  floe run       │                    │                 │
└─────────────────┘                    └─────────────────┘
```

**CLI Command:**

```bash
# Pull artifacts from Control Plane
floe pull --env preview

# Run with pulled artifacts
floe run
```

---

## 4. Authentication

### 4.1 API Key Authentication

```python
# Environment variable
FLOE_API_KEY=floe_ak_xxx

# Or in configuration
# floe.yaml
control_plane:
  api_url: https://api.floe.dev
  api_key_env: FLOE_API_KEY  # Reference to env var
```

### 4.2 Service Account (Kubernetes)

```yaml
# ServiceAccount with Control Plane annotation
apiVersion: v1
kind: ServiceAccount
metadata:
  name: floe-runtime
  annotations:
    floe.dev/tenant-id: tenant-123
    floe.dev/api-key-secret: floe-api-key
---
apiVersion: v1
kind: Secret
metadata:
  name: floe-api-key
type: Opaque
stringData:
  api-key: floe_ak_xxx
```

### 4.3 OAuth2 / OIDC

```python
# For enterprise deployments with SSO
from authlib.integrations.httpx_client import OAuth2Client

class OIDCAuthenticatedClient:
    def __init__(self, client_id: str, client_secret: str, token_url: str):
        self.client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=token_url,
        )

    def get_artifacts(self, environment_id: str) -> CompiledArtifacts:
        token = self.client.fetch_token()
        response = httpx.get(
            f"{API_URL}/environments/{environment_id}/artifacts",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        return CompiledArtifacts.model_validate(response.json())
```

---

## 5. Observability Integration

### 5.1 Tenant Context Propagation

All telemetry from runtime includes tenant context:

```python
# floe_dagster/telemetry.py
from opentelemetry import trace, baggage
from opentelemetry.context import Context

def create_tenant_context(artifacts: CompiledArtifacts) -> Context:
    """Create context with tenant baggage."""
    ctx = Context()

    for key, value in artifacts.observability.attributes.items():
        ctx = baggage.set_baggage(key, value, context=ctx)

    return ctx

def add_tenant_attributes(span: trace.Span, artifacts: CompiledArtifacts):
    """Add tenant attributes to span."""
    for key, value in artifacts.observability.attributes.items():
        span.set_attribute(key, value)
```

### 5.2 Centralized Observability

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Runtime A     │      │   Runtime B     │      │   Runtime C     │
│  (tenant-123)   │      │  (tenant-456)   │      │  (tenant-123)   │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    OTel Collector       │
                    │    (floe-system)        │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       ┌───────────┐     ┌───────────┐     ┌───────────┐
       │   Tempo   │     │  Marquez  │     │   Mimir   │
       │  (traces) │     │ (lineage) │     │ (metrics) │
       └───────────┘     └───────────┘     └───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    Control Plane        │
                    │    (Aggregation UI)     │
                    └─────────────────────────┘
```

### 5.3 Lineage Namespace Strategy

```
Namespace format: floe.{tenant_id}.{project_slug}

Examples:
  floe.tenant-123.customer-analytics
  floe.tenant-456.revenue-pipeline
```

This enables:
- Tenant-isolated lineage views
- Cross-project lineage within tenant
- No cross-tenant data leakage

---

## 6. What Control Plane Provides

### 6.1 Feature Comparison

| Feature | Standalone | With Control Plane |
|---------|------------|-------------------|
| Pipeline execution | ✅ | ✅ |
| dbt transformations | ✅ | ✅ |
| Dagster orchestration | ✅ | ✅ |
| Local development | ✅ | ✅ |
| Manual K8s deployment | ✅ | ✅ |
| Git-push-to-deploy | ❌ | ✅ |
| Environment lifecycle | Manual | ✅ Automated |
| Preview environments | Manual | ✅ Automated |
| Synthetic test data | ❌ | ✅ |
| Managed observability | Self-hosted | ✅ Grafana Cloud |
| Cross-tenant isolation | N/A | ✅ |
| Team collaboration | ❌ | ✅ |
| Web UI | ❌ | ✅ |
| Audit logs | ❌ | ✅ |
| Billing | ❌ | ✅ |

### 6.2 Synthetic Data Service

The Control Plane provides a **Synthetic Data Service** that:

1. **Trains models** on production data (scheduled jobs)
2. **Generates synthetic data** preserving statistical properties
3. **Pre-populates** non-production environments
4. **Validates privacy** (k-anonymity, re-identification risk)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTROL PLANE: SYNTHETIC DATA FLOW                        │
│                                                                              │
│   Production Data                                                            │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────┐                                                       │
│   │  SDV Training   │ ◄─── Scheduled job (nightly)                          │
│   │  (GaussianCopula│                                                       │
│   │   or CTGAN)     │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐     ┌─────────────────┐                               │
│   │  Trained Model  │────►│  Generate Data  │◄─── On environment creation   │
│   │  (per table)    │     │                 │                               │
│   └─────────────────┘     └────────┬────────┘                               │
│                                    │                                         │
│                                    ▼                                         │
│                           ┌─────────────────┐                               │
│                           │  Pre-populate   │                               │
│                           │  Iceberg Tables │                               │
│                           └────────┬────────┘                               │
│                                    │                                         │
│                                    ▼                                         │
│                           Runtime starts with                                │
│                           realistic test data                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Runtime's Role:** Execute pipelines on whatever data exists. The runtime doesn't know or care whether data is real, synthetic, or test fixtures.

---

## 7. Migration Path

### 7.1 Standalone → Managed

```bash
# 1. Install floe CLI
pip install floe-cli

# 2. Login to Control Plane
floe login

# 3. Connect existing project
floe connect --project my-pipeline

# 4. Push to trigger deployment
git push origin main

# Control Plane now manages deployments
```

### 7.2 Managed → Standalone

```bash
# 1. Export artifacts
floe pull --env production --output artifacts.json

# 2. Deploy manually
kubectl create configmap floe-artifacts --from-file=artifacts.json
helm install floe-runtime floe/floe-runtime -f my-values.yaml

# Runtime works independently
```

---

## 8. API Reference

### 8.1 Artifacts API

```
GET /api/v1/environments/{environment_id}/artifacts
Authorization: Bearer {api_key}

Response:
{
  "version": "1.0.0",
  "metadata": { ... },
  "compute": { ... },
  "transforms": [ ... ],
  "observability": { ... }
}
```

### 8.2 Health Check

```
GET /api/v1/health

Response:
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### 8.3 Webhook Events

Control Plane can send webhooks on:

| Event | Payload |
|-------|---------|
| `environment.created` | Environment details |
| `environment.updated` | Updated artifacts |
| `environment.deleted` | Environment ID |
| `run.started` | Run metadata |
| `run.completed` | Run results |
| `run.failed` | Error details |
