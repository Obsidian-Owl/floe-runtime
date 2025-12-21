# 06. Deployment View

This document describes deployment options for floe-runtime: local development, Docker, and Kubernetes.

**Important**: floe-runtime is a **metadata-driven framework**. It generates configuration (profiles.yml, CompiledArtifacts) that other tools consume (Dagster, dbt, Cube). Understanding this architecture is critical for successful deployment.

---

## 1. Metadata-Driven Architecture

### What floe-runtime Deploys

floe-runtime deploys an **orchestration layer**, not the data infrastructure itself:

```
DEPLOYED BY FLOE (Your containers/pods):
├── Dagster (webserver, daemon, workers)
├── dbt (inside Dagster workers)
└── Cube (optional semantic layer)

EXTERNAL SERVICES (You provision):
├── Compute Engine (DuckDB, Trino, Snowflake, BigQuery)
├── Object Storage (S3, GCS, ADLS)
├── Catalog (Polaris, Nessie, or cloud-native)
├── PostgreSQL (Dagster metadata)
└── Observability (OTel Collector, Jaeger/Tempo, Marquez)
```

### Configuration Flow

```
floe.yaml (user config)
    │
    ▼
┌─────────────┐
│ floe compile │  ◄── BUILD TIME (CI/CD)
└──────┬──────┘
       │
       ├──► CompiledArtifacts.json (packaged in container)
       │
       └──► profiles.yml (generated at runtime)
                │
                ▼
         ┌─────────────┐
         │ dbt build   │  ◄── RUNTIME (inside Dagster worker)
         └──────┬──────┘
                │
                ▼
         External Compute Engine (DuckDB/Trino/Snowflake)
                │
                ▼
         Iceberg Tables in S3/GCS (via Polaris catalog)
```

---

## 2. Prerequisites

### External Services Required

| Service | Purpose | Options |
|---------|---------|---------|
| **Compute Engine** | SQL execution | DuckDB (default), MotherDuck, Trino, Snowflake, BigQuery |
| **Object Storage** | Iceberg data files | S3, GCS, ADLS |
| **Catalog** | Iceberg metadata | Apache Polaris, Nessie, Snowflake, AWS Glue |
| **PostgreSQL** | Dagster metadata | RDS, Cloud SQL, K8s StatefulSet |
| **OTel Collector** | Observability (optional) | Jaeger, Tempo, Datadog |

### DuckDB as Default Compute

DuckDB is the **default compute engine** for standalone-first deployments:

- **Zero infrastructure**: Embedded in Dagster workers, no external server
- **Production-ready**: Handles datasets up to several TB with sufficient RAM
- **Upgrade path**: Same Iceberg tables work with MotherDuck, Trino, Snowflake

When to upgrade from DuckDB:

| Trigger | Upgrade To |
|---------|------------|
| Dataset > 500GB with limited RAM | MotherDuck or Trino |
| 50+ concurrent analytical users | Trino or Snowflake |
| Strict SLA requirements (99.9%+) | Snowflake/BigQuery |

---

## 3. Deployment Options Overview

| Option | Use Case | Complexity |
|--------|----------|------------|
| **Local (pip)** | Development, single user | Low |
| **Docker Compose** | Development, evaluation, integration testing | Low |
| **Kubernetes (Helm)** | Production, team use | Medium |
| **GitOps (ArgoCD/Flux)** | Production, automated deployment | Medium |

---

## 3. Local Development (pip)

### 3.1 Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install CLI and dependencies
pip install floe-cli

# For specific compute targets
pip install dbt-duckdb      # Local development
pip install dbt-snowflake   # Snowflake
pip install dbt-bigquery    # BigQuery
```

### 3.2 Project Setup

```bash
# Initialize project
floe init my-project
cd my-project

# Validate configuration
floe validate

# Run locally (DuckDB)
floe run --env dev
```

### 3.3 Local Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOCAL MACHINE                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  floe-cli process                                        │    │
│  │                                                          │    │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐               │    │
│  │  │ Dagster │──►│   dbt   │──►│ DuckDB  │               │    │
│  │  │ (in-    │   │  (in-   │   │  (in-   │               │    │
│  │  │ process)│   │ process)│   │ process)│               │    │
│  │  └─────────┘   └─────────┘   └─────────┘               │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────┐   ┌─────────────────┐                      │
│  │ ./warehouse/    │   │ .floe/          │                      │
│  │ └─ data.duckdb  │   │ └─ artifacts.json│                      │
│  └─────────────────┘   └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Limitations

- No persistent Dagster UI (run-and-exit)
- No built-in observability backends
- Single-user, single-machine only

---

## 4. Docker Compose

Docker Compose is used for local development, evaluation, and integration testing.

### 4.1 Quick Start

```bash
cd testing/docker

# Start base services (PostgreSQL, Jaeger)
docker compose up -d

# Start with storage (+ LocalStack S3, Polaris catalog)
docker compose --profile storage up -d

# Start with compute (+ Trino, Spark)
docker compose --profile compute up -d

# Start full stack (+ Cube semantic layer, Marquez lineage)
docker compose --profile full up -d

# Start demo e-commerce pipeline (+ Dagster orchestration)
docker compose --profile demo up -d
```

### 4.2 Available Profiles

| Profile | Services Added | Use Case |
|---------|----------------|----------|
| (none) | PostgreSQL, Jaeger | Unit tests, basic development |
| `storage` | + LocalStack (S3+STS), Polaris | Iceberg storage tests |
| `compute` | + Trino, Spark | Distributed compute tests |
| `full` | + Cube, cube-init, Marquez | Semantic layer tests |
| `demo` | + Dagster webserver/daemon | Demo e-commerce pipeline |
| `test` | test-runner container | Automated integration tests |

### 4.3 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOCKER HOST                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  docker-compose network: floe                                        │    │
│  │                                                                      │    │
│  │  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐         │    │
│  │  │   dagster     │   │   postgres    │   │   marquez     │         │    │
│  │  │   :3000       │──►│   :5432       │◄──│   :5000/:5001 │         │    │
│  │  └───────────────┘   └───────────────┘   └───────────────┘         │    │
│  │         │                                        ▲                  │    │
│  │         │                                        │                  │    │
│  │         ▼                                        │                  │    │
│  │  ┌───────────────┐   ┌───────────────┐          │                  │    │
│  │  │ otel-collector│──►│    jaeger     │──────────┘                  │    │
│  │  │   :4317       │   │   :16686      │                             │    │
│  │  └───────────────┘   └───────────────┘                             │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  volumes                                                             │    │
│  │  ├── postgres_data (persistent)                                     │    │
│  │  ├── ./models (bind mount, live reload)                             │    │
│  │  └── ./.floe/artifacts.json (bind mount)                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 docker-compose.yml Example

```yaml
version: "3.8"

services:
  # PostgreSQL - Dagster metadata + Marquez storage
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: floe
      POSTGRES_PASSWORD: floe
      POSTGRES_DB: dagster
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "floe"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - floe

  # Dagster - Orchestration
  dagster:
    image: ghcr.io/floe-runtime/dagster:latest
    ports:
      - "3000:3000"
    environment:
      DAGSTER_HOME: /opt/dagster/dagster_home
      DAGSTER_POSTGRES_HOST: postgres
      DAGSTER_POSTGRES_USER: floe
      DAGSTER_POSTGRES_PASSWORD: floe
      DAGSTER_POSTGRES_DB: dagster
      FLOE_ARTIFACTS_PATH: /app/artifacts.json
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: floe-dagster
      OPENLINEAGE_URL: http://marquez-api:5000
      OPENLINEAGE_NAMESPACE: floe
    volumes:
      - ./.floe/artifacts.json:/app/artifacts.json:ro
      - ./models:/app/models:ro
      - ./seeds:/app/seeds:ro
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - floe

  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config", "/etc/otel/config.yaml"]
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
    networks:
      - floe

  # Jaeger - Distributed Tracing
  jaeger:
    image: jaegertracing/all-in-one:1.53
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC
    networks:
      - floe

  # Marquez API - Data Lineage
  marquez-api:
    image: marquezproject/marquez:0.47.0
    environment:
      MARQUEZ_PORT: 5000
      MARQUEZ_ADMIN_PORT: 5001
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: marquez
      POSTGRES_USER: floe
      POSTGRES_PASSWORD: floe
    ports:
      - "5000:5000"   # API
      - "5001:5001"   # Admin
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - floe

  # Marquez Web - Lineage UI
  marquez-web:
    image: marquezproject/marquez-web:0.47.0
    environment:
      MARQUEZ_HOST: marquez-api
      MARQUEZ_PORT: 5000
    ports:
      - "3001:3000"
    depends_on:
      - marquez-api
    networks:
      - floe

networks:
  floe:
    driver: bridge

volumes:
  postgres_data:
```

### 4.5 OTel Collector Configuration

```yaml
# otel-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  logging:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger, logging]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [logging]
```

### 4.6 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dagster UI | http://localhost:3000 | Asset management, runs |
| Jaeger UI | http://localhost:16686 | Distributed tracing |
| Marquez Web | http://localhost:3001 | Data lineage |
| Marquez API | http://localhost:5000 | Lineage API |

---

## 5. Kubernetes (Helm)

### 5.1 Available Charts

Currently, floe-runtime provides the `floe-dagster` Helm chart, which uses the official Dagster Helm chart as a dependency.

```
charts/
└── floe-dagster/           # Dagster chart with floe extensions
    ├── Chart.yaml          # Depends on dagster/dagster
    ├── values.yaml         # Default values
    ├── values-dev.yaml     # Development overrides
    ├── values-prod.yaml    # Production overrides
    ├── values-demo.yaml    # Demo e-commerce pipeline
    └── templates/
        ├── configmap.yaml      # CompiledArtifacts mount
        ├── ingress.yaml        # Optional ingress
        ├── external-secret.yaml # External Secrets Operator
        ├── sealed-secret.yaml   # Bitnami Sealed Secrets
        └── secret-sops.yaml     # Mozilla SOPS
```

**Note**: Cube and observability stacks should be deployed separately using their official Helm charts.

### 5.2 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KUBERNETES CLUSTER                                   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Namespace: floe-runtime                                               │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐     │  │
│  │  │ dagster-webserver│  │  dagster-daemon │   │  dagster-worker │     │  │
│  │  │   (Deployment)   │   │  (Deployment)   │   │  (Deployment)   │     │  │
│  │  │   replicas: 2    │   │   replicas: 1   │   │   replicas: 3   │     │  │
│  │  └────────┬─────────┘   └────────┬────────┘   └────────┬────────┘     │  │
│  │           │                      │                     │              │  │
│  │           └──────────────────────┼─────────────────────┘              │  │
│  │                                  │                                    │  │
│  │                                  ▼                                    │  │
│  │                    ┌─────────────────────────┐                        │  │
│  │                    │  PostgreSQL (StatefulSet)│                        │  │
│  │                    │  or external RDS         │                        │  │
│  │                    └─────────────────────────┘                        │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐   ┌─────────────────┐                           │  │
│  │  │  otel-collector │   │     marquez     │                           │  │
│  │  │   (DaemonSet)   │   │  (Deployment)   │                           │  │
│  │  └─────────────────┘   └─────────────────┘                           │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Ingress                                                               │  │
│  │  ├── dagster.example.com → dagster-webserver:3000                     │  │
│  │  ├── traces.example.com → jaeger-query:16686                          │  │
│  │  └── lineage.example.com → marquez-web:3000                           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Installation

```bash
# From local chart
cd charts/floe-dagster
helm dependency update
helm install floe-dagster . \
  --namespace floe-runtime \
  --create-namespace

# With development values
helm install floe-dagster . \
  --namespace floe-runtime \
  --create-namespace \
  -f values-dev.yaml

# With production values
helm install floe-dagster . \
  --namespace floe-runtime \
  --create-namespace \
  -f values-prod.yaml

# With demo e-commerce pipeline
helm install floe-dagster . \
  --namespace floe-demo \
  --create-namespace \
  -f values-demo.yaml
```

### 5.4 values.yaml

```yaml
# values.yaml
global:
  # Compute target for dbt
  compute:
    target: snowflake
    secretRef: snowflake-credentials

  # Observability endpoints
  observability:
    otlpEndpoint: http://otel-collector:4317
    lineageEndpoint: http://marquez:5000

# Dagster configuration
dagster:
  enabled: true
  webserver:
    replicas: 2
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 2000m
        memory: 4Gi

  daemon:
    enabled: true
    resources:
      requests:
        cpu: 250m
        memory: 512Mi

  worker:
    replicas: 3
    resources:
      requests:
        cpu: 1000m
        memory: 2Gi

  # External database (recommended for production)
  postgresql:
    enabled: false
  externalPostgresql:
    host: my-rds-instance.xxx.us-east-1.rds.amazonaws.com
    port: 5432
    database: dagster
    existingSecret: dagster-postgresql
    secretKeys:
      username: username
      password: password

# OTel Collector
otel-collector:
  enabled: true
  mode: daemonset
  config:
    exporters:
      otlp/grafana:
        endpoint: tempo-us-east-1.grafana.net:443
        headers:
          authorization: "Basic ${GRAFANA_API_KEY}"

# Marquez (optional - can use external)
marquez:
  enabled: true
  api:
    replicas: 2
  web:
    enabled: true

# Ingress
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: dagster.example.com
      paths:
        - path: /
          pathType: Prefix
          backend:
            service:
              name: dagster-webserver
              port: 3000
  tls:
    - secretName: dagster-tls
      hosts:
        - dagster.example.com
```

### 5.5 Secrets Management

```yaml
# secrets.yaml (apply separately, store in Vault/SOPS)
apiVersion: v1
kind: Secret
metadata:
  name: snowflake-credentials
  namespace: floe-runtime
type: Opaque
stringData:
  SNOWFLAKE_ACCOUNT: "xxx.us-east-1"
  SNOWFLAKE_USER: "floe_user"
  SNOWFLAKE_PASSWORD: "secret"
  SNOWFLAKE_ROLE: "floe_role"
  SNOWFLAKE_WAREHOUSE: "floe_wh"
  SNOWFLAKE_DATABASE: "floe_db"
---
apiVersion: v1
kind: Secret
metadata:
  name: dagster-postgresql
  namespace: floe-runtime
type: Opaque
stringData:
  username: "dagster"
  password: "secret"
```

### 5.6 Resource Requirements

| Component | Min CPU | Min Memory | Recommended |
|-----------|---------|------------|-------------|
| dagster-webserver | 500m | 1Gi | 2 replicas |
| dagster-daemon | 250m | 512Mi | 1 replica |
| dagster-worker | 1000m | 2Gi | 3+ replicas |
| postgresql | 500m | 1Gi | External RDS |
| otel-collector | 200m | 256Mi | DaemonSet |
| marquez | 500m | 1Gi | 2 replicas |

---

## 6. Production Considerations

### 6.1 High Availability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       HIGH AVAILABILITY SETUP                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Load Balancer                                                       │    │
│  │  └── health checks: /health                                         │    │
│  └────────────────────────────────┬────────────────────────────────────┘    │
│                                   │                                         │
│            ┌──────────────────────┼──────────────────────┐                 │
│            ▼                      ▼                      ▼                 │
│     ┌──────────────┐       ┌──────────────┐       ┌──────────────┐        │
│     │  webserver   │       │  webserver   │       │  webserver   │        │
│     │  (zone-a)    │       │  (zone-b)    │       │  (zone-c)    │        │
│     └──────────────┘       └──────────────┘       └──────────────┘        │
│                                   │                                         │
│                                   ▼                                         │
│                    ┌─────────────────────────────┐                          │
│                    │  PostgreSQL (Multi-AZ RDS)  │                          │
│                    │  └── automatic failover      │                          │
│                    └─────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Scaling Guidelines

| Workload | Scaling Strategy |
|----------|------------------|
| **Light** (< 100 runs/day) | 1 webserver, 1 daemon, 2 workers |
| **Medium** (100-1000 runs/day) | 2 webservers, 1 daemon, 5 workers |
| **Heavy** (1000+ runs/day) | 3 webservers, 1 daemon, 10+ workers, queue partitioning |

### 6.3 Backup Strategy

```yaml
# CronJob for PostgreSQL backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: dagster-backup
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h $PGHOST -U $PGUSER -d dagster | \
                  gzip | \
                  aws s3 cp - s3://backups/dagster/$(date +%Y%m%d-%H%M%S).sql.gz
              envFrom:
                - secretRef:
                    name: dagster-postgresql
```

### 6.4 Monitoring

```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dagster
spec:
  selector:
    matchLabels:
      app: dagster
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

**Key Metrics:**

| Metric | Alert Threshold |
|--------|-----------------|
| `dagster_runs_failed_total` | > 5 in 1 hour |
| `dagster_runs_duration_seconds` | p99 > 3600s |
| `dagster_daemon_heartbeat_age` | > 60s |
| `container_memory_usage_bytes` | > 90% limit |

---

## 7. Deployment Comparison

| Aspect | Local | Docker Compose | Kubernetes |
|--------|-------|----------------|------------|
| **Setup time** | 5 min | 10 min | 30 min |
| **Scalability** | Single user | Single host | Multi-node |
| **HA** | No | No | Yes |
| **Persistence** | File-based | Docker volumes | PVCs + RDS |
| **Observability** | Minimal | Full stack | Full stack |
| **Cost** | Free | Free | Cloud costs |
| **Use case** | Development | Evaluation | Production |
