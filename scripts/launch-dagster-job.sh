#!/bin/bash
set -e

# launch-dagster-job.sh - Launch Dagster jobs programmatically via GraphQL
#
# Usage:
#   ./scripts/launch-dagster-job.sh <job-name> [dagster-url]
#
# Examples:
#   ./scripts/launch-dagster-job.sh demo_bronze
#   ./scripts/launch-dagster-job.sh demo_silver http://localhost:30000/graphql
#
# Environment Variables:
#   DAGSTER_URL - Dagster GraphQL endpoint (default: http://localhost:30000/graphql)
#
# Outputs:
#   - Run ID (for use with monitor-dagster-run.sh)
#   - Dagster UI URL
#
# Exit Codes:
#   0 - Success (job launched)
#   1 - Error (workspace query failed, launch failed, or invalid arguments)

# Configuration
JOB_NAME="${1:?Error: Job name required. Usage: $0 <job-name> [dagster-url]}"
DAGSTER_URL="${2:-${DAGSTER_URL:-http://localhost:30000/graphql}}"

echo "Launching Dagster job: ${JOB_NAME}"
echo "Dagster URL: ${DAGSTER_URL}"
echo

# Step 1: Get workspace location
echo "Step 1: Querying workspace for location name..."
WORKSPACE_QUERY='{"query": "{ workspaceOrError { ... on Workspace { locationEntries { name } } } }"}'
WORKSPACE_JSON=$(curl -sf -X POST "$DAGSTER_URL" \
  -H "Content-Type: application/json" \
  -d "$WORKSPACE_QUERY")

if [ $? -ne 0 ]; then
  echo "❌ Failed to query Dagster workspace (is Dagster running at ${DAGSTER_URL}?)"
  exit 1
fi

LOCATION_NAME=$(echo "$WORKSPACE_JSON" | jq -r '.data.workspaceOrError.locationEntries[0].name')

if [ -z "$LOCATION_NAME" ] || [ "$LOCATION_NAME" = "null" ]; then
  echo "❌ No workspace location found in response:"
  echo "$WORKSPACE_JSON" | jq .
  exit 1
fi

echo "  ✓ Workspace location: $LOCATION_NAME"
echo

# Step 2: Launch job
echo "Step 2: Launching job '${JOB_NAME}'..."
LAUNCH_MUTATION=$(cat <<EOF
{
  "query": "mutation { launchPipelineExecution(executionParams: { mode: \\\"default\\\", executionMetadata: { tags: [{key: \\\"source\\\", value: \\\"cli\\\"}] }, selector: { repositoryLocationName: \\\"$LOCATION_NAME\\\", repositoryName: \\\"__repository__\\\", pipelineName: \\\"${JOB_NAME}\\\" } }) { ... on LaunchRunSuccess { run { runId status } } ... on PipelineNotFoundError { message } ... on InvalidSubsetError { message } } }"
}
EOF
)

LAUNCH_JSON=$(curl -sf -X POST "$DAGSTER_URL" \
  -H "Content-Type: application/json" \
  -d "$LAUNCH_MUTATION")

if [ $? -ne 0 ]; then
  echo "❌ Failed to launch job (GraphQL request failed)"
  exit 1
fi

RUN_ID=$(echo "$LAUNCH_JSON" | jq -r '.data.launchPipelineExecution.run.runId')

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
  ERROR=$(echo "$LAUNCH_JSON" | jq -r '.data.launchPipelineExecution.message')
  echo "❌ Job launch failed: $ERROR"
  echo "Full response:"
  echo "$LAUNCH_JSON" | jq .
  exit 1
fi

echo "  ✓ Job launched successfully"
echo

# Output results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Job '${JOB_NAME}' launched successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Run ID: $RUN_ID"
echo "View in UI: http://localhost:30000/runs/$RUN_ID"
echo
echo "Monitor with:"
echo "  ./scripts/monitor-dagster-run.sh $RUN_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
