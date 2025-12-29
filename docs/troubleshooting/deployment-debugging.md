# Deployment Debugging Guide

## Lessons Learned from E2E Validation Debugging

This guide documents common deployment issues discovered during the production-grade validation implementation and their solutions.

---

## Issue #1: PyIceberg S3 Endpoint Resolution

### Symptom
```
java.net.UnknownHostException: floe-infra-localstack
```

When PyIceberg tries to write to S3, it fails with hostname resolution errors.

### Root Cause
PyIceberg's REST catalog client receives S3 endpoint configuration from Polaris server metadata. When Polaris is running in Kubernetes and vends credentials with the internal service hostname (`http://floe-infra-localstack:4566`), PyIceberg tries to use that hostname but cannot resolve it from certain contexts.

### Solution
**File**: `packages/floe-polaris/src/floe_polaris/client.py` (lines 188-191)

```python
# Force path-style S3 access (CRITICAL for LocalStack/MinIO)
# This ensures PyIceberg FileIO uses our client-side endpoint config
# instead of accepting the endpoint from Polaris server metadata
properties["s3.path-style-access"] = "true"
```

**Key insight**: Always force `s3.path-style-access = true` when using S3-compatible storage (LocalStack, MinIO) with Polaris.

### Prevention
- Add socket-based connectivity validation in scripts before S3 operations
- Use retry logic with exponential backoff for transient failures
- Configure environment-aware endpoint detection (K8s vs Docker vs local)

**Reference**: See `scripts/seed_iceberg_tables.py` lines 87-111 for endpoint validation example.

---

## Issue #2: Docker Image Distribution Mismatch

### Symptom
Pod keeps showing old code despite rebuilds. New commits don't appear in running pods.

### Root Cause
Building to one registry (`localhost:5050/floe/demo:latest`) but Helm pulling from another (`ghcr.io/obsidian-owl/floe-demo:latest`).

### Solution
**Always use git SHA tags for immutable image references:**

```bash
# Build with SHA tag
GIT_SHA=$(git rev-parse --short HEAD)
docker build -t "ghcr.io/obsidian-owl/floe-demo:$GIT_SHA" -f docker/Dockerfile.demo .
docker tag "ghcr.io/obsidian-owl/floe-demo:$GIT_SHA" "ghcr.io/obsidian-owl/floe-demo:latest"

# Deploy with explicit SHA tag
helm upgrade --install floe-dagster charts/floe-dagster/ \
  --set 'dagster-user-deployments.deployments[0].image.tag'=$GIT_SHA \
  --set 'dagster-user-deployments.deployments[0].image.pullPolicy'=Always
```

### Prevention
- Never use `latest` tag in production
- Always verify image with: `kubectl get deployment -o jsonpath='{.spec.template.spec.containers[0].image}'`
- Use `--wait` flag with Helm to ensure new pods are running

---

## Issue #3: Missing Files in Docker Image

### Symptom
```
python: can't open file '/app/demo/scripts/seed_iceberg_tables.py': [Errno 2] No such file or directory
```

Scripts in `scripts/` directory not present in Docker image.

### Root Cause
Dockerfile only copies specific directories (`packages/` and `demo/`), not `scripts/`.

### Solution (Temporary)
```bash
# Copy script to pod temporarily
kubectl cp scripts/seed_iceberg_tables.py floe/$POD_NAME:/tmp/seed_iceberg_tables.py
kubectl exec -n floe deployment/... -- python /tmp/seed_iceberg_tables.py
```

### Solution (Permanent)
Update `docker/Dockerfile.demo` to include scripts:

```dockerfile
# Copy scripts directory
COPY scripts/ /app/scripts/
```

### Prevention
- Document which directories are included in Docker image
- Add validation step in CI/CD to verify expected files exist in image
- Use `docker run --rm <image> ls -la /app` to inspect image contents

---

## Issue #4: Dagster Resource Injection Pattern Mismatch

### Symptom
```
Invariant violation for parameter: Cannot specify resource requirements in both @asset decorator and as arguments
```

### Root Cause
Dagster 1.12.x doesn't allow both `required_resource_keys` in decorator AND typed context parameter.

### Solution
```python
# ❌ WRONG - Causes invariant violation
@asset(required_resource_keys={"_floe_observability_orchestrator"})
def my_asset(context: AssetExecutionContext, ...):
    pass

# ✅ CORRECT - No required_resource_keys, no type annotation on context
@asset()
def my_asset(context, ...):
    orchestrator = context.resources._floe_observability_orchestrator
    pass
```

### Prevention
- Don't use `required_resource_keys` when context has type annotation
- Access resources via `context.resources.<resource_name>` at runtime
- Let Dagster infer resource requirements from usage

---

## Issue #5: Helm Schema Validation Failures

### Symptom
```
Error: values don't meet the specifications of the schema(s)
failing loading "https://kubernetesjsonschema.dev/v1.18.0/_definitions.json": HTTP 404
```

### Root Cause
Official Dagster Helm chart (v1.9.x) includes JSON schema validation that fetches external schemas from `kubernetesjsonschema.dev`, which may be unavailable.

### Solution
This is an external dependency issue. The chart will deploy successfully with `helm install` (fresh install), but `helm upgrade` may fail if schema validation endpoint is down.

### Workaround
- Use `helm install` instead of `helm upgrade` when possible
- Test configuration with `helm template` first (doesn't validate schemas)
- Wait for upstream fix or use a different chart version

### Prevention
- Pin Helm chart versions in `Chart.yaml` dependencies
- Test deployments in CI/CD before production
- Have rollback plan ready (`helm rollback`)

---

## Debugging Workflow

### 1. Check Pod Logs First
```bash
# Get recent logs (tail last 50 lines)
kubectl logs -n floe deployment/<name> --tail=50

# Follow logs in real-time
kubectl logs -n floe deployment/<name> --follow

# Get logs from previous container (if pod crashed)
kubectl logs -n floe pod/<name> --previous
```

### 2. Verify Image is Correct
```bash
# Check deployed image tag
kubectl get deployment -n floe <name> \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

# Should match your expected SHA
```

### 3. Force Pod Restart with New Image
```bash
# Delete pod to force recreation
kubectl delete pod -n floe -l deployment=<name>

# Wait for new pod to be ready
kubectl wait --for=condition=ready pod -n floe -l deployment=<name> --timeout=180s
```

### 4. Interactive Debugging Inside Pod
```bash
# Exec into running pod
kubectl exec -n floe deployment/<name> -it -- /bin/bash

# Test Python imports
python
>>> from dagster import Definitions
>>> # Verify modules load correctly

# Check file system
ls -la /app/
cat /app/demo/data_engineering/orchestration/definitions.py
```

### 5. Inspect Kubernetes Events
```bash
# Get recent events (sorted by time)
kubectl get events -n floe --sort-by='.lastTimestamp' | tail -20

# Filter events for specific pod
kubectl describe pod -n floe <pod-name>
```

### 6. Check Resource Status
```bash
# Get all resources in namespace
kubectl get all -n floe

# Check pod status and restarts
kubectl get pods -n floe -o wide

# Check persistent volume claims
kubectl get pvc -n floe
```

---

## Quick Reference: Common Commands

### Dagster Job Management
```bash
# Launch job programmatically
./scripts/launch-dagster-job.sh demo_bronze

# Monitor run status
./scripts/monitor-dagster-run.sh <run-id>

# Get run logs from pod
kubectl logs -n floe -l job-name=dagster-run-<run-id>
```

### Helm Operations
```bash
# Upgrade with --wait to ensure readiness
helm upgrade floe-dagster charts/floe-dagster/ --wait --timeout 5m

# Rollback to previous release
helm rollback floe-dagster -n floe

# Check release history
helm history floe-dagster -n floe

# Uninstall cleanly
helm uninstall floe-dagster -n floe
```

### S3 / LocalStack
```bash
# List S3 buckets
kubectl exec -n floe <localstack-pod> -- awslocal s3 ls

# List objects in bucket
kubectl exec -n floe <localstack-pod> -- awslocal s3 ls s3://iceberg-bronze/demo/

# Get object
kubectl exec -n floe <localstack-pod> -- awslocal s3 cp s3://iceberg-bronze/demo/metadata/... -
```

### Port Forwarding
```bash
# Forward Dagster UI
kubectl port-forward -n floe svc/floe-dagster-dagster-webserver 3000:80

# Forward Polaris API
kubectl port-forward -n floe svc/floe-infra-polaris 8181:8181

# Forward LocalStack
kubectl port-forward -n floe svc/floe-infra-localstack 4566:4566
```

---

## Troubleshooting Checklist

When debugging deployment issues, systematically check:

- [ ] **Image version**: Verify SHA matches expected commit
- [ ] **Pod status**: Check `kubectl get pods` for CrashLoopBackOff, ImagePullBackOff
- [ ] **Recent logs**: Use `--tail=50` to avoid context overload
- [ ] **Kubernetes events**: Check `kubectl get events` for recent errors
- [ ] **Resource limits**: Verify pods have sufficient CPU/memory
- [ ] **Volume mounts**: Check ConfigMaps and Secrets are mounted correctly
- [ ] **Network connectivity**: Verify services can reach dependencies
- [ ] **Environment variables**: Check env vars are set correctly in pod spec
- [ ] **Helm values**: Verify values.yaml matches deployment requirements
- [ ] **Init containers**: Check if init containers completed successfully

---

## Additional Resources

- [Kubernetes Debugging Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
- [Helm Troubleshooting](https://helm.sh/docs/faq/troubleshooting/)
- [Dagster Deployment Guides](https://docs.dagster.io/deployment)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
