# Platform Configuration Guide

> **Status**: T010 Placeholder - Full content in Phase 5 (T078-T082)

## Overview

Platform configuration (`platform.yaml`) defines infrastructure concerns managed by Platform Engineers:

- Storage profiles (S3, GCS, ADLS endpoints)
- Catalog profiles (Polaris, Glue, Unity connections)
- Compute profiles (dbt adapter configurations)
- Credential management (secret references, OAuth2 scopes)
- Observability endpoints (OTel, OpenLineage)

## Quick Start

```yaml
# platform/local/platform.yaml
version: "1.0.0"
environment: local

storage:
  default:
    type: s3
    endpoint: http://localhost:9000
    bucket: warehouse
    path_style_access: true

catalogs:
  default:
    type: polaris
    uri: http://localhost:8181/api/catalog
    warehouse: local_catalog
```

## Environment Selection

Set the `FLOE_PLATFORM_ENV` environment variable to select the platform configuration:

```bash
export FLOE_PLATFORM_ENV=local  # Uses platform/local/platform.yaml
export FLOE_PLATFORM_ENV=prod   # Uses platform/prod/platform.yaml
```

## Detailed Documentation

- [Security Architecture](security.md) - Credential modes and secret management
- [ADR-0002](adr/0002-two-tier-config.md) - Two-tier configuration decision record

---

*TODO(T078-T082): Expand with full platform configuration reference*
