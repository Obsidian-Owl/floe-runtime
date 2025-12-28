#!/usr/bin/env bash
# Complete Infrastructure Rebuild with Timezone and SHA Tagging
# Applies Australia/Sydney timezone to ALL pods and implements SHA-based deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

GIT_SHA=$(git rev-parse --short HEAD)
DEMO_IMAGE="ghcr.io/obsidian-owl/floe-demo:${GIT_SHA}"
TIMEZONE="Australia/Sydney"

echo "=========================================="
echo "🌏 Complete Infrastructure Rebuild"
echo "=========================================="
echo "Git SHA: $GIT_SHA"
echo "Image: $DEMO_IMAGE"
echo "Timezone: $TIMEZONE"
echo ""

# Step 1: Build Docker image with SHA tag
echo "📦 Building Docker image..."
docker build -f docker/Dockerfile.demo -t "$DEMO_IMAGE" .
docker tag "$DEMO_IMAGE" ghcr.io/obsidian-owl/floe-demo:latest
echo "✅ Image built: $DEMO_IMAGE"
echo ""

# Step 2: Teardown existing cluster
echo "🗑️  Tearing down existing floe namespace..."
kubectl delete namespace floe --wait --timeout=120s || echo "Namespace already deleted"
kubectl get pv | grep floe | awk '{print $1}' | xargs -r kubectl delete pv || echo "No PVs to delete"
echo "✅ Cluster torn down"
echo ""

# Step 3: Deploy infrastructure with timezone from platform.yaml
echo "⎈ Deploying floe-infrastructure..."
make deploy-local-infra
echo "✅ Infrastructure deployed"
echo ""

# Step 4: Wait for Polaris to be ready
echo "⏳ Waiting for Polaris to be ready..."
kubectl wait --for=condition=ready pod -n floe -l app=polaris --timeout=120s
sleep 10
echo "✅ Polaris ready"
echo ""

# Step 5: Deploy Dagster with SHA-tagged image
echo "⎈ Deploying floe-dagster with SHA tag..."
helm upgrade --install floe-dagster demo/platform-config/charts/floe-dagster/ \
  --namespace floe \
  --values demo/platform-config/charts/floe-dagster/values-local.yaml \
  --set dagster-user-deployments.deployments[0].image.tag="$GIT_SHA" \
  --set dagster-user-deployments.deployments[0].image.pullPolicy=Always \
  --wait --timeout 5m
echo "✅ Dagster deployed with image: $DEMO_IMAGE"
echo ""

# Step 6: Verify timezone in all pods
echo "🕒 Verifying timezone in all pods..."
echo ""
for pod in $(kubectl get pods -n floe -o name); do
    pod_name=$(echo "$pod" | cut -d'/' -f2)
    tz=$(kubectl exec -n floe "$pod_name" -- date +%Z 2>/dev/null || echo "N/A")
    time=$(kubectl exec -n floe "$pod_name" -- date 2>/dev/null || echo "N/A")
    echo "  $pod_name: $tz | $time"
done
echo ""

# Step 7: Check deployment updated time in Dagster UI
echo "📊 Deployment info:"
kubectl get deployment -n floe floe-dagster-dagster-user-deployments-floe-demo \
  -o jsonpath='{.metadata.name}{"\n  Image: "}{.spec.template.spec.containers[0].image}{"\n  Pull Policy: "}{.spec.template.spec.containers[0].imagePullPolicy}{"\n"}'
echo ""

echo "=========================================="
echo "✅ Rebuild Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Access Dagster UI: http://localhost:30000"
echo "  2. Check deployment shows 'Updated: Just now'"
echo "  3. Run pipeline: ./scripts/materialize-demo.sh --pipeline"
echo ""
