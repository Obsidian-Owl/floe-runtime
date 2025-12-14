# 06. Deployment View

This document describes deployment options for floe-runtime: local development, Docker, and Kubernetes.

---

## 1. Deployment Options Overview

| Option | Use Case | Complexity |
|--------|----------|------------|
| **Local (pip)** | Development, single user | Low |
| **Docker Compose** | Development, evaluation | Low |
| **Kubernetes (Helm)** | Production, team use | Medium |
| **Managed (SaaS)** | Production, enterprise | Low (managed) |

---

## 2. Local Development (pip)

### 2.1 Installation

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

### 2.2 Project Setup

```bash
# Initialize project
floe init my-project
cd my-project

# Validate configuration
floe validate

# Run locally (DuckDB)
floe run --env dev
```

### 2.3 Local Architecture

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

### 2.4 Limitations

- No persistent Dagster UI (run-and-exit)
- No built-in observability backends
- Single-user, single-machine only

---

## 3. Docker Compose

### 3.1 Quick Start

```bash
# Start full development environment
floe dev

# Or manually with Docker Compose
docker compose up -d
```

### 3.2 Architecture

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

### 3.3 docker-compose.yml

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

### 3.4 OTel Collector Configuration

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

### 3.5 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dagster UI | http://localhost:3000 | Asset management, runs |
| Jaeger UI | http://localhost:16686 | Distributed tracing |
| Marquez Web | http://localhost:3001 | Data lineage |
| Marquez API | http://localhost:5000 | Lineage API |

---

## 4. Kubernetes (Helm)

### 4.1 Chart Structure

```
charts/
├── floe-runtime/           # Umbrella chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── charts/
│       ├── dagster/        # Dagster subchart
│       ├── marquez/        # Marquez subchart
│       └── otel-collector/ # OTel subchart
└── floe-dagster/           # Standalone Dagster chart
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment.yaml
        ├── service.yaml
        ├── configmap.yaml
        └── secrets.yaml
```

### 4.2 Deployment Architecture

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

### 4.3 Installation

```bash
# Add Helm repository
helm repo add floe https://charts.floe.dev
helm repo update

# Install with default values
helm install floe-runtime floe/floe-runtime \
  --namespace floe-runtime \
  --create-namespace

# Install with custom values
helm install floe-runtime floe/floe-runtime \
  --namespace floe-runtime \
  --create-namespace \
  --values values-production.yaml
```

### 4.4 values.yaml

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

### 4.5 Secrets Management

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

### 4.6 Resource Requirements

| Component | Min CPU | Min Memory | Recommended |
|-----------|---------|------------|-------------|
| dagster-webserver | 500m | 1Gi | 2 replicas |
| dagster-daemon | 250m | 512Mi | 1 replica |
| dagster-worker | 1000m | 2Gi | 3+ replicas |
| postgresql | 500m | 1Gi | External RDS |
| otel-collector | 200m | 256Mi | DaemonSet |
| marquez | 500m | 1Gi | 2 replicas |

---

## 5. Production Considerations

### 5.1 High Availability

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

### 5.2 Scaling Guidelines

| Workload | Scaling Strategy |
|----------|------------------|
| **Light** (< 100 runs/day) | 1 webserver, 1 daemon, 2 workers |
| **Medium** (100-1000 runs/day) | 2 webservers, 1 daemon, 5 workers |
| **Heavy** (1000+ runs/day) | 3 webservers, 1 daemon, 10+ workers, queue partitioning |

### 5.3 Backup Strategy

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

### 5.4 Monitoring

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

## 6. Deployment Comparison

| Aspect | Local | Docker Compose | Kubernetes |
|--------|-------|----------------|------------|
| **Setup time** | 5 min | 10 min | 30 min |
| **Scalability** | Single user | Single host | Multi-node |
| **HA** | No | No | Yes |
| **Persistence** | File-based | Docker volumes | PVCs + RDS |
| **Observability** | Minimal | Full stack | Full stack |
| **Cost** | Free | Free | Cloud costs |
| **Use case** | Development | Evaluation | Production |
