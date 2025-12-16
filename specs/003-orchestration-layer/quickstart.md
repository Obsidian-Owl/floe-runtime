# Quickstart: Orchestration Layer

**Time to complete**: 5 minutes
**Prerequisites**: Python 3.10+, existing dbt project with `manifest.json`

---

## Overview

The orchestration layer connects your dbt transformations to Dagster orchestration with:

- **floe-dbt**: Generates dbt `profiles.yml` from your `floe.yaml` configuration
- **floe-dagster**: Creates Dagster Software-Defined Assets from dbt models with OpenLineage lineage and OpenTelemetry tracing

---

## Step 1: Install Packages

```bash
# Install orchestration layer packages
pip install floe-cli floe-core floe-dbt floe-dagster

# Or with uv
uv pip install floe-cli floe-core floe-dbt floe-dagster
```

---

## Step 2: Configure floe.yaml

Create a `floe.yaml` in your project root:

```yaml
# floe.yaml
name: my-pipeline
version: "1.0.0"

compute:
  target: duckdb  # or snowflake, bigquery, redshift, databricks, postgres, spark
  properties:
    threads: 4

transforms:
  - type: dbt
    path: ./dbt_project

# Optional: Enable observability
observability:
  traces: true
  lineage: true
  # otlp_endpoint: http://localhost:4317  # Uncomment for tracing
  # lineage_endpoint: http://localhost:5000  # Uncomment for lineage
```

---

## Step 3: Compile and Generate Profiles

```bash
# Validate your configuration
floe validate

# Compile to generate artifacts
floe compile

# This creates:
# - .floe/compiled_artifacts.json
# - .floe/profiles/profiles.yml (dbt profiles)
```

---

## Step 4: Verify dbt Configuration

```bash
# Test dbt connection using generated profiles
cd dbt_project
dbt debug --profiles-dir ../.floe/profiles

# Expected output:
# Connection test: OK
# All checks passed!
```

---

## Step 5: Start Dagster Development Server

```bash
# Start Dagster with your dbt assets
floe dev

# Or directly with dagster
dagster dev -f definitions.py
```

Open http://localhost:3000 in your browser.

---

## Step 6: Materialize Assets

In the Dagster UI:

1. Navigate to **Assets** tab
2. Select your dbt models
3. Click **Materialize selected**
4. Watch the execution in **Runs**

---

## Example: definitions.py

If you need a custom Dagster definitions file:

```python
"""Dagster definitions for floe orchestration."""

from __future__ import annotations

from pathlib import Path

from dagster import Definitions
from floe_core import CompiledArtifacts
from floe_dagster import create_dbt_definitions

# Load compiled artifacts
artifacts = CompiledArtifacts.from_json_file(
    Path(".floe/compiled_artifacts.json")
)

# Create Dagster definitions from artifacts
defs = create_dbt_definitions(artifacts)
```

---

## Compute Target Examples

### DuckDB (Local Development)

```yaml
compute:
  target: duckdb
  properties:
    path: data/warehouse.duckdb
    threads: 4
```

No environment variables needed - perfect for local development.

### Snowflake

```yaml
compute:
  target: snowflake
  connection_secret_ref: env:SNOWFLAKE_PASSWORD
  properties:
    threads: 8
```

Set environment variables:

```bash
export SNOWFLAKE_ACCOUNT=abc12345.us-east-1
export SNOWFLAKE_USER=transformer
export SNOWFLAKE_PASSWORD=your-password
export SNOWFLAKE_DATABASE=analytics
export SNOWFLAKE_WAREHOUSE=transforming
export SNOWFLAKE_SCHEMA=public
export SNOWFLAKE_ROLE=TRANSFORMER
```

### BigQuery

```yaml
compute:
  target: bigquery
  properties:
    method: service-account
    location: US
```

Set environment variables:

```bash
export GCP_PROJECT=my-project-id
export BQ_DATASET=analytics
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

---

## Observability Configuration

### Enable OpenTelemetry Tracing

```yaml
observability:
  traces: true
  otlp_endpoint: http://localhost:4317
  attributes:
    environment: development
    team: data-platform
```

### Enable OpenLineage Lineage

```yaml
observability:
  lineage: true
  lineage_endpoint: http://localhost:5000
```

### Standalone Mode (No External Dependencies)

```yaml
observability:
  traces: false
  lineage: false
  # No endpoints configured = graceful degradation
```

---

## Column Classifications

Add governance metadata in your dbt models:

```yaml
# dbt_project/models/schema.yml
models:
  - name: customers
    columns:
      - name: email
        meta:
          floe:
            classification: pii
            pii_type: email
            sensitivity: high
      - name: customer_id
        meta:
          floe:
            classification: internal
```

Classifications appear in:
- OpenLineage dataset facets
- Dagster asset metadata

---

## Troubleshooting

### "manifest.json not found"

Run `dbt compile` first:

```bash
cd dbt_project
dbt compile --profiles-dir ../.floe/profiles
```

### "Connection failed"

Check environment variables:

```bash
# Verify env vars are set
env | grep SNOWFLAKE  # For Snowflake
env | grep GCP        # For BigQuery
```

### "OpenLineage/OTLP endpoint unreachable"

Observability is non-blocking. Pipeline continues with warning:

```
WARN: OpenLineage endpoint unreachable, lineage disabled
```

---

## Next Steps

- [spec.md](spec.md) - Full feature specification
- [data-model.md](data-model.md) - Pydantic models reference
- [research.md](research.md) - Technology research and patterns
- [Dagster dbt Integration](https://docs.dagster.io/integrations/libraries/dbt) - Official docs
