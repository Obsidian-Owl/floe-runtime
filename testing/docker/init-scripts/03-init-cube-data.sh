#!/bin/bash
# Initialize Cube test data in Iceberg via Python + Trino
#
# This script creates the orders table and loads sample data for Cube integration tests.
# It uses floe-synthetic for data generation (Python/Faker) to avoid Trino's RANDOM() bug
# which returns the same value for all rows in a query.
#
# The script generates 15,000+ rows to support pagination tests (T038).
#
# Prerequisites:
# - Trino container healthy with Iceberg catalog configured
# - Polaris warehouse initialized (via polaris-init)
# - LocalStack S3 running for table storage
# - Python 3.10+ with floe-synthetic installed

set -e

TRINO_HOST="${TRINO_HOST:-trino}"
TRINO_PORT="${TRINO_PORT:-8080}"
DATA_COUNT="${DATA_COUNT:-15500}"
PARQUET_FILE="/tmp/orders.parquet"

echo "==> Initializing Cube test data..."
echo "    Trino: ${TRINO_HOST}:${TRINO_PORT}"
echo "    Target count: ${DATA_COUNT}"

# Wait for Trino to be ready
echo "==> Waiting for Trino to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "SELECT 1" >/dev/null 2>&1; then
        echo "    Trino is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "    Waiting for Trino... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 5
done

if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "ERROR: Trino did not become ready in time" >&2
    exit 1
fi

# Create namespace if not exists
echo "==> Creating iceberg.default namespace..."
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
CREATE SCHEMA IF NOT EXISTS iceberg.default
" || echo "    Schema may already exist, continuing..."

# Check if table exists with sufficient data
TABLE_EXISTS=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SHOW TABLES FROM iceberg.default LIKE 'orders'
" 2>/dev/null | grep -c "orders" || echo "0")

if [[ "$TABLE_EXISTS" != "0" ]]; then
    echo "==> Orders table already exists, checking data quality..."

    # Check row count
    ROW_COUNT=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT COUNT(*) FROM iceberg.default.orders
" 2>/dev/null | tail -1 | tr -d ' "')
    echo "    Current row count: $ROW_COUNT"

    # Check region distribution (key issue was all rows in 'west')
    REGION_CHECK=$(trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT COUNT(DISTINCT region) FROM iceberg.default.orders
" 2>/dev/null | tail -1 | tr -d ' "')
    echo "    Distinct regions: $REGION_CHECK"

    if [[ "$ROW_COUNT" -ge 15000 ]] && [[ "$REGION_CHECK" -ge 4 ]]; then
        echo "==> Sufficient test data with proper distribution exists, skipping data load"
        exit 0
    fi

    echo "==> Data needs regeneration (count=$ROW_COUNT, regions=$REGION_CHECK), dropping table..."
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
    amount DOUBLE,
    created_at TIMESTAMP(6)
)
WITH (
    format = 'PARQUET',
    partitioning = ARRAY['status']
)
"

# Generate test data using floe-synthetic (Python/Faker)
# This avoids Trino's RANDOM() bug which returns same value for all rows
echo "==> Generating ${DATA_COUNT} test orders using floe-synthetic..."

# Check if floe-synthetic is available
if python3 -c "import floe_synthetic" 2>/dev/null; then
    echo "    Using installed floe-synthetic package"
    GENERATOR_SCRIPT="python3 -c \"
from datetime import datetime
from floe_synthetic.generators.ecommerce import EcommerceGenerator
import pyarrow.parquet as pq

generator = EcommerceGenerator(seed=42)
generator.generate_customers(1000, start_date=datetime(2022, 1, 1), end_date=datetime(2024, 1, 1))
orders = generator.generate_orders(${DATA_COUNT}, start_date=datetime(2024, 1, 1), end_date=datetime(2024, 12, 31))
pq.write_table(orders, '${PARQUET_FILE}')
print(f'Generated {len(orders)} orders')
\""
    eval "$GENERATOR_SCRIPT"
elif [[ -f "/app/testing/docker/init-scripts/generate_test_data.py" ]]; then
    echo "    Using generate_test_data.py script"
    python3 /app/testing/docker/init-scripts/generate_test_data.py \
        --output "${PARQUET_FILE}" \
        --count "${DATA_COUNT}" \
        --seed 42 \
        --verify
else
    # Fallback to SQL-based generation with xxhash64 (less optimal but works)
    echo "    WARNING: floe-synthetic not available, using SQL fallback with xxhash64"
    echo "    This may produce less realistic distributions"

    # Insert data using xxhash64 for pseudo-randomness
    # NOTE: xxhash64 returns VARBINARY, so we use from_big_endian_64() to convert to BIGINT
    #       and to_utf8() to convert input strings to VARBINARY
    for batch in 1 2 3; do
        case $batch in
            1) START=1; END=5000; OFFSET=0 ;;
            2) START=1; END=5000; OFFSET=5000 ;;
            3) START=1; END=5500; OFFSET=10000 ;;
        esac

        echo "    Inserting batch ${batch}/3 (rows $((OFFSET+1))-$((OFFSET+END)))..."
        trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
INSERT INTO iceberg.default.orders (id, customer_id, status, region, amount, created_at)
SELECT
    ${OFFSET} + n as id,
    (ABS(from_big_endian_64(xxhash64(to_utf8(CAST(${OFFSET} + n AS VARCHAR))))) % 1000) + 1 as customer_id,
    CASE ABS(from_big_endian_64(xxhash64(to_utf8(CAST((${OFFSET} + n) * 2 AS VARCHAR))))) % 4
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'processing'
        WHEN 2 THEN 'completed'
        ELSE 'cancelled'
    END as status,
    CASE ABS(from_big_endian_64(xxhash64(to_utf8(CAST((${OFFSET} + n) * 3 AS VARCHAR))))) % 4
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END as region,
    CAST((ABS(from_big_endian_64(xxhash64(to_utf8(CAST((${OFFSET} + n) * 5 AS VARCHAR))))) % 99000 + 1000) / 100.0 AS DOUBLE) as amount,
    TIMESTAMP '2024-01-01 00:00:00' + (ABS(from_big_endian_64(xxhash64(to_utf8(CAST((${OFFSET} + n) * 7 AS VARCHAR))))) % 31536000) * INTERVAL '1' SECOND as created_at
FROM UNNEST(sequence(${START}, ${END})) AS s(n)
"
    done

    # Skip Parquet loading since we used SQL
    PARQUET_FILE=""
fi

# Load generated Parquet file into Trino if it exists
if [[ -n "${PARQUET_FILE}" ]] && [[ -f "${PARQUET_FILE}" ]]; then
    echo "==> Loading Parquet data into Iceberg table..."

    # Create external table pointing to the Parquet file
    # Then INSERT SELECT into the target table
    trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
CREATE TABLE IF NOT EXISTS iceberg.default.orders_staging (
    id BIGINT,
    customer_id BIGINT,
    status VARCHAR,
    region VARCHAR,
    amount DOUBLE,
    created_at TIMESTAMP(6)
) WITH (
    external_location = 'file://${PARQUET_FILE}',
    format = 'PARQUET'
)
" 2>/dev/null || true

    # Copy data from staging to target
    trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
INSERT INTO iceberg.default.orders
SELECT id, customer_id, status, region, amount, created_at
FROM iceberg.default.orders_staging
" 2>/dev/null || {
        # If external table approach fails, use pyarrow to read and insert directly
        echo "    External table approach failed, using batch insert..."
        python3 -c "
import pyarrow.parquet as pq
import subprocess
import json

table = pq.read_table('${PARQUET_FILE}')
batch_size = 1000
total = len(table)

for i in range(0, total, batch_size):
    batch = table.slice(i, min(batch_size, total - i))
    values = []
    for row_idx in range(len(batch)):
        row = [
            str(batch.column('id')[row_idx].as_py()),
            str(batch.column('customer_id')[row_idx].as_py()),
            \"'\" + str(batch.column('status')[row_idx].as_py()) + \"'\",
            \"'\" + str(batch.column('region')[row_idx].as_py()) + \"'\",
            str(batch.column('amount')[row_idx].as_py()),
            \"TIMESTAMP '\" + batch.column('created_at')[row_idx].as_py().strftime('%Y-%m-%d %H:%M:%S') + \"'\"
        ]
        values.append('(' + ', '.join(values) + ')')

    if values:
        sql = 'INSERT INTO iceberg.default.orders VALUES ' + ', '.join(values)
        subprocess.run(['trino', '--server', 'http://${TRINO_HOST}:${TRINO_PORT}', '--execute', sql], check=True)

    print(f'  Loaded {min(i + batch_size, total)}/{total} rows...')
"
    }

    # Clean up staging table
    trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
DROP TABLE IF EXISTS iceberg.default.orders_staging
" 2>/dev/null || true

    rm -f "${PARQUET_FILE}"
fi

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
SELECT status, COUNT(*) as count, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
FROM iceberg.default.orders
GROUP BY status
ORDER BY status
"

# Show region distribution
echo "==> Region distribution:"
trino --server "http://${TRINO_HOST}:${TRINO_PORT}" --execute "
SELECT region, COUNT(*) as count, ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
FROM iceberg.default.orders
GROUP BY region
ORDER BY region
"

echo "==> Cube test data initialization complete!"
echo "    Orders table: iceberg.default.orders"
echo "    Row count: $FINAL_COUNT"
