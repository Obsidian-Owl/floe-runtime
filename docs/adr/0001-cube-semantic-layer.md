# ADR-R0001: Use Cube for Semantic/Consumption Layer

## Status

Accepted

## Context

floe-runtime provides a complete data pipeline stack:

- **Transformation**: dbt for SQL models
- **Orchestration**: Dagster for scheduling and dependencies
- **Storage**: Apache Iceberg for ACID tables
- **Catalog**: Apache Polaris for metadata management

However, the stack lacks a **consumption layer**—an API through which downstream applications, BI tools, and AI agents can query the transformed data. Without this:

1. Users must connect directly to data warehouses, bypassing governance
2. No caching layer means expensive repeated queries
3. No unified API for diverse consumers (REST, GraphQL, SQL)
4. No semantic model to translate business concepts to physical tables
5. AI agents lack a structured interface for data queries

Key requirements for a consumption layer:

- API-first architecture (REST, GraphQL, SQL wire protocol)
- Semantic modeling on top of dbt models
- Caching and pre-aggregations for performance
- Multi-tenant row-level security
- Integration with OpenTelemetry and OpenLineage
- Support for AI/agent interfaces (MCP)

Technologies considered:

- **Cube** - Open-source semantic layer, API-first, dbt integration, multi-tenant
- **dbt Semantic Layer (MetricFlow)** - dbt-native, but tightly coupled to dbt Cloud
- **LookML/Looker** - Powerful but proprietary, heavy vendor lock-in
- **Custom API layer** - Full control but significant development effort
- **Trino/Presto** - Query engine, not semantic layer

## Decision

Use **Cube** as the semantic/consumption layer for floe-runtime.

Cube will be implemented as a new package `floe-cube` that:

1. Syncs dbt models to Cube cubes via the `cube_dbt` package
2. Provides REST, GraphQL, and SQL APIs for data consumption
3. Implements caching via Cube Store pre-aggregations
4. Enforces row-level security using tenant context
5. Exposes MCP server interface for AI agent queries
6. Emits OpenLineage events for query lineage

## Consequences

### Positive

- **Complete stack**: floe-runtime becomes end-to-end (ingest → transform → store → serve)
- **Native dbt integration**: `cube_dbt` package loads dbt manifest directly
- **Universal APIs**: REST, GraphQL, and Postgres-compatible SQL serve any consumer
- **Performance**: Cube Store pre-aggregations provide sub-second query response
- **Multi-tenancy**: Built-in row-level security with `queryRewrite` and security context
- **AI-ready**: MCP server and AI API enable agent-based analytics
- **Open source**: Cube Core is Apache 2.0 licensed, aligns with floe-runtime licensing
- **BI connectivity**: 40+ native integrations (Tableau, Metabase, Superset, etc.)

### Negative

- **Additional complexity**: New component to deploy, configure, monitor
- **Resource requirements**: Cube Store requires persistent storage for pre-aggregations
- **Learning curve**: Team must learn Cube data modeling concepts
- **Versioning**: Must coordinate Cube, dbt, and Dagster versions

### Neutral

- **Cube Cloud available**: Managed option exists if self-hosting becomes burdensome
- **Community Helm charts**: No official Helm chart, but community options exist
- **Instrumentation needed**: OpenTelemetry/OpenLineage integration requires custom work

## Architecture Integration

### Package Structure

```
floe-runtime/
├── floe-core/          # Schema, validation, CompiledArtifacts
├── floe-cli/           # Developer CLI
├── floe-dagster/       # Orchestration
├── floe-dbt/           # Transformation
├── floe-iceberg/       # Storage
├── floe-polaris/       # Catalog
└── floe-cube/          # Consumption (NEW)
    ├── config.py       # Cube configuration from CompiledArtifacts
    ├── model_sync.py   # Sync dbt models → Cube cubes
    ├── security.py     # Row-level security context
    ├── lineage.py      # OpenLineage emission
    └── mcp_server.py   # MCP server wrapper
```

### Data Flow

```
floe.yaml
    │
    ▼
floe-core (compile)
    │
    ▼
floe-dagster (orchestrate) ──► floe-dbt (transform)
    │                              │
    │                              ▼
    │                         dbt models
    │                              │
    │                              ▼
    │                    floe-iceberg (store)
    │                              │
    │                              ▼
    │                    floe-polaris (catalog)
    │                              │
    ▼                              ▼
floe-cube (consume) ◄───── dbt manifest.json
    │
    ▼
REST / GraphQL / SQL APIs
    │
    ▼
BI Tools, AI Agents, Applications
```

### Schema Extension

```yaml
# floe.yaml - consumption section
consumption:
  enabled: true
  cube:
    port: 4000
    api_secret_ref: "cube-api-secret"
    pre_aggregations:
      refresh_schedule: "*/30 * * * *"
    security:
      row_level: true
      tenant_column: "tenant_id"
```

### Deployment Components

| Component | Purpose | Scaling |
|-----------|---------|---------|
| Cube API | Handle incoming queries | Horizontal (2+ replicas) |
| Cube Refresh Worker | Build pre-aggregations | Single replica |
| Cube Store Router | Route queries | Single replica |
| Cube Store Workers | Execute cached queries | Horizontal (2+ replicas) |

## Pre-Aggregation Strategy

Pre-aggregations are materialized rollups that improve query performance. Cube supports two storage modes:

### Storage Options

| Environment | `external` | Storage Location | Use Case |
|-------------|-----------|------------------|----------|
| Testing | `false` | Source database (Trino/DuckDB) | No additional infrastructure |
| Production | `true` | Cube Store + S3/GCS | High concurrency, sub-second queries |

### Build Strategies by Database

| Database | Default Strategy | Export Bucket Support | Notes |
|----------|-----------------|----------------------|-------|
| DuckDB | Batching | Not supported | Memory-bound, set `DUCKDB_MEMORY_LIMIT` |
| Trino | Simple | S3 + GCS | For datasets >100k rows |
| Snowflake | Batching | S3 + GCS + Azure | Uses storage integration |
| BigQuery | Stream | GCS | Native export |

### Configuration

**Testing (source database storage):**
```yaml
# floe.yaml
consumption:
  pre_aggregations:
    external: false  # Store in source database
```

**Production (Cube Store + S3):**
```yaml
# floe.yaml
consumption:
  pre_aggregations:
    external: true  # Store in Cube Store
    cube_store:
      enabled: true
      s3_bucket: "my-cube-preaggs"
      s3_region: "us-east-1"
    # Optional: Export bucket for large builds (Trino/Snowflake only)
    export_bucket:
      enabled: true
      bucket_type: "s3"
      name: "my-cube-export"
      region: "us-east-1"
```

### Architecture

```
Build Phase:
Refresh Worker → SQL Query → Source Database (DuckDB/Trino/Snowflake)
                     │
                     ▼ (external: true)
               Cube Store → S3 Parquet Files

Query Phase:
API Request → Cube Store → S3 Parquet → Sub-second Response
```

## References

- [Cube Documentation](https://cube.dev/docs/product/introduction)
- [Cube + dbt Integration](https://cube.dev/docs/product/data-modeling/recipes/dbt)
- [cube_dbt Package](https://github.com/cube-js/cube_dbt)
- [Cube Multitenancy](https://cube.dev/docs/product/configuration/multitenancy)
- [Cube Row-Level Security](https://cube.dev/docs/product/auth/row-level-security)
- [Cube Deployment](https://cube.dev/docs/product/deployment)
- [Community Helm Charts](https://github.com/narioinc/cube-helm)
- [ADR-0009: dbt Owns SQL](../../architecture/adr/0009-dbt-owns-sql.md)
