# Data Model: Consumption Layer (floe-cube)

**Feature Branch**: `005-consumption-layer`
**Date**: 2025-12-18

## Entity Overview

This document defines the data models for the floe-cube package. All models use Pydantic v2 with strict validation.

---

## 1. CubeConfig

Runtime configuration for Cube deployment.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| database_type | `Literal["postgres", "snowflake", "bigquery", "databricks", "trino"]` | Yes | Database driver type |
| api_port | `int` | No (default: 4000) | REST/GraphQL API port |
| sql_port | `int` | No (default: 15432) | SQL API port (Postgres wire) |
| api_secret_ref | `str \| None` | No | K8s secret reference for API secret |
| dev_mode | `bool` | No (default: False) | Enable Cube Playground |
| pre_aggregations_schema | `str` | No (default: "pre_aggregations") | Schema for pre-agg tables |
| export_bucket | `str \| None` | No | S3 bucket for pre-aggregations |
| jwt_audience | `str \| None` | No | Expected JWT audience claim |
| jwt_issuer | `str \| None` | No | Expected JWT issuer claim |

### Validation Rules

- `database_type` must be one of the supported drivers
- `api_port` must be between 1024 and 65535
- `sql_port` must be between 1024 and 65535
- `api_secret_ref` must match K8s secret naming pattern: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$`

### Source

Derived from `ConsumptionConfig` in CompiledArtifacts.

---

## 2. CubeSchema

Generated cube definitions derived from dbt models.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | `str` | Yes | Cube name (from dbt model name) |
| sql_table | `str` | Yes | Fully-qualified table reference |
| description | `str \| None` | No | Cube description (from dbt) |
| dimensions | `list[CubeDimension]` | Yes | List of dimensions |
| measures | `list[CubeMeasure]` | Yes | List of measures |
| joins | `list[CubeJoin]` | No | Relationships to other cubes |
| pre_aggregations | `list[CubePreAggregation]` | No | Pre-aggregation definitions |
| filter_column | `str \| None` | No | Column for row-level security filtering (e.g., organization_id, department) |

### Validation Rules

- `name` must be a valid identifier (alphanumeric, underscores)
- `sql_table` must be a valid SQL identifier path (catalog.schema.table)
- At least one dimension is required
- Dimension and measure names must be unique within the cube

### Lifecycle

1. **Created**: When dbt manifest.json is parsed
2. **Updated**: When manifest.json changes and sync runs
3. **Deleted**: When corresponding dbt model is removed from manifest

---

## 3. CubeDimension

Dimension definition within a cube.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | `str` | Yes | Dimension name |
| sql | `str` | Yes | SQL expression for dimension |
| type | `Literal["string", "number", "time", "boolean", "geo"]` | Yes | Dimension data type |
| primary_key | `bool` | No (default: False) | Whether this is the primary key |
| description | `str \| None` | No | Dimension description |
| meta | `dict[str, Any]` | No | Additional metadata (classification, etc.) |

### Validation Rules

- `name` must be a valid identifier
- `type` must be one of the allowed Cube dimension types

### Source

- Column name from dbt model columns
- Type inferred from dbt column data_type or meta.cube.type
- Primary key from meta.cube.primary_key tag

---

## 4. CubeMeasure

Measure definition within a cube.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | `str` | Yes | Measure name |
| sql | `str` | Yes | SQL expression for measure |
| type | `Literal["count", "sum", "avg", "min", "max", "countDistinct", "countDistinctApprox", "runningTotal"]` | Yes | Aggregation type |
| description | `str \| None` | No | Measure description |
| filters | `list[CubeMeasureFilter]` | No | Measure-level filters |

### Validation Rules

- `name` must be a valid identifier
- `type` must be one of the allowed Cube aggregation types

### Source

Extracted from dbt model meta.cube.measures tags.

---

## 5. CubeJoin

Join relationship between cubes.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | `str` | Yes | Name of the joined cube |
| relationship | `Literal["one_to_one", "one_to_many", "many_to_one"]` | Yes | Cardinality |
| sql | `str` | Yes | Join condition SQL |

### Validation Rules

- `name` must reference an existing cube
- `relationship` must be one of the allowed cardinalities

### Source

Derived from dbt model relationships (refs, meta.cube.joins).

---

## 6. CubePreAggregation

Pre-aggregation definition for caching.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | `str` | Yes | Pre-aggregation name |
| measures | `list[str]` | Yes | Measures to include |
| dimensions | `list[str]` | No | Dimensions to include |
| time_dimension | `str \| None` | No | Time dimension for time-series |
| granularity | `Literal["second", "minute", "hour", "day", "week", "month", "quarter", "year"]` | No | Time granularity |
| refresh_every | `str` | Yes | Cron expression for refresh |
| external | `bool` | No (default: True) | Use Cube Store |

### Validation Rules

- `measures` must reference measures defined in the same cube
- `dimensions` must reference dimensions defined in the same cube
- `refresh_every` must be a valid cron expression

---

## 7. SecurityContext

Request-scoped security context for row-level security. This is **user-managed** and **role-based** - users define which JWT claims map to filter columns.

**Note on Security Model**: This is distinct from SaaS tenant isolation. The future Floe SaaS Control Plane provides infrastructure-level isolation (separate environments per customer). SecurityContext is for data-level filtering within a single deployment based on user-defined attributes.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| filter_claims | `dict[str, str]` | Yes | User-defined filter values extracted from JWT (e.g., {"organization_id": "org_a", "department": "sales"}) |
| user_id | `str \| None` | No | User identifier from JWT |
| roles | `list[str]` | No | User roles from JWT |
| exp | `datetime` | Yes | Token expiration time |

### Validation Rules

- `filter_claims` must contain at least one entry when row-level security is enabled
- The filter claim key must match the configured `filter_column` in CubeSecurityConfig
- `exp` must be in the future (not expired)

### Source

Extracted from JWT token claims (user-configurable mapping):
- `u.<claim_name>` → `filter_claims[<claim_name>]` (e.g., `u.organization_id` → `filter_claims["organization_id"]`)
- `sub` → `user_id`
- `u.roles` → `roles`
- `exp` → `exp`

### Example JWT Token

```json
{
  "sub": "user-123",
  "iat": 1702900000,
  "exp": 1702903600,
  "u": {
    "organization_id": "org_abc",
    "department": "engineering",
    "roles": ["analyst", "viewer"]
  }
}
```

---

## 8. QueryTraceSpan

OpenTelemetry trace span for operational observability. Captures query execution performance and timing.

**Note on Observability Model**: QueryTraceSpan (OpenTelemetry) captures **operational metrics** - "how is the system performing?" This is complementary to QueryLineageEvent (OpenLineage) which captures **data lineage** - "what data is being accessed?"

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| trace_id | `str` | Yes | W3C Trace ID (propagated or generated) |
| span_id | `str` | Yes | Unique span identifier |
| parent_span_id | `str \| None` | No | Parent span (from incoming request) |
| name | `str` | Yes | Span name (e.g., "cube.query", "cube.execute") |
| kind | `Literal["SERVER", "CLIENT", "INTERNAL"]` | Yes | Span kind |
| start_time | `datetime` | Yes | Span start time (UTC) |
| end_time | `datetime \| None` | No | Span end time (UTC) |
| status | `Literal["OK", "ERROR", "UNSET"]` | Yes | Span status |
| attributes | `dict[str, str \| int \| bool]` | No | Span attributes (see below) |

### Safe Attributes (never include sensitive data)

| Attribute | Type | Description |
|-----------|------|-------------|
| cube.name | `str` | Name of the cube being queried |
| cube.measures_count | `int` | Number of measures requested |
| cube.dimensions_count | `int` | Number of dimensions requested |
| cube.filter_count | `int` | Number of filters applied (**NOT** filter values!) |
| cube.row_count | `int` | Number of rows returned |
| cube.error_type | `str` | Error classification (e.g., "ValidationError") |

### Forbidden Attributes (security)

**NEVER include in trace spans:**
- Filter values (e.g., `organization_id = "org_abc"`)
- JWT claims or token contents
- Row data or query results
- SQL query text (use OpenLineage for this)
- User PII

### Span Hierarchy

```
cube.query (root SERVER span)
├── cube.parse (INTERNAL)
├── cube.security (INTERNAL - JWT validation)
├── cube.execute (INTERNAL)
│   └── database.query (CLIENT - actual DB call)
└── cube.response (INTERNAL)
```

---

## 9. QueryLineageEvent

OpenLineage event for data lineage and query audit.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| run_id | `str` | Yes | Unique query run identifier (UUID) |
| job_name | `str` | Yes | Job name (cube.{cube_name}.query) |
| namespace | `str` | Yes | OpenLineage namespace |
| event_type | `Literal["START", "COMPLETE", "FAIL"]` | Yes | Event state |
| event_time | `datetime` | Yes | Event timestamp (UTC) |
| inputs | `list[str]` | Yes | Input dataset names (cubes queried) |
| sql | `str \| None` | No | Query SQL (for START events) |
| row_count | `int \| None` | No | Result row count (for COMPLETE events) |
| error | `str \| None` | No | Sanitized error (for FAIL events) |

### Validation Rules

- `run_id` must be a valid UUID
- `event_time` must be UTC
- `error` must not contain sensitive information

---

## Entity Relationships

```
CompiledArtifacts
    │
    └── ConsumptionConfig
            │
            ├──► CubeConfig (1:1)
            │
            └── dbt_manifest_path
                    │
                    └──► CubeSchema (1:N)
                            │
                            ├── CubeDimension (1:N)
                            ├── CubeMeasure (1:N)
                            ├── CubeJoin (0:N)
                            └── CubePreAggregation (0:N)

SecurityContext ◄── JWT Token (per request)

QueryTraceSpan ◄── Query Execution (per query, OpenTelemetry - "how is system performing?")

QueryLineageEvent ◄── Query Execution (per query, OpenLineage - "what data is accessed?")
```

---

## Type Mapping: dbt to Cube

| dbt data_type | Cube dimension type |
|---------------|---------------------|
| `text`, `varchar`, `string`, `char` | `string` |
| `integer`, `bigint`, `smallint`, `int`, `number`, `numeric`, `decimal`, `float`, `double` | `number` |
| `timestamp`, `datetime`, `date`, `time` | `time` |
| `boolean`, `bool` | `boolean` |
| `geography`, `geometry` | `geo` |

---

## Pydantic Model Definitions

All models will be implemented in `packages/floe-cube/src/floe_cube/models.py` using:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
```

Key conventions:
- `ConfigDict(frozen=True, extra="forbid")` for immutable models
- `Field(...)` with descriptions for all attributes
- `@field_validator` for custom validation
- Google-style docstrings with examples
