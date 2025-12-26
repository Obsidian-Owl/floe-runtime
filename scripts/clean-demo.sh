#!/bin/bash
# Clean Demo Environment - Complete Reset
#
# This script performs a complete cleanup of the local demo environment:
# - Removes all Kubernetes resources
# - Cleans Docker volumes and images
# - Removes build artifacts
#
# Usage: ./scripts/clean-demo.sh [--all]
#   --all  : Also remove Docker images (slower rebuild)

set -e

FLOE_NAMESPACE="floe"
CLEAN_IMAGES=false

# Parse arguments
if [[ "$1" == "--all" ]]; then
    CLEAN_IMAGES=true
fi

echo "=============================================="
echo "🧹 Cleaning Floe Demo Environment"
echo "=============================================="
echo ""

# 1. Stop all port-forwards
echo "1️⃣  Stopping port-forwards..."
pkill -f 'kubectl port-forward' 2>/dev/null || true
rm -f /tmp/pf-*.log /tmp/pf-*.pid 2>/dev/null || true
echo "   ✅ Port-forwards stopped"
echo ""

# 2. Remove Kubernetes resources
echo "2️⃣  Removing Kubernetes resources..."
if kubectl get namespace "$FLOE_NAMESPACE" >/dev/null 2>&1; then
    # Uninstall Helm releases
    helm uninstall floe-cube -n "$FLOE_NAMESPACE" 2>/dev/null || echo "   ℹ️  floe-cube not found"
    helm uninstall floe-dagster -n "$FLOE_NAMESPACE" 2>/dev/null || echo "   ℹ️  floe-dagster not found"
    helm uninstall floe-infra -n "$FLOE_NAMESPACE" 2>/dev/null || echo "   ℹ️  floe-infra not found"

    # Delete namespace (removes all resources including PVCs, Secrets, ConfigMaps)
    kubectl delete namespace "$FLOE_NAMESPACE" --timeout=120s 2>/dev/null || true

    # Wait for namespace deletion
    echo "   ⏳ Waiting for namespace deletion..."
    timeout 120s bash -c "while kubectl get namespace $FLOE_NAMESPACE >/dev/null 2>&1; do sleep 2; done" || true

    echo "   ✅ Kubernetes resources removed"
else
    echo "   ℹ️  Namespace $FLOE_NAMESPACE not found"
fi
echo ""

# 3. Clean Docker volumes
echo "3️⃣  Cleaning Docker volumes..."
docker volume prune -f 2>/dev/null || true
echo "   ✅ Docker volumes cleaned"
echo ""

# 4. Clean Docker images (optional)
if [ "$CLEAN_IMAGES" = true ]; then
    echo "4️⃣  Removing Docker images..."
    docker rmi ghcr.io/obsidian-owl/floe-demo:latest 2>/dev/null || echo "   ℹ️  Demo image not found"
    docker image prune -f 2>/dev/null || true
    echo "   ✅ Docker images removed"
    echo ""
fi

# 5. Clean build artifacts
echo "5️⃣  Cleaning build artifacts..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
rm -rf /tmp/dagster-* 2>/dev/null || true
echo "   ✅ Build artifacts cleaned"
echo ""

echo "=============================================="
echo "✅ Cleanup Complete!"
echo "=============================================="
echo ""
echo "Your environment is now clean. To deploy the demo:"
echo "  make demo-image-build    # Build demo image"
echo "  make deploy-local-full   # Deploy complete stack"
echo "  make show-urls           # See service URLs"
echo ""
