# Data Model: Kubernetes Demo Deployment

**Feature**: 008-kubernetes-demo
**Date**: 2025-12-22

## Overview

This document defines the key entities for the Kubernetes demo deployment feature. These are primarily Kubernetes/Helm configuration entities rather than application data models.

---

## Entities

### 1. HelmRelease

Represents a deployed Helm chart instance.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Release name (e.g., "floe-infrastructure") |
| `namespace` | `str` | Kubernetes namespace |
| `chart` | `str` | Chart name or path |
| `version` | `str` | Chart version |
| `values` | `dict[str, Any]` | Values override |
| `status` | `Literal["deployed", "pending", "failed"]` | Release status |
| `created_at` | `datetime` | Installation timestamp |

**Relationships:**
- HelmRelease → multiple Kubernetes resources (Pods, Services, ConfigMaps)

---

### 2. InfrastructureConfig

Configuration for the floe-infrastructure Helm chart.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `postgresql.enabled` | `bool` | `true` | Enable PostgreSQL |
| `postgresql.persistence.enabled` | `bool` | `false` | Use emptyDir for local |
| `minio.enabled` | `bool` | `true` | Enable MinIO |
| `minio.persistence.enabled` | `bool` | `false` | Use emptyDir for local |
| `polaris.enabled` | `bool` | `true` | Enable Polaris catalog |
| `jaeger.enabled` | `bool` | `true` | Enable Jaeger tracing |
| `marquez.enabled` | `bool` | `true` | Enable Marquez lineage |

**Validation Rules:**
- If `polaris.enabled`, then `postgresql.enabled` must be `true` (Polaris needs PostgreSQL)
- If `marquez.enabled`, then `postgresql.enabled` must be `true` (Marquez needs PostgreSQL)

---

### 3. DuckDBCatalogConnection

Configuration for DuckDB to connect to Polaris REST catalog.

| Field | Type | Description |
|-------|------|-------------|
| `endpoint` | `str` | Polaris REST endpoint (e.g., "http://polaris:8181/api/catalog") |
| `catalog_name` | `str` | Iceberg catalog name |
| `client_id` | `str` | OAuth2 client ID |
| `client_secret` | `SecretStr` | OAuth2 client secret |
| `s3_endpoint` | `str` | MinIO/S3 endpoint for HTTPFS |
| `s3_access_key` | `str` | S3 access key |
| `s3_secret_key` | `SecretStr` | S3 secret key |

**Validation Rules:**
- `endpoint` must be a valid URL
- `catalog_name` must match `^[a-z][a-z0-9_]*$`

---

### 4. CubeDataSource

Cube configuration for DuckDB + Iceberg queries.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | `Literal["duckdb"]` | `"duckdb"` | Database type |
| `polaris_endpoint` | `str` | Required | Polaris REST endpoint |
| `s3_endpoint` | `str` | Required | MinIO/S3 endpoint |
| `cubestore_host` | `str` | `"cubestore-router"` | Cube Store router host |
| `cubestore_port` | `int` | `10000` | Cube Store router port |
| `sql_api_enabled` | `bool` | `true` | Enable SQL API on port 15432 |
| `sql_api_user` | `str` | `"cube"` | SQL API username |
| `sql_api_password` | `SecretStr` | Required | SQL API password |

**Relationships:**
- CubeDataSource → DuckDBCatalogConnection (uses same Polaris/MinIO endpoints)

---

### 5. SeedJob

Dagster job for generating initial demo data.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Job name ("seed_demo_data") |
| `tables` | `list[str]` | Tables to seed (["customers", "products", "orders"]) |
| `record_counts` | `dict[str, int]` | Records per table |
| `status` | `Literal["pending", "running", "completed", "failed"]` | Job status |
| `run_id` | `str | None` | Dagster run ID |

**Default Record Counts:**
```python
{
    "customers": 1000,
    "products": 500,
    "orders": 5000,
    "order_items": 15000
}
```

---

### 6. GenerationSchedule

Dagster schedule for continuous data generation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"generate_orders"` | Schedule name |
| `cron_schedule` | `str` | `"*/5 * * * *"` | Cron expression (every 5 minutes) |
| `enabled` | `bool` | `true` | Schedule enabled |
| `records_per_run` | `int` | `100` | Orders to generate per run |
| `timezone` | `str` | `"UTC"` | Schedule timezone |

**Validation Rules:**
- `cron_schedule` must be valid cron expression
- `records_per_run` must be between 1 and 10000

---

### 7. PolarisInitConfig

Configuration for Polaris initialization Helm hook.

| Field | Type | Description |
|-------|------|-------------|
| `catalog_name` | `str` | Catalog to create (e.g., "demo_catalog") |
| `namespaces` | `list[str]` | Namespaces to create (e.g., ["demo.bronze", "demo.silver"]) |
| `storage_type` | `Literal["S3", "GCS", "AZURE"]` | Storage backend |
| `storage_location` | `str` | S3 bucket/path (e.g., "s3://iceberg-data/") |
| `oauth_client_id` | `str` | OAuth2 client ID for DuckDB access |

**Relationships:**
- PolarisInitConfig → DuckDBCatalogConnection (provides credentials)

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HELM RELEASES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  floe-infrastructure                   floe-dagster                         │
│  ├─► PostgreSQL                        ├─► Webserver                        │
│  ├─► MinIO                             ├─► Daemon                           │
│  ├─► Polaris ──────────────────────────┼─► Workers                          │
│  │    └─► PolarisInitConfig            │    └─► SeedJob                     │
│  ├─► Jaeger                            │    └─► GenerationSchedule          │
│  └─► Marquez                           │                                    │
│                                        │                                    │
│                                        floe-cube                            │
│                                        ├─► Cube API                         │
│  InfrastructureConfig ─────────────────┤    └─► CubeDataSource              │
│  (values-local.yaml)                   │         └─► DuckDBCatalogConnection│
│                                        └─► Cube Store                       │
│                                             ├─► Router                      │
│                                             └─► Workers                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pydantic Models

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator


class DuckDBCatalogConnection(BaseModel):
    """DuckDB connection to Polaris REST catalog."""

    endpoint: str = Field(..., description="Polaris REST endpoint")
    catalog_name: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    client_id: str
    client_secret: SecretStr
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: SecretStr

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a valid HTTP(S) URL")
        return v


class CubeDataSource(BaseModel):
    """Cube configuration for DuckDB + Iceberg."""

    type: Literal["duckdb"] = "duckdb"
    polaris_endpoint: str
    s3_endpoint: str
    cubestore_host: str = "cubestore-router"
    cubestore_port: int = 10000
    sql_api_enabled: bool = True
    sql_api_user: str = "cube"
    sql_api_password: SecretStr


class SeedJob(BaseModel):
    """Dagster job for initial data seeding."""

    name: str = "seed_demo_data"
    tables: list[str] = Field(
        default=["customers", "products", "orders", "order_items"]
    )
    record_counts: dict[str, int] = Field(
        default={
            "customers": 1000,
            "products": 500,
            "orders": 5000,
            "order_items": 15000,
        }
    )
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    run_id: str | None = None


class GenerationSchedule(BaseModel):
    """Dagster schedule for continuous data generation."""

    name: str = "generate_orders"
    cron_schedule: str = "*/5 * * * *"
    enabled: bool = True
    records_per_run: int = Field(default=100, ge=1, le=10000)
    timezone: str = "UTC"


class PolarisInitConfig(BaseModel):
    """Polaris initialization configuration."""

    catalog_name: str = "demo_catalog"
    namespaces: list[str] = Field(
        default=["demo.bronze", "demo.silver", "demo.gold"]
    )
    storage_type: Literal["S3", "GCS", "AZURE"] = "S3"
    storage_location: str = "s3://iceberg-data/"
    oauth_client_id: str = "demo_client"
```

---

## State Transitions

### SeedJob States

```
pending → running → completed
           │
           └─────→ failed
```

**Transitions:**
- `pending → running`: Sensor triggers run
- `running → completed`: All tables seeded successfully
- `running → failed`: Error during data generation

### HelmRelease States

```
pending → deployed
    │
    └─────→ failed
```

**Transitions:**
- `pending → deployed`: `helm install` succeeds
- `pending → failed`: `helm install` fails
- `deployed → deployed`: `helm upgrade` succeeds
