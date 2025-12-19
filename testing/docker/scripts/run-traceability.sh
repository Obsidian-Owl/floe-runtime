#!/bin/bash
# Run traceability report generation
#
# This script generates traceability reports that map functional requirements
# (FR-XXX) from spec files to their covering integration tests.
#
# Usage:
#   ./run-traceability.sh                          # Generate report for feature 006
#   ./run-traceability.sh --format json            # Output as JSON
#   ./run-traceability.sh --threshold 80           # Fail if coverage < 80%
#   ./run-traceability.sh --feature-id 004         # Report for different feature
#
# Prerequisites:
#   - Python 3.10+ with uv installed
#   - testing.traceability module available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$DOCKER_DIR")")"

cd "$PROJECT_ROOT"

# Default values
FEATURE_ID="${FEATURE_ID:-006}"
FEATURE_NAME="${FEATURE_NAME:-Integration Testing}"
FORMAT="${FORMAT:-console}"
THRESHOLD="${THRESHOLD:-}"

# Parse arguments
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --feature-id)
            FEATURE_ID="$2"
            shift 2
            ;;
        --feature-name)
            FEATURE_NAME="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

# Find spec files for the feature
SPEC_FILES=""
SPEC_DIR=$(ls -d specs/"${FEATURE_ID}"-* 2>/dev/null | head -1)
if [[ -n "$SPEC_DIR" && -f "${SPEC_DIR}/spec.md" ]]; then
    SPEC_FILES="${SPEC_DIR}/spec.md"
fi

# Find test directories with requirement markers
TEST_DIRS=""
for pkg_dir in packages/*/tests/integration packages/*/tests/e2e; do
    if [[ -d "$pkg_dir" ]]; then
        if [[ -n "$TEST_DIRS" ]]; then
            TEST_DIRS="$TEST_DIRS,$pkg_dir"
        else
            TEST_DIRS="$pkg_dir"
        fi
    fi
done

echo "==> Generating traceability report for feature $FEATURE_ID..."
echo "    Spec files: ${SPEC_FILES:-none}"
echo "    Test dirs: ${TEST_DIRS:-none}"
echo "    Format: $FORMAT"
if [[ -n "$THRESHOLD" ]]; then
    echo "    Threshold: ${THRESHOLD}%"
fi

# Build command
CMD="uv run python -m testing.traceability"
CMD="$CMD --feature-id \"$FEATURE_ID\""
CMD="$CMD --feature-name \"$FEATURE_NAME\""

if [[ -n "$SPEC_FILES" ]]; then
    CMD="$CMD --spec-files \"$SPEC_FILES\""
fi

if [[ -n "$TEST_DIRS" ]]; then
    CMD="$CMD --test-dirs \"$TEST_DIRS\""
fi

CMD="$CMD --format $FORMAT"

if [[ -n "$THRESHOLD" ]]; then
    CMD="$CMD --threshold $THRESHOLD"
fi

# Run the traceability report
echo ""
eval "$CMD"
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "==> Traceability report completed successfully"
else
    echo ""
    echo "==> Traceability report failed (exit code: $EXIT_CODE)" >&2
fi

exit $EXIT_CODE
