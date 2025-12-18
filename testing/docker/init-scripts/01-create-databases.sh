#!/bin/bash
# Initialize multiple databases for floe-runtime test infrastructure
#
# This script runs automatically when PostgreSQL starts for the first time.
# It creates separate databases for each service that needs persistence.

set -e

echo "Creating floe-runtime databases..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Database for Apache Polaris (Iceberg catalog metadata)
    CREATE DATABASE polaris;
    COMMENT ON DATABASE polaris IS 'Apache Polaris - Iceberg REST catalog metadata';

    -- Database for Marquez (OpenLineage backend)
    CREATE DATABASE marquez;
    COMMENT ON DATABASE marquez IS 'Marquez - OpenLineage data lineage storage';

    -- Database for floe development/testing
    CREATE DATABASE floe_dev;
    COMMENT ON DATABASE floe_dev IS 'floe-runtime development and test data';

    -- Database for dbt compute target testing
    CREATE DATABASE floe_dbt;
    COMMENT ON DATABASE floe_dbt IS 'dbt PostgreSQL compute target for testing';
EOSQL

echo "Databases created successfully:"
echo "  - polaris   (Iceberg catalog)"
echo "  - marquez   (OpenLineage)"
echo "  - floe_dev  (Development)"
echo "  - floe_dbt  (dbt target)"
