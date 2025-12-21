# Quick Start: Deployment Automation

**Feature**: 007-deployment-automation
**Date**: 2025-12-21

This guide provides step-by-step instructions to deploy floe-runtime to Kubernetes using Helm charts with GitOps automation.

---

## Prerequisites

Before deploying, ensure you have:

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| kubectl | 1.25+ | Kubernetes CLI |
| helm | 3.12+ | Helm package manager |
| docker | 24+ | Container runtime |
| floe CLI | 0.1+ | floe-runtime CLI |

### External Services

The following services must be provisioned **before** deploying floe-runtime:

| Service | Options | Purpose |
|---------|---------|---------|
| Kubernetes | EKS, GKE, AKS, kind | Container orchestration |
| Compute Engine | Trino, Snowflake, BigQuery | SQL execution |
| Object Storage | S3, GCS, ADLS | Iceberg table storage |
| Iceberg Catalog | Apache Polaris | Table metadata |
| PostgreSQL | RDS, Cloud SQL, self-hosted | Dagster metadata |

---

## Step 1: Pre-Deployment Validation

Before deploying, validate your infrastructure connectivity:

```bash
# Set environment variables for your services
export POLARIS_URI="https://polaris.example.com/api/catalog"
export POLARIS_CLIENT_ID="your-client-id"
export POLARIS_CLIENT_SECRET="your-client-secret"
export DAGSTER_PG_HOST="postgres.example.com"
export DAGSTER_PG_PASSWORD="your-password"

# Run preflight checks
floe preflight --all

# Expected output:
# ┌─────────────────────────────────────────────────────────────────┐
# │                    Preflight Validation                         │
# ├──────────┬──────────┬───────────────────────────────┬──────────┤
# │ Service  │ Status   │ Message                       │ Duration │
# ├──────────┼──────────┼───────────────────────────────┼──────────┤
# │ Compute  │ ✅ OK    │ Trino connection successful   │ 456ms    │
# │ Storage  │ ✅ OK    │ S3 bucket accessible          │ 234ms    │
# │ Catalog  │ ✅ OK    │ Polaris OAuth2 authenticated  │ 345ms    │
# │ Postgres │ ✅ OK    │ PostgreSQL connected          │ 199ms    │
# └──────────┴──────────┴───────────────────────────────┴──────────┘
#
# Overall Status: PASS
```

If any checks fail, review the remediation suggestions before proceeding.

---

## Step 2: Compile Configuration

Generate CompiledArtifacts from your floe.yaml:

```bash
# Validate floe.yaml
floe validate

# Compile artifacts
floe compile --output .floe/compiled_artifacts.json

# Verify output
cat .floe/compiled_artifacts.json | jq '.version'
```

---

## Step 3: Build Container Images

Build and push Docker images for Dagster and Cube:

```bash
# Build Dagster image
docker build -t your-registry/floe-dagster:latest -f docker/Dockerfile.dagster .

# Build Cube image (optional)
docker build -t your-registry/floe-cube:latest -f docker/Dockerfile.cube .

# Push to registry
docker push your-registry/floe-dagster:latest
docker push your-registry/floe-cube:latest
```

---

## Step 4: Create Kubernetes Secrets

Create secrets for credentials (using External Secrets or manually):

### Option A: External Secrets Operator (Recommended)

```yaml
# externalsecret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: floe-secrets
  namespace: floe
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: aws-secrets-manager
  target:
    name: floe-secrets
  data:
    - secretKey: POLARIS_CLIENT_SECRET
      remoteRef:
        key: floe/polaris
        property: client_secret
    - secretKey: DAGSTER_PG_PASSWORD
      remoteRef:
        key: floe/postgres
        property: password
```

```bash
kubectl apply -f externalsecret.yaml
```

### Option B: Manual Secrets

```bash
kubectl create secret generic floe-secrets \
  --namespace floe \
  --from-literal=POLARIS_CLIENT_SECRET="your-secret" \
  --from-literal=DAGSTER_PG_PASSWORD="your-password"
```

---

## Step 5: Deploy with Helm

### Create Namespace

```bash
kubectl create namespace floe
```

### Create CompiledArtifacts ConfigMap

```bash
kubectl create configmap floe-artifacts \
  --namespace floe \
  --from-file=compiled_artifacts.json=.floe/compiled_artifacts.json
```

### Install Helm Chart

```bash
# Add Dagster Helm repo (for dependency)
helm repo add dagster https://dagster-io.github.io/helm
helm repo update

# Install floe-dagster
helm install floe-runtime charts/floe-dagster \
  --namespace floe \
  --values charts/floe-dagster/values-prod.yaml \
  --set image.repository=your-registry/floe-dagster \
  --set image.tag=latest

# Verify deployment
kubectl get pods -n floe
```

Expected output:
```
NAME                                    READY   STATUS    RESTARTS   AGE
floe-runtime-dagster-webserver-xxx      1/1     Running   0          2m
floe-runtime-dagster-daemon-xxx         1/1     Running   0          2m
floe-runtime-dagster-worker-xxx         1/1     Running   0          2m
```

---

## Step 6: Access Dagster UI

### Port Forward (Development)

```bash
kubectl port-forward svc/floe-runtime-dagster-webserver 3000:80 -n floe
# Open http://localhost:3000
```

### Ingress (Production)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: floe-dagster
  namespace: floe
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
    - host: dagster.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: floe-runtime-dagster-webserver
                port:
                  number: 80
```

---

## Step 7: Deploy Cube (Optional)

If you need the Cube semantic layer:

```bash
helm install floe-cube charts/floe-cube \
  --namespace floe \
  --values charts/floe-cube/values-prod.yaml \
  --set image.repository=your-registry/floe-cube \
  --set image.tag=latest

# Verify Cube is running
kubectl get pods -n floe | grep cube
```

---

## Step 8: GitOps Setup (Optional)

### ArgoCD

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: floe-runtime
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/floe-deploy
    targetRevision: HEAD
    path: environments/prod
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: floe
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

```bash
kubectl apply -f argocd-application.yaml
```

### Flux

```yaml
# flux-helmrelease.yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: floe-runtime
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: ./charts/floe-dagster
      sourceRef:
        kind: GitRepository
        name: floe-deploy
  values:
    image:
      repository: your-registry/floe-dagster
      tag: latest
  valuesFrom:
    - kind: Secret
      name: floe-secrets
```

```bash
kubectl apply -f flux-helmrelease.yaml
```

---

## Demo Mode

To deploy with continuous synthetic data generation for demos:

```bash
# Deploy with demo mode enabled
helm install floe-demo charts/floe-dagster \
  --namespace floe-demo \
  --values charts/floe-dagster/values-demo.yaml \
  --set demo.enabled=true \
  --set demo.schedule.interval="*/5 * * * *" \
  --set demo.schedule.batchSize=100

# Verify demo schedule is running
kubectl get cronjobs -n floe-demo
```

Access observability UIs:
- **Dagster**: http://localhost:3000 (pipeline runs, asset graph)
- **Marquez**: http://localhost:5000 (data lineage)
- **Jaeger**: http://localhost:16686 (distributed traces)

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Pods stuck in Pending | Check resource requests/limits, node capacity |
| ImagePullBackOff | Verify image registry credentials |
| CrashLoopBackOff | Check logs: `kubectl logs <pod> -n floe` |
| Preflight fails | Review error message, check credentials |

### Debugging Commands

```bash
# View pod logs
kubectl logs -f deployment/floe-runtime-dagster-webserver -n floe

# Describe pod for events
kubectl describe pod <pod-name> -n floe

# Check ConfigMap
kubectl get configmap floe-artifacts -n floe -o yaml

# Verify secrets
kubectl get secret floe-secrets -n floe
```

---

## Next Steps

1. **Configure production values**: Review `values-prod.yaml` for resource limits, replicas
2. **Set up monitoring**: Configure Prometheus/Grafana for metrics
3. **Enable alerting**: Set up PagerDuty/Slack alerts for pipeline failures
4. **Schedule backups**: Configure PostgreSQL backups for Dagster metadata

For detailed documentation, see:
- [Deployment View](../../docs/06-deployment-view.md)
- [Infrastructure Provisioning](../../docs/07-infrastructure-provisioning.md)
