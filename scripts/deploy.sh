#!/bin/bash
# deploy.sh - Master deployment script with pre-flight checks
#
# Robust deployment script for floe-runtime with safety checks and validation.
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   --clean         Clean deployment (delete namespace, full cleanup)
#   --quick         Quick deployment (skip cleanup)
#   --validate      Run E2E validation after deployment
#   --help          Show this help message
#
# Examples:
#   ./scripts/deploy.sh --clean --validate     # Full clean deployment with validation (recommended)
#   ./scripts/deploy.sh --quick                # Quick deployment (development)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default options
CLEAN=false
VALIDATE=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Usage function
usage() {
    cat <<EOF
Floe Runtime - Master Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --clean         Clean deployment (delete namespace, full cleanup)
    --quick         Quick deployment (skip cleanup)
    --validate      Run E2E validation after deployment
    --help          Show this help message

EXAMPLES:
    $0 --clean --validate     # Full clean deployment with validation (RECOMMENDED)
    $0 --quick                # Quick deployment (development)
    $0 --clean                # Clean deployment without validation

REQUIREMENTS:
    - kubectl installed and cluster accessible
    - helm installed
    - Infrastructure MUST be deployed with release name 'floe-infra'

See: ../demo/platform-config/DEPLOYMENT-REQUIREMENTS.md

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --quick)
            CLEAN=false
            shift
            ;;
        --validate)
            VALIDATE=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo ""
            usage
            ;;
    esac
done

# Pre-flight checks
echo "🔍 Pre-flight Checks"
echo "===================="
echo ""

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    echo "   Install: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi
echo -e "${GREEN}✅ kubectl found${NC}"

# Check helm
if ! command -v helm &> /dev/null; then
    echo -e "${RED}❌ helm not found. Please install helm.${NC}"
    echo "   Install: https://helm.sh/docs/intro/install/"
    exit 1
fi
echo -e "${GREEN}✅ helm found${NC}"

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster.${NC}"
    echo "   Check: kubectl cluster-info"
    exit 1
fi
echo -e "${GREEN}✅ Kubernetes cluster accessible${NC}"

# Check for orphaned resources in default namespace
echo ""
echo "Checking for orphaned resources in default namespace..."
if kubectl get deployment floe-infra-polaris -n default &> /dev/null; then
    echo -e "${YELLOW}⚠️  Found orphaned Polaris in default namespace${NC}"
    echo -e "${YELLOW}   Cleaning up...${NC}"
    kubectl delete deployment floe-infra-polaris -n default
    kubectl delete service floe-infra-polaris -n default --ignore-not-found
    echo -e "${GREEN}✅ Orphaned resources cleaned${NC}"
else
    echo -e "${GREEN}✅ No orphaned resources in default namespace${NC}"
fi

# Check for stuck Helm releases
echo ""
echo "Checking for stuck Helm releases..."
STUCK_RELEASES=$(helm list -n floe 2>/dev/null | grep -E "pending-install|pending-upgrade" || true)
if [[ -n "$STUCK_RELEASES" ]]; then
    echo -e "${YELLOW}⚠️  Found stuck Helm releases:${NC}"
    echo "$STUCK_RELEASES"
    echo -e "${YELLOW}   These will be cleaned during deployment${NC}"
else
    echo -e "${GREEN}✅ No stuck Helm releases${NC}"
fi

echo ""
echo -e "${GREEN}✅ All pre-flight checks passed${NC}"
echo ""

# Main deployment
echo "🚀 Starting Deployment"
echo "======================"
echo ""

if [ "$CLEAN" = true ]; then
    echo "🧹 Running clean deployment..."
    echo ""
    "$SCRIPT_DIR/deploy/local.sh"
else
    echo "⚡ Running quick deployment..."
    echo ""

    # Quick deployment: infrastructure → dagster → cube
    echo "Deploying infrastructure..."
    make deploy-local-infra

    echo ""
    echo "Waiting for infrastructure pods..."
    kubectl wait --for=condition=ready pod \
        --field-selector=status.phase!=Succeeded \
        -n floe \
        --timeout=300s 2>&1 | grep -v "no matching resources" || true

    echo ""
    echo "Deploying Dagster..."
    make deploy-local-dagster

    echo ""
    echo "Deploying Cube..."
    make deploy-local-cube
fi

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"

# Validation
if [ "$VALIDATE" = true ]; then
    echo ""
    echo "✅ Running E2E validation..."
    echo "============================"
    echo ""
    "$SCRIPT_DIR/validate/e2e.sh"
    echo ""
    echo -e "${GREEN}✅ Validation complete!${NC}"
fi

# Final status
echo ""
echo "📊 Deployment Summary"
echo "====================="
echo ""

# Check pod status
echo "Pod Status:"
kubectl get pods -n floe 2>/dev/null || echo "  No pods found"

echo ""
echo "Helm Releases:"
helm list -n floe 2>/dev/null || echo "  No releases found"

echo ""
echo -e "${GREEN}🎉 All done!${NC}"
echo ""
echo "Next steps:"
echo "  • Check logs: kubectl logs -n floe <pod-name>"
echo "  • Port-forward services: kubectl port-forward -n floe svc/<service> <port>"
echo "  • Run validation: ./scripts/validate/e2e.sh"
echo ""
