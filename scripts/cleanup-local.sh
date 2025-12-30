#!/bin/bash
# cleanup-local.sh - Complete cleanup of local Floe deployment
#
# This script performs a complete teardown of the local Kubernetes deployment:
# 0. Cleans service-level metadata (Polaris, Dagster, Marquez)
# 1. Cleans S3 buckets (removes orphaned data)
# 2. Uninstalls Helm releases
# 3. Deletes namespace (removes all K8s resources)
# 4. Recreates clean namespace
#
# Usage:
#   ./scripts/cleanup-local.sh

set -e

echo "🧹 Cleaning up local Floe deployment..."
echo ""

# Step 0: Clean service-level metadata BEFORE killing pods
echo "Step 0/5: Cleaning service metadata..."
echo "  Cleaning Polaris catalog..."
./scripts/cleanup-polaris.sh || echo "    ⚠️  Polaris cleanup skipped (not critical)"
echo "  Cleaning Dagster run history..."
./scripts/cleanup-dagster.sh || echo "    ⚠️  Dagster cleanup skipped (not critical)"
echo "  Cleaning Marquez lineage..."
./scripts/cleanup-marquez.sh || echo "    ⚠️  Marquez cleanup skipped (not critical)"

# Step 1: Clean S3 data
echo ""
echo "Step 1/5: Cleaning S3 buckets..."
./scripts/cleanup-s3.sh || echo "  ⚠️  S3 cleanup skipped (LocalStack not running)"

# Step 2: Delete Helm releases
echo ""
echo "Step 2/5: Uninstalling Helm releases..."
helm uninstall floe-dagster -n floe --wait 2>/dev/null && echo "  ✅ floe-dagster uninstalled" || echo "  ⏭️  floe-dagster not found"
helm uninstall floe-cube -n floe --wait 2>/dev/null && echo "  ✅ floe-cube uninstalled" || echo "  ⏭️  floe-cube not found"
helm uninstall floe-infra -n floe --wait 2>/dev/null && echo "  ✅ floe-infra uninstalled" || echo "  ⏭️  floe-infra not found"

# Step 3: Delete namespace (removes all resources)
echo ""
echo "Step 3/5: Deleting namespace..."
kubectl delete namespace floe --wait=true --timeout=60s 2>/dev/null && echo "  ✅ Namespace deleted" || echo "  ⏭️  Namespace not found"

# Step 4: Recreate clean namespace
echo ""
echo "Step 4/5: Creating fresh namespace..."
kubectl create namespace floe
echo "  ✅ Clean namespace created"

echo ""
echo "✅ Cleanup complete - ready for fresh deployment"
echo ""
echo "Cleaned:"
echo "  • Polaris catalog metadata (namespaces, tables, roles)"
echo "  • Dagster run history (runs, event logs, asset materializations)"
echo "  • Marquez lineage (datasets, jobs, lineage graphs)"
echo "  • S3 buckets (all Iceberg data files)"
echo "  • Helm releases (Dagster, Cube, Infrastructure)"
echo "  • Kubernetes namespace (all pods, services, configmaps)"
