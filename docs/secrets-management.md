# Secrets Management for floe-runtime

This document describes the available options for managing secrets in floe-runtime Kubernetes deployments.

**Covers**: 007-FR-003 (Secure secrets management for Kubernetes deployments)

## Overview

floe-runtime requires secrets for various components:

| Component | Secrets Required |
|-----------|------------------|
| **PostgreSQL** (Dagster metadata) | Database password, username, host |
| **Compute Engine** (Snowflake, Trino, BigQuery) | Account credentials, service account keys |
| **Storage** (S3, GCS, ADLS) | Access keys, service account credentials |
| **Catalog** (Polaris) | OAuth2 client ID and secret |

## Comparison of Approaches

| Approach | Secret Storage | Git-Safe | Auto-Rotation | Audit | Best For |
|----------|----------------|----------|---------------|-------|----------|
| **External Secrets** | AWS SM, Vault, GCP, Azure | ✅ | ✅ | ✅ | Production, Enterprise |
| **Sealed Secrets** | Encrypted in Git | ✅ | ❌ | ❌ | GitOps, Small teams |
| **SOPS** | Encrypted files | ✅ | ❌ | ❌ | GitOps, Multi-cloud |
| **Kubernetes Secrets** | etcd (cluster) | ❌ | ❌ | ❌ | Development only |

## 1. External Secrets Operator (Recommended for Production)

External Secrets Operator syncs secrets from external secret management services into Kubernetes.

### Prerequisites

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system --create-namespace
```

### AWS Secrets Manager Example

1. **Create SecretStore**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: floe
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

2. **Configure floe-dagster**:
```yaml
# values-external-secrets-aws.yaml
floe:
  externalSecrets:
    enabled: true
    secretStoreRef: "aws-secrets-manager"
    refreshInterval: "15m"

    postgresql:
      enabled: true
      passwordKey: "floe/prod/dagster-postgresql"
      passwordProperty: "password"
```

3. **Deploy**:
```bash
helm upgrade floe-dagster charts/floe-dagster \
  -f charts/floe-dagster/values-external-secrets-aws.yaml \
  -n floe
```

### HashiCorp Vault Example

See [values-external-secrets-vault.yaml](../charts/floe-dagster/values-external-secrets-vault.yaml) for complete configuration.

```bash
# Configure Vault Kubernetes auth
vault auth enable kubernetes
vault write auth/kubernetes/role/floe-dagster \
  bound_service_account_names=external-secrets-sa \
  bound_service_account_namespaces=floe \
  policies=floe-dagster \
  ttl=1h
```

### Supported Providers

- AWS Secrets Manager / Parameter Store
- HashiCorp Vault
- GCP Secret Manager
- Azure Key Vault
- IBM Cloud Secrets Manager
- CyberArk Conjur

## 2. Sealed Secrets (GitOps-Friendly)

Sealed Secrets encrypts secrets so they can be safely stored in Git.

### Prerequisites

```bash
# Install Sealed Secrets controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# Install kubeseal CLI
brew install kubeseal
```

### Workflow

1. **Fetch public key**:
```bash
kubeseal --fetch-cert \
  --controller-name=sealed-secrets \
  --controller-namespace=kube-system \
  > sealed-secrets-pub.pem
```

2. **Encrypt secrets**:
```bash
echo -n "your-password" | kubeseal --raw \
  --from-file=/dev/stdin \
  --scope namespace-wide \
  --name floe-dagster-postgresql-secret \
  --namespace floe
```

3. **Add to values file**:
```yaml
# values-sealed-secrets.yaml
floe:
  sealedSecrets:
    enabled: true
    postgresql:
      enabled: true
      encryptedData:
        postgresql-password: "AgBy3i4OJSWK+..."
```

4. **Deploy**:
```bash
helm upgrade floe-dagster charts/floe-dagster \
  -f charts/floe-dagster/values-sealed-secrets.yaml \
  -n floe
```

### Key Rotation

When rotating Sealed Secrets keys:
1. Re-encrypt all secrets with new public key
2. Update all values files
3. Redeploy

## 3. SOPS (Secrets OPerationS)

SOPS encrypts entire files, allowing secret values to be stored encrypted in Git.

### Prerequisites

```bash
# Install SOPS
brew install sops

# Install age for encryption (recommended)
brew install age

# Generate age key
age-keygen -o key.txt
```

### Configuration

1. **Create `.sops.yaml`** in repo root:
```yaml
creation_rules:
  - path_regex: .*values-sops\.yaml$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
```

2. **Create values file with secrets**:
```yaml
# values-sops.yaml
secrets:
  postgresql:
    password: "actual-password-here"
    username: "dagster"
```

3. **Encrypt**:
```bash
sops -e values-sops.yaml > values-sops.enc.yaml
git add values-sops.enc.yaml
```

4. **Deploy**:
```bash
# Using helm-secrets plugin
helm secrets upgrade floe-dagster charts/floe-dagster \
  -f charts/floe-dagster/values-sops.enc.yaml \
  -n floe

# Or without plugin
sops -d charts/floe-dagster/values-sops.enc.yaml | \
  helm upgrade floe-dagster charts/floe-dagster -f - -n floe
```

### Supported Encryption Backends

- **age** (recommended, simple and secure)
- AWS KMS
- GCP KMS
- Azure Key Vault
- HashiCorp Vault
- PGP/GPG

## Decision Matrix

### When to Use External Secrets

✅ Production environments
✅ Enterprise with central secret management
✅ Need automatic rotation
✅ Require audit trails
✅ Multiple teams sharing secrets

### When to Use Sealed Secrets

✅ Pure GitOps workflows
✅ Small teams
✅ Kubernetes-native approach
✅ No external secret management service

### When to Use SOPS

✅ Multi-cloud environments
✅ File-based configuration
✅ CI/CD pipelines that need decrypted values
✅ Existing SOPS infrastructure

## Security Best Practices

1. **Never commit plaintext secrets** to Git
2. **Use namespace-scoped** SecretStores when possible
3. **Enable audit logging** for secret access
4. **Rotate secrets regularly** (at least quarterly)
5. **Use short refresh intervals** (15m-1h) for External Secrets
6. **Restrict RBAC** for secret access
7. **Encrypt secrets at rest** in etcd (enable K8s encryption)

## Example Files

| Approach | Values File |
|----------|-------------|
| External Secrets (AWS) | [values-external-secrets-aws.yaml](../charts/floe-dagster/values-external-secrets-aws.yaml) |
| External Secrets (Vault) | [values-external-secrets-vault.yaml](../charts/floe-dagster/values-external-secrets-vault.yaml) |
| Sealed Secrets | [values-sealed-secrets.yaml](../charts/floe-dagster/values-sealed-secrets.yaml) |
| SOPS | [values-sops.yaml](../charts/floe-dagster/values-sops.yaml) |

## Troubleshooting

### External Secrets not syncing

```bash
# Check ExternalSecret status
kubectl get externalsecret -n floe
kubectl describe externalsecret floe-dagster-postgresql-secret -n floe

# Check SecretStore
kubectl get secretstore -n floe
kubectl describe secretstore aws-secrets-manager -n floe
```

### Sealed Secrets not decrypting

```bash
# Check SealedSecret status
kubectl get sealedsecret -n floe
kubectl logs -n kube-system -l app.kubernetes.io/name=sealed-secrets

# Verify key matches
kubeseal --fetch-cert | sha256sum
cat sealed-secrets-pub.pem | sha256sum
```

### SOPS decryption failing

```bash
# Check SOPS configuration
sops -d values-sops.enc.yaml

# Verify age key is available
export SOPS_AGE_KEY_FILE=$HOME/.sops/age/keys.txt
sops -d values-sops.enc.yaml
```
