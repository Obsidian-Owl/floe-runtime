#!/bin/bash
# Initialize Cube test data in Iceberg via Trino
#
# This script creates the orders table and loads sample data for Cube integration tests.
# It runs after Trino is healthy and Polaris has initialized the warehouse.
#
# The script generates 15,000+ rows to support pagination tests (T038).
#
# Prerequisites:
# - Trino container healthy with Iceberg catalog configured
# - Polaris warehouse initialized (via polaris-init)
# - LocalStack S3 running for table storage

set -e

TRINO_HOST="${TRINO_HOST:-trino}"
TRINO_PORT="${TRINO_PORT:-8080}"

echo "==> Initializing Cube test data..."
echo "    Trino: ${TRINO_HOST}:${TRINO_PORT}"

# Wait for Trino to be ready
echo "==> Waiting for Trino to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "SELECT 1" >/dev/null 2>&1; then
        echo "    Trino is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "    Waiting for Trino... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 5
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "ERROR: Trino did not become ready in time"
    exit 1
fi

# Create namespace if not exists
echo "==> Creating iceberg.default namespace..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.default
" || echo "    Schema may already exist, continuing..."

# Check if table exists
TABLE_EXISTS=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SHOW TABLES FROM iceberg.default LIKE 'orders'
" 2>/dev/null | grep -c "orders" || echo "0")

if [ "$TABLE_EXISTS" != "0" ]; then
    echo "==> Orders table already exists, checking row count..."
    ROW_COUNT=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT COUNT(*) FROM iceberg.default.orders
" 2>/dev/null | tail -1 | tr -d ' "')
    echo "    Current row count: $ROW_COUNT"

    if [ "$ROW_COUNT" -ge 15000 ]; then
        echo "==> Sufficient test data exists, skipping data load"
        exit 0
    fi
    echo "==> Insufficient data, dropping and recreating table..."
    trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
DROP TABLE IF EXISTS iceberg.default.orders
" || true
fi

# Create the orders table
echo "==> Creating orders table..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
CREATE TABLE iceberg.default.orders (
    id BIGINT,
    customer_id BIGINT,
    status VARCHAR,
    region VARCHAR,
    amount DECIMAL(10, 2),
    created_at TIMESTAMP(6)
)
WITH (
    format = 'PARQUET',
    partitioning = ARRAY['status']
)
"

# Generate and insert test data
# We need 15,000+ rows for pagination tests
# Using sequence() to generate IDs and CROSS JOIN for combinations
echo "==> Generating 15,000+ test orders..."

# Insert data in batches to avoid memory issues
# Batch 1: 5000 rows
echo "    Inserting batch 1/3 (rows 1-5000)..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
INSERT INTO iceberg.default.orders (id, customer_id, status, region, amount, created_at)
SELECT
    ROW_NUMBER() OVER () as id,
    (ABS(RANDOM()) % 1000) + 1 as customer_id,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'processing'
        WHEN 2 THEN 'completed'
        ELSE 'cancelled'
    END as status,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END as region,
    CAST((ABS(RANDOM()) % 99000 + 1000) / 100.0 AS DECIMAL(10, 2)) as amount,
    TIMESTAMP '2024-01-01 00:00:00' + (ABS(RANDOM()) % 31536000) * INTERVAL '1' SECOND as created_at
FROM (SELECT 1) AS t
CROSS JOIN UNNEST(sequence(1, 5000)) AS s(n)
"

# Batch 2: 5000 rows
echo "    Inserting batch 2/3 (rows 5001-10000)..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
INSERT INTO iceberg.default.orders (id, customer_id, status, region, amount, created_at)
SELECT
    5000 + ROW_NUMBER() OVER () as id,
    (ABS(RANDOM()) % 1000) + 1 as customer_id,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'processing'
        WHEN 2 THEN 'completed'
        ELSE 'cancelled'
    END as status,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END as region,
    CAST((ABS(RANDOM()) % 99000 + 1000) / 100.0 AS DECIMAL(10, 2)) as amount,
    TIMESTAMP '2024-01-01 00:00:00' + (ABS(RANDOM()) % 31536000) * INTERVAL '1' SECOND as created_at
FROM (SELECT 1) AS t
CROSS JOIN UNNEST(sequence(1, 5000)) AS s(n)
"

# Batch 3: 5500 rows (to exceed 15000)
echo "    Inserting batch 3/3 (rows 10001-15500)..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
INSERT INTO iceberg.default.orders (id, customer_id, status, region, amount, created_at)
SELECT
    10000 + ROW_NUMBER() OVER () as id,
    (ABS(RANDOM()) % 1000) + 1 as customer_id,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'processing'
        WHEN 2 THEN 'completed'
        ELSE 'cancelled'
    END as status,
    CASE (ABS(RANDOM()) % 4)
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END as region,
    CAST((ABS(RANDOM()) % 99000 + 1000) / 100.0 AS DECIMAL(10, 2)) as amount,
    TIMESTAMP '2024-01-01 00:00:00' + (ABS(RANDOM()) % 31536000) * INTERVAL '1' SECOND as created_at
FROM (SELECT 1) AS t
CROSS JOIN UNNEST(sequence(1, 5500)) AS s(n)
"

# Verify data
echo "==> Verifying data..."
FINAL_COUNT=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT COUNT(*) FROM iceberg.default.orders
" | tail -1 | tr -d ' "')

echo "    Total rows: $FINAL_COUNT"

# Show sample of data
echo "==> Sample data:"
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT * FROM iceberg.default.orders LIMIT 5
"

# Show status distribution
echo "==> Status distribution:"
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT status, COUNT(*) as count
FROM iceberg.default.orders
GROUP BY status
ORDER BY status
"

echo "==> Cube test data initialization complete!"
echo "    Orders table: iceberg.default.orders"
echo "    Row count: $FINAL_COUNT"
