# Pipeline Configuration Guide

> **Status**: T010 Placeholder - Full content in Phase 5 (T078-T082)

## Overview

Pipeline configuration (`floe.yaml`) defines data pipeline concerns managed by Data Engineers:

- Pipeline name and version
- Logical profile references (compute, catalog, storage)
- Transform definitions (dbt models)
- Governance policies (classification, lineage)
- Observability settings (traces, metrics)

## Quick Start

```yaml
# floe.yaml - Data Engineer writes this
name: customer-analytics
version: "1.0.0"

# Logical references only - no infrastructure details
compute: default
catalog: default
storage: default

transforms:
  - type: dbt
    path: ./dbt
    target: prod

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  lineage: true
```

## Key Principle: Separation of Concerns

The `floe.yaml` contains **ZERO** infrastructure details:

- ❌ No endpoints, URIs, or connection strings
- ❌ No credentials or secret references
- ❌ No environment-specific configuration
- ✅ Only logical names (`compute: default`)
- ✅ Same file works across dev/staging/prod

## Compilation

When `floe compile` runs, it merges:

1. `floe.yaml` (logical references)
2. `platform.yaml` (concrete infrastructure)

→ Produces `CompiledArtifacts` with fully resolved configuration

## Related Documentation

- [Platform Configuration](platform-config.md) - Infrastructure configuration
- [Security Architecture](security.md) - Why credentials stay in platform.yaml

---

*TODO(T078-T082): Expand with full pipeline configuration reference*
