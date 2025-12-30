#!/bin/bash
# cleanup-dagster.sh - Clean Dagster run history from PostgreSQL
#
# This script truncates Dagster tables to remove run history, logs, and asset metadata.

set -e

echo "🧹 Cleaning Dagster run history..."

# Get PostgreSQL pod
PG_POD=$(kubectl get pods -n floe -l app.kubernetes.io/name=postgresql -o name 2>/dev/null | head -1)

if [ -z "$PG_POD" ]; then
    echo "⚠️  PostgreSQL pod not found - skipping Dagster cleanup"
    exit 0
fi

echo "  Truncating Dagster tables..."
kubectl exec -n floe "$PG_POD" -- bash -c 'PGPASSWORD=floe-postgres psql -U postgres -d dagster -c "
DO \$\$
DECLARE
    r RECORD;
BEGIN
    -- Disable foreign key checks
    SET session_replication_role = replica;

    -- Truncate all tables in public schema (Dagster uses public)
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = '\''public'\'') LOOP
        EXECUTE '\''TRUNCATE TABLE '\'' || quote_ident(r.tablename) || '\'' CASCADE'\'';
        RAISE NOTICE '\''Truncated table: %'\'', r.tablename;
    END LOOP;

    -- Re-enable foreign key checks
    SET session_replication_role = DEFAULT;
END
\$\$;
"' 2>/dev/null || echo "⚠️  Dagster table truncation failed (continuing anyway)"

echo "✅ Dagster run history cleaned"
