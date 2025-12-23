# Platform Configuration Directory

This directory contains environment-specific platform configurations.

## Structure

```
platform/
├── local/          # Local development (MinIO, local Polaris)
│   └── platform.yaml
├── dev/            # Development environment (AWS dev account)
│   └── platform.yaml
├── staging/        # Staging environment (AWS staging account)
│   └── platform.yaml
└── prod/           # Production environment (AWS prod account)
    └── platform.yaml
```

## Usage

Select environment via `FLOE_PLATFORM_ENV` environment variable or `--platform` CLI flag:

```bash
# Local development
export FLOE_PLATFORM_ENV=local
floe compile

# Or via CLI flag
floe compile --platform staging
```

## Configuration Schema

See [platform-spec.schema.json](../specs/009-two-tier-config/contracts/platform-spec.schema.json) for the full schema.

Each platform.yaml contains:
- **storage**: S3-compatible storage profiles (endpoints, buckets, credentials)
- **catalogs**: Iceberg catalog profiles (Polaris, Glue, Unity)
- **compute**: Compute engine profiles (DuckDB, Snowflake, BigQuery)
- **observability**: Tracing and lineage configuration

## Credential Modes

Platform configurations support multiple credential modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `static` | Client ID/secret from `secret_ref` | Local development, simple deployments |
| `oauth2` | OAuth2 client credentials flow | Production with automatic token refresh |
| `iam_role` | AWS IAM role assumption | AWS deployments, no static credentials |
| `service_account` | GCP/Azure workload identity | Cloud-native deployments |

### Example: OAuth2 with Secret Reference

```yaml
catalogs:
  default:
    type: polaris
    uri: "http://polaris:8181/api/catalog"
    warehouse: warehouse
    credentials:
      mode: oauth2
      client_id:
        secret_ref: polaris-client-id    # Resolved from env var or K8s secret
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
```

### Secret Resolution

Secrets are resolved at **runtime** (not compile time) in this order:
1. Environment variable: `POLARIS_CLIENT_SECRET` (uppercase, underscores)
2. K8s secret mount: `/var/run/secrets/polaris-client-secret`

**Never commit plaintext credentials.** The schema validation rejects configurations with hardcoded secrets.

## Two-Tier Architecture

This directory is part of the two-tier configuration architecture ([ADR-0002](../docs/adr/0002-two-tier-config.md)):

| Tier | File | Owner | Contents |
|------|------|-------|----------|
| **Platform** | `platform.yaml` | Platform Engineer | This directory - infrastructure |
| **Pipeline** | `floe.yaml` | Data Engineer | Project root - pipeline logic |

Data engineers write `floe.yaml` with profile references (`catalog: default`), which are resolved to platform-specific configuration at compile time. This enables the same pipeline to work across all environments without modification.

## Documentation

- [Platform Configuration Guide](../docs/platform-config.md) - Complete reference
- [Security Architecture](../docs/security.md) - Zero-trust credential model
- [ADR-0002](../docs/adr/0002-two-tier-config.md) - Design rationale
