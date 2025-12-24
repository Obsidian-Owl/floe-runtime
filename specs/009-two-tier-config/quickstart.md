# Quickstart: Two-Tier Configuration Architecture

**Purpose**: Get started with the platform.yaml + floe.yaml configuration pattern
**Audience**: Platform Engineers and Data Engineers
**Prerequisites**: floe-runtime installed, basic familiarity with YAML

---

## Overview

The two-tier configuration separates concerns:

| File | Owner | Contains |
|------|-------|----------|
| `platform.yaml` | Platform Engineer | Infrastructure, credentials, endpoints |
| `floe.yaml` | Data Engineer | Pipelines, transforms, governance |

**Key principle**: Data engineers never see credentials or infrastructure details.

---

## For Data Engineers

### Step 1: Create floe.yaml

```yaml
# floe.yaml - Your pipeline definition
name: customer-analytics
version: "1.0.0"

# Logical references only - no URLs, no credentials
catalog: default
storage: default
compute: default

transforms:
  - type: dbt
    path: ./dbt

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  lineage: true
```

That's it. The same file works in dev, staging, and production.

### Step 2: Run Your Pipeline

```bash
# Local development (platform.yaml or env vars provide config)
floe run

# CI/CD will inject environment-specific platform.yaml
```

### What You CAN'T Do (By Design)

```yaml
# FORBIDDEN - Security violation
catalog:
  uri: http://polaris.internal:8181  # NO - infrastructure detail
  client_secret: abc123               # NO - credential in code
```

If you try this, validation will fail with a clear error.

---

## For Platform Engineers

### Step 1: Create platform.yaml

```yaml
# platform/local/platform.yaml - Local development
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: http://localhost:9000  # MinIO
    region: us-east-1
    bucket: demo-bucket
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials

catalogs:
  default:
    type: polaris
    uri: http://localhost:8181/api/catalog
    warehouse: demo
    credentials:
      mode: oauth2
      client_id: data-platform-svc
      client_secret:
        secret_ref: POLARIS_CLIENT_SECRET
      scope: PRINCIPAL_ROLE:ALL
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: duckdb
    properties:
      threads: 4

observability:
  traces: true
  otlp_endpoint: http://localhost:4317
  lineage: true
  lineage_endpoint: http://localhost:5000
```

### Step 2: Create Secrets

```bash
# For local development, use environment variables
export POLARIS_CLIENT_SECRET="your-oauth-secret"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"

# For Kubernetes, create secrets
kubectl create secret generic polaris-oauth \
  --from-literal=client_id=data-platform-svc \
  --from-literal=client_secret=your-oauth-secret
```

### Step 3: Create Environment-Specific Configs

```
platform/
├── local/
│   └── platform.yaml     # LocalStack/MinIO endpoints
├── dev/
│   └── platform.yaml     # Dev AWS endpoints
├── staging/
│   └── platform.yaml     # Staging endpoints
└── prod/
    └── platform.yaml     # Production endpoints
```

### Production Example

```yaml
# platform/prod/platform.yaml
version: "1.0.0"

storage:
  default:
    type: s3
    region: us-east-1
    bucket: prod-iceberg-data
    credentials:
      mode: iam_role
      role_arn: arn:aws:iam::123456789012:role/FloeStorageRole

catalogs:
  default:
    type: polaris
    uri:
      secret_ref: POLARIS_PROD_URI  # Hide internal topology
    warehouse: production
    credentials:
      mode: oauth2
      client_id:
        secret_ref: POLARIS_CLIENT_ID
      client_secret:
        secret_ref: POLARIS_CLIENT_SECRET
      scope: PRINCIPAL_ROLE:DATA_ENGINEER  # Least privilege
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: snowflake
    properties:
      account: acme.us-east-1
      warehouse: ANALYTICS_WH
    credentials:
      mode: static
      secret_ref: snowflake-prod-credentials
```

---

## Credential Modes Reference

| Mode | Use Case | Secret Contains |
|------|----------|-----------------|
| `static` | Local dev, K8s secrets | access_key, secret_key |
| `oauth2` | Polaris catalog | client_id, client_secret |
| `iam_role` | AWS production | (no secret - uses STS) |
| `service_account` | GCP/Azure | (uses workload identity) |

---

## Common Workflows

### Adding a New Environment

1. Create `platform/<env>/platform.yaml`
2. Create K8s secrets in target cluster
3. Deploy - data engineers change nothing

### Changing Storage Endpoint

1. Platform engineer updates `platform.yaml`
2. Redeploy - data engineers change nothing

### Rotating Credentials

1. Update K8s secret
2. Restart pods - no config file changes needed

---

## Troubleshooting

### "Profile 'X' not found"

```
ConfigurationError: Profile 'analytics' not found in platform.catalogs
  File: /app/floe.yaml, field: catalog
  Available profiles: [default, production]
```

**Fix**: Add the missing profile to platform.yaml or use an existing profile name.

### "Secret 'X' not found"

```
SecretNotFoundError: Secret 'polaris-oauth' not found
  Expected: Environment variable POLARIS_OAUTH or K8s secret polaris-oauth
```

**Fix**: Create the environment variable or K8s secret.

### "Field 'X' must use secret_ref"

```
ValidationError: Field 'client_secret' must use secret_ref, not plaintext value
  File: platform.yaml, line 15
```

**Fix**: Use `secret_ref:` syntax instead of inline value:
```yaml
client_secret:
  secret_ref: MY_SECRET_NAME
```

---

## Production Deployment Notes

### Token TTL Configuration

Cloud provider credentials use short-lived tokens with automatic renewal:

| Provider | Default TTL | Maximum | Notes |
|----------|-------------|---------|-------|
| AWS STS (IRSA) | 1 hour | 12 hours | Configure via IAM role trust policy `DurationSeconds` |
| GCP Workload Identity | 1 hour | 12 hours | SDK handles auto-refresh transparently |
| Azure Workload Identity | 1 hour | 24 hours | SDK handles auto-refresh transparently |
| OAuth2 (Polaris) | Varies | Provider-specific | Set `token_refresh_enabled: true` |

**Best Practices**:
- Keep default 1-hour TTL for security (shorter = smaller blast radius)
- SDK auto-refreshes at ~80% expiry (no application code needed)
- For batch jobs >1 hour, consider increasing TTL via IAM policy

### HashiCorp Vault Integration (Future)

The platform supports three Vault integration patterns:

1. **Vault Secrets Operator (Recommended)**: Vault operator syncs secrets to K8s secrets. No config changes needed—existing `secret_ref` works.

2. **Vault Agent Injector**: Sidecar injects secrets to file paths. Add annotation to pod spec.

3. **Direct API**: Application authenticates directly. Future `vault_config` section in platform.yaml.

---

## Next Steps

- [Data Model Reference](data-model.md) - Full entity documentation
- [Research Document](research.md) - Design decisions and rationale (includes future extensibility)
- [JSON Schemas](contracts/) - IDE autocomplete schemas
