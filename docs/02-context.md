# 02. System Context (C4 Level 1)

This document describes the system context—floe-runtime and its interactions with users and external systems.

---

## 1. Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USERS & OPERATORS                                   │
│                                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│   │    Data     │    │  Analytics  │    │  Platform   │    │    OSS      │     │
│   │  Engineer   │    │  Engineer   │    │  Engineer   │    │ Contributor │     │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│          │                  │                  │                  │             │
└──────────┼──────────────────┼──────────────────┼──────────────────┼─────────────┘
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│                            FLOE RUNTIME                                          │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                                                                         │   │
│   │  floe-cli        floe-core        floe-dagster       floe-dbt          │   │
│   │  (User CLI)      (Schema)         (Orchestration)    (Transform)       │   │
│   │                                                                         │   │
│   │  floe-iceberg    floe-polaris     floe-cube                            │   │
│   │  (Storage)       (Catalog)        (Consumption)                         │   │
│   │                                                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                    │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Compute    │  │   Storage    │  │  Observability │  │   Catalog   │        │
│  │   Targets    │  │   Backends   │  │   Backends   │  │   Backend   │        │
│  │              │  │              │  │              │  │              │        │
│  │ • DuckDB     │  │ • S3         │  │ • Jaeger     │  │ • Polaris   │        │
│  │ • Snowflake  │  │ • GCS        │  │ • Grafana    │  │ • Hive      │        │
│  │ • BigQuery   │  │ • Azure Blob │  │ • Marquez    │  │ • Glue      │        │
│  │ • Postgres   │  │ • MinIO      │  │ • Datadog    │  │              │        │
│  │ • Spark      │  │ • Local FS   │  │              │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                                  │
│  ┌──────────────┐                                                               │
│  │  Consumption │   (Data Access APIs)                                          │
│  │   Clients    │                                                               │
│  │              │                                                               │
│  │ • BI Tools   │   Tableau, Metabase, Superset, etc.                          │
│  │ • AI Agents  │   MCP, LangChain, etc.                                        │
│  │ • Apps       │   Custom applications                                         │
│  └──────────────┘                                                               │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐                                            │
│  │   Control    │  │   Version    │    (Optional integrations)                 │
│  │    Plane     │  │   Control    │                                            │
│  │  (Optional)  │  │              │                                            │
│  │              │  │ • Git        │                                            │
│  │ • Floe SaaS  │  │ • GitHub     │                                            │
│  └──────────────┘  └──────────────┘                                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. User Roles

### 2.1 Data Engineer (Primary User)

**Goals:**
- Define data pipelines via floe.yaml
- Run pipelines locally during development
- Deploy to production environments
- Debug failed runs with full observability

**Interactions:**
```
Data Engineer
    │
    ├──► floe init          Create new project
    ├──► floe validate      Check configuration
    ├──► floe compile       Generate artifacts
    ├──► floe run           Execute pipeline
    ├──► floe dev           Start dev environment
    └──► floe test          Run data tests
```

### 2.2 Analytics Engineer

**Goals:**
- Write dbt models with SQL
- Use familiar dbt patterns (ref, source, tests)
- Preview changes before production
- Understand data lineage

**Interactions:**
```
Analytics Engineer
    │
    ├──► Write dbt models in models/
    ├──► Define sources in floe.yaml
    ├──► floe run --select model_name
    └──► View lineage in Marquez UI
```

### 2.3 Platform Engineer

**Goals:**
- Deploy floe-runtime to Kubernetes
- Configure observability backends
- Manage infrastructure
- Ensure security and compliance

**Interactions:**
```
Platform Engineer
    │
    ├──► helm install floe-runtime
    ├──► Configure values.yaml
    ├──► Monitor via Grafana dashboards
    └──► Manage secrets in K8s
```

### 2.4 Open Source Contributor

**Goals:**
- Understand architecture
- Add features or fix bugs
- Ensure code quality
- Document changes

**Interactions:**
```
Contributor
    │
    ├──► Read architecture docs
    ├──► Fork and clone repository
    ├──► Run tests locally
    ├──► Submit pull request
    └──► Respond to review feedback
```

---

## 3. External Systems

### 3.1 Compute Targets

floe-runtime is **target-agnostic**. Users choose where SQL executes.

| Target | Role | Integration |
|--------|------|-------------|
| **DuckDB** | Local development, small production | Embedded, zero config |
| **Snowflake** | Enterprise data warehouse | Via dbt-snowflake |
| **BigQuery** | Google Cloud warehouse | Via dbt-bigquery |
| **Redshift** | AWS warehouse | Via dbt-redshift |
| **Databricks** | Lakehouse platform | Via dbt-databricks |
| **PostgreSQL** | Relational database | Via dbt-postgres |
| **Spark** | Distributed processing | Via dbt-spark |

**Data Flow:**
```
floe-runtime
    │
    ├──► Generate dbt profiles.yml
    │
    └──► dbt connects to target
              │
              └──► Executes SQL transformations
```

### 3.2 Storage Backends

Iceberg tables require object storage or filesystem.

| Backend | Use Case | Configuration |
|---------|----------|---------------|
| **Local filesystem** | Development | `file:///path/to/warehouse` |
| **MinIO** | Local S3-compatible | `s3://bucket/` with MinIO endpoint |
| **AWS S3** | Production cloud | `s3://bucket/` with AWS credentials |
| **Google GCS** | Production cloud | `gs://bucket/` with GCP credentials |
| **Azure Blob** | Production cloud | `abfs://container@account/` |

**Data Flow:**
```
dbt transformation completes
    │
    └──► Iceberg writer
              │
              ├──► Write Parquet data files
              └──► Update Iceberg metadata
                        │
                        └──► Register in Polaris catalog
```

### 3.3 Observability Backends

floe-runtime emits OpenTelemetry and OpenLineage. Users choose backends.

| Backend | Type | Data |
|---------|------|------|
| **Jaeger** | Tracing | OpenTelemetry spans |
| **Grafana Tempo** | Tracing | OpenTelemetry spans |
| **Prometheus** | Metrics | OpenTelemetry metrics |
| **Grafana Mimir** | Metrics | OpenTelemetry metrics |
| **Marquez** | Lineage | OpenLineage events |
| **DataHub** | Lineage | OpenLineage events |

**Data Flow:**
```
Pipeline execution
    │
    ├──► OpenTelemetry SDK
    │         │
    │         └──► OTel Collector ──► Jaeger/Tempo/Grafana
    │
    └──► OpenLineage SDK
              │
              └──► HTTP POST ──► Marquez/DataHub
```

### 3.4 Catalog Backend (Polaris)

Apache Polaris manages Iceberg table metadata.

| Aspect | Description |
|--------|-------------|
| **Purpose** | Centralized table metadata management |
| **Protocol** | Iceberg REST Catalog API |
| **Authentication** | OAuth2 or token-based |
| **Data Flow** | Table create/alter/drop operations |

**Integration:**
```
floe-runtime
    │
    └──► floe-polaris client
              │
              ├──► Create namespace
              ├──► Register tables
              └──► Query table metadata
```

### 3.5 Consumption Layer (Cube)

The Cube semantic layer provides unified data consumption APIs. See [ADR-R0001](adr/0001-cube-semantic-layer.md).

| Aspect | Description |
|--------|-------------|
| **Purpose** | Unified API for BI tools, AI agents, applications |
| **APIs** | REST, GraphQL, SQL (Postgres wire protocol) |
| **Caching** | Cube Store pre-aggregations |
| **Security** | Row-level security via security context |

**Data Flow:**
```
dbt models (transformed data)
    │
    └──► Cube semantic layer
              │
              ├──► REST API    ──► Custom apps
              ├──► GraphQL API ──► Modern frontends
              ├──► SQL API     ──► BI tools (Tableau, Metabase)
              └──► MCP Server  ──► AI agents
```

**Consumer Types:**

| Consumer | Integration | Use Case |
|----------|-------------|----------|
| **BI Tools** | SQL API (Postgres wire) | Dashboards, reports |
| **AI Agents** | MCP Server | Natural language queries |
| **Applications** | REST/GraphQL | Embedded analytics |
| **Data Science** | SQL API | Ad-hoc analysis |

### 3.6 Control Plane (Optional)

The Floe SaaS Control Plane is **optional**. When integrated:

| Aspect | Description |
|--------|-------------|
| **Purpose** | Enhanced DX, managed infrastructure |
| **Integration** | CompiledArtifacts API |
| **Data Flow** | Artifacts from Control Plane → Runtime |
| **Dependency** | Optional—runtime works standalone |

**Integration Modes:**
```
┌─────────────────────────────────────────────────────────┐
│  STANDALONE MODE                                        │
│                                                         │
│  User ──► floe-cli ──► CompiledArtifacts ──► Runtime   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  MANAGED MODE (with Control Plane)                      │
│                                                         │
│  User ──► Git push ──► Control Plane ──► Artifacts     │
│                              │                          │
│                              └──► Deploy Runtime        │
│                                        │                │
│                                        └──► Execute     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Data Flows

### 4.1 Pipeline Definition Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│  floe.yaml  │────►│  floe-core  │────►│  CompiledArtifacts  │
│  (User)     │     │  (Parser)   │     │  (Internal)         │
└─────────────┘     └─────────────┘     └─────────────────────┘
                                                  │
                                                  ▼
                          ┌───────────────────────────────────┐
                          │  Dagster Asset Definitions        │
                          │  dbt profiles.yml                 │
                          │  Observability configuration      │
                          └───────────────────────────────────┘
```

### 4.2 Execution Flow

```
floe run
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Dagster Orchestration                                       │
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ Asset A │───►│ Asset B │───►│ Asset C │───►│ Asset D │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │        │
│       ▼              ▼              ▼              ▼        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   dbt Execution                      │   │
│  │    model_a.sql → model_b.sql → model_c.sql → ...    │   │
│  └─────────────────────────────────────────────────────┘   │
│                             │                               │
└─────────────────────────────┼───────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Compute Target │
                    │  (DuckDB, etc.) │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Iceberg Tables │
                    └─────────────────┘
```

### 4.3 Observability Flow

```
Every operation
    │
    ├──► Span created (OTel)
    │         │
    │         ├──► Attributes: operation, duration, status
    │         └──► Baggage: user context (optional)
    │
    ├──► Metric recorded (OTel)
    │         │
    │         └──► Counter/Gauge/Histogram
    │
    └──► Lineage event (OpenLineage)
              │
              ├──► Job: what ran
              ├──► Inputs: what was read
              └──► Outputs: what was written
```

---

## 5. System Boundaries

### 5.1 In Scope (floe-runtime)

| Capability | Description |
|------------|-------------|
| Pipeline execution | Run data transformations |
| Orchestration | Dagster asset management |
| SQL transformation | dbt model execution |
| Storage management | Iceberg table operations |
| Catalog integration | Polaris metadata |
| **Data consumption** | Cube semantic layer APIs (REST, GraphQL, SQL) |
| Observability emission | OTel traces, OpenLineage events |
| CLI interface | Developer commands |
| Local development | Docker Compose environment |
| Kubernetes deployment | Helm charts |

### 5.2 Out of Scope (Handled Elsewhere)

| Capability | Where Handled |
|------------|---------------|
| Multi-tenant isolation | Control Plane (SaaS) |
| Synthetic data generation | Control Plane (SaaS) |
| Environment lifecycle | Control Plane (SaaS) |
| Git-push-to-deploy | Control Plane (SaaS) |
| Team collaboration | Control Plane (SaaS) |
| Billing | Control Plane (SaaS) |
| Web UI | Control Plane (SaaS) |
| User authentication | Control Plane (SaaS) |

### 5.3 Extension Points

floe-runtime provides clear interfaces for extension:

| Extension Point | Purpose |
|-----------------|---------|
| Custom transforms | Beyond dbt (Python, etc.) |
| Custom compute targets | New dbt adapters |
| Custom observability | Alternative backends |
| Custom catalog | Beyond Polaris |
| Plugin system | Entry point groups |
