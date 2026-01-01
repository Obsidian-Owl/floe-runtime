#!/bin/bash
# cleanup-s3.sh - Clean S3 buckets in LocalStack before fresh deployment
#
# This script removes all objects from Iceberg buckets to prevent
# orphaned data from previous runs interfering with testing.

set -e

echo "🧹 Cleaning S3 buckets in LocalStack..."

# Get LocalStack pod
LOCALSTACK_POD=$(kubectl get pods -n floe -l app=floe-infra-localstack -o name 2>/dev/null | head -1)

if [ -z "$LOCALSTACK_POD" ]; then
    echo "⚠️  LocalStack pod not found - skipping S3 cleanup"
    exit 0
fi

# Delete all objects in Iceberg buckets
for bucket in iceberg-bronze iceberg-silver iceberg-gold; do
    echo "  Cleaning s3://$bucket..."
    kubectl exec -n floe "$LOCALSTACK_POD" -- \
        aws s3 rm "s3://$bucket" --recursive --endpoint-url http://localhost:4566 2>/dev/null || true
done

echo "✅ S3 buckets cleaned"
