#!/bin/bash
set -e

echo "=== Floe Demo Container Entrypoint ==="

# Wait for Python module to be importable (sanity check)
python -c "import data_engineering.orchestration.definitions" 2>&1 || {
    echo "WARNING: Failed to import data_engineering.orchestration.definitions (non-fatal)"
    echo "This may indicate missing platform.yaml or configuration issues"
    # Continue anyway to let Dagster gRPC server provide better diagnostics
}

# Initialize DuckDB Iceberg catalog (ATTACH statement)
# This creates a persistent secret and attaches the Polaris catalog
# so dbt models can reference tables via: polaris_catalog.namespace.table
echo "Initializing DuckDB Iceberg catalog connection..."
CATALOG_INIT_SQL="/tmp/init_catalog.sql"

cat > "$CATALOG_INIT_SQL" <<EOF
-- Load extensions
INSTALL iceberg;
INSTALL httpfs;
LOAD iceberg;
LOAD httpfs;

-- Create secret for Polaris OAuth2 authentication
CREATE SECRET IF NOT EXISTS polaris_secret (
    TYPE iceberg,
    CLIENT_ID '${POLARIS_CLIENT_ID}',
    CLIENT_SECRET '${POLARIS_CLIENT_SECRET}'
);

-- Attach Polaris catalog for read operations
-- dbt-duckdb ATTACH configuration will handle this at session startup
-- This script is here for debugging and manual testing
-- SELECT * FROM polaris_catalog.demo.bronze_customers LIMIT 5;
EOF

echo "✓ Catalog initialization SQL prepared at $CATALOG_INIT_SQL"

# Generate dbt profiles.yml from platform.yaml (Two-Tier Architecture)
PROFILES_PATH="/app/demo/data_engineering/dbt/profiles.yml"
PROJECT_DIR="/app/demo/data_engineering/dbt"
FLOE_YAML_PATH="/app/demo/data_engineering/floe.yaml"

echo "Generating dbt profiles.yml from platform.yaml..."
python3 << EOF
from pathlib import Path
from floe_core.compiler.dbt_profiles_generator import DbtProfilesGenerator

try:
    DbtProfilesGenerator.generate_from_env(
        floe_path=Path("$FLOE_YAML_PATH"),
        output_path=Path("$PROFILES_PATH"),
        platform_file_env="FLOE_PLATFORM_FILE",
        profile_name="default",
    )
    print("✓ profiles.yml generated successfully")
except Exception as e:
    print(f"ERROR: Failed to generate profiles.yml: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "FATAL: profiles.yml generation failed"
    exit 1
fi

# Run dbt compile to update manifest.json with runtime platform config
# Note: manifest.json already exists from build time (dbt parse), this updates it
echo "Running dbt compile to update manifest with platform config..."
if (cd "$PROJECT_DIR" && dbt compile --profiles-dir "$(dirname $PROFILES_PATH)" --target dev 2>&1); then
    echo "✓ manifest.json updated successfully"
else
    echo "WARNING: dbt compile failed, using build-time manifest"
    echo "  This is non-fatal - dbt assets will use build-time schema"
fi

# Copy instance.yaml from ConfigMap mount to writable DAGSTER_HOME
# ConfigMap is mounted at /opt/dagster/instance/dagster.yaml (read-only)
# DAGSTER_HOME is /tmp/dagster_home (writable emptyDir)
mkdir -p "$DAGSTER_HOME"
if [ -f "/opt/dagster/instance/dagster.yaml" ]; then
  cp /opt/dagster/instance/dagster.yaml "$DAGSTER_HOME/dagster.yaml"
  echo "✓ Copied instance.yaml from ConfigMap to $DAGSTER_HOME/dagster.yaml"
else
  echo "WARNING: No instance.yaml found at /opt/dagster/instance/dagster.yaml"
fi

# Ensure we're in the correct working directory for Dagster
cd /app/demo

# Start Dagster gRPC code server
echo "Starting Dagster gRPC code server..."
exec "$@"
