# 05. Runtime View

This document describes key execution workflows and sequences in floe-runtime.

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION LIFECYCLE                                │
│                                                                              │
│   1. INIT        2. VALIDATE      3. COMPILE       4. EXECUTE               │
│   ─────────────────────────────────────────────────────────────             │
│   floe init  ──► floe validate ──► floe compile ──► floe run               │
│                                                                              │
│   Create         Check            Generate         Run pipeline             │
│   project        floe.yaml        artifacts        via Dagster              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Project Initialization

### 2.1 Sequence: `floe init`

```
User                    floe-cli                Templates              Filesystem
  │                        │                        │                      │
  │  floe init my-project  │                        │                      │
  │───────────────────────►│                        │                      │
  │                        │                        │                      │
  │                        │  Load template "basic" │                      │
  │                        │───────────────────────►│                      │
  │                        │◄───────────────────────│                      │
  │                        │                        │                      │
  │                        │  Create directory structure                   │
  │                        │──────────────────────────────────────────────►│
  │                        │                        │                      │
  │                        │  Write floe.yaml                              │
  │                        │──────────────────────────────────────────────►│
  │                        │                        │                      │
  │                        │  Write dbt project files                      │
  │                        │──────────────────────────────────────────────►│
  │                        │                        │                      │
  │  ✓ Created my-project  │                        │                      │
  │◄───────────────────────│                        │                      │
```

### 2.2 Generated Structure

```
my-project/
├── floe.yaml           # Pipeline configuration
├── models/             # dbt models
│   └── example.sql
├── seeds/              # Sample data (optional)
│   └── sample.csv
├── tests/              # Data tests (optional)
│   └── test_example.sql
└── .gitignore
```

### 2.3 Default floe.yaml

```yaml
# floe.yaml
name: my-project
version: "1.0"

compute:
  target: duckdb
  properties:
    path: ./warehouse/my-project.duckdb

transforms:
  - type: dbt
    path: models/

observability:
  traces: true
  metrics: true
  lineage: true
```

---

## 3. Configuration Validation

### 3.1 Sequence: `floe validate`

```
User                floe-cli            floe-core           Filesystem
  │                    │                    │                    │
  │  floe validate     │                    │                    │
  │───────────────────►│                    │                    │
  │                    │                    │                    │
  │                    │  Read floe.yaml    │                    │
  │                    │───────────────────────────────────────►│
  │                    │◄───────────────────────────────────────│
  │                    │                    │                    │
  │                    │  Validate schema   │                    │
  │                    │───────────────────►│                    │
  │                    │                    │                    │
  │                    │                    │  Parse YAML        │
  │                    │                    │  Validate types    │
  │                    │                    │  Check references  │
  │                    │                    │                    │
  │                    │  ValidationResult  │                    │
  │                    │◄───────────────────│                    │
  │                    │                    │                    │
  │  ✓ Valid / ✗ Error │                    │                    │
  │◄───────────────────│                    │                    │
```

### 3.2 Validation Rules

| Rule | Description |
|------|-------------|
| Schema compliance | All fields match Pydantic schema |
| Profile references valid | Referenced profiles exist in platform.yaml |
| Zero secrets in floe.yaml | No credentials or endpoints in pipeline config |
| Transform paths exist | Referenced directories exist |
| No circular refs | Transform dependencies are acyclic |
| Secret refs valid | Secret references follow K8s naming convention |
| Credential modes valid | OAuth2 requires client_id, client_secret, scope |

### 3.3 Error Messages

```
$ floe validate
✗ Validation failed:

  floe.yaml:5 - compute.target
    Value 'duckdbb' is not valid. Did you mean 'duckdb'?

  floe.yaml:8 - transforms[0].path
    Directory 'modells/' does not exist. Found 'models/'.
```

**Profile resolution errors** (FR-038):

```
$ floe validate
✗ Validation failed:

  floe.yaml:3 - catalog: "analytics"
    Profile 'analytics' not found in platform.catalogs.
    Available profiles: [default, production]

  platform.yaml:12 - catalogs.default.credentials.client_secret
    Field 'client_secret' must use secret_ref, not plaintext value.
    Use: client_secret: { secret_ref: "polaris-oauth" }
```

**Secret resolution errors** (at runtime, FR-039):

```
$ floe run
✗ Secret resolution failed:

  Secret 'polaris-oauth' not found.
  Expected in environment variable: POLARIS_OAUTH
  Or K8s secret mount: /var/run/secrets/polaris-oauth
```

---

## 4. Compilation

### 4.1 Two-Tier Configuration Merge

The compilation process merges `platform.yaml` (infrastructure) with `floe.yaml` (pipeline) to produce `CompiledArtifacts`. This is the core of the two-tier architecture ([ADR-0002](adr/0002-two-tier-config.md)).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TWO-TIER CONFIGURATION MERGE                             │
│                                                                              │
│  ┌─────────────────────┐                    ┌─────────────────────┐         │
│  │  platform.yaml      │                    │  floe.yaml          │         │
│  │  (Platform Engineer)│                    │  (Data Engineer)    │         │
│  ├─────────────────────┤                    ├─────────────────────┤         │
│  │ storage:            │                    │ name: my-pipeline   │         │
│  │   default:          │                    │ catalog: default    │         │
│  │     type: s3        │                    │ storage: default    │         │
│  │     bucket: data    │                    │ compute: default    │         │
│  │ catalogs:           │  ───────────────►  │ transforms:         │         │
│  │   default:          │  Profile           │   - type: dbt       │         │
│  │     uri: polaris:81 │  Resolution        │     path: ./models  │         │
│  │     credentials:    │  ───────────────►  │ observability:      │         │
│  │       mode: oauth2  │                    │   traces: true      │         │
│  │       secret_ref:.. │                    │   lineage: true     │         │
│  └─────────────────────┘                    └─────────────────────┘         │
│            │                                           │                     │
│            └───────────────────┬───────────────────────┘                     │
│                                │                                             │
│                                ▼                                             │
│            ┌───────────────────────────────────────┐                        │
│            │           PlatformResolver            │                        │
│            │  • Load platform config (local/registry)                       │
│            │  • Validate secret_ref patterns       │                        │
│            │  • Check profile references exist     │                        │
│            └───────────────────┬───────────────────┘                        │
│                                │                                             │
│                                ▼                                             │
│            ┌───────────────────────────────────────┐                        │
│            │              Compiler                 │                        │
│            │  • Resolve profile references         │                        │
│            │  • Merge into CompiledArtifacts       │                        │
│            │  • NO secrets resolved yet            │                        │
│            └───────────────────┬───────────────────┘                        │
│                                │                                             │
│                                ▼                                             │
│            ┌───────────────────────────────────────┐                        │
│            │         CompiledArtifacts v2.0        │                        │
│            ├───────────────────────────────────────┤                        │
│            │ resolved_catalog:                     │                        │
│            │   uri: "polaris:8181/api/catalog"     │                        │
│            │   credentials:                        │                        │
│            │     mode: oauth2                      │                        │
│            │     client_secret:                    │                        │
│            │       secret_ref: polaris-oauth       │ ◄── Still a reference │
│            │ resolved_storage:                     │                        │
│            │   type: s3                            │                        │
│            │   bucket: data                        │                        │
│            │ transforms: [...]                     │                        │
│            │ platform_source: registry/v1.2.3     │                        │
│            └───────────────────────────────────────┘                        │
│                                │                                             │
│                                ▼                                             │
│            ┌───────────────────────────────────────┐                        │
│            │       Runtime (Dagster/K8s Pod)       │                        │
│            │  • Secret resolution happens HERE     │                        │
│            │  • Reads from env vars or K8s secrets │                        │
│            │  • Never persisted to disk            │                        │
│            └───────────────────────────────────────┘                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key security principle**: Credentials are resolved at **runtime**, never at compile time. CompiledArtifacts contains `secret_ref` references, not actual secrets.

### 4.2 Sequence: `floe compile`

```
User              floe-cli         PlatformResolver      Compiler         Filesystem
  │                  │                   │                   │                 │
  │  floe compile    │                   │                   │                 │
  │─────────────────►│                   │                   │                 │
  │                  │                   │                   │                 │
  │                  │  Read floe.yaml   │                   │                 │
  │                  │─────────────────────────────────────────────────────►│
  │                  │◄─────────────────────────────────────────────────────│
  │                  │                   │                   │                 │
  │                  │  Load platform config (FLOE_PLATFORM_ENV)             │
  │                  │──────────────────►│                   │                 │
  │                  │                   │                   │                 │
  │                  │                   │  Read platform/{env}/platform.yaml │
  │                  │                   │─────────────────────────────────►│
  │                  │                   │◄─────────────────────────────────│
  │                  │                   │                   │                 │
  │                  │  PlatformSpec     │                   │                 │
  │                  │◄──────────────────│                   │                 │
  │                  │                   │                   │                 │
  │                  │  Compile(FloeSpec, PlatformSpec)      │                 │
  │                  │─────────────────────────────────────►│                 │
  │                  │                   │                   │                 │
  │                  │                   │                   │  Resolve profile│
  │                  │                   │                   │  references     │
  │                  │                   │                   │                 │
  │                  │                   │                   │  Validate       │
  │                  │                   │                   │  secret_refs    │
  │                  │                   │                   │                 │
  │                  │  CompiledArtifacts                    │                 │
  │                  │◄─────────────────────────────────────│                 │
  │                  │                   │                   │                 │
  │                  │  Write .floe/artifacts.json          │                 │
  │                  │─────────────────────────────────────────────────────►│
  │                  │                   │                   │                 │
  │  ✓ Compiled      │                   │                   │                 │
  │◄─────────────────│                   │                   │                 │
```

### 4.3 CompiledArtifacts Output

```json
{
  "version": "1.0.0",
  "metadata": {
    "compiled_at": "2024-12-10T10:30:00Z",
    "floe_core_version": "0.1.0",
    "source_hash": "abc123..."
  },
  "compute": {
    "target": "duckdb",
    "properties": {
      "path": "./warehouse/my-project.duckdb"
    }
  },
  "transforms": [
    {
      "type": "dbt",
      "path": "models/"
    }
  ],
  "observability": {
    "traces": true,
    "metrics": true,
    "lineage": true
  },
  "dbt_project_path": "/path/to/project",
  "dbt_manifest_path": "/path/to/project/target/manifest.json",
  "dbt_profiles_path": "/path/to/project/.floe"
}
```

---

## 5. Pipeline Execution

### 5.1 Sequence: `floe run`

```
User          floe-cli       floe-dagster      Dagster          dbt          OTel
  │               │               │               │               │            │
  │  floe run     │               │               │               │            │
  │──────────────►│               │               │               │            │
  │               │               │               │               │            │
  │               │  Load artifacts               │               │            │
  │               │──────────────►│               │               │            │
  │               │               │               │               │            │
  │               │               │  Create assets│               │            │
  │               │               │──────────────►│               │            │
  │               │               │               │               │            │
  │               │               │               │  Start span   │            │
  │               │               │               │──────────────────────────►│
  │               │               │               │               │            │
  │               │               │  Materialize assets           │            │
  │               │               │──────────────►│               │            │
  │               │               │               │               │            │
  │               │               │               │  For each asset:          │
  │               │               │               │  ─────────────────────────│
  │               │               │               │               │            │
  │               │               │               │  Start asset span         │
  │               │               │               │──────────────────────────►│
  │               │               │               │               │            │
  │               │               │               │  dbt build    │            │
  │               │               │               │──────────────►│            │
  │               │               │               │               │            │
  │               │               │               │               │  Execute   │
  │               │               │               │               │  SQL       │
  │               │               │               │               │            │
  │               │               │               │  Result       │            │
  │               │               │               │◄──────────────│            │
  │               │               │               │               │            │
  │               │               │               │  End asset span           │
  │               │               │               │──────────────────────────►│
  │               │               │               │               │            │
  │               │               │               │  Emit lineage │            │
  │               │               │               │──────────────────────────►│
  │               │               │               │               │            │
  │               │               │  Assets materialized          │            │
  │               │               │◄──────────────│               │            │
  │               │               │               │               │            │
  │               │  End span     │               │               │            │
  │               │──────────────────────────────────────────────────────────►│
  │               │               │               │               │            │
  │  ✓ Complete   │               │               │               │            │
  │◄──────────────│               │               │               │            │
```

### 5.2 Asset Materialization

Each dbt model becomes a Dagster asset:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Asset Graph (from dbt manifest)                                             │
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                 │
│  │  stg_orders  │────►│  int_orders  │────►│ mart_orders  │                 │
│  └──────────────┘     └──────────────┘     └──────────────┘                 │
│          │                                          ▲                        │
│          │            ┌──────────────┐              │                        │
│          └───────────►│stg_customers │──────────────┘                        │
│                       └──────────────┘                                       │
│                                                                              │
│  Execution order: stg_orders → stg_customers → int_orders → mart_orders     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Observability Output

**OpenTelemetry Trace:**
```
Trace: floe.run
├── Span: dagster.materialize
│   ├── Span: dbt.build.stg_orders (2.3s)
│   ├── Span: dbt.build.stg_customers (1.8s)
│   ├── Span: dbt.build.int_orders (3.1s)
│   └── Span: dbt.build.mart_orders (4.2s)
└── Duration: 11.4s
```

**OpenLineage Events:**
```json
{
  "eventType": "COMPLETE",
  "job": {"namespace": "floe", "name": "mart_orders"},
  "run": {"runId": "abc-123"},
  "inputs": [
    {"namespace": "floe", "name": "int_orders"},
    {"namespace": "floe", "name": "stg_customers"}
  ],
  "outputs": [
    {"namespace": "floe", "name": "mart_orders"}
  ]
}
```

---

## 6. Development Environment

### 6.1 Sequence: `floe dev`

```
User              floe-cli           Docker Compose        Services
  │                   │                    │                   │
  │  floe dev         │                    │                   │
  │──────────────────►│                    │                   │
  │                   │                    │                   │
  │                   │  Generate compose  │                   │
  │                   │  configuration     │                   │
  │                   │                    │                   │
  │                   │  docker compose up │                   │
  │                   │───────────────────►│                   │
  │                   │                    │                   │
  │                   │                    │  Start PostgreSQL │
  │                   │                    │──────────────────►│
  │                   │                    │                   │
  │                   │                    │  Start Dagster    │
  │                   │                    │──────────────────►│
  │                   │                    │                   │
  │                   │                    │  Start OTel       │
  │                   │                    │  Collector        │
  │                   │                    │──────────────────►│
  │                   │                    │                   │
  │                   │                    │  Start Jaeger     │
  │                   │                    │──────────────────►│
  │                   │                    │                   │
  │                   │                    │  Start Marquez    │
  │                   │                    │──────────────────►│
  │                   │                    │                   │
  │  Services ready   │                    │                   │
  │  Dagster: :3000   │                    │                   │
  │  Jaeger:  :16686  │                    │                   │
  │  Marquez: :5000   │                    │                   │
  │◄──────────────────│                    │                   │
```

### 6.2 Docker Compose Configuration

```yaml
# Generated docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: dagster
      POSTGRES_PASSWORD: dagster
      POSTGRES_DB: dagster
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "dagster"]
      interval: 5s
      timeout: 5s
      retries: 5

  dagster:
    image: ghcr.io/floe-runtime/dagster:latest
    ports:
      - "3000:3000"
    environment:
      DAGSTER_POSTGRES_HOST: postgres
      DAGSTER_POSTGRES_USER: dagster
      DAGSTER_POSTGRES_PASSWORD: dagster
      DAGSTER_POSTGRES_DB: dagster
      FLOE_ARTIFACTS_PATH: /app/artifacts.json
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OPENLINEAGE_URL: http://marquez:5000
    volumes:
      - ./.floe/artifacts.json:/app/artifacts.json:ro
      - ./models:/app/models:ro
    depends_on:
      postgres:
        condition: service_healthy

  otel-collector:
    image: otel/opentelemetry-collector:latest
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml:ro
    command: ["--config", "/etc/otel/config.yaml"]

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "14250:14250"  # gRPC

  marquez:
    image: marquezproject/marquez:latest
    ports:
      - "5000:5000"   # API
      - "5001:5001"   # Web UI
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### 6.3 Development Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPMENT LOOP                                      │
│                                                                              │
│   1. Edit dbt models                                                        │
│      └──► models/marts/customers.sql                                        │
│                                                                              │
│   2. View in Dagster UI                                                     │
│      └──► http://localhost:3000                                             │
│      └──► Auto-reload on file changes                                       │
│                                                                              │
│   3. Materialize assets                                                     │
│      └──► Click "Materialize" in UI                                         │
│      └──► Or: floe run --select customers                                   │
│                                                                              │
│   4. Debug with traces                                                      │
│      └──► http://localhost:16686 (Jaeger)                                   │
│      └──► Find slow queries, errors                                         │
│                                                                              │
│   5. View lineage                                                           │
│      └──► http://localhost:5001 (Marquez)                                   │
│      └──► Understand data flow                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Data Testing

### 7.1 Sequence: `floe test`

```
User            floe-cli          floe-dbt           dbt
  │                 │                 │                │
  │  floe test      │                 │                │
  │────────────────►│                 │                │
  │                 │                 │                │
  │                 │  Load artifacts │                │
  │                 │────────────────►│                │
  │                 │                 │                │
  │                 │                 │  dbt test      │
  │                 │                 │───────────────►│
  │                 │                 │                │
  │                 │                 │                │  Execute tests
  │                 │                 │                │  - not_null
  │                 │                 │                │  - unique
  │                 │                 │                │  - relationships
  │                 │                 │                │  - custom tests
  │                 │                 │                │
  │                 │                 │  Test results  │
  │                 │                 │◄───────────────│
  │                 │                 │                │
  │  ✓ 15 passed    │                 │                │
  │  ✗ 2 failed     │                 │                │
  │◄────────────────│                 │                │
```

### 7.2 Test Types

| Test Type | Description | Example |
|-----------|-------------|---------|
| **not_null** | Column has no nulls | `customer_id` |
| **unique** | Column values unique | `order_id` |
| **relationships** | FK references exist | `order.customer_id → customer.id` |
| **accepted_values** | Values in set | `status in ('active', 'inactive')` |
| **custom** | SQL expression | `amount > 0` |

### 7.3 Test Output

```
$ floe test

Running dbt tests...

  ✓ not_null_orders_order_id                    PASS (0.2s)
  ✓ unique_orders_order_id                      PASS (0.3s)
  ✓ not_null_customers_customer_id              PASS (0.1s)
  ✓ unique_customers_customer_id                PASS (0.2s)
  ✓ relationships_orders_customer_id            PASS (0.4s)
  ✗ accepted_values_orders_status               FAIL (0.2s)
    └─ Found values: ['active', 'inactive', 'pending']
       Expected: ['active', 'inactive']

Summary: 5 passed, 1 failed
```

---

## 8. Error Handling

### 8.1 Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Configuration** | Invalid YAML, missing fields | Fail fast with clear message |
| **Compilation** | dbt compile error, missing refs | Show dbt error, suggest fix |
| **Execution** | SQL error, timeout | Capture in span, emit lineage FAIL |
| **Infrastructure** | DB connection, OOM | Retry with backoff, alert |

### 8.2 Error Sequence

```
User             Dagster            dbt            OTel          Lineage
  │                 │                │               │               │
  │                 │  Execute model │               │               │
  │                 │───────────────►│               │               │
  │                 │                │               │               │
  │                 │                │  SQL Error!   │               │
  │                 │                │               │               │
  │                 │  Error result  │               │               │
  │                 │◄───────────────│               │               │
  │                 │                │               │               │
  │                 │  Record error span             │               │
  │                 │──────────────────────────────►│               │
  │                 │                │               │               │
  │                 │  Emit FAIL event               │               │
  │                 │─────────────────────────────────────────────►│
  │                 │                │               │               │
  │  ✗ Failed       │                │               │               │
  │  Error: ...     │                │               │               │
  │◄────────────────│                │               │               │
```

### 8.3 Error Messages

```
$ floe run

✗ Execution failed

  Asset: mart_orders
  Error: SQL compilation error

  dbt output:
  ────────────────────────────────────────
  Database Error in model mart_orders (models/marts/orders.sql)
    column "cusotmer_id" does not exist
    Did you mean "customer_id"?

  Trace ID: abc123-def456
  View trace: http://localhost:16686/trace/abc123-def456

  Lineage event emitted with status: FAIL
```
