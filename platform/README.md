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

## Credential Security

Platform configurations use `secret_ref:` references instead of inline credentials:

```yaml
catalogs:
  default:
    credentials:
      mode: oauth2
      client_id: ${POLARIS_CLIENT_ID}  # Env var reference
      client_secret:
        secret_ref: polaris-oauth-secret  # K8s secret reference
```

**Never commit plaintext credentials.** The system validates and rejects configurations with hardcoded secrets.
