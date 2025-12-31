# Platform Configuration Guide

This guide is for **Platform Engineers** who manage infrastructure configuration for floe-runtime.

## Overview

The two-tier configuration architecture separates concerns:

| File | Audience | Contains |
|------|----------|----------|
| `platform.yaml` | Platform Engineers | Infrastructure: storage, catalogs, compute, credentials |
| `floe.yaml` | Data Engineers | Pipelines: transforms, governance, profile references |

Platform engineers configure infrastructure once. Data engineers reference it by name.

## Quick Start

```bash
# 1. Set environment
export FLOE_PLATFORM_ENV=local

# 2. Create platform configuration
mkdir -p platform/local
cat > platform/local/platform.yaml << 'EOF'
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    bucket: iceberg-data
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials

catalogs:
  default:
    type: polaris
    uri: "http://polaris:8181/api/catalog"
    warehouse: demo
    credentials:
      mode: oauth2
      client_id: "root"
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:ALL"

compute:
  default:
    type: duckdb
EOF

# 3. Validate configuration
floe platform validate

# 4. List available profiles
floe platform list-profiles
```

## Environment Selection

Platform configurations are environment-specific. Set `FLOE_PLATFORM_ENV` to select:

```bash
export FLOE_PLATFORM_ENV=local    # platform/local/platform.yaml
export FLOE_PLATFORM_ENV=dev      # platform/dev/platform.yaml
export FLOE_PLATFORM_ENV=staging  # platform/staging/platform.yaml
export FLOE_PLATFORM_ENV=prod     # platform/prod/platform.yaml
```

Or specify a file directly:

```bash
export FLOE_PLATFORM_FILE=/path/to/custom-platform.yaml
```

## Schema Reference

### Top-Level Structure

```yaml
version: "1.0.0"                    # Schema version (semver)

storage:                            # Named storage profiles
  <profile_name>: <StorageProfile>

catalogs:                           # Named catalog profiles
  <profile_name>: <CatalogProfile>

compute:                            # Named compute profiles
  <profile_name>: <ComputeProfile>

observability:                      # Optional observability config
  <ObservabilityConfig>
```

### Storage Profiles

Configure S3-compatible object storage backends.

```yaml
storage:
  default:                          # Profile name (referenced in floe.yaml)
    type: s3                        # s3 | gcs | azure | local
    endpoint: ""                    # Empty for AWS S3, set for MinIO/LocalStack
    region: us-east-1               # AWS region
    bucket: iceberg-data            # Bucket name (3-63 chars)
    path_style_access: false        # true for MinIO, false for AWS S3
    credentials:
      mode: static                  # static | iam_role | service_account
      secret_ref: storage-creds     # K8s secret name or env var prefix
```

**Storage Types:**

| Type | Description | Endpoint Required |
|------|-------------|-------------------|
| `s3` | AWS S3 or S3-compatible (MinIO, LocalStack) | Only for non-AWS |
| `gcs` | Google Cloud Storage | No |
| `azure` | Azure Blob Storage | No |
| `local` | Local filesystem (dev only) | No |

**Local Development (MinIO):**

```yaml
storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    bucket: iceberg-data
    path_style_access: true         # Required for MinIO
    credentials:
      mode: static
      secret_ref: minio-credentials
```

**Production (AWS S3 with IAM):**

```yaml
storage:
  default:
    type: s3
    endpoint: ""                    # Empty = AWS S3
    bucket: prod-data-lake
    path_style_access: false
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/DataLakeRole"
```

### Catalog Profiles

Configure Iceberg REST catalog connections.

```yaml
catalogs:
  default:                          # Profile name
    type: polaris                   # polaris | glue | nessie | rest | hive
    uri: "http://polaris:8181/api/catalog"
    warehouse: demo                 # Catalog/warehouse name
    namespace: default              # Default namespace
    credentials:
      mode: oauth2                  # static | oauth2 | iam_role | service_account
      client_id: "root"
      client_secret:
        secret_ref: polaris-secret
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials  # vended-credentials | remote-signing | none
    token_refresh_enabled: true     # Auto-refresh OAuth2 tokens
    properties:                     # Additional catalog properties
      rest.auth-type: oauth2
```

**Catalog Types:**

| Type | Description | Use Case |
|------|-------------|----------|
| `polaris` | Apache Polaris REST catalog | Primary recommendation |
| `glue` | AWS Glue Data Catalog | AWS-native deployments |
| `nessie` | Project Nessie | Git-like versioning |
| `rest` | Generic Iceberg REST | Other REST catalogs |
| `hive` | Hive Metastore | Legacy systems |

**Namespace Format:**

Namespaces in `platform.yaml` follow the Iceberg REST specification:

- **Warehouse**: Defined in `catalogs.<catalog_name>.warehouse` (catalog-level config parameter)
- **Namespace**: Logical grouping within warehouse (NO warehouse prefix)

The warehouse and namespace are separate concepts in Iceberg REST:

```yaml
catalogs:
  default:
    type: polaris
    warehouse: demo_catalog  # ← Warehouse defined here

layers:
  bronze:
    catalog_ref: default
    namespace: bronze  # ← Simple namespace (NOT demo_catalog.bronze)
```

**Why separate warehouse from namespace**:
- Aligns with Iceberg REST API specification
- Warehouse is a config parameter, not part of the namespace path
- Supports multi-warehouse scenarios via `catalog_ref` indirection
- Enables clean namespace hierarchies without warehouse prefix duplication

**REST URL Construction**:
```
/api/catalog/v1/{warehouse}/namespaces/{namespace}/tables
                 ^^^^^^^^^              ^^^^^^^^^
                 From catalog           From layer
```

**Namespace Examples**:

| Format | Description | Use Case |
|--------|-------------|----------|
| `bronze` | Simple namespace | Single-level organization |
| `analytics.bronze` | Nested namespace | Team-based organization |
| `prod.analytics.bronze` | Multi-level | Environment + team + layer |

**Access Delegation Modes:**

| Mode | Description | When to Use |
|------|-------------|-------------|
| `vended-credentials` | Catalog vends temporary STS credentials | Recommended for production |
| `remote-signing` | Catalog signs requests remotely | High-security environments |
| `none` | Use storage credentials directly | Local development |

**OAuth2 Scopes:**

| Scope | Access Level | Environment |
|-------|--------------|-------------|
| `PRINCIPAL_ROLE:ALL` | Full access | Local development only |
| `PRINCIPAL_ROLE:DATA_ENGINEER` | Read/write tables | Standard data engineering |
| `PRINCIPAL_ROLE:DATA_ANALYST` | Read-only access | Reporting/analytics |

### Compute Profiles

Configure dbt compute targets.

```yaml
compute:
  default:                          # Profile name
    type: duckdb                    # duckdb | snowflake | bigquery | ...
    properties:                     # Target-specific properties
      path: ":memory:"
      threads: 4
    credentials:
      mode: static
      secret_ref: compute-creds
```

**Compute Types and Properties:**

| Type | Required Properties | Optional Properties |
|------|---------------------|---------------------|
| `duckdb` | - | `path`, `threads`, `memory_limit` |
| `snowflake` | `account` | `warehouse`, `database`, `schema`, `role` |
| `bigquery` | `project` | `dataset`, `location` |
| `redshift` | `host` | `port`, `database` |
| `databricks` | `host`, `http_path` | `catalog` |
| `postgres` | `host` | `port`, `database` |

**DuckDB (Local Development):**

```yaml
compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"              # In-memory database
      threads: 4
```

**Snowflake (Production):**

```yaml
compute:
  default:
    type: snowflake
    properties:
      account: "acme.us-east-1"
      warehouse: PROD_WH
      database: PROD_DB
      schema: ANALYTICS
      role: DATA_ENGINEER
    credentials:
      mode: static
      secret_ref: snowflake-credentials
```

### Observability Configuration

Configure OpenTelemetry traces and OpenLineage lineage.

```yaml
observability:
  traces: true                      # Enable OTel traces
  metrics: true                     # Enable metrics
  lineage: true                     # Enable OpenLineage
  otlp_endpoint: "http://jaeger:4317"      # OTLP exporter endpoint
  lineage_endpoint: "http://marquez:5000"  # OpenLineage endpoint
  attributes:                       # Custom trace attributes
    service.name: my-pipeline
    deployment.environment: production
```

## Credential Management

### Credential Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `static` | Credentials from K8s secret or env var | Simple deployments |
| `oauth2` | OAuth2 client credentials flow | Polaris, enterprise systems |
| `iam_role` | AWS IAM role assumption | AWS production |
| `service_account` | GCP/Azure workload identity | Cloud-native |

### Secret Resolution

Secrets are **never** stored in configuration files. Use `secret_ref` to reference:

1. **Environment variables**: `SECRET_REF` -> looks for `SECRET_REF` env var (uppercase with underscores)
2. **K8s secrets**: Mounted at `/var/run/secrets/{secret_ref}`

```yaml
# References POLARIS_CLIENT_SECRET env var or /var/run/secrets/polaris-client-secret
credentials:
  mode: oauth2
  client_secret:
    secret_ref: polaris-client-secret
```

### Setting Up Secrets

**Environment Variables (Local Development):**

```bash
export POLARIS_CLIENT_SECRET="your-secret-here"
export MINIO_CREDENTIALS="access_key:secret_key"
```

**Kubernetes Secrets (Production):**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: polaris-oauth-prod
type: Opaque
stringData:
  client_secret: "your-oauth-secret"
```

## Complete Examples

### Local Development

```yaml
# platform/local/platform.yaml
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    region: us-east-1
    bucket: iceberg-data
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials

catalogs:
  default:
    type: polaris
    uri: "http://polaris:8181/api/catalog"
    warehouse: demo
    namespace: default
    credentials:
      mode: oauth2
      client_id: "root"
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:ALL"
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"
      threads: 4

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: "http://jaeger:4317"
  lineage_endpoint: "http://marquez:5000"
  attributes:
    service.name: floe-local
    deployment.environment: local
```

### Production Environment

```yaml
# platform/prod/platform.yaml
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: ""                    # AWS S3
    region: us-east-1
    bucket: prod-data-lake
    path_style_access: false
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/DataLakeRole"

  archive:
    type: s3
    endpoint: ""
    region: us-east-1
    bucket: prod-archive
    path_style_access: false
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/ArchiveRole"

catalogs:
  default:
    type: polaris
    uri: "https://polaris.example.com/api/catalog"
    warehouse: production
    namespace: prod
    credentials:
      mode: oauth2
      client_id: "prod-service"
      client_secret:
        secret_ref: polaris-oauth-prod
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials
    token_refresh_enabled: true

  analytics:
    type: polaris
    uri: "https://polaris.example.com/api/catalog"
    warehouse: analytics
    namespace: analytics
    credentials:
      mode: oauth2
      client_id: "analytics-service"
      client_secret:
        secret_ref: polaris-analytics-prod
      scope: "PRINCIPAL_ROLE:DATA_ANALYST"
    access_delegation: vended-credentials

compute:
  default:
    type: snowflake
    properties:
      account: "acme.us-east-1"
      warehouse: PROD_WH
      database: PROD_DB
      role: DATA_ENGINEER
    credentials:
      mode: static
      secret_ref: snowflake-prod

  reporting:
    type: snowflake
    properties:
      account: "acme.us-east-1"
      warehouse: REPORTING_WH
      database: PROD_DB
      role: REPORTING_SERVICE
    credentials:
      mode: static
      secret_ref: snowflake-reporting

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: "https://otel.example.com:4317"
  lineage_endpoint: "https://marquez.example.com:5000"
  attributes:
    service.name: floe-production
    deployment.environment: production
```

## CLI Commands

```bash
# Validate platform configuration
floe platform validate
floe platform validate --platform-file /path/to/platform.yaml

# List available profiles
floe platform list-profiles
floe platform list-profiles --json

# Export JSON Schema for IDE support
floe schema export --output schemas/platform.schema.json
```

## Troubleshooting

### Common Errors

**"No platform configuration found"**

```bash
# Check environment variable
echo $FLOE_PLATFORM_ENV

# Verify file exists
ls -la platform/$FLOE_PLATFORM_ENV/platform.yaml
```

**"Secret not found"**

```bash
# Check environment variable (uppercase with underscores)
echo $POLARIS_CLIENT_SECRET

# For K8s, check secret mount
ls -la /var/run/secrets/
```

**"Invalid profile name"**

Profile names must:
- Start with a letter
- Contain only letters, numbers, hyphens, underscores
- Match pattern: `^[a-zA-Z][a-zA-Z0-9_-]*$`

### Validation

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('platform/local/platform.yaml'))"

# Validate against schema
floe platform validate --platform-file platform/local/platform.yaml
```

## Related Documentation

- [Pipeline Configuration Guide](pipeline-config.md) - For data engineers
- [Security Architecture](security.md) - Credential flows and zero-trust model
- [ADR-0002: Two-Tier Configuration](adr/0002-two-tier-config.md) - Design rationale
