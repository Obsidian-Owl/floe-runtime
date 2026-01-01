#!/bin/bash
set -e

# monitor-dagster-run.sh - Monitor Dagster run status with timeout
#
# Usage:
#   ./scripts/monitor-dagster-run.sh <run-id> [timeout-seconds] [dagster-url]
#
# Examples:
#   ./scripts/monitor-dagster-run.sh 09d24d92-dd29-4ab5-8a1b-90c84df120bc
#   ./scripts/monitor-dagster-run.sh 09d24d92-dd29-4ab5-8a1b-90c84df120bc 300
#   ./scripts/monitor-dagster-run.sh <run-id> 120 http://localhost:30000/graphql
#
# Environment Variables:
#   DAGSTER_URL - Dagster GraphQL endpoint (default: http://localhost:30000/graphql)
#
# Exit Codes:
#   0 - Success (run completed successfully)
#   1 - Failure (run failed, canceled, or timeout reached)

# Configuration
RUN_ID="${1:?Error: Run ID required. Usage: $0 <run-id> [timeout-seconds] [dagster-url]}"
TIMEOUT="${2:-120}"  # Default: 2 minutes
DAGSTER_URL="${3:-${DAGSTER_URL:-http://localhost:30000/graphql}}"
POLL_INTERVAL=3  # Poll every 3 seconds

echo "Monitoring Dagster run: ${RUN_ID}"
echo "Timeout: ${TIMEOUT}s | Poll interval: ${POLL_INTERVAL}s"
echo "Dagster URL: ${DAGSTER_URL}"
echo

START_TIME=$(date +%s)
ITERATION=0

while true; do
  ELAPSED=$(($(date +%s) - START_TIME))
  ITERATION=$((ITERATION + 1))

  # Check timeout
  if [ $ELAPSED -gt $TIMEOUT ]; then
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏱️ Timeout after ${TIMEOUT}s"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Last status: $STATUS"
    echo "View in UI: http://localhost:30000/runs/$RUN_ID"
    exit 1
  fi

  # Query run status
  QUERY="{\"query\": \"{ runOrError(runId: \\\"$RUN_ID\\\") { ... on Run { status } } }\"}"
  RESULT=$(curl -sf -X POST "$DAGSTER_URL" \
    -H "Content-Type: application/json" \
    -d "$QUERY")

  if [ $? -ne 0 ]; then
    echo "❌ Failed to query run status (GraphQL request failed)"
    exit 1
  fi

  STATUS=$(echo "$RESULT" | jq -r '.data.runOrError.status')

  # Display progress
  printf "[%3d] Elapsed: %3ds | Status: %-12s\r" "$ITERATION" "$ELAPSED" "$STATUS"

  # Check terminal states
  case "$STATUS" in
    SUCCESS)
      echo
      echo
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "✅ Run completed successfully!"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "Run ID: $RUN_ID"
      echo "Duration: ${ELAPSED}s"
      echo "View in UI: http://localhost:30000/runs/$RUN_ID"
      exit 0
      ;;
    FAILURE)
      echo
      echo
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "❌ Run failed!"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "Run ID: $RUN_ID"
      echo "Duration: ${ELAPSED}s"
      echo "View logs: http://localhost:30000/runs/$RUN_ID"
      exit 1
      ;;
    CANCELED|CANCELING)
      echo
      echo
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "⚠️  Run was canceled"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "Run ID: $RUN_ID"
      echo "View in UI: http://localhost:30000/runs/$RUN_ID"
      exit 1
      ;;
    STARTED|STARTING|QUEUED)
      # Continue polling
      sleep $POLL_INTERVAL
      ;;
    *)
      echo
      echo "⚠️  Unknown status: $STATUS"
      echo "Continuing to poll..."
      sleep $POLL_INTERVAL
      ;;
  esac
done
