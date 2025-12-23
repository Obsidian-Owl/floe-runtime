# Research: Kubernetes Demo Deployment

**Feature**: 008-kubernetes-demo
**Date**: 2025-12-22
**Status**: Complete

## Overview

This document consolidates research findings for deploying the floe-runtime stack to Kubernetes (Docker Desktop) with DuckDB as the embedded compute engine.

---

## 1. DuckDB + Iceberg Connection via Polaris REST Catalog

### Decision: Polaris REST Catalog with OAuth2

**Rationale:**
- DuckDB's Iceberg extension supports REST catalog endpoints natively
- OAuth2 provides secure, rotatable credentials
- Polaris is already the catalog for this project
- No additional infrastructure required (vs direct S3 access)

**Implementation:**
```sql
-- DuckDB connects to Polaris REST catalog
CREATE SECRET polaris_secret (
    TYPE iceberg,
    CLIENT_ID 'demo_client',
    CLIENT_SECRET '${POLARIS_CLIENT_SECRET}'
);

LOAD httpfs;
ATTACH 'demo_catalog' AS iceberg (
    TYPE iceberg,
    ENDPOINT 'http://polaris:8181/api/catalog',
    SECRET 'polaris_secret'
);

-- Query Iceberg tables
SELECT * FROM iceberg.bronze.customers;
```

**Limitations:**
- DuckDB Iceberg is **read-only** for INSERT (no UPDATE/DELETE)
- Writes go through PyIceberg (already used in floe-iceberg)

**Alternatives Considered:**
- **Direct S3 access**: More complex, requires separate credential management
- **Unity Catalog**: Not applicable (Databricks-specific)

---

## 2. Helm Chart Strategy: Subchart Dependencies

### Decision: Use Official Charts as Dependencies

**Rationale:**
- Community-maintained, battle-tested configurations
- Automatic upstream security patches
- Reduces custom code maintenance
- Standard Helm pattern for infrastructure

**Chart Dependencies:**
```yaml
# charts/floe-infrastructure/Chart.yaml
dependencies:
  - name: postgresql
    version: "15.x.x"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: minio
    version: "5.x.x"
    repository: https://charts.min.io/
    condition: minio.enabled
  - name: jaeger
    version: "3.x.x"
    repository: https://jaegertracing.github.io/helm-charts
    condition: jaeger.enabled
```

**Local Values Override:**
```yaml
# values-local.yaml - Docker Desktop optimized
postgresql:
  primary:
    persistence:
      enabled: false  # Uses emptyDir
    resources:
      requests:
        cpu: 100m
        memory: 256Mi

minio:
  persistence:
    enabled: false  # Uses emptyDir
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
```

**Alternatives Considered:**
- **Custom templates for each service**: Higher maintenance burden
- **Umbrella chart only**: Less flexibility for individual service tuning
- **Kustomize overlays**: Not Helm-native, adds complexity

---

## 3. Data Seeding: Dagster Sensor

### Decision: Sensor-Based Empty Table Detection

**Rationale:**
- Dagster sensors are already used in floe-runtime
- Automatic triggering without manual intervention
- Idempotent (only triggers when tables are empty)
- Follows existing orchestration patterns

**Implementation Pattern:**
```python
@sensor(job=seed_demo_data_job)
def empty_tables_sensor(context):
    """Detect empty Iceberg tables and trigger seed job."""
    from pyiceberg.catalog import load_catalog

    catalog = load_catalog("polaris")
    tables_to_seed = []

    for table_name in ["customers", "products", "orders"]:
        try:
            table = catalog.load_table(f"demo.bronze.{table_name}")
            if table.scan().count() == 0:
                tables_to_seed.append(table_name)
        except NoSuchTableException:
            tables_to_seed.append(table_name)

    if tables_to_seed:
        yield RunRequest(
            run_key=f"seed-{datetime.now().isoformat()}",
            run_config={"tables": tables_to_seed}
        )
```

**Alternatives Considered:**
- **Helm hook Job**: One-time execution, no automatic retry
- **Init container**: Blocks pod startup, less observable
- **Manual trigger only**: Poor user experience

---

## 4. Polaris Initialization: Helm Hook Job

### Decision: Post-Install Hook with Retry

**Rationale:**
- Helm hooks are declarative and version-controlled
- `post-install` ensures PostgreSQL is ready first
- Retries handle transient startup issues
- Clean integration with `helm install` flow

**Implementation:**
```yaml
# templates/polaris-init-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-polaris-init
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "5"
    "helm.sh/hook-delete-policy": before-hook-creation
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: polaris-init
          image: python:3.12-slim
          command:
            - python
            - -c
            - |
              import requests
              import os

              POLARIS_URI = os.environ["POLARIS_URI"]

              # Create demo catalog
              requests.post(f"{POLARIS_URI}/api/management/v1/catalogs", json={
                  "name": "demo_catalog",
                  "type": "INTERNAL",
                  "storageConfigInfo": {
                      "storageType": "S3",
                      "allowedLocations": ["s3://iceberg-data/"]
                  }
              })

              # Create demo namespace
              requests.post(f"{POLARIS_URI}/api/catalog/v1/demo_catalog/namespaces", json={
                  "namespace": ["demo", "bronze"]
              })

              # Create OAuth2 principal
              # ... (simplified for research doc)
```

**Alternatives Considered:**
- **Init container**: Blocks Polaris pod startup
- **Manual setup**: Not reproducible, poor DX
- **ConfigMap with scripts**: Less integrated with Helm lifecycle

---

## 5. Docker Desktop Kubernetes Considerations

### Storage: emptyDir for All Stateful Services

**Problem:** Docker Desktop's hostpath provisioner has issues with dynamic PVC provisioning.

**Solution:** Use `emptyDir` volumes which are ephemeral but reliable:
```yaml
# All stateful services use emptyDir
postgresql:
  primary:
    persistence:
      enabled: false

minio:
  persistence:
    enabled: false

cubestore:
  persistence:
    enabled: false
```

**Trade-offs:**
- Data is ephemeral (lost on pod restart)
- Acceptable for demo environment
- Production would use proper PersistentVolumeClaims

### Resources: Minimal Requests

**Docker Desktop has limited resources. Use minimal requests:**
```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Health Checks: Fast Failure Detection

**Don't wait 5 minutes for failures:**
```yaml
readinessProbe:
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3

livenessProbe:
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

---

## 6. Cube Configuration for DuckDB

### Decision: Built-in DuckDB with Polaris Connection

**Cube has built-in DuckDB support** - no separate compute service needed.

**Environment Variables:**
```yaml
cube:
  env:
    # DuckDB as data source
    CUBEJS_DB_TYPE: duckdb

    # DuckDB Iceberg extension config
    CUBEJS_DB_DUCKDB_S3_ENDPOINT: http://minio:9000
    CUBEJS_DB_DUCKDB_S3_ACCESS_KEY_ID: minioadmin
    CUBEJS_DB_DUCKDB_S3_SECRET_ACCESS_KEY: minioadmin

    # Cube Store for pre-aggregations
    CUBEJS_EXTERNAL_DEFAULT: "true"
    CUBEJS_CUBESTORE_HOST: cubestore-router
    CUBEJS_CUBESTORE_PORT: "10000"
```

### SQL API for BI Tools

**Cube exposes Postgres-compatible SQL on port 15432:**
```python
import psycopg2

conn = psycopg2.connect(
    host="cube.floe.local",
    port=15432,
    user="cube",
    password="cube_password",
    database="cube"
)
cursor = conn.cursor()
cursor.execute("""
    SELECT status, MEASURE(count), MEASURE(total_amount)
    FROM Orders
    WHERE created_at >= '2025-01-01'
    GROUP BY 1
""")
```

---

## 7. Dagster Helm Chart Patterns

### Decision: Custom Wrapper Chart with Dagster Dependency

**Rationale:**
- Extends official Dagster chart without forking
- Values override for configuration
- Custom templates for floe-specific resources

**Structure:**
```
charts/floe-dagster/
├── Chart.yaml       # Depends on dagster/dagster
├── values.yaml      # Default configuration
├── values-local.yaml # Docker Desktop optimized
└── templates/
    ├── configmap-artifacts.yaml  # CompiledArtifacts
    └── _helpers.tpl
```

**Key Configuration:**
```yaml
dagster:
  dagster-user-deployments:
    deployments:
      - name: floe-pipelines
        image:
          repository: ghcr.io/your-org/floe-dagster
          tag: latest
        dagsterApiGrpcArgs:
          - "-m"
          - "demo.orchestration.definitions"
```

---

## 8. Production Dockerfile Patterns

### Decision: Multi-Stage Build with uv

**Pattern:**
```dockerfile
# Stage 1: Build wheels
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
COPY --from=builder /app/.venv /app/.venv
COPY . /app

USER 1000:1000
```

**Key Decisions:**
- **Base image**: `python:3.12-slim` (glibc for pre-built wheels)
- **Package manager**: `uv` (10-100x faster than pip)
- **Security**: Non-root user (UID 1000)
- **Size**: 150-300MB (vs 1.2GB without optimization)

---

## 9. Enterprise Query Access

### Decision: No Standalone DuckDB Server

**DuckDB is NOT designed as a standalone server:**
- Embedded-first (in-process), like SQLite
- No multi-user concurrency
- Single-node only

**Cube provides all enterprise access:**
- REST API (port 4000) - JSON for dashboards
- GraphQL API (port 4000) - Flexible queries
- SQL API (port 15432) - BI tool connections

**When to add Trino:**
- Arbitrary SQL without Cube cubes
- Federated queries across sources
- 100+ concurrent analysts
- Multi-TB ad-hoc scans

---

## Sources

### DuckDB + Iceberg
- [DuckDB Iceberg Extension](https://duckdb.org/docs/extensions/iceberg.html)
- [Polaris REST Catalog Spec](https://github.com/apache/polaris/blob/main/spec/polaris-management-service.yaml)

### Helm Patterns
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Dagster Helm Documentation](https://docs.dagster.io/deployment/oss/deployment-options/kubernetes/deploying-to-kubernetes)
- [Bitnami PostgreSQL Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)

### Cube
- [Cube DuckDB Driver](https://cube.dev/docs/product/configuration/data-sources/duckdb)
- [Cube SQL API](https://cube.dev/docs/product/apis-integrations/sql-api)
- [Cube Store Architecture](https://cube.dev/docs/product/caching/using-pre-aggregations)

### Docker
- [Production Python Docker with uv](https://hynek.me/articles/docker-uv/)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/best-practices/)

### Dagster
- [Dagster Sensors](https://docs.dagster.io/concepts/partitions-schedules-sensors/sensors)
- [Dagster Kubernetes Deployment](https://docs.dagster.io/deployment/oss/deployment-options/kubernetes)
