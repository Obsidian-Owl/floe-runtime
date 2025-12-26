#!/bin/bash
# Floe Runtime Quickstart - One Command Demo
#
# This script performs a complete fresh deployment of floe-runtime:
# 1. Cleans existing deployment (if any)
# 2. Builds demo Docker image
# 3. Deploys complete stack to Kubernetes
# 4. Validates deployment health
# 5. Shows service URLs
#
# Prerequisites:
#   - Docker Desktop with Kubernetes enabled
#   - kubectl configured for Docker Desktop
#   - Helm 3.x installed
#   - uv package manager installed
#
# Usage: ./scripts/quickstart.sh [--clean-all]
#   --clean-all : Remove Docker images before rebuild (slower)

set -e

CLEAN_ALL_FLAG=""
if [[ "$1" == "--clean-all" ]]; then
    CLEAN_ALL_FLAG="--all"
fi

echo "=============================================="
echo "🚀 Floe Runtime Quickstart"
echo "=============================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "❌ Helm not found. Please install Helm 3.x."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check Kubernetes is running
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Kubernetes cluster not accessible. Enable Kubernetes in Docker Desktop."
    exit 1
fi

echo "✅ All prerequisites met"
echo ""

# Step 1: Clean existing deployment
echo "=============================================="
echo "1️⃣  Cleaning Existing Deployment"
echo "=============================================="
./scripts/clean-demo.sh $CLEAN_ALL_FLAG
echo ""

# Step 2: Install dependencies
echo "=============================================="
echo "2️⃣  Installing Dependencies"
echo "=============================================="
echo "📦 Running: uv sync --all-packages"
uv sync --all-packages
echo "✅ Dependencies installed"
echo ""

# Step 3: Build demo image
echo "=============================================="
echo "3️⃣  Building Demo Image"
echo "=============================================="
echo "🐳 Building ghcr.io/obsidian-owl/floe-demo:latest"
make demo-image-build
echo ""

# Step 4: Deploy complete stack
echo "=============================================="
echo "4️⃣  Deploying to Kubernetes"
echo "=============================================="
echo "⎈ Running: make deploy-local-full"
echo ""
make deploy-local-full
echo ""

# Wait for pods to be ready
echo "⏳ Waiting for all pods to be ready (timeout: 3 minutes)..."
kubectl wait --for=condition=ready pod --all -n floe --timeout=180s 2>&1 | grep -v "condition met" || true
echo ""

# Step 5: Validate deployment
echo "=============================================="
echo "5️⃣  Validating Deployment"
echo "=============================================="
./scripts/validate-demo.sh
VALIDATION_EXIT_CODE=$?
echo ""

# Step 6: Show next steps
if [ $VALIDATION_EXIT_CODE -eq 0 ]; then
    echo "=============================================="
    echo "✅ Quickstart Complete!"
    echo "=============================================="
    echo ""
    echo "🎯 Next Steps:"
    echo ""
    echo "1. Access Dagster UI:"
    echo "   http://localhost:30000"
    echo ""
    echo "2. Run your first pipeline:"
    echo "   - Navigate to 'Jobs' in Dagster UI"
    echo "   - Click 'demo_bronze'"
    echo "   - Click 'Launch Run'"
    echo ""
    echo "3. Verify observability:"
    echo "   Jaeger (Traces):  http://localhost:30686"
    echo "   Marquez (Lineage): http://localhost:30301"
    echo ""
    echo "4. Query data via Cube:"
    echo "   curl 'http://localhost:30400/cubejs-api/v1/load' \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"query\":{\"measures\":[\"Orders.count\"]}}'"
    echo ""
    echo "5. Explore the data:"
    echo "   kubectl exec -n floe -l app.kubernetes.io/name=localstack -- \\"
    echo "     awslocal s3 ls s3://iceberg-bronze/demo/ --recursive"
    echo ""
    echo "📚 Documentation:"
    echo "   README: demo/README.md"
    echo "   Docs:   docs/"
    echo ""
    echo "🛠️  Useful commands:"
    echo "   make demo-status     # Check deployment status"
    echo "   make demo-logs       # View logs"
    echo "   make demo-cleanup    # Remove completed pods"
    echo "   make undeploy-local  # Remove deployment"
    echo ""
else
    echo "=============================================="
    echo "⚠️  Validation Failed"
    echo "=============================================="
    echo ""
    echo "Some checks failed. Review the output above for details."
    echo ""
    echo "Common issues:"
    echo "  - Pods still starting: Wait a few minutes and re-run ./scripts/validate-demo.sh"
    echo "  - Resource limits: Ensure Docker Desktop has ≥4GB RAM allocated"
    echo "  - Port conflicts: Check nothing else is using ports 30000-30686"
    echo ""
    echo "Debug commands:"
    echo "  kubectl get pods -n floe"
    echo "  kubectl describe pod -n floe <pod-name>"
    echo "  make demo-logs"
    echo ""
    exit 1
fi
