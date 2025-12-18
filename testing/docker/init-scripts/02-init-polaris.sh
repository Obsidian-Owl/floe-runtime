#!/bin/sh
# Initialize Polaris catalog with warehouse and proper permissions
# This script is run by the polaris-init container after Polaris is healthy
#
# Creates:
# - warehouse catalog with LocalStack S3 storage
# - warehouse_admin principal role
# - warehouse_admin catalog role with CATALOG_MANAGE_CONTENT privilege
# - Assigns roles to root principal for full catalog access
#
# NOTE: This script dynamically extracts auto-generated credentials from Polaris logs.
#       Polaris auto-generates root credentials on startup - we read them from logs.
# See: https://docs.localstack.cloud/snowflake/features/polaris-catalog/

set -e

POLARIS_URI="${POLARIS_URI:-http://polaris:8181}"
# Realm is always 'POLARIS' - the default realm name in Apache Polaris
POLARIS_REALM="${POLARIS_REALM:-POLARIS}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
AWS_REGION="${AWS_REGION:-us-east-1}"
# Single S3 endpoint - LocalStack's Polaris handles path-style access internally
S3_ENDPOINT="${S3_ENDPOINT:-http://localstack:4566}"

echo "Waiting for Polaris to be ready..."
sleep 5

# ==============================================================================
# Extract auto-generated credentials from Polaris container logs
# ==============================================================================
echo "Extracting root credentials from Polaris logs..."

# Get credentials from Polaris container logs
# Format: "realm: POLARIS root principal credentials: CLIENT_ID:CLIENT_SECRET"
CREDS_LINE=$(docker logs floe-polaris 2>&1 | grep "root principal credentials:" | head -1)

if [ -z "${CREDS_LINE}" ]; then
  echo "ERROR: Could not find credentials in Polaris logs" >&2
  echo "Polaris logs:" >&2
  docker logs floe-polaris 2>&1 | head -30
  exit 1
fi

# Parse CLIENT_ID:CLIENT_SECRET from the line
CREDS=$(echo "${CREDS_LINE}" | sed 's/.*credentials: //')
POLARIS_CLIENT_ID=$(echo "${CREDS}" | cut -d: -f1)
POLARIS_CLIENT_SECRET=$(echo "${CREDS}" | cut -d: -f2)

if [ -z "${POLARIS_CLIENT_ID}" ] || [ -z "${POLARIS_CLIENT_SECRET}" ]; then
  echo "ERROR: Failed to parse credentials from line: ${CREDS_LINE}" >&2
  exit 1
fi

echo "Extracted credentials:"
echo "  Realm: ${POLARIS_REALM}"
echo "  Client ID: ${POLARIS_CLIENT_ID}"
echo "  Client Secret: ${POLARIS_CLIENT_SECRET:0:8}... (truncated)"

# ==============================================================================
# Get OAuth2 token
# ==============================================================================
echo "Getting OAuth2 token from realm '${POLARIS_REALM}'..."

# Install curl in docker:cli image
apk add --no-cache curl >/dev/null 2>&1 || true

TOKEN_RESPONSE=$(curl -s -X POST "${POLARIS_URI}/api/catalog/v1/oauth/tokens" \
  -d "grant_type=client_credentials" \
  -d "client_id=${POLARIS_CLIENT_ID}" \
  -d "client_secret=${POLARIS_CLIENT_SECRET}" \
  -d "scope=PRINCIPAL_ROLE:ALL")

TOKEN=$(echo "${TOKEN_RESPONSE}" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -z "${TOKEN}" ]; then
  echo "Failed to get token. Response: ${TOKEN_RESPONSE}"
  exit 1
fi
echo "Token acquired successfully"

# ==============================================================================
# Step 1: Create the warehouse catalog
# ==============================================================================
echo "Creating warehouse catalog with LocalStack S3 storage..."
# Configuration notes for LocalStack's Polaris (from LocalStack docs):
# - storageType: S3_COMPATIBLE (not just "S3")
# - s3.pathStyleAccess: true (CRITICAL for LocalStack - prevents virtual-hosted URLs)
# - s3.endpoint: internal Docker endpoint for Polaris server to use
# - roleArn: IAM role for credential vending
#
# The S3 endpoint in storageConfigInfo is used by Polaris SERVER for metadata writes.
# PyIceberg clients override this with localhost:4566 at connection time.
CATALOG_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${POLARIS_URI}/api/management/v1/catalogs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"catalog\": {
      \"name\": \"warehouse\",
      \"type\": \"INTERNAL\",
      \"properties\": {
        \"default-base-location\": \"s3://warehouse/\"
      },
      \"storageConfigInfo\": {
        \"storageType\": \"S3_COMPATIBLE\",
        \"allowedLocations\": [\"s3://warehouse/\", \"s3://iceberg/\"],
        \"s3.roleArn\": \"arn:aws:iam::000000000000:role/polaris-storage-role\",
        \"region\": \"${AWS_REGION}\",
        \"s3.pathStyleAccess\": true,
        \"s3.endpoint\": \"${S3_ENDPOINT}\"
      }
    }
  }")

HTTP_CODE=$(echo "${CATALOG_RESPONSE}" | tail -n1)
RESPONSE_BODY=$(echo "${CATALOG_RESPONSE}" | sed '$d')

if [ "${HTTP_CODE}" = "201" ]; then
  echo "Catalog 'warehouse' created successfully"
elif [ "${HTTP_CODE}" = "409" ]; then
  echo "Catalog 'warehouse' already exists"
else
  echo "Catalog creation response (HTTP ${HTTP_CODE}): ${RESPONSE_BODY}"
fi

# ==============================================================================
# Step 2: Create principal role (warehouse_admin)
# ==============================================================================
echo "Creating principal role 'warehouse_admin'..."
PR_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${POLARIS_URI}/api/management/v1/principal-roles" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"principalRole\": {\"name\": \"warehouse_admin\"}}")

HTTP_CODE=$(echo "${PR_RESPONSE}" | tail -n1)
if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "409" ]; then
  echo "Principal role 'warehouse_admin' ready"
else
  echo "Principal role creation response (HTTP ${HTTP_CODE})"
fi

# ==============================================================================
# Step 3: Create catalog role (warehouse_admin) on the warehouse catalog
# ==============================================================================
echo "Creating catalog role 'warehouse_admin' on catalog 'warehouse'..."
CR_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${POLARIS_URI}/api/management/v1/catalogs/warehouse/catalog-roles" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"catalogRole\": {\"name\": \"warehouse_admin\"}}")

HTTP_CODE=$(echo "${CR_RESPONSE}" | tail -n1)
if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "409" ]; then
  echo "Catalog role 'warehouse_admin' ready"
else
  echo "Catalog role creation response (HTTP ${HTTP_CODE})"
fi

# ==============================================================================
# Step 4: Grant CATALOG_MANAGE_CONTENT privilege to the catalog role
# This provides full create/list/read/write privileges on all entities
# ==============================================================================
echo "Granting CATALOG_MANAGE_CONTENT privilege to 'warehouse_admin'..."
GRANT_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${POLARIS_URI}/api/management/v1/catalogs/warehouse/catalog-roles/warehouse_admin/grants" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"grant\": {\"type\": \"catalog\", \"privilege\": \"CATALOG_MANAGE_CONTENT\"}}")

HTTP_CODE=$(echo "${GRANT_RESPONSE}" | tail -n1)
if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "409" ]; then
  echo "CATALOG_MANAGE_CONTENT privilege granted"
else
  echo "Grant privilege response (HTTP ${HTTP_CODE})"
fi

# ==============================================================================
# Step 5: Assign catalog role to principal role
# This connects the principal role to the catalog role
# ==============================================================================
echo "Assigning catalog role 'warehouse_admin' to principal role 'warehouse_admin'..."
ASSIGN_CR_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${POLARIS_URI}/api/management/v1/principal-roles/warehouse_admin/catalog-roles/warehouse" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"catalogRole\": {\"name\": \"warehouse_admin\"}}")

HTTP_CODE=$(echo "${ASSIGN_CR_RESPONSE}" | tail -n1)
if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "409" ]; then
  echo "Catalog role assigned to principal role"
else
  echo "Assign catalog role response (HTTP ${HTTP_CODE})"
fi

# ==============================================================================
# Step 6: Assign principal role to root principal
# This gives the root principal access via the warehouse_admin role chain
# ==============================================================================
echo "Assigning principal role 'warehouse_admin' to principal 'root'..."
ASSIGN_PR_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${POLARIS_URI}/api/management/v1/principals/root/principal-roles" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"principalRole\": {\"name\": \"warehouse_admin\"}}")

HTTP_CODE=$(echo "${ASSIGN_PR_RESPONSE}" | tail -n1)
if [ "${HTTP_CODE}" = "201" ] || [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "409" ]; then
  echo "Principal role assigned to root principal"
else
  echo "Assign principal role response (HTTP ${HTTP_CODE})"
fi

# ==============================================================================
# Write credentials to a file for test fixtures to read
# ==============================================================================
CREDS_FILE="/config/polaris-credentials.env"
echo "Writing credentials to ${CREDS_FILE}..."

cat > "${CREDS_FILE}" << EOF
# Polaris credentials - auto-generated by polaris-init container
# These credentials are extracted from Polaris logs on startup
# Source this file before running integration tests:
#   source testing/docker/config/polaris-credentials.env
#   pytest -m integration packages/floe-iceberg/tests/

POLARIS_CLIENT_ID=${POLARIS_CLIENT_ID}
POLARIS_CLIENT_SECRET=${POLARIS_CLIENT_SECRET}
POLARIS_URI=http://localhost:8181/api/catalog
POLARIS_WAREHOUSE=warehouse
POLARIS_REALM=${POLARIS_REALM}

# LocalStack S3 configuration (for PyIceberg FileIO)
LOCALSTACK_ENDPOINT=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=${AWS_REGION:-us-east-1}
EOF

echo "Credentials written to ${CREDS_FILE}"

echo ""
echo "========================================"
echo "Polaris catalog initialization complete!"
echo "========================================"
echo ""
echo "Catalog: warehouse"
echo "Realm: ${POLARIS_REALM}"
echo "Principal: root"
echo "Client ID: ${POLARIS_CLIENT_ID}"
echo "Client Secret: ${POLARIS_CLIENT_SECRET:0:8}..."
echo "Principal Role: warehouse_admin"
echo "Catalog Role: warehouse_admin"
echo "Privileges: CATALOG_MANAGE_CONTENT"
echo "Storage: LocalStack S3 (${S3_ENDPOINT})"
echo ""
echo "Credentials saved to: ${CREDS_FILE}"
echo "Run tests with:"
echo "  source testing/docker/config/polaris-credentials.env"
echo "  pytest -m integration packages/floe-iceberg/tests/"
