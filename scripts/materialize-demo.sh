#!/bin/bash
# Materialize Demo Data - Automated Dagster Job Execution
#
# This script triggers Dagster jobs via GraphQL API (no UI interaction required).
# It materializes the full demo pipeline: Raw → Bronze → Silver → Gold
#
# Prerequisites:
#   - Dagster deployed and running (make deploy-local-dagster)
#   - jq installed for JSON parsing
#
# Usage: ./scripts/materialize-demo.sh [OPTIONS]
#
# Options:
#   --bronze    : Materialize bronze layer only (demo_bronze job)
#   --pipeline  : Run full pipeline (demo_pipeline job)
#   --all       : Run bronze first, then full pipeline (default)
#
# Exit codes:
#   0 - All jobs completed successfully
#   1 - Job launch or execution failed

set -e

DAGSTER_URL="http://localhost:30000/graphql"
FAILED_JOBS=0
DEBUG="${DEBUG:-0}"

echo "=============================================="
echo "🚀 Materialize Demo Data (Automated)"
echo "=============================================="
echo ""

# Check prerequisites
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Please install jq for JSON parsing."
    echo "   macOS: brew install jq"
    echo "   Linux: apt-get install jq"
    exit 1
fi

# Wait for Dagster webserver to be ready
wait_for_dagster() {
    echo "⏳ Waiting for Dagster webserver to be ready..."
    local HEALTH_URL="http://localhost:30000/server_info"
    for i in {1..60}; do
        # Use server_info endpoint (GET request, returns JSON with dagster version info)
        # GraphQL endpoint requires POST with valid query, returns 400 for GET
        if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
            echo "✅ Dagster webserver is ready"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    echo "❌ Dagster webserver not ready after 120 seconds"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check Dagster pods: kubectl get pods -n floe -l component=dagster-webserver"
    echo "  - Check Dagster logs: kubectl logs -n floe -l component=dagster-webserver"
    echo "  - Verify NodePort service: kubectl get svc -n floe | grep dagster"
    echo "  - Test health endpoint: curl http://localhost:30000/server_info"
    echo ""
    exit 1
}

# Discover repository location name from workspace
get_repo_location() {
    local query=$(cat <<EOF
query {
  workspaceOrError {
    ... on Workspace {
      locationEntries {
        name
      }
    }
  }
}
EOF
)

    local result=$(curl -s "$DAGSTER_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": $(echo "$query" | jq -Rs .)}")

    local repo_location=$(echo "$result" | jq -r '.data.workspaceOrError.locationEntries[0].name // "floe-demo"')

    if [ "$DEBUG" = "1" ]; then
        echo "  [DEBUG] Discovered repository location: $repo_location" >&2
    fi

    echo "$repo_location"
}

# Launch Dagster job via GraphQL mutation
launch_job() {
    local job_name=$1
    echo "" >&2
    echo "==============================================" >&2
    echo "🚀 Launching Job: $job_name" >&2
    echo "==============================================" >&2

    # Discover repository location dynamically
    local repo_location=$(get_repo_location)

    # GraphQL mutation to launch job
    local mutation=$(cat <<EOF
mutation {
  launchPipelineExecution(
    executionParams: {
      selector: {
        jobName: "$job_name"
        repositoryName: "__repository__"
        repositoryLocationName: "$repo_location"
      }
      mode: "default"
    }
  ) {
    __typename
    ... on LaunchRunSuccess {
      run {
        runId
        status
      }
    }
    ... on PythonError {
      message
      stack
    }
    ... on UnauthorizedError {
      message
    }
  }
}
EOF
)

    # Execute GraphQL mutation
    local result=$(curl -s "$DAGSTER_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": $(echo "$mutation" | jq -Rs .)}")

    # Debug: Save raw response for troubleshooting
    if [ "$DEBUG" = "1" ]; then
        echo "$result" | jq '.' > "/tmp/dagster-launch-$job_name.json"
        echo "  [DEBUG] Launch response saved to: /tmp/dagster-launch-$job_name.json" >&2
    fi

    # Extract run ID from response
    local run_id=$(echo "$result" | jq -r '.data.launchPipelineExecution.run.runId // empty')

    if [ -n "$run_id" ]; then
        echo "  ✅ Job launched successfully" >&2
        echo "  Run ID: $run_id" >&2
        echo "" >&2
        echo "$run_id"  # Output run_id for capture by caller
        return 0
    else
        echo "  ❌ Job launch failed" >&2
        echo "" >&2
        echo "Error details:" >&2
        echo "$result" | jq '.' >&2
        echo "" >&2
        ((FAILED_JOBS++))
        return 1
    fi
}

# Wait for Dagster run to complete
wait_for_run() {
    local run_id=$1
    local job_name=$2

    echo "⏳ Waiting for job to complete (timeout: 10 minutes)..."
    echo ""

    local start_time=$(date +%s)
    local timeout=600  # 10 minutes

    while true; do
        # Check elapsed time
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -gt $timeout ]; then
            echo "  ⚠️  Job timeout after 10 minutes"
            echo "  Run ID: $run_id"
            echo ""
            echo "Check status in Dagster UI:"
            echo "  http://localhost:30000/runs/$run_id"
            echo ""
            ((FAILED_JOBS++))
            return 1
        fi

        # Query run status via GraphQL
        local query=$(cat <<EOF
query {
  runOrError(runId: "$run_id") {
    ... on Run {
      status
      stats {
        ... on RunStatsSnapshot {
          stepsSucceeded
          stepsFailed
        }
      }
    }
    ... on RunNotFoundError {
      message
    }
  }
}
EOF
)

        local result=$(curl -s "$DAGSTER_URL" \
            -H "Content-Type: application/json" \
            -d "{\"query\": $(echo "$query" | jq -Rs .)}")

        # Debug: Save raw response for troubleshooting
        if [ "$DEBUG" = "1" ]; then
            echo "$result" | jq '.' > "/tmp/dagster-status-$run_id.json"
        fi

        local status=$(echo "$result" | jq -r '.data.runOrError.status // "UNKNOWN"')
        local steps_succeeded=$(echo "$result" | jq -r '.data.runOrError.stats.stepsSucceeded // 0')
        local steps_failed=$(echo "$result" | jq -r '.data.runOrError.stats.stepsFailed // 0')

        case "$status" in
            "SUCCESS")
                echo "  ✅ Job completed successfully"
                echo "  Steps succeeded: $steps_succeeded"
                echo "  Run ID: $run_id"
                echo ""
                echo "View in Dagster UI:"
                echo "  http://localhost:30000/runs/$run_id"
                echo ""
                return 0
                ;;
            "FAILURE")
                echo "  ❌ Job failed"
                echo "  Steps succeeded: $steps_succeeded"
                echo "  Steps failed: $steps_failed"
                echo "  Run ID: $run_id"
                echo ""
                echo "View failure details:"
                echo "  http://localhost:30000/runs/$run_id"
                echo ""
                ((FAILED_JOBS++))
                return 1
                ;;
            "CANCELED")
                echo "  ⚠️  Job was canceled"
                echo "  Run ID: $run_id"
                echo ""
                ((FAILED_JOBS++))
                return 1
                ;;
            "STARTED"|"STARTING"|"QUEUED")
                echo -n "  ⏳ Status: $status | Steps: $steps_succeeded succeeded"
                if [ "$steps_failed" != "0" ]; then
                    echo -n ", $steps_failed failed"
                fi
                echo " | Elapsed: ${elapsed}s"
                sleep 5
                ;;
            "UNKNOWN"|*)
                echo "  ⚠️  Unknown status: $status"
                if [ "$DEBUG" = "1" ]; then
                    echo "  [DEBUG] Full response saved to: /tmp/dagster-status-$run_id.json"
                    echo "  [DEBUG] Response preview:"
                    echo "$result" | jq '.' | head -20
                fi
                sleep 5
                ;;
        esac
    done
}

# Execute jobs based on options
execute_jobs() {
    local mode="${1:---all}"

    case "$mode" in
        --bronze)
            echo "Mode: Bronze layer only"
            echo ""
            local run_id=$(launch_job "demo_bronze")
            if [ -n "$run_id" ]; then
                wait_for_run "$run_id" "demo_bronze"
            fi
            ;;
        --pipeline)
            echo "Mode: Full pipeline (bronze → silver → gold)"
            echo ""
            local run_id=$(launch_job "demo_pipeline")
            if [ -n "$run_id" ]; then
                wait_for_run "$run_id" "demo_pipeline"
            fi
            ;;
        --all)
            echo "Mode: Bronze first, then full pipeline"
            echo ""

            # Step 1: Bronze layer
            echo "Step 1/2: Bronze Layer"
            local bronze_run_id=$(launch_job "demo_bronze")
            if [ -n "$bronze_run_id" ]; then
                if wait_for_run "$bronze_run_id" "demo_bronze"; then
                    echo "✅ Bronze layer materialized"
                else
                    echo "❌ Bronze layer failed - aborting"
                    return 1
                fi
            else
                echo "❌ Failed to launch bronze job - aborting"
                return 1
            fi

            # Brief pause between jobs
            echo "⏳ Waiting 5 seconds before next job..."
            sleep 5
            echo ""

            # Step 2: Full pipeline
            echo "Step 2/2: Full Pipeline (Bronze → Silver → Gold)"
            local pipeline_run_id=$(launch_job "demo_pipeline")
            if [ -n "$pipeline_run_id" ]; then
                wait_for_run "$pipeline_run_id" "demo_pipeline"
            else
                echo "❌ Failed to launch pipeline job"
                return 1
            fi
            ;;
        *)
            echo "❌ Invalid option: $mode"
            echo ""
            echo "Usage: $0 [--bronze|--pipeline|--all]"
            echo ""
            echo "Options:"
            echo "  --bronze    : Materialize bronze layer only"
            echo "  --pipeline  : Run full pipeline (bronze → silver → gold)"
            echo "  --all       : Run bronze first, then full pipeline (default)"
            exit 1
            ;;
    esac
}

# Main execution
wait_for_dagster
execute_jobs "${1:---all}"

# Summary
echo "=============================================="
if [ $FAILED_JOBS -eq 0 ]; then
    echo "✅ All Jobs Completed Successfully!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Validate data: ./scripts/validate-e2e.sh"
    echo "  2. View lineage: http://localhost:30301"
    echo "  3. View traces: http://localhost:30686"
    echo "  4. Query data: curl 'http://localhost:30400/cubejs-api/v1/meta'"
    echo ""
    exit 0
else
    echo "❌ $FAILED_JOBS Job(s) Failed"
    echo "=============================================="
    echo ""
    echo "Troubleshooting:"
    echo "  - Check Dagster UI: http://localhost:30000"
    echo "  - View logs: kubectl logs -n floe -l deployment=floe-demo"
    echo "  - Check resources: kubectl get pods -n floe"
    echo ""
    exit 1
fi
