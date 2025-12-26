# E2E Validation Resolution Plan - T046

## Current Status

✅ **Infrastructure**: All infra pods running (Jaeger, Marquez, Polaris, MinIO, PostgreSQL)
✅ **Dagster**: Webserver and daemon running
✅ **Cube**: API and refresh worker running
✅ **Code Changes**: T047-T049 completed and committed
✅ **Demo Image**: Built locally as `floe-demo-local:latest` with new refactored code
❌ **Deployment**: Using old remote image, not new local image with refactored code

## Problem

Deployed user-deployment pod still has OLD code (wrapper assets `silver_staging`, `gold_marts` instead of auto-discovered bronze assets from modules).

## Root Cause

Helm chart `charts/floe-dagster/values-local.yaml` references remote image:
```yaml
image:
  repository: "ghcr.io/obsidian-owl/floe-demo"
  tag: "latest"
```

This remote image was built before demo refactoring (T039-T043).

## Solution

### Step 1: Update Helm Chart to Use Local Image
```bash
# Edit charts/floe-dagster/values-local.yaml
# Change:
#   repository: "ghcr.io/obsidian-owl/floe-demo"
# To:
#   repository: "floe-demo-local"
```

### Step 2: Restart User Deployment with New Image
```bash
# Delete existing deployment to force image pull
kubectl delete deployment floe-dagster-dagster-user-deployments-floe-demo -n floe

# Helm upgrade will recreate with new image
helm upgrade floe-dagster charts/floe-dagster/ \
  --namespace floe \
  --values charts/floe-dagster/values-local.yaml \
  --wait

# Wait for new pod to be running
kubectl wait --for=condition=ready pod \
  -l app=dagster-user-deployments \
  -n floe \
  --timeout=120s
```

### Step 3: Verify New Code Deployed
```bash
# Check deployed definitions.py has new code
kubectl exec <pod-name> -n floe -- \
  cat /app/demo/data_engineering/orchestration/definitions.py | head -80

# Expected: See FloeDefinitions.from_compiled_artifacts(namespace="demo")
# NOT: Old wrapper assets (silver_staging, gold_marts)

# Check bronze.py exists
kubectl exec <pod-name> -n floe -- \
  ls -la /app/demo/data_engineering/orchestration/assets/

# Expected: See bronze.py, ops.py, __init__.py
```

### Step 4: Verify Auto-Discovery in Dagster UI

Access `http://localhost:30000` and verify:

**Assets Tab**:
- ✅ `bronze_customers` (from `demo.orchestration.assets.bronze`)
- ✅ `bronze_products` (from `demo.orchestration.assets.bronze`)
- ✅ `bronze_orders` (from `demo.orchestration.assets.bronze`)
- ✅ `bronze_order_items` (from `demo.orchestration.assets.bronze`)
- ✅ Individual dbt silver/gold models (NOT wrapper assets)
- ❌ NO `silver_staging` wrapper asset
- ❌ NO `gold_marts` wrapper asset

**Jobs Tab**:
- ✅ `demo_bronze` (from `floe.yaml orchestration.jobs`)
- ✅ `demo_pipeline` (from `floe.yaml orchestration.jobs`)
- ✅ `maintenance` (ops job from `floe.yaml orchestration.jobs`)

**Schedules Tab**:
- ✅ `bronze_refresh_schedule` (from `floe.yaml orchestration.schedules`)
- ✅ `transform_pipeline_schedule` (from `floe.yaml orchestration.schedules`)

**Sensors Tab**:
- ✅ `file_arrival_sensor` (from `floe.yaml orchestration.sensors`)

### Step 5: Run Pipeline and Verify Execution

```bash
# Check recent pipeline runs
kubectl get pods -n floe | grep dagster-run | grep Completed | head -3

# Get most recent run logs
RECENT_RUN=$(kubectl get pods -n floe | grep dagster-run | grep Completed | head -1 | awk '{print $1}')
kubectl logs $RECENT_RUN -n floe | tail -100

# Expected in logs:
# - "bronze_customers" asset execution
# - "bronze_products" asset execution
# - "bronze_orders" asset execution
# - "bronze_order_items" asset execution
# - Individual dbt model executions (per-model observability)
# - "RUN_SUCCESS" final status
```

### Step 6: Verify Observability

**Jaeger Traces**:
```bash
# Access Jaeger UI at http://localhost:30686
# Verify:
# - Service "floe-demo" present
# - Recent traces for pipeline runs
# - Spans for bronze_customers, bronze_products, etc.
# - Tags: dagster.run_id, dagster.step_key, service.name
```

**Marquez Lineage**:
```bash
# Access Marquez UI at http://localhost:30301
# Verify:
# - Namespace "floe-demo" exists
# - Jobs: demo_bronze, demo_pipeline, maintenance
# - Datasets: bronze tables, silver tables, gold tables
# - Lineage graph shows: raw → bronze → silver → gold
```

### Step 7: Verify Data Layer

**MinIO (Iceberg Storage)**:
```bash
# Access MinIO Console at http://localhost:30901
# Username: minioadmin, Password: minioadmin
# Verify bucket "warehouse" contains:
# - demo.db/bronze_customers/ (metadata + data)
# - demo.db/bronze_products/ (metadata + data)
# - demo.db/bronze_orders/ (metadata + data)
# - demo.db/bronze_order_items/ (metadata + data)
# - demo.db/silver_*/ (dbt outputs)
# - demo.db/gold_*/ (dbt outputs)
```

**Polaris (Iceberg Catalog)**:
```bash
# Check Polaris logs for table serving
kubectl logs -l app.kubernetes.io/name=polaris -n floe --tail=30

# Expected: No errors, catalog serving requests
```

### Step 8: Verify Cube Semantic Layer

**Cube REST API**:
```bash
# Get available cubes
curl -s http://localhost:30400/cubejs-api/v1/meta | jq '.cubes[].name'

# Expected: "Orders", "Customers", etc.

# Query metrics
curl -s http://localhost:30400/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"]
    }
  }' | jq '.data'

# Expected: JSON array with order_count and totalAmount
```

**Cube SQL API**:
```bash
# Test Postgres wire protocol
PGPASSWORD=cube_password psql -h localhost -p 30432 -U cube -d cube \
  -c "SELECT MEASURE(count) as order_count FROM Orders"

# Expected: Table output with metrics
```

### Step 9: Document E2E Results

Create `testing/e2e/VALIDATION_RESULTS.md`:
```markdown
# E2E Validation Results - [DATE]

## Test Execution

### Infrastructure: ✅ PASS
- All pods Running
- Services accessible via NodePort

### Auto-Discovery: ✅ PASS
- Bronze assets discovered from modules
- dbt models loaded as individual assets
- Jobs auto-created from floe.yaml
- Schedules auto-created from floe.yaml
- Sensors auto-created from floe.yaml

### Pipeline Execution: ✅ PASS
- demo_pipeline runs successfully
- All assets materialized
- No wrapper assets present

### Observability: ✅ PASS
- Jaeger traces present
- Marquez lineage complete
- Full end-to-end trace visible

### Data Layer: ✅ PASS
- Iceberg tables in MinIO
- Polaris catalog healthy
- Data queryable

### Semantic Layer: ✅ PASS
- Cube API queries succeed
- SQL API queries succeed
- Data matches source tables

## Verdict: ✅ PASS

All auto-discovery features working as designed.
Demo successfully showcases zero-boilerplate orchestration.
```

### Step 10: Commit T046 and Close Task

```bash
# Stage E2E documentation
git add testing/e2e/README.md
git add testing/e2e/VALIDATION_RESULTS.md

# Commit
git commit -m "docs(e2e): add end-to-end validation documentation for T046

T046: [010-orchestration-auto-discovery] E2E test documentation

Created comprehensive E2E test plan covering:
- Infrastructure health verification
- Dagster auto-discovery validation
- Pipeline execution verification
- Observability validation (Jaeger, Marquez)
- Data layer verification (Iceberg, Polaris)
- Semantic layer verification (Cube)

Result: Complete E2E validation framework for demo

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Close task
bd close floe-runtime-4kxf
```

## Next Actions

1. ✅ Update Helm chart to use `floe-demo-local:latest`
2. ✅ Restart deployment
3. ✅ Execute validation steps 4-8
4. ✅ Document results
5. ✅ Commit and close T046

## Demo Organization Issue

**User Question**: "Should these dockerfiles be in the demo folder?"

**Answer**: YES. To keep demo self-contained:

```bash
# Move Dockerfiles to demo folder
mkdir -p demo/docker
mv docker/Dockerfile.demo demo/docker/
mv docker/Dockerfile.cube demo/docker/  # If demo-specific

# Update build command in Makefile/docs
# From: docker build -f docker/Dockerfile.demo
# To:   docker build -f demo/docker/Dockerfile.demo
```

**User Question**: "Is there anything else related to the demo that should be in demo folder?"

**Items to move to `demo/`**:
- ✅ `demo/data_engineering/` (already there)
- ✅ `demo/platform/` (already there)
- ✅ `demo/docker/` (should be added - Dockerfile.demo)
- ❓ `charts/` - Keep at root (infrastructure, not demo-specific)
- ❓ `testing/docker/` - Keep separate (test infrastructure)

The demo folder should contain ONLY:
- `demo/data_engineering/` - Pipeline code
- `demo/platform/` - Platform configs
- `demo/docker/` - Demo-specific Dockerfiles
- `demo/README.md` - Demo quickstart (move from docs/demo-quickstart.md?)

## Timeline

- **Estimated Time**: 30-45 minutes
- **Step 1-2**: 5 minutes (update chart, redeploy)
- **Step 3**: 2 minutes (verify code)
- **Step 4-8**: 20-30 minutes (manual verification)
- **Step 9-10**: 5-10 minutes (document and commit)

## Success Criteria

✅ All infrastructure pods Running
✅ Dagster discovers assets, jobs, schedules, sensors from config
✅ Pipeline executes successfully
✅ Traces visible in Jaeger
✅ Lineage visible in Marquez
✅ Data in Iceberg (MinIO)
✅ Data queryable via Cube
✅ End-to-end trace complete
✅ Demo showcases zero-boilerplate orchestration
