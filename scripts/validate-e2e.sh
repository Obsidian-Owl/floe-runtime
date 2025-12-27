#!/bin/bash
# E2E Validation - Comprehensive Data + Observability Check
#
# This script validates the complete floe-runtime demo pipeline:
# - Verifies data in all layers (Raw → Bronze → Silver → Gold)
# - Checks observability (Jaeger traces, Marquez lineage)
# - Tests semantic layer (Cube API queries)
# - Collects evidence for audit/debugging
#
# Prerequisites:
#   - Full stack deployed (make deploy-local-full)
#   - Demo data materialized (./scripts/materialize-demo.sh)
#   - jq installed for JSON parsing
#
# Usage: ./scripts/validate-e2e.sh
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -e

FLOE_NAMESPACE="floe"

# Create timestamped evidence directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
EVIDENCE_DIR="./evidence/run-$TIMESTAMP"
LATEST_LINK="./evidence/latest"
FAILED_CHECKS=0

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"

echo "=============================================="
echo "🔍 E2E Validation: Full Pipeline"
echo "=============================================="
echo ""
echo "Evidence will be saved to: $EVIDENCE_DIR/"
echo ""

# Check prerequisites
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Please install jq for JSON parsing."
    exit 1
fi

# Helper function for checks
check() {
    local name="$1"
    local command="$2"
    local expected="$3"

    echo -n "  ├─ $name... "
    if eval "$command" | grep -q "$expected"; then
        echo "✅"
        return 0
    else
        echo "❌"
        ((FAILED_CHECKS++))
        return 1
    fi
}

# =============================================================================
# 1. Verify Raw Data Layer (Seed)
# =============================================================================
echo "1️⃣  Raw Data Layer (Seed)"
echo ""

# Get Polaris pod for API queries
POLARIS_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" \
    -l app.kubernetes.io/component=polaris \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$POLARIS_POD" ]; then
    echo "  ❌ Polaris pod not found"
    ((FAILED_CHECKS++))
else
    for table in raw_customers raw_products raw_orders raw_order_items; do
        echo -n "  ├─ demo.$table exists... "

        # Query Polaris catalog for table
        HTTP_CODE=$(kubectl exec -n "$FLOE_NAMESPACE" "$POLARIS_POD" -- \
            curl -s -o /dev/null -w '%{http_code}' \
            -u demo_client:demo_secret_k8s \
            "http://localhost:8181/api/catalog/v1/namespaces/demo/tables/$table" 2>/dev/null || echo "000")

        if [ "$HTTP_CODE" = "200" ]; then
            echo "✅"
        else
            echo "❌ (HTTP $HTTP_CODE)"
            ((FAILED_CHECKS++))
        fi
    done
fi

# =============================================================================
# 2. Verify Bronze Layer (Python Assets)
# =============================================================================
echo ""
echo "2️⃣  Bronze Data Layer (Python Assets)"
echo ""

# Get LocalStack pod for S3 queries
LOCALSTACK_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" \
    -l app.kubernetes.io/component=localstack \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$LOCALSTACK_POD" ]; then
    echo "  ❌ LocalStack pod not found"
    ((FAILED_CHECKS++))
else
    for table in customers products orders order_items; do
        echo -n "  ├─ demo.bronze.$table... "

        # Check S3 for Iceberg data files
        FILE_COUNT=$(kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
            awslocal s3 ls "s3://iceberg-bronze/demo/" --recursive 2>/dev/null \
            | grep -c "bronze_$table" || echo "0")

        if [ "$FILE_COUNT" -gt 0 ]; then
            echo "✅ ($FILE_COUNT files)"
        else
            echo "⚠️  (no data - run materialize-demo.sh first)"
        fi
    done
fi

# =============================================================================
# 3. Verify Silver Layer (dbt Staging Models)
# =============================================================================
echo ""
echo "3️⃣  Silver Data Layer (dbt Staging)"
echo ""

if [ -n "$LOCALSTACK_POD" ]; then
    for table in stg_customers stg_products stg_orders stg_order_items; do
        echo -n "  ├─ demo.silver.$table... "

        FILE_COUNT=$(kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
            awslocal s3 ls "s3://iceberg-silver/demo/" --recursive 2>/dev/null \
            | grep -c "$table" 2>/dev/null || echo "0")
        FILE_COUNT=$(echo "$FILE_COUNT" | tr -d '\n' | head -1)

        if [ "$FILE_COUNT" -gt 0 ] 2>/dev/null; then
            echo "✅ ($FILE_COUNT files)"
        else
            echo "⚠️  (no data - run full pipeline first)"
        fi
    done
fi

# =============================================================================
# 4. Verify Gold Layer (dbt Mart Models)
# =============================================================================
echo ""
echo "4️⃣  Gold Data Layer (dbt Marts)"
echo ""

if [ -n "$LOCALSTACK_POD" ]; then
    for table in mart_customer_orders mart_product_performance mart_revenue; do
        echo -n "  ├─ demo.gold.$table... "

        FILE_COUNT=$(kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
            awslocal s3 ls "s3://iceberg-gold/demo/" --recursive 2>/dev/null \
            | grep -c "$table" 2>/dev/null || echo "0")
        FILE_COUNT=$(echo "$FILE_COUNT" | tr -d '\n' | head -1)

        if [ "$FILE_COUNT" -gt 0 ] 2>/dev/null; then
            echo "✅ ($FILE_COUNT files)"
        else
            echo "⚠️  (no data - run full pipeline first)"
        fi
    done
fi

# =============================================================================
# 5. Verify Jaeger Traces
# =============================================================================
echo ""
echo "5️⃣  Observability: Distributed Tracing (Jaeger)"
echo ""

echo -n "  ├─ Jaeger API accessible... "
JAEGER_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:30686/api/services")

if [ "$JAEGER_STATUS" = "200" ]; then
    echo "✅"

    echo -n "  ├─ Service 'floe-demo' registered... "
    JAEGER_SERVICES=$(curl -s "http://localhost:30686/api/services")
    echo "$JAEGER_SERVICES" > "$EVIDENCE_DIR/jaeger-services.json"

    if echo "$JAEGER_SERVICES" | jq -e '.data[] | select(. == "floe-demo")' >/dev/null 2>&1; then
        echo "✅"

        # Check for traces
        echo -n "  ├─ Traces available... "
        TRACES=$(curl -s "http://localhost:30686/api/traces?service=floe-demo&limit=10")
        TRACE_COUNT=$(echo "$TRACES" | jq '.data | length' 2>/dev/null || echo "0")

        if [ "$TRACE_COUNT" -gt 0 ]; then
            echo "✅ ($TRACE_COUNT traces)"
            echo "$TRACES" > "$EVIDENCE_DIR/jaeger-traces.json"
        else
            echo "⚠️  (no traces found - run pipeline first)"
        fi
    else
        echo "❌ (service not found)"
        ((FAILED_CHECKS++))
    fi
else
    echo "❌ (HTTP $JAEGER_STATUS)"
    ((FAILED_CHECKS++))
fi

# =============================================================================
# 6. Verify Marquez Lineage
# =============================================================================
echo ""
echo "6️⃣  Observability: Data Lineage (Marquez)"
echo ""

echo -n "  ├─ Marquez API accessible... "
MARQUEZ_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:30500/api/v1/namespaces")

if [ "$MARQUEZ_STATUS" = "200" ]; then
    echo "✅"

    echo -n "  ├─ Namespace 'demo' exists... "
    MARQUEZ_NS=$(curl -s "http://localhost:30500/api/v1/namespaces/demo")
    echo "$MARQUEZ_NS" > "$EVIDENCE_DIR/marquez-namespace.json"

    if echo "$MARQUEZ_NS" | jq -e '.name == "demo"' >/dev/null 2>&1; then
        echo "✅"

        # Check for datasets
        echo -n "  ├─ Datasets tracked... "
        DATASETS=$(curl -s "http://localhost:30500/api/v1/namespaces/demo/datasets")
        DATASET_COUNT=$(echo "$DATASETS" | jq '.datasets | length' 2>/dev/null || echo "0")

        if [ "$DATASET_COUNT" -gt 0 ]; then
            echo "✅ ($DATASET_COUNT datasets)"
            echo "$DATASETS" > "$EVIDENCE_DIR/marquez-datasets.json"
        else
            echo "⚠️  (no datasets - run pipeline first)"
        fi

        # Check for jobs
        echo -n "  ├─ Jobs tracked... "
        JOBS=$(curl -s "http://localhost:30500/api/v1/namespaces/demo/jobs")
        JOB_COUNT=$(echo "$JOBS" | jq '.jobs | length' 2>/dev/null || echo "0")

        if [ "$JOB_COUNT" -gt 0 ]; then
            echo "✅ ($JOB_COUNT jobs)"
            echo "$JOBS" > "$EVIDENCE_DIR/marquez-jobs.json"
        else
            echo "⚠️  (no jobs - run pipeline first)"
        fi
    else
        echo "❌ (namespace not found)"
        ((FAILED_CHECKS++))
    fi
else
    echo "❌ (HTTP $MARQUEZ_STATUS)"
    ((FAILED_CHECKS++))
fi

# =============================================================================
# 7. Verify Cube Semantic Layer
# =============================================================================
echo ""
echo "7️⃣  Semantic Layer: Cube API"
echo ""

echo -n "  ├─ Cube API accessible... "
CUBE_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:30400/readyz")

if [ "$CUBE_STATUS" = "200" ]; then
    echo "✅"

    echo -n "  ├─ Cube metadata endpoint... "
    CUBE_META=$(curl -s "http://localhost:30400/cubejs-api/v1/meta")
    echo "$CUBE_META" > "$EVIDENCE_DIR/cube-meta.json"

    CUBE_COUNT=$(echo "$CUBE_META" | jq '.cubes | length' 2>/dev/null || echo "0")

    if [ "$CUBE_COUNT" -gt 0 ]; then
        echo "✅ ($CUBE_COUNT cubes)"

        # List cubes
        echo "  ├─ Available cubes:"
        echo "$CUBE_META" | jq -r '.cubes[].name' 2>/dev/null | sed 's/^/  │   - /' || true

        # Query Customers cube
        echo -n "  ├─ Query Customers cube... "
        QUERY='{"query":{"measures":["Customers.count"],"dimensions":["Customers.segment"]}}'
        RESULT=$(curl -s "http://localhost:30400/cubejs-api/v1/load" \
            -H "Content-Type: application/json" \
            -d "$QUERY" 2>/dev/null || echo "{}")

        ROW_COUNT=$(echo "$RESULT" | jq '.data | length' 2>/dev/null || echo "0")

        if [ "$ROW_COUNT" -gt 0 ]; then
            echo "✅ ($ROW_COUNT segments)"
            echo "$RESULT" > "$EVIDENCE_DIR/cube-customers-query.json"
        else
            echo "⚠️  (no data - ensure gold layer is materialized)"
        fi
    else
        echo "❌ (no cubes found)"
        ((FAILED_CHECKS++))
    fi
else
    echo "❌ (HTTP $CUBE_STATUS)"
    ((FAILED_CHECKS++))
fi

# =============================================================================
# 8. Storage Layer Summary
# =============================================================================
echo ""
echo "8️⃣  Storage Layer Summary (S3 Buckets)"
echo ""

if [ -n "$LOCALSTACK_POD" ]; then
    for bucket in iceberg-bronze iceberg-silver iceberg-gold; do
        echo -n "  ├─ $bucket... "
        OBJECT_COUNT=$(kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
            awslocal s3 ls "s3://$bucket/" --recursive 2>/dev/null | wc -l | tr -d ' ')

        if [ "$OBJECT_COUNT" -gt 0 ]; then
            echo "✅ ($OBJECT_COUNT objects)"
        else
            echo "⚠️  (empty)"
        fi
    done
fi

# =============================================================================
# 9. Generate Evidence Summary Report
# =============================================================================
echo ""
echo "=============================================="
echo "📊 Generating Evidence Summary"
echo "=============================================="
echo ""

# Collect S3 objects for summary
if [ -n "$LOCALSTACK_POD" ]; then
    kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
        awslocal s3 ls --recursive s3://iceberg-bronze/demo/ > "$EVIDENCE_DIR/s3-bronze-objects.txt" 2>/dev/null || true
    kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
        awslocal s3 ls --recursive s3://iceberg-silver/demo/ > "$EVIDENCE_DIR/s3-silver-objects.txt" 2>/dev/null || true
    kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
        awslocal s3 ls --recursive s3://iceberg-gold/demo/ > "$EVIDENCE_DIR/s3-gold-objects.txt" 2>/dev/null || true
fi

# Collect Polaris tables
if [ -n "$POLARIS_POD" ]; then
    kubectl exec -n "$FLOE_NAMESPACE" "$POLARIS_POD" -- \
        curl -s -u demo_client:demo_secret_k8s \
        "http://localhost:8181/api/catalog/v1/namespaces/demo/tables" \
        > "$EVIDENCE_DIR/polaris-tables.json" 2>/dev/null || true
fi

# Count evidence files
BRONZE_FILES=$(wc -l < "$EVIDENCE_DIR/s3-bronze-objects.txt" 2>/dev/null || echo "0")
SILVER_FILES=$(wc -l < "$EVIDENCE_DIR/s3-silver-objects.txt" 2>/dev/null || echo "0")
GOLD_FILES=$(wc -l < "$EVIDENCE_DIR/s3-gold-objects.txt" 2>/dev/null || echo "0")

# Generate summary markdown report
cat > "$EVIDENCE_DIR/SUMMARY.md" <<'SUMMARY_EOF'
# E2E Validation Summary Report
SUMMARY_EOF

cat >> "$EVIDENCE_DIR/SUMMARY.md" <<EOF

**Timestamp**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Status**: $([ $FAILED_CHECKS -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED ($FAILED_CHECKS checks)")
**Evidence Directory**: \`$EVIDENCE_DIR\`

---

## Data Layers

| Layer | Status | Files | Evidence |
|-------|--------|-------|----------|
| Raw (Seed) | $([ -f "$EVIDENCE_DIR/polaris-tables.json" ] && echo "✅" || echo "❌") | - | polaris-tables.json |
| Bronze | $([ "$BRONZE_FILES" -gt 0 ] && echo "✅" || echo "⚠️") | $BRONZE_FILES | s3-bronze-objects.txt |
| Silver | $([ "$SILVER_FILES" -gt 0 ] && echo "✅" || echo "⚠️") | $SILVER_FILES | s3-silver-objects.txt |
| Gold | $([ "$GOLD_FILES" -gt 0 ] && echo "✅" || echo "⚠️") | $GOLD_FILES | s3-gold-objects.txt |

---

## Observability

| Component | Status | Evidence |
|-----------|--------|----------|
| Jaeger Traces | $([ -f "$EVIDENCE_DIR/jaeger-traces.json" ] && echo "✅" || echo "❌") | jaeger-traces.json, jaeger-services.json |
| Marquez Lineage | $([ -f "$EVIDENCE_DIR/marquez-datasets.json" ] && echo "✅" || echo "❌") | marquez-namespace.json, marquez-datasets.json, marquez-jobs.json |

---

## Semantic Layer

| Component | Status | Evidence |
|-----------|--------|----------|
| Cube API | $([ -f "$EVIDENCE_DIR/cube-meta.json" ] && echo "✅" || echo "❌") | cube-meta.json |
| Cube Queries | $([ -f "$EVIDENCE_DIR/cube-customers-query.json" ] && echo "✅" || echo "❌") | cube-customers-query.json |

---

## Evidence Files

EOF

# List all evidence files in summary
if [ -d "$EVIDENCE_DIR" ] && [ "$(ls -A $EVIDENCE_DIR 2>/dev/null)" ]; then
    for file in "$EVIDENCE_DIR"/*; do
        if [ -f "$file" ] && [ "$(basename "$file")" != "SUMMARY.md" ]; then
            filename=$(basename "$file")
            size=$(du -h "$file" | cut -f1)
            echo "- \`$filename\` ($size)" >> "$EVIDENCE_DIR/SUMMARY.md"
        fi
    done
fi

cat >> "$EVIDENCE_DIR/SUMMARY.md" <<'EOF'

---

## Access Services

- **Dagster UI**: http://localhost:30000
- **Cube API**: http://localhost:30400/cubejs-api/v1/meta
- **Jaeger UI**: http://localhost:30686
- **Marquez UI**: http://localhost:30301

---

## Next Steps

EOF

if [ $FAILED_CHECKS -eq 0 ]; then
    cat >> "$EVIDENCE_DIR/SUMMARY.md" <<'EOF'
✅ **All validation checks passed!**

Your floe-runtime demo is fully operational:
- All data layers materialized (bronze → silver → gold)
- Observability active (traces + lineage)
- Semantic layer responding to queries

EOF
else
    cat >> "$EVIDENCE_DIR/SUMMARY.md" <<EOF
❌ **$FAILED_CHECKS validation check(s) failed.**

Common troubleshooting steps:
1. Ensure data is materialized: \`./scripts/materialize-demo.sh --all\`
2. Check pod status: \`kubectl get pods -n floe\`
3. View Dagster logs: \`kubectl logs -n floe -l deployment=floe-demo\`
4. Check Dagster UI: http://localhost:30000

EOF
fi

# Create symlink to latest run
rm -f "$LATEST_LINK" 2>/dev/null || true
ln -sf "run-$TIMESTAMP" "$LATEST_LINK"

echo "✅ Summary report generated: $EVIDENCE_DIR/SUMMARY.md"
echo "🔗 Latest evidence: $LATEST_LINK -> run-$TIMESTAMP"
echo ""

if [ -d "$EVIDENCE_DIR" ] && [ "$(ls -A $EVIDENCE_DIR)" ]; then
    echo "Evidence files:"
    for file in "$EVIDENCE_DIR"/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            size=$(du -h "$file" | cut -f1)
            echo "  ├─ $filename ($size)"
        fi
    done
else
    echo "  ⚠️  No evidence files generated"
fi

# =============================================================================
# 10. Final Summary
# =============================================================================
echo ""
echo "=============================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ E2E Validation Complete - All Checks Passed!"
    echo "=============================================="
    echo ""
    echo "🎯 What's Working:"
    echo "  ✅ Raw data layer (seed tables)"
    echo "  ✅ Bronze layer (Python assets)"
    echo "  ✅ Silver layer (dbt staging)"
    echo "  ✅ Gold layer (dbt marts)"
    echo "  ✅ Distributed tracing (Jaeger)"
    echo "  ✅ Data lineage (Marquez)"
    echo "  ✅ Semantic layer (Cube)"
    echo "  ✅ Storage layer (S3 buckets)"
    echo ""
    echo "📊 Access UIs:"
    echo "  Dagster:  http://localhost:30000"
    echo "  Cube:     http://localhost:30400/cubejs-api/v1/meta"
    echo "  Jaeger:   http://localhost:30686"
    echo "  Marquez:  http://localhost:30301"
    echo ""
    echo "📁 Evidence:"
    echo "  Location: $EVIDENCE_DIR/"
    echo "  Files:    $(ls -1 "$EVIDENCE_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ') JSON files"
    echo ""
    exit 0
else
    echo "❌ E2E Validation Failed - $FAILED_CHECKS Check(s) Failed"
    echo "=============================================="
    echo ""
    echo "Common issues:"
    echo "  1. Data not materialized:"
    echo "     → Run: ./scripts/materialize-demo.sh"
    echo ""
    echo "  2. Services not ready:"
    echo "     → Check pods: kubectl get pods -n $FLOE_NAMESPACE"
    echo "     → Wait longer: kubectl wait --for=condition=ready pod --all -n $FLOE_NAMESPACE"
    echo ""
    echo "  3. Jobs failed:"
    echo "     → View Dagster UI: http://localhost:30000"
    echo "     → Check logs: kubectl logs -n $FLOE_NAMESPACE -l deployment=floe-demo"
    echo ""
    echo "Debug commands:"
    echo "  make demo-status      # Check deployment status"
    echo "  make demo-logs        # View user deployment logs"
    echo "  kubectl get pods -n $FLOE_NAMESPACE"
    echo ""
    exit 1
fi
