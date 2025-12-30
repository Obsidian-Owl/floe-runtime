#!/bin/bash
# cleanup-marquez.sh - Clean Marquez lineage data from PostgreSQL
#
# This script truncates Marquez tables to remove lineage graphs and dataset metadata.

set -e

echo "🧹 Cleaning Marquez lineage data..."

# Get PostgreSQL pod
PG_POD=$(kubectl get pods -n floe -l app.kubernetes.io/name=postgresql -o name 2>/dev/null | head -1)

if [ -z "$PG_POD" ]; then
    echo "⚠️  PostgreSQL pod not found - skipping Marquez cleanup"
    exit 0
fi

# Check if marquez database exists
DB_EXISTS=$(kubectl exec -n floe "$PG_POD" -- bash -c 'PGPASSWORD=floe-postgres psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='\''marquez'\''"' 2>/dev/null || echo "0")

if [ "$DB_EXISTS" != "1" ]; then
    echo "  ⏭️  Marquez database doesn't exist yet - skipping"
    exit 0
fi

echo "  Truncating Marquez tables..."
kubectl exec -n floe "$PG_POD" -- bash -c 'PGPASSWORD=floe-postgres psql -U postgres -d marquez -c "
DO \$\$
DECLARE
    r RECORD;
BEGIN
    -- Disable foreign key checks
    SET session_replication_role = replica;

    -- Truncate all tables in public schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = '\''public'\'') LOOP
        EXECUTE '\''TRUNCATE TABLE '\'' || quote_ident(r.tablename) || '\'' CASCADE'\'';
        RAISE NOTICE '\''Truncated table: %'\'', r.tablename;
    END LOOP;

    -- Re-enable foreign key checks
    SET session_replication_role = DEFAULT;
END
\$\$;
"' 2>/dev/null || echo "⚠️  Marquez table truncation failed (continuing anyway)"

echo "✅ Marquez lineage data cleaned"
