#!/bin/bash
# detect-already-implemented.sh
# Detects if a task's implementation might already exist based on patterns

set -euo pipefail

TASK_DESCRIPTION="$1"
TASK_ID="$2"
FEATURE_DIR="$3"

# Extract key patterns from task description
detect_patterns() {
    local desc="$1"

    # Check for common test task patterns
    if echo "$desc" | grep -qi "Write test.*WithConnector.*sets both"; then
        echo "WithConnector_sets_both_phases"
        return 0
    fi

    if echo "$desc" | grep -qi "Write test.*WithMetadataConnector"; then
        echo "WithMetadataConnector"
        return 0
    fi

    if echo "$desc" | grep -qi "Write test.*WithMediaConnector"; then
        echo "WithMediaConnector"
        return 0
    fi

    if echo "$desc" | grep -qi "Write test.*precedence"; then
        echo "connector_precedence"
        return 0
    fi

    return 1
}

# Search for existing implementations
search_implementation() {
    local pattern="$1"
    local file_path="$2"

    if [ ! -f "$file_path" ]; then
        return 1
    fi

    case "$pattern" in
        "WithConnector_sets_both_phases")
            if grep -q "func (d \*Downloader) WithConnector" "$file_path" 2>/dev/null; then
                return 0
            fi
            ;;
        "WithMetadataConnector")
            if grep -q "func (d \*Downloader) WithMetadataConnector" "$file_path" 2>/dev/null; then
                return 0
            fi
            ;;
        "WithMediaConnector")
            if grep -q "func (d \*Downloader) WithMediaConnector" "$file_path" 2>/dev/null; then
                return 0
            fi
            ;;
        *)
            return 1
            ;;
    esac

    return 1
}

# Main detection logic
main() {
    # Extract pattern from task description
    if ! PATTERN=$(detect_patterns "$TASK_DESCRIPTION"); then
        # No recognizable pattern - assume new implementation
        echo "NEW_IMPLEMENTATION"
        exit 0
    fi

    # Extract platform from task description
    PLATFORM=""
    if echo "$TASK_DESCRIPTION" | grep -qi "instagram"; then
        PLATFORM="instagram"
    elif echo "$TASK_DESCRIPTION" | grep -qi "youtube"; then
        PLATFORM="youtube"
    elif echo "$TASK_DESCRIPTION" | grep -qi "tiktok"; then
        PLATFORM="tiktok"
    fi

    if [ -z "$PLATFORM" ]; then
        echo "NEW_IMPLEMENTATION"
        exit 0
    fi

    # Check implementation file
    IMPL_FILE="${FEATURE_DIR}/../../services/download-api/business/domain/${PLATFORM}/downloader.go"

    if search_implementation "$PATTERN" "$IMPL_FILE"; then
        echo "ALREADY_IMPLEMENTED:${PLATFORM}:${PATTERN}"
        exit 0
    fi

    echo "NEW_IMPLEMENTATION"
    exit 0
}

main
