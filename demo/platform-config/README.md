# Platform Configuration Repository

**Owner**: Platform Engineering Team
**Purpose**: Infrastructure configuration, deployment charts, and environment-specific settings for the Floe Runtime platform

This repository represents **Tier 2 (Platform Configuration)** and **Tier 3 (Kubernetes Configuration)** of the three-tier architecture. It contains everything needed to deploy and manage Floe infrastructure across environments, but NO data engineering code or pipelines.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Three-Tier Configuration                        │
├─────────────────────────────────────────────────────────────────┤
│ Tier 1: floe.yaml          (Data Engineering Repo)              │
│         └─ Pipelines, transforms, governance                     │
│                                                                  │
│ Tier 2: platform.yaml      (THIS REPO)                          │
│         └─ Infrastructure endpoints, secret refs                 │
│                                                                  │
│ Tier 3: values.yaml        (THIS REPO)                          │
│         └─ K8s config, secret mounts, resource limits            │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
platform-config/
├── platform/              # Tier 2: Platform configurations per environment
│   ├── local/
│   │   └── platform.yaml  # LocalStack, Docker Desktop K8s
│   ├── dev/
│   │   └── platform.yaml  # AWS Dev (EKS, S3, IAM roles)
│   └── prod/
│       └── platform.yaml  # AWS Prod (multi-region, HA, compliance)
│
├── charts/                # Tier 3: Helm charts for infrastructure
│   ├── floe-infrastructure/
│   │   ├── Chart.yaml
│   │   ├── values.yaml              # BASE values (all environments)
│   │   ├── values-local.yaml        # Local overrides
│   │   ├── values-dev.yaml          # Dev overrides
│   │   ├── values-prod.yaml         # Prod overrides
│   │   └── templates/
│   │       ├── platform-configmap.yaml       # Injects platform.yaml
│   │       ├── demo-credentials-secret.yaml  # Local dev credentials
│   │       ├── postgresql.yaml
│   │       ├── localstack.yaml
│   │       ├── polaris.yaml
│   │       └── ...
│   │
│   └── floe-dagster/
│       ├── Chart.yaml
│       ├── values.yaml              # BASE values
│       ├── values-local.yaml        # Local overrides (mounts ConfigMap)
│       ├── values-dev.yaml
│       └── values-prod.yaml
│
└── secrets/               # Secret management (NOT in git)
    ├── local/
    │   └── demo-credentials.yaml    # For kubectl apply (local only)
    ├── dev/
    │   └── sealed-secrets/          # Encrypted, safe to commit
    └── prod/
        └── external-secrets/        # References to AWS Secrets Manager
```

## Environment Configurations

### Local (Docker Desktop)

**Infrastructure**:
- LocalStack (S3, STS, IAM, Secrets Manager)
- Polaris (Iceberg catalog)
- PostgreSQL (Dagster metadata)
- Jaeger (tracing)
- Marquez (lineage)

**Access**: NodePort services at `localhost:30xxx`
- Dagster UI: http://localhost:30000
- Polaris: http://localhost:30181
- LocalStack: http://localhost:30566
- Jaeger: http://localhost:30686
- Marquez: http://localhost:30500

**Platform Config**: `platform/local/platform.yaml`
**Helm Values**: `charts/*/values-local.yaml`

### Dev (AWS EKS)

**Infrastructure**:
- AWS S3 (multi-bucket medallion architecture)
- Polaris (managed Iceberg catalog)
- RDS PostgreSQL (Dagster metadata)
- AWS X-Ray (tracing)
- DataHub (lineage)

**Platform Config**: `platform/dev/platform.yaml`
**Helm Values**: `charts/*/values-dev.yaml`

**Key Differences from Local**:
- IAM roles instead of static credentials
- TLS/encryption enabled
- Basic governance policies
- CloudWatch logging

### Prod (AWS EKS - Multi-Region HA)

**Infrastructure**:
- Multi-region S3 with replication
- HA Polaris cluster
- Multi-AZ RDS with read replicas
- AWS X-Ray with enhanced sampling
- DataHub with backup/disaster recovery

**Platform Config**: `platform/prod/platform.yaml`
**Helm Values**: `charts/*/values-prod.yaml`

**Key Differences from Dev**:
- Multi-region deployment (us-east-1, us-west-2)
- Compliance frameworks (SOC2, GDPR, HIPAA, PCI-DSS)
- 7-year audit retention
- MFA required
- Advanced governance (PII detection, column-level encryption)

## Release Process

Platform configurations are versioned and released as artifacts consumed by data engineering repos.

### 1. Version Platform Configs

```bash
# Validate all environments
for env in local dev prod; do
  floe validate platform/${env}/platform.yaml
done

# Update Chart.yaml versions
vim charts/floe-infrastructure/Chart.yaml  # Bump appVersion
vim charts/floe-dagster/Chart.yaml

# Commit changes
git add platform/ charts/
git commit -m "feat(platform): update dev environment to use new S3 buckets"
```

### 2. Create Release Tag

```bash
# Tag format: platform-config-v<semver>
git tag -a platform-config-v1.2.3 -m "Platform config v1.2.3

- Add dev environment S3 lifecycle policies
- Enable Polaris catalog caching
- Update PostgreSQL to 15.4
"

git push origin platform-config-v1.2.3
```

### 3. Publish GitHub Release

```bash
# Using GitHub CLI
gh release create platform-config-v1.2.3 \
  --title "Platform Config v1.2.3" \
  --notes "See CHANGELOG.md for details" \
  platform/local/platform.yaml \
  platform/dev/platform.yaml \
  platform/prod/platform.yaml \
  charts/floe-infrastructure/values-*.yaml \
  charts/floe-dagster/values-*.yaml
```

### 4. Notify Data Engineering Teams

Data engineering repos pin platform-config versions in their CI/CD:

```yaml
# data-engineering-repo/.github/workflows/deploy.yml
env:
  PLATFORM_CONFIG_VERSION: "platform-config-v1.2.3"  # Update here
```

## Secret Management

### Local Development (INSECURE - Demo Only)

```yaml
# charts/floe-infrastructure/templates/demo-credentials-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: floe-demo-credentials
stringData:
  polaris-client-id: "demo_client"
  polaris-client-secret: "demo_secret_k8s"
  aws-access-key-id: "minioadmin"
  aws-secret-access-key: "minioadmin"
```

**WARNING**: Never use plain secrets in staging/production.

### Dev/Prod (Sealed Secrets)

```bash
# Install Sealed Secrets controller (once per cluster)
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Encrypt a secret
kubectl create secret generic floe-credentials \
  --from-literal=polaris-client-id=xyz \
  --from-literal=polaris-client-secret=abc \
  --dry-run=client -o yaml | \
kubeseal -o yaml > secrets/dev/sealed-secrets/floe-credentials.yaml

# Commit encrypted secret (safe)
git add secrets/dev/sealed-secrets/floe-credentials.yaml
git commit -m "feat(secrets): add dev Polaris credentials"
```

### Prod (External Secrets Operator)

```yaml
# secrets/prod/external-secrets/polaris-credentials.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: polaris-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: floe-polaris-credentials
  data:
    - secretKey: client-id
      remoteRef:
        key: prod/floe/polaris
        property: client_id
    - secretKey: client-secret
      remoteRef:
        key: prod/floe/polaris
        property: client_secret
```

## Deployment

### Local (Docker Desktop)

```bash
# Deploy infrastructure
helm upgrade --install floe-infra charts/floe-infrastructure/ \
  --namespace floe --create-namespace \
  --values charts/floe-infrastructure/values-local.yaml \
  --set platformConfig.enabled=true \
  --set-file platformConfig.content=platform/local/platform.yaml \
  --wait --timeout 5m

# Deploy Dagster
helm upgrade --install floe-dagster charts/floe-dagster/ \
  --namespace floe \
  --values charts/floe-dagster/values-local.yaml \
  --wait --timeout 5m

# Verify
kubectl get pods -n floe
kubectl get secret floe-demo-credentials -n floe
```

### Dev (EKS)

```bash
# Configure kubectl context
aws eks update-kubeconfig --name floe-dev-cluster --region us-east-1

# Deploy infrastructure
helm upgrade --install floe-infra charts/floe-infrastructure/ \
  --namespace floe --create-namespace \
  --values charts/floe-infrastructure/values-dev.yaml \
  --set platformConfig.enabled=true \
  --set-file platformConfig.content=platform/dev/platform.yaml \
  --wait --timeout 10m

# Deploy sealed secrets first
kubectl apply -f secrets/dev/sealed-secrets/

# Deploy Dagster
helm upgrade --install floe-dagster charts/floe-dagster/ \
  --namespace floe \
  --values charts/floe-dagster/values-dev.yaml \
  --wait --timeout 10m
```

### Prod (EKS - Multi-Region)

```bash
# Primary region (us-east-1)
aws eks update-kubeconfig --name floe-prod-cluster-east --region us-east-1

helm upgrade --install floe-infra charts/floe-infrastructure/ \
  --namespace floe --create-namespace \
  --values charts/floe-infrastructure/values-prod.yaml \
  --set platformConfig.enabled=true \
  --set-file platformConfig.content=platform/prod/platform.yaml \
  --wait --timeout 15m

# Deploy External Secrets Operator (if not already installed)
kubectl apply -f secrets/prod/external-secrets/

# Secondary region (us-west-2)
aws eks update-kubeconfig --name floe-prod-cluster-west --region us-west-2
# Repeat deployment with regional overrides...
```

## Integration with Data Engineering Repos

Data engineering repos fetch platform configs as build artifacts:

```yaml
# data-engineering-repo/.github/workflows/build.yml
name: Build and Deploy
on:
  push:
    branches: [main]

env:
  PLATFORM_CONFIG_VERSION: "platform-config-v1.2.3"

jobs:
  build:
    steps:
      - uses: actions/checkout@v4

      - name: Download platform config
        run: |
          gh release download $PLATFORM_CONFIG_VERSION \
            --repo myorg/platform-config \
            --pattern 'platform/dev/platform.yaml' \
            --output platform.yaml

      - name: Compile artifacts
        run: |
          floe compile \
            --floe-yaml=floe.yaml \
            --platform-yaml=platform.yaml \
            --output=compiled/

      - name: Build Docker image
        run: |
          docker build \
            --build-arg COMPILED_ARTIFACTS=compiled/ \
            -t ghcr.io/myorg/customer-analytics:${{ github.sha }} .

      - name: Deploy to EKS
        run: |
          helm upgrade --install customer-analytics \
            charts/floe-dagster/ \
            --namespace analytics \
            --set image.tag=${{ github.sha }} \
            --values charts/floe-dagster/values-dev.yaml
```

## Validation

### Schema Validation

```bash
# Validate platform.yaml against schema
floe validate platform/dev/platform.yaml

# Validate all environments
for env in local dev prod; do
  echo "Validating ${env}..."
  floe validate platform/${env}/platform.yaml
done
```

### Helm Chart Validation

```bash
# Lint charts
helm lint charts/floe-infrastructure/
helm lint charts/floe-dagster/

# Template and validate (dry-run)
helm template floe-infra charts/floe-infrastructure/ \
  --values charts/floe-infrastructure/values-dev.yaml \
  --set platformConfig.enabled=true \
  --set-file platformConfig.content=platform/dev/platform.yaml | \
kubectl apply --dry-run=client -f -
```

### Security Scanning

```bash
# Scan for hardcoded secrets
git secrets --scan

# Scan Helm charts
trivy config charts/

# Validate RBAC policies
kubectl auth can-i --list --as=system:serviceaccount:floe:dagster
```

## Troubleshooting

### Secret Not Found

```bash
# Check secret exists
kubectl get secret floe-demo-credentials -n floe

# Inspect secret keys
kubectl get secret floe-demo-credentials -n floe -o jsonpath='{.data}' | jq 'keys'

# Check pod can access secret
kubectl describe pod <dagster-pod> -n floe | grep -A 5 "Environment"
```

### Platform Config Not Loaded

```bash
# Check ConfigMap exists
kubectl get configmap floe-infra-platform-config -n floe

# View ConfigMap content
kubectl get configmap floe-infra-platform-config -n floe -o yaml

# Check volume mount in pod
kubectl describe pod <dagster-pod> -n floe | grep -A 10 "Mounts"
```

### Helm Dependency Issues

```bash
# Update chart dependencies
helm dependency update charts/floe-infrastructure/
helm dependency update charts/floe-dagster/

# List dependencies
helm dependency list charts/floe-infrastructure/
```

## Contributing

### Adding a New Environment

1. Create `platform/<env>/platform.yaml`
2. Create `charts/*/values-<env>.yaml`
3. Update `secrets/<env>/` with secret templates
4. Add validation to CI/CD
5. Document in this README

### Updating Infrastructure Components

1. Update `charts/floe-infrastructure/templates/<component>.yaml`
2. Update `values.yaml` and environment-specific values
3. Test in local environment first
4. Create PR with validation evidence
5. Release new platform-config version

## References

- [ADR-0002: Three-Tier Configuration Architecture](../../docs/adr/0002-three-tier-config.md)
- [Platform Configuration Guide](../../docs/platform-config.md)
- [Security Architecture](../../docs/security.md)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Sealed Secrets Documentation](https://sealed-secrets.netlify.app/)
- [External Secrets Operator](https://external-secrets.io/)
