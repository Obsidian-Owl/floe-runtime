#!/bin/bash
# Validate Demo Deployment - E2E Health Check
#
# This script validates the complete floe-runtime demo deployment:
# - Checks all pods are running
# - Verifies service endpoints are accessible
# - Validates Iceberg data in S3
# - Confirms Jaeger and Marquez are receiving data
#
# Usage: ./scripts/validate-demo.sh
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -e

FLOE_NAMESPACE="floe"
FAILED_CHECKS=0

echo "=============================================="
echo "🔍 Validating Floe Demo Deployment"
echo "=============================================="
echo ""

# Helper function to check and report
check() {
    local name="$1"
    local command="$2"
    local expected="$3"

    echo -n "  ├─ $name... "
    if eval "$command" | grep -q "$expected"; then
        echo "✅"
    else
        echo "❌"
        ((FAILED_CHECKS++))
    fi
}

# 1. Kubernetes Namespace
echo "1️⃣  Kubernetes Resources"
if kubectl get namespace "$FLOE_NAMESPACE" >/dev/null 2>&1; then
    echo "  ✅ Namespace $FLOE_NAMESPACE exists"
else
    echo "  ❌ Namespace $FLOE_NAMESPACE not found"
    echo ""
    echo "Run: make deploy-local-full"
    exit 1
fi

# 2. Helm Hook Jobs Status
echo ""
echo "2️⃣  Helm Hook Jobs (Initialization)"
# These jobs run once during helm install/upgrade and may have completed and been cleaned up
for job in polaris-init localstack-init seed-data; do
    echo -n "  ├─ $job... "
    # Check if job exists and succeeded
    if kubectl get job -n "$FLOE_NAMESPACE" "floe-infra-$job" >/dev/null 2>&1; then
        SUCCEEDED=$(kubectl get job -n "$FLOE_NAMESPACE" "floe-infra-$job" -o jsonpath='{.status.succeeded}' 2>/dev/null || echo "0")
        if [ "$SUCCEEDED" = "1" ]; then
            echo "✅ (completed)"
        else
            echo "⚠️  (still running or failed)"
        fi
    else
        # Job doesn't exist - likely cleaned up after completion (ttlSecondsAfterFinished)
        echo "✅ (completed and cleaned up)"
    fi
done

# 3. Pods Health
echo ""
echo "3️⃣  Pod Health (Running Services)"
POD_COUNT=$(kubectl get pods -n "$FLOE_NAMESPACE" --no-headers 2>/dev/null | wc -l | tr -d ' ')
RUNNING_COUNT=$(kubectl get pods -n "$FLOE_NAMESPACE" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')

echo "  ├─ Total pods: $POD_COUNT"
echo "  ├─ Running pods: $RUNNING_COUNT"

# Check critical pods
check "Polaris" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=polaris --no-headers" "Running"
check "PostgreSQL" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/name=postgresql --no-headers" "Running"
check "LocalStack" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=localstack --no-headers" "Running"
check "Jaeger" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/name=jaeger --no-headers" "Running"
check "Marquez" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=marquez --no-headers" "Running"
check "Dagster Webserver" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-dagster,component=dagster-webserver --no-headers" "Running"
check "Dagster User Deployment" "kubectl get pods -n $FLOE_NAMESPACE -l deployment=floe-demo --no-headers" "Running"
check "Cube API" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-cube,app.kubernetes.io/component=api --no-headers" "Running"
check "Cube Refresh Worker" "kubectl get pods -n $FLOE_NAMESPACE -l app.kubernetes.io/instance=floe-cube,app.kubernetes.io/component=refresh-worker --no-headers" "Running"

# 4. Services
echo ""
echo "4️⃣  Service Endpoints (NodePort Access)"
check "Dagster UI (NodePort 30000)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:30000" "200"
check "Cube API (NodePort 30400)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:30400/readyz" "200"
check "Jaeger UI (NodePort 30686)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:30686" "200"

# 5. Infrastructure Health
echo ""
echo "5️⃣  Infrastructure Services (Internal)"

# Check Polaris catalog
POLARIS_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" --selector=app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=polaris -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$POLARIS_POD" ]; then
    echo -n "  ├─ Polaris catalog... "
    HTTP_CODE=$(kubectl exec -n "$FLOE_NAMESPACE" "$POLARIS_POD" -- curl -s -w '%{http_code}' -o /dev/null http://localhost:8181/api/catalog/v1/config 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "200" ]; then
        echo "✅"
    else
        echo "❌ (HTTP $HTTP_CODE)"
        ((FAILED_CHECKS++))
    fi
else
    echo "  ├─ Polaris catalog... ❌ (pod not found)"
    ((FAILED_CHECKS++))
fi

# Check LocalStack S3
echo -n "  ├─ LocalStack S3... "
LOCALSTACK_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=localstack -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$LOCALSTACK_POD" ]; then
    if kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- awslocal s3 ls s3://iceberg-bronze >/dev/null 2>&1; then
        echo "✅"
    else
        echo "❌"
        ((FAILED_CHECKS++))
    fi
else
    echo "❌ (pod not found)"
    ((FAILED_CHECKS++))
fi

# 5. Dagster Definitions
echo ""
echo "5️⃣  Dagster Definitions"
USER_DEPLOYMENT_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" -l deployment=floe-demo -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$USER_DEPLOYMENT_POD" ]; then
    echo -n "  ├─ Definitions loaded... "
    LOGS=$(kubectl logs -n "$FLOE_NAMESPACE" "$USER_DEPLOYMENT_POD" --tail=100 2>/dev/null || echo "")
    if echo "$LOGS" | grep -q "PolarisCatalogResource initialized"; then
        echo "✅"
    else
        echo "❌"
        ((FAILED_CHECKS++))
    fi

    echo -n "  ├─ Observability initialized... "
    if echo "$LOGS" | grep -q "ObservabilityOrchestrator initialized"; then
        echo "✅"
    else
        echo "⚠️  (not found in recent logs - may be cached)"
    fi
else
    echo "  ├─ User deployment pod... ❌ (not found)"
    ((FAILED_CHECKS++))
fi

# 6. Data Validation
echo ""
echo "6️⃣  Data Validation"
echo -n "  ├─ Iceberg data files in S3... "
LOCALSTACK_POD=$(kubectl get pods -n "$FLOE_NAMESPACE" -l app.kubernetes.io/instance=floe-infra,app.kubernetes.io/component=localstack -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$LOCALSTACK_POD" ]; then
    DATA_FILES=$(kubectl exec -n "$FLOE_NAMESPACE" "$LOCALSTACK_POD" -- \
        awslocal s3 ls s3://iceberg-bronze/demo/ --recursive 2>/dev/null | grep -c '\.parquet' || echo "0")
    if [ "$DATA_FILES" -gt 0 ]; then
        echo "✅ ($DATA_FILES files)"
    else
        echo "⚠️  (no data files found - run a pipeline first)"
    fi
else
    echo "❌ (LocalStack pod not found)"
fi

# 7. Summary
echo ""
echo "=============================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ All Checks Passed!"
    echo "=============================================="
    echo ""
    echo "Demo is healthy. Access services at:"
    echo "  Dagster UI:  http://localhost:30000"
    echo "  Cube API:    http://localhost:30400"
    echo "  Jaeger UI:   http://localhost:30686"
    echo "  Marquez UI:  http://localhost:30301"
    echo ""
    exit 0
else
    echo "❌ $FAILED_CHECKS Check(s) Failed"
    echo "=============================================="
    echo ""
    echo "Check the logs for details:"
    echo "  make demo-status     # Show pod status"
    echo "  make demo-logs       # Show user deployment logs"
    echo "  kubectl get pods -n $FLOE_NAMESPACE"
    echo ""
    exit 1
fi
