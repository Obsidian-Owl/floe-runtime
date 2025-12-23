# Pipeline Configuration Guide

This guide is for **Data Engineers** who build and configure data pipelines with floe-runtime.

## Overview

The two-tier configuration architecture separates concerns:

| File | Audience | Contains |
|------|----------|----------|
| `platform.yaml` | Platform Engineers | Infrastructure: storage, catalogs, compute, credentials |
| `floe.yaml` | Data Engineers | Pipelines: transforms, governance, profile references |

Data engineers focus on pipeline logic. Platform engineers handle infrastructure.

## Quick Start

```bash
# 1. Create your pipeline configuration
cat > floe.yaml << 'EOF'
name: my-pipeline
version: "1.0.0"

# Logical references - resolved from platform.yaml
storage: default
catalog: default
compute: default

transforms:
  - type: dbt
    path: ./dbt

governance:
  classification_source: dbt_meta

observability:
  traces: true
  lineage: true
EOF

# 2. Validate your configuration
floe validate

# 3. Compile to artifacts
floe compile

# 4. Run the pipeline
floe run
```

## Schema Reference

### Top-Level Structure

```yaml
name: my-pipeline                # Pipeline name (required)
version: "1.0.0"                 # Semantic version (required)

# Profile references (resolved at compile time)
storage: default                 # Storage profile name
catalog: default                 # Catalog profile name
compute: default                 # Compute profile name

transforms:                      # Transformation steps
  - <TransformConfig>

consumption:                     # Semantic layer (Cube)
  <ConsumptionConfig>

governance:                      # Data governance
  <GovernanceConfig>

observability:                   # Observability settings
  <ObservabilityConfig>
```

### Profile References

Profile references are **logical names** that resolve to infrastructure defined in `platform.yaml`. This enables the same `floe.yaml` to work across all environments.

```yaml
# floe.yaml - works in dev, staging, prod
storage: default        # Resolves to S3/MinIO/GCS depending on environment
catalog: default        # Resolves to Polaris/Glue/Unity depending on environment
compute: default        # Resolves to DuckDB/Snowflake/BigQuery depending on environment
```

**Why this matters:**
- Same pipeline definition across environments
- No infrastructure details leak into pipeline code
- Platform engineers control infrastructure
- Data engineers focus on data logic

**Profile naming rules:**
- Start with a letter
- Contain only letters, numbers, hyphens, underscores
- Pattern: `^[a-zA-Z][a-zA-Z0-9_-]*$`

**Common profiles:**

| Profile Name | Description |
|-------------|-------------|
| `default` | Standard profile for most workloads |
| `archive` | Cold storage for historical data |
| `analytics` | Read-optimized for reporting |
| `high-performance` | Compute-intensive workloads |

### Transform Configuration

Define SQL transformations using dbt.

```yaml
transforms:
  - type: dbt                    # Transform type (currently only 'dbt')
    path: ./dbt                  # Path to dbt project (relative to floe.yaml)
    target: prod                 # Optional target override
```

**Transform types:**

| Type | Description | Status |
|------|-------------|--------|
| `dbt` | dbt SQL transformations | Supported |
| `python` | Python transformations | Planned |
| `flink` | Apache Flink streaming | Planned |

**Example with multiple transforms:**

```yaml
transforms:
  - type: dbt
    path: ./dbt/bronze
    target: bronze

  - type: dbt
    path: ./dbt/silver
    target: silver

  - type: dbt
    path: ./dbt/gold
    target: gold
```

### Consumption Configuration (Cube)

Configure the Cube semantic layer for data consumption.

```yaml
consumption:
  enabled: true                  # Enable Cube semantic layer
  port: 4000                     # Cube API port
  database_type: postgres        # Database driver type
  dev_mode: false                # Enable Cube Playground
  api_secret_ref: cube-api-key   # K8s secret for API key

  pre_aggregations:
    refresh_schedule: "*/30 * * * *"    # Cron expression
    timezone: UTC                        # Schedule timezone
    external: true                       # Use Cube Store (recommended)
    cube_store:
      enabled: true
      s3_bucket: my-cube-preaggs
      s3_region: us-east-1

  security:
    row_level: true              # Enable row-level security
    filter_column: organization_id  # Column for RLS filtering
```

**Database types:**

| Type | Description |
|------|-------------|
| `postgres` | PostgreSQL / Polaris SQL API |
| `duckdb` | DuckDB (local development) |
| `snowflake` | Snowflake |
| `bigquery` | Google BigQuery |
| `trino` | Trino / Presto |

**Pre-aggregation storage:**

| Mode | Description | Use Case |
|------|-------------|----------|
| `external: true` | Cube Store (Parquet on S3) | Production |
| `external: false` | Source database storage | Development/testing |

### Governance Configuration

Configure data governance and classification.

```yaml
governance:
  classification_source: dbt_meta    # Source for classifications
  emit_lineage: true                 # Emit OpenLineage events
  policies:                          # Custom policies
    masking:
      - pattern: "*email*"
        action: hash
```

**Classification sources:**

| Source | Description |
|--------|-------------|
| `dbt_meta` | Extract from dbt model meta tags (default) |
| `external` | External classification service |

**dbt meta tag example:**

```yaml
# In dbt schema.yml
models:
  - name: customers
    columns:
      - name: email
        meta:
          floe:
            classification: pii
            pii_type: email
            sensitivity: high

      - name: customer_id
        meta:
          floe:
            classification: identifier
            sensitivity: low
```

**Classification types:**

| Type | Description | Sensitivity |
|------|-------------|-------------|
| `pii` | Personally identifiable information | high |
| `confidential` | Business-sensitive data | high |
| `internal` | Internal use only | medium |
| `public` | Public data | low |
| `identifier` | Non-sensitive identifiers | low |

### Observability Configuration

Configure tracing, metrics, and lineage.

```yaml
observability:
  traces: true                   # Enable OpenTelemetry traces
  metrics: true                  # Enable metrics collection
  lineage: true                  # Enable OpenLineage emission
  attributes:                    # Custom trace attributes
    service.name: my-pipeline
    deployment.environment: production
    team: data-engineering
```

**Note:** Observability endpoints (OTLP collector, OpenLineage API) are configured in `platform.yaml`, not here. Data engineers only control what to trace, not where traces go.

**Common attributes:**

| Attribute | Description |
|-----------|-------------|
| `service.name` | Pipeline name for trace grouping |
| `deployment.environment` | Environment (dev, staging, prod) |
| `team` | Owning team for filtering |
| `version` | Pipeline version |

## Complete Examples

### Simple Pipeline

```yaml
# floe.yaml - Minimal configuration
name: simple-etl
version: "1.0.0"

transforms:
  - type: dbt
    path: ./dbt
```

### Analytics Pipeline with Governance

```yaml
# floe.yaml - Analytics with PII handling
name: customer-analytics
version: "2.0.0"

storage: default
catalog: analytics
compute: default

transforms:
  - type: dbt
    path: ./dbt/models
    target: prod

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  lineage: true
  attributes:
    service.name: customer-analytics
    team: analytics
```

### Production Pipeline with Cube

```yaml
# floe.yaml - Production with semantic layer
name: sales-reporting
version: "3.1.0"

storage: default
catalog: default
compute: high-performance

transforms:
  - type: dbt
    path: ./dbt
    target: prod

consumption:
  enabled: true
  port: 4000
  database_type: postgres
  pre_aggregations:
    refresh_schedule: "0 * * * *"
    external: true
    cube_store:
      enabled: true
      s3_bucket: sales-cube-preaggs
      s3_region: us-east-1
  security:
    row_level: true
    filter_column: region_id

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  metrics: true
  lineage: true
  attributes:
    service.name: sales-reporting
    deployment.environment: production
```

## CLI Commands

```bash
# Validate floe.yaml
floe validate
floe validate --file custom-floe.yaml

# Compile to artifacts
floe compile
floe compile --output target/

# Run pipeline
floe run
floe run --target prod

# Export JSON Schema for IDE support
floe schema export --output schemas/floe.schema.json
```

## IDE Support

Add JSON Schema for autocomplete and validation:

```yaml
# floe.yaml
# $schema: ./schemas/floe.schema.json

name: my-pipeline
version: "1.0.0"
# ... IDE provides autocomplete from here
```

Generate the schema:

```bash
floe schema export --output schemas/floe.schema.json
```

## Security

### No Credentials in floe.yaml

**IMPORTANT:** floe.yaml should NEVER contain:
- API keys or tokens
- Passwords or secrets
- Endpoints or URIs
- Credential references

If you attempt to add credentials, the validation will fail:

```bash
$ floe validate
ERROR: Credential detected in floe.yaml - credentials belong in platform.yaml
```

### Secret References

For Cube API keys and other secrets, use K8s secret references:

```yaml
consumption:
  api_secret_ref: cube-api-key  # References K8s secret, not actual key
```

Platform engineers create the actual secrets in Kubernetes.

## Troubleshooting

### Common Errors

**"Profile not found"**

```bash
ERROR: Profile 'analytics' not found in platform.yaml
```

Check that the profile exists in platform.yaml or use `default`.

**"Credential detected"**

```bash
ERROR: Credential detected in 'api_key' field
```

Remove credentials from floe.yaml. Credentials belong in platform.yaml.

**"Invalid profile name"**

```bash
ERROR: Invalid profile name '123-bad'
```

Profile names must start with a letter and contain only alphanumeric, hyphen, underscore.

### Validation

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('floe.yaml'))"

# Validate against schema
floe validate --file floe.yaml

# Check for credentials
floe validate --strict
```

## Related Documentation

- [Platform Configuration Guide](platform-config.md) - For platform engineers
- [Security Architecture](security.md) - Credential flows and access control
- [ADR-0002: Two-Tier Configuration](adr/0002-two-tier-config.md) - Design rationale
