#!/bin/bash
set -e

echo "🧹 Clean Deployment Script"
echo "=========================="

# Clean up namespace
echo "1. Cleaning up floe namespace..."
helm uninstall floe-infra -n floe --wait || true
helm uninstall floe-dagster -n floe --wait || true  
helm uninstall floe-cube -n floe --wait || true
kubectl delete namespace floe || true
sleep 10

# Recreate namespace
echo "2. Creating fresh namespace..."
kubectl create namespace floe

# Deploy infrastructure
echo "3. Deploying infrastructure..."
helm install floe-infra demo/platform-config/charts/floe-infrastructure \
  -n floe \
  --wait --timeout 10m

# Deploy Dagster
echo "4. Deploying Dagster..."
helm install floe-dagster demo/platform-config/charts/floe-dagster \
  -f demo/platform-config/charts/floe-dagster/values-local.yaml \
  -n floe \
  --wait --timeout 10m

# Deploy Cube  
echo "5. Deploying Cube..."
helm install floe-cube demo/platform-config/charts/floe-cube \
  -f demo/platform-config/charts/floe-cube/values-local.yaml \
  -n floe \
  --wait --timeout 10m

echo "✅ Clean deployment complete!"
echo "Run ./scripts/validate-e2e.sh to validate"
