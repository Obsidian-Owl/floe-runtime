# Security Architecture

This document describes the security architecture for floe-runtime, designed for enterprise-grade deployments.

## Overview

Floe-runtime implements security-by-design principles with a zero-trust approach:

- **Zero secrets in code** - Credentials never appear in configuration files
- **Least privilege** - Each component has minimal required permissions
- **Defense in depth** - Multiple layers of security controls
- **Audit everywhere** - All operations traced and logged

## Threat Model

| Threat | Impact | Mitigation |
|--------|--------|------------|
| Credential exposure in config files | Critical | Credentials never in floe.yaml; only secret_ref names |
| Overly permissive access | High | Per-profile OAuth2 scopes with least-privilege |
| Credential theft from containers | High | Short-lived tokens, vended credentials, IAM roles |
| Unauthorized catalog access | High | Catalog-level RBAC (Polaris roles + grants) |
| Man-in-the-middle attacks | High | TLS everywhere, certificate validation |
| Audit trail gaps | Medium | OpenLineage lineage, OTel traces for all operations |
| Credential rotation failure | Medium | Automatic token refresh, no static credentials |
| Secret sprawl | Medium | Centralized K8s secrets, no config file secrets |

## Security Principles

### 1. Zero Secrets in Code

The two-tier architecture enforces strict separation:

```
┌─────────────────────────────────────────────────────────────┐
│  Data Engineer (floe.yaml)                                   │
│  • NEVER contains credentials, endpoints, or infrastructure │
│  • Only logical names: storage: "default", catalog: "prod"  │
│  • Scanned with detect-secrets before parsing               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Platform Engineer (platform.yaml)                           │
│  • Contains secret references (not actual secrets)          │
│  • secret_ref: "polaris-oauth-secret" (K8s secret name)     │
│  • Never committed to git with real credentials             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Kubernetes Secrets                                          │
│  • Actual credentials stored encrypted at rest              │
│  • Mounted as files or injected as environment variables    │
│  • Managed by platform team, external secrets operators     │
└─────────────────────────────────────────────────────────────┘
```

### 2. Least Privilege by Default

Each profile defines explicit OAuth2 scopes:

| Environment | OAuth2 Scope | Permissions |
|-------------|--------------|-------------|
| Local Development | `PRINCIPAL_ROLE:ALL` | Full access (local only) |
| Development | `PRINCIPAL_ROLE:DEV` | Read all, write own tables |
| Production | `PRINCIPAL_ROLE:DATA_ENGINEER` | Read + write assigned tables |
| Analytics | `PRINCIPAL_ROLE:DATA_ANALYST` | Read-only access |

**Example configuration:**

```yaml
# platform.yaml
catalogs:
  production:
    credentials:
      mode: oauth2
      scope: PRINCIPAL_ROLE:DATA_ENGINEER
      # Limited to production tables only
```

### 3. Credential Injection Modes

Floe-runtime supports multiple credential management strategies:

| Mode | Description | Use Case |
|------|-------------|----------|
| `static` | K8s secret with static credentials | Simple deployments |
| `oauth2` | OAuth2 client credentials flow | Polaris, enterprise systems |
| `iam_role` | AWS IAM role assumption | AWS-native deployments |
| `service_account` | GCP/Azure workload identity | Cloud-native deployments |

**Recommended for production:**

```yaml
credentials:
  mode: iam_role
  role_arn: arn:aws:iam::123456789:role/FloeDataPlatform
  # No static credentials - uses instance metadata
```

### 4. Short-Lived Credentials

- OAuth2 tokens expire after 1 hour (configurable)
- Automatic token refresh before expiration
- STS credentials for S3 access (15-60 minute TTL)
- No long-lived credentials in production

## Credential Flow

### OAuth2 + Vended Credentials (Production)

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Dagster    │────▶│  Polaris OAuth  │────▶│   Polaris    │
│    Pod       │     │   (get token)   │     │   Catalog    │
└──────────────┘     └─────────────────┘     └──────────────┘
       │                                            │
       │ Access token with scope                    │
       │ PRINCIPAL_ROLE:DATA_ENGINEER               │
       ▼                                            ▼
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   PyIceberg  │────▶│  Polaris STS    │────▶│   S3/MinIO   │
│   (read/     │     │  (vend creds)   │     │   Storage    │
│    write)    │     │                 │     │              │
└──────────────┘     └─────────────────┘     └──────────────┘
                     │
                     │ Temporary S3 credentials
                     │ (15-60 min TTL)
                     ▼
              Credentials NEVER stored
              in container filesystem
```

### Secret Resolution

Secrets are resolved at runtime using this priority:

1. **Environment variable**: `{SECRET_REF_UPPER_SNAKE_CASE}`
   - Example: `polaris-oauth-secret` → `POLARIS_OAUTH_SECRET`
2. **K8s secret mount**: `/var/run/secrets/{secret_ref}`
3. **Fail with clear error** if not found

```python
# Example: SecretReference resolution
ref = SecretReference(secret_ref="polaris-oauth-secret")
secret = ref.resolve()  # Returns SecretStr
```

## Configuration Security

### Credential Detection

All configuration files are scanned with [detect-secrets](https://github.com/Yelp/detect-secrets) before parsing:

```python
# floe.yaml with embedded credential will FAIL validation
$ floe validate
ERROR: Field 'catalog' contains a potential credential (AWS Access Key).
       floe.yaml should only contain logical profile references.
       Move credentials to platform.yaml or K8s secrets.
```

**Detected patterns:**
- AWS Access Keys / Secret Keys
- API tokens and passwords
- Private keys and certificates
- Base64-encoded secrets
- High-entropy strings

### Git Security

**NEVER commit:**
- `.env` files with real credentials
- `platform.yaml` with actual secrets
- K8s secret YAML with stringData populated

**Use these patterns:**

```yaml
# platform.yaml - SAFE to commit
catalogs:
  production:
    credentials:
      mode: oauth2
      client_id: "data-platform-svc"
      client_secret:
        secret_ref: polaris-prod-oauth  # Just the reference, not the value
```

```yaml
# K8s secret - created by platform team, NOT committed
apiVersion: v1
kind: Secret
metadata:
  name: polaris-prod-oauth
stringData:
  client_secret: "actual-secret-value"  # Never in git
```

## Kubernetes Security

### Pod Security

```yaml
# Recommended pod security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### Network Policies

```yaml
# Example: Dagster can only reach Polaris and storage
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dagster-egress
spec:
  podSelector:
    matchLabels:
      app: dagster
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: polaris
      ports:
        - port: 8181
    - to:
        - podSelector:
            matchLabels:
              app: minio
      ports:
        - port: 9000
```

### Secret Management

**Recommended approaches:**

| Approach | Description | Complexity |
|----------|-------------|------------|
| K8s Secrets + RBAC | Basic K8s secrets with access control | Low |
| External Secrets Operator | Sync from Vault/AWS SM/GCP SM | Medium |
| HashiCorp Vault | Full secrets management | High |
| AWS Secrets Manager | AWS-native secrets | Medium |

**External Secrets Operator example:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: polaris-oauth
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: polaris-prod-oauth
  data:
    - secretKey: client_secret
      remoteRef:
        key: prod/polaris/oauth
        property: client_secret
```

## Access Control

### Polaris RBAC

Polaris provides catalog-level access control:

```sql
-- Create a principal role with limited access
CREATE PRINCIPAL_ROLE data_engineer;

-- Grant access to specific catalog
GRANT CATALOG_MANAGE_ACCESS ON CATALOG production TO PRINCIPAL_ROLE data_engineer;

-- Assign to service principal
GRANT PRINCIPAL_ROLE data_engineer TO PRINCIPAL service_account;
```

### OAuth2 Scopes

| Scope | Access Level |
|-------|--------------|
| `PRINCIPAL_ROLE:ALL` | Full access (admin) |
| `PRINCIPAL_ROLE:DATA_ENGINEER` | Read/write tables |
| `PRINCIPAL_ROLE:DATA_ANALYST` | Read-only |
| `PRINCIPAL_ROLE:SERVICE` | Automated pipeline access |

## Audit and Observability

### Trace Context

All operations include trace context for audit:

```python
observability:
  traces: true
  attributes:
    service.name: my-pipeline
    principal: data-platform-svc
    environment: production
```

### OpenLineage Events

Data lineage events include:

- Who initiated the operation
- What data was accessed/modified
- When the operation occurred
- Success/failure status

### Audit Logging

Enable comprehensive audit logging:

```yaml
# Polaris audit configuration
audit:
  enabled: true
  log_level: INFO
  include:
    - authentication
    - authorization
    - data_access
    - schema_changes
```

## Security Checklist

### Development

- [ ] floe.yaml contains no credentials
- [ ] platform.yaml uses only secret_ref (not actual values)
- [ ] `.env` files in `.gitignore`
- [ ] detect-secrets pre-commit hook enabled
- [ ] Code reviewed for credential exposure

### Deployment

- [ ] K8s secrets encrypted at rest
- [ ] Pod security policies enforced
- [ ] Network policies restrict pod communication
- [ ] Service accounts with minimal permissions
- [ ] TLS enabled for all internal communication

### Operations

- [ ] Secret rotation schedule defined
- [ ] OAuth2 token refresh working
- [ ] Audit logging enabled and monitored
- [ ] Access reviews performed quarterly
- [ ] Incident response plan documented

## Penetration Testing

For security assessments, verify:

1. **No credentials in git**: `git grep -i "password\|secret\|key" -- '*.yaml' '*.py'`
2. **K8s secrets encrypted**: `kubectl get secret -o yaml | grep -v "^kind\|^api"` (should be base64 encoded)
3. **Pod security**: `kubectl get pods -o jsonpath='{.items[*].spec.containers[*].securityContext}'`
4. **Network policies**: `kubectl get networkpolicies`
5. **TLS verification**: Check all internal endpoints use HTTPS

## Related Documentation

- [Platform Configuration Guide](platform-config.md) - Credential configuration
- [Pipeline Configuration Guide](pipeline-config.md) - No credentials policy
- [ADR-0002: Two-Tier Configuration](adr/0002-two-tier-config.md) - Security design rationale
