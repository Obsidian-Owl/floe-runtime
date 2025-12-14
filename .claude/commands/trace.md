---
description: Show execution trace and observability data for pipeline runs
allowed-tools: Bash(python:*), Bash(dagster:*), Read, Grep, Glob
argument-hint: [run_id or asset_name]
model: sonnet
---

# Show Execution Trace and Observability

Display execution traces, OpenTelemetry spans, and observability data for Dagster pipeline runs.

## Arguments

- `$ARGUMENTS`: Optional run ID or asset name to filter traces

## Pre-requisites

1. **Check Dagster availability**:
   - Verify Dagster installed: `python -c "import dagster; print(dagster.__version__)"`
   - Check if Dagster is running: `curl -s http://localhost:3000/graphql || echo "Dagster not running"`

2. **Check observability configuration**:
   - Search for OpenTelemetry config: `rg "OpenTelemetry|OTEL" --type py --type yaml`
   - Search for trace instrumentation: `rg "trace|span|tracer" --type py`

## Trace Display Options

### Option 1: Dagster UI (if running locally)

If Dagster dev server is running (`http://localhost:3000`):

1. **List recent runs**:
   ```bash
   dagster run list --limit 10
   ```

2. **Show run details** (if run_id in $ARGUMENTS):
   ```bash
   dagster run show $ARGUMENTS
   ```

3. **Direct user to Dagster UI**:
   - URL: `http://localhost:3000/runs/<run_id>`
   - Show how to navigate: Runs → Select run → View timeline

### Option 2: OpenTelemetry Traces (if configured)

If OpenTelemetry endpoint is configured in CompiledArtifacts:

1. **Read CompiledArtifacts** to find OTEL endpoint:
   ```bash
   cat target/compiled_artifacts.json | grep -A5 "observability"
   ```

2. **Check for trace files** (if file-based):
   ```bash
   find . -name "*trace*.json" -o -name "spans.json"
   ```

3. **Display trace information**:
   - Trace ID
   - Span hierarchy (parent → child spans)
   - Duration for each span
   - Status (success/error)
   - Attributes (asset_key, run_id, etc.)

### Option 3: Dagster Event Logs

Read Dagster event logs from storage:

1. **Find event log storage**:
   - Check `$DAGSTER_HOME` for SQLite database or event log files
   - Default: `$DAGSTER_HOME/history/runs.db`

2. **Query event logs** (if SQLite):
   ```bash
   sqlite3 $DAGSTER_HOME/history/runs.db "
   SELECT
     run_id,
     event_type,
     timestamp,
     message
   FROM event_logs
   WHERE run_id = '<run_id>'
   ORDER BY timestamp;
   "
   ```

3. **Display events in timeline format**:
   ```
   Run ID: abc123
   ==================
   [12:00:00] RUN_START
   [12:00:01] ASSET_MATERIALIZATION_PLANNED: customers
   [12:00:05] ASSET_MATERIALIZATION: customers (4.2s)
   [12:00:06] ASSET_MATERIALIZATION_PLANNED: orders
   [12:00:12] ASSET_MATERIALIZATION: orders (6.1s)
   [12:00:12] RUN_SUCCESS (12.5s total)
   ```

## Asset-Level Traces

If `$ARGUMENTS` is an asset name (not a run_id):

1. **Find runs that materialized the asset**:
   - Query Dagster for asset materializations
   - Show last 5 runs

2. **Display asset materialization history**:
   ```
   Asset: customers
   ==================
   Last Materialized: 2025-12-12 12:00:12
   Run ID: abc123
   Duration: 4.2s
   Status: SUCCESS

   Recent Materializations:
   - 2025-12-12 12:00:12 | abc123 | SUCCESS (4.2s)
   - 2025-12-11 12:00:05 | def456 | SUCCESS (4.1s)
   - 2025-12-10 12:00:09 | ghi789 | FAILED (2.3s)
   ```

## Span Visualization

If OpenTelemetry traces are available, visualize span hierarchy:

```
Trace: floe-pipeline-run-abc123
Duration: 12.5s
==================

├─ pipeline-execution (12.5s)
│  ├─ dbt-run (10.2s)
│  │  ├─ model-customers (4.2s)
│  │  └─ model-orders (6.0s)
│  ├─ iceberg-write (2.1s)
│  └─ metadata-update (0.2s)
```

## Error Traces

If run failed, show error details:

1. **Extract error information**:
   - Error message
   - Stack trace
   - Failed asset/op
   - Timestamp

2. **Display formatted error**:
   ```
   ❌ Run Failed: abc123
   ==================
   Asset: orders
   Error: ValidationError in column 'amount'

   Stack Trace:
   <formatted stack trace>

   Debug:
   - Check data source for invalid values
   - Review dbt test results
   - Check logs: dagster run show abc123
   ```

## Output Format

Provide clear, formatted output:

```
🔍 Execution Trace
==================
Run ID:     abc123
Status:     SUCCESS
Started:    2025-12-12 12:00:00
Duration:   12.5s
Assets:     3 materialized

Timeline:
[12:00:00] 🚀 Run started
[12:00:01] 📊 customers (4.2s) ✅
[12:00:06] 📊 orders (6.0s) ✅
[12:00:12] 📊 analytics_summary (2.1s) ✅
[12:00:12] ✅ Run completed

View in Dagster UI: http://localhost:3000/runs/abc123
```

## Fallback

If no trace data available:
- Inform user observability not yet configured
- Suggest enabling OpenTelemetry in CompiledArtifacts
- Provide documentation on setting up tracing
