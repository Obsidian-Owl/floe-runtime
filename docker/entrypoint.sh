#!/bin/bash
set -e

echo "=== Floe Demo Container Entrypoint ==="

# Wait for Python module to be importable (sanity check)
python -c "import data_engineering.orchestration.definitions" 2>&1 || {
    echo "WARNING: Failed to import data_engineering.orchestration.definitions (non-fatal)"
    echo "This may indicate missing platform.yaml or configuration issues"
    # Continue anyway to let Dagster gRPC server provide better diagnostics
}

# Pre-install DuckDB extensions
# Extensions must be installed before dbt runs to avoid timing issues
# INSTALL persists across sessions for file databases
echo "Pre-installing DuckDB extensions..."

python3 << 'PYTHON_EOF'
import duckdb
import os

try:
    db_path = '/tmp/floe.duckdb'
    conn = duckdb.connect(db_path)

    conn.execute("INSTALL iceberg")
    conn.execute("INSTALL httpfs")

    print(f"✓ Installed DuckDB extensions (iceberg, httpfs)")
    print(f"  Database: {db_path}")
    print(f"  Extensions will be available for dbt execution")

    conn.close()

except Exception as e:
    print(f"WARNING: Failed to pre-install DuckDB extensions: {e}")
    import traceback
    traceback.print_exc()
    print("  Continuing anyway - dbt will attempt to install extensions")

PYTHON_EOF

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

# SKIP dbt compile - it triggers secret manager errors during DuckDB connection init
# The build-time manifest.json from 'dbt parse' is sufficient for Dagster asset discovery
# The actual dbt run will use the runtime profiles.yml with proper ATTACH configuration
echo "Skipping dbt compile - using build-time manifest.json"
echo "  Runtime profiles.yml will be used during actual dbt execution"

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
