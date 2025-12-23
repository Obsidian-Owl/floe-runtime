# Quickstart: Kubernetes Demo Deployment

**Feature**: 008-kubernetes-demo
**Date**: 2025-12-22

Deploy the complete floe-runtime stack to Docker Desktop Kubernetes in under 10 minutes.

---

## Prerequisites

### Required Tools

```bash
# Verify Docker Desktop with Kubernetes enabled
docker version
kubectl cluster-info

# Verify Helm 3.x
helm version

# Expected output:
# version.BuildInfo{Version:"v3.x.x", ...}
```

### Docker Desktop Configuration

1. Open Docker Desktop → Settings → Resources
2. Allocate at least **4GB RAM** (8GB recommended)
3. Allocate at least **4 CPU cores**
4. Enable Kubernetes in Settings → Kubernetes

---

## Quick Deploy

### One-Command Deployment

```bash
# Deploy entire stack
make deploy-local-full

# This runs:
# 1. helm install floe-infra (PostgreSQL, MinIO, Polaris, Jaeger, Marquez)
# 2. Wait for infrastructure readiness
# 3. helm install floe-dagster (Webserver, Daemon, Workers)
# 4. helm install floe-cube (API, Refresh Worker, Cube Store)
```

### Verify Deployment

```bash
# Check all pods are running (should show 8+ pods)
kubectl get pods -n floe

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# floe-postgresql-0                       1/1     Running   0          2m
# floe-minio-0                            1/1     Running   0          2m
# floe-polaris-xxx                        1/1     Running   0          2m
# floe-jaeger-xxx                         1/1     Running   0          2m
# floe-marquez-xxx                        1/1     Running   0          2m
# floe-dagster-webserver-xxx              1/1     Running   0          1m
# floe-dagster-daemon-xxx                 1/1     Running   0          1m
# floe-cube-xxx                           1/1     Running   0          1m
# floe-cubestore-router-xxx               1/1     Running   0          1m
```

---

## Access Services

### Port-Forward Commands

```bash
# Dagster UI (Pipeline orchestration)
kubectl port-forward svc/floe-dagster-webserver 3000:80 -n floe
# Open: http://localhost:3000

# Cube REST/GraphQL API (Semantic layer)
kubectl port-forward svc/floe-cube 4000:4000 -n floe
# Test: curl http://localhost:4000/readyz

# Cube SQL API (BI tool connections)
kubectl port-forward svc/floe-cube-sql 15432:15432 -n floe
# Connect with psql: psql -h localhost -p 15432 -U cube

# Jaeger UI (Distributed tracing)
kubectl port-forward svc/floe-jaeger 16686:16686 -n floe
# Open: http://localhost:16686

# Marquez UI (Data lineage)
kubectl port-forward svc/floe-marquez 5001:5000 -n floe
# Open: http://localhost:5001

# MinIO Console (Object storage)
kubectl port-forward svc/floe-minio-console 9001:9001 -n floe
# Open: http://localhost:9001 (minioadmin/minioadmin)
```

### All Port-Forwards (Convenience Script)

```bash
# Start all port-forwards in background
make port-forward-all

# Or manually:
kubectl port-forward svc/floe-dagster-webserver 3000:80 -n floe &
kubectl port-forward svc/floe-cube 4000:4000 -n floe &
kubectl port-forward svc/floe-cube-sql 15432:15432 -n floe &
kubectl port-forward svc/floe-jaeger 16686:16686 -n floe &
kubectl port-forward svc/floe-marquez 5001:5000 -n floe &
kubectl port-forward svc/floe-minio-console 9001:9001 -n floe &
```

---

## Demo Workflow

### 1. Trigger Initial Data Seeding

The Dagster sensor automatically detects empty tables and triggers seeding.
Alternatively, manually trigger:

```bash
# Via Dagster UI
# 1. Open http://localhost:3000
# 2. Navigate to Jobs → seed_demo_data
# 3. Click "Launch Run"

# Via GraphQL API
curl -X POST http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { launchRun(executionParams: { selector: { jobName: \"seed_demo_data\" } }) { run { runId } } }"
  }'
```

### 2. Query Data via Cube REST API

```bash
# Get order counts by status
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"],
      "dimensions": ["Orders.status"],
      "timeDimensions": [{
        "dimension": "Orders.createdAt",
        "granularity": "day",
        "dateRange": "last 7 days"
      }]
    }
  }'
```

### 3. Query via SQL API (BI Tools)

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=15432,
    user="cube",
    password="cube_password",
    database="cube"
)
cursor = conn.cursor()
cursor.execute("""
    SELECT status, MEASURE(count), MEASURE(total_amount)
    FROM Orders
    GROUP BY 1
""")
print(cursor.fetchall())
```

### 4. View Traces in Jaeger

1. Open http://localhost:16686
2. Select Service: `dagster`
3. Click "Find Traces"
4. View spans for pipeline execution, dbt runs, Iceberg operations

### 5. View Lineage in Marquez

1. Open http://localhost:5001
2. Browse datasets and jobs
3. Click on a dataset to see upstream/downstream dependencies

---

## Cleanup

```bash
# Remove all floe resources
make undeploy-local

# This runs:
# helm uninstall floe-cube -n floe
# helm uninstall floe-dagster -n floe
# helm uninstall floe-infra -n floe
# kubectl delete namespace floe
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n floe

# Common issues:
# - ImagePullBackOff: Check image name and registry access
# - CrashLoopBackOff: Check logs with `kubectl logs <pod-name> -n floe`
# - Pending: Check resources with `kubectl describe pod`
```

### Polaris Initialization Failed

```bash
# Check init job logs
kubectl logs -l job-name=floe-infra-polaris-init -n floe

# Re-run init job
kubectl delete job floe-infra-polaris-init -n floe
helm upgrade floe-infra charts/floe-infrastructure -n floe
```

### Insufficient Memory

```bash
# Check node resources
kubectl top nodes

# Symptoms:
# - OOMKilled pods
# - Slow performance

# Solution:
# Increase Docker Desktop memory to 8GB+
```

### Port Already in Use

```bash
# Find process using port
lsof -i :3000

# Kill existing port-forward
pkill -f "kubectl port-forward"

# Use alternative port
kubectl port-forward svc/floe-dagster-webserver 3001:80 -n floe
```

### Data Not Appearing in Cube

```bash
# Check Dagster job completed
kubectl logs -l app=floe-dagster-daemon -n floe | grep seed

# Check Polaris has tables
kubectl exec -it deploy/floe-polaris -n floe -- \
  curl http://localhost:8181/api/catalog/v1/demo_catalog/namespaces/demo.bronze/tables

# Refresh Cube schema
curl -X POST http://localhost:4000/cubejs-api/v1/pre-aggregations/jobs \
  -H "Content-Type: application/json" \
  -d '{"action": "build"}'
```

---

## Resource Requirements

| Service | CPU Request | Memory Request | Notes |
|---------|-------------|----------------|-------|
| PostgreSQL | 100m | 256Mi | Shared by Dagster + Marquez |
| MinIO | 100m | 256Mi | Iceberg data + Cube Store |
| Polaris | 100m | 256Mi | Iceberg catalog |
| Dagster Webserver | 100m | 256Mi | UI and API |
| Dagster Daemon | 100m | 128Mi | Schedules and sensors |
| Dagster Worker | 200m | 512Mi | Job execution |
| Cube API | 100m | 256Mi | Query processing |
| Cube Store Router | 100m | 128Mi | Pre-aggregation routing |
| Cube Store Worker | 100m | 256Mi | Pre-aggregation storage |
| Jaeger | 100m | 128Mi | Tracing UI |
| Marquez | 100m | 256Mi | Lineage UI |

**Total Minimum**: ~1.2 CPU, ~2.6 GB RAM
**Recommended**: 4 CPU, 8 GB RAM (Docker Desktop allocation)

---

## Next Steps

- [Deployment Automation](../../docs/06-deployment-view.md) - Production deployment patterns
- [Demo Pipeline](../007-deployment-automation/spec.md) - E2E demo infrastructure
- [Cube Semantic Layer](../../packages/floe-cube/README.md) - Query API documentation
