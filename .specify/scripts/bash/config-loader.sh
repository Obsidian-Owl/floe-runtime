#!/bin/bash
# config-loader.sh - Load SpecKit-Beads configuration
# Used by implementwithbeads workflow to read user preferences

set -euo pipefail

# Default configuration
DEFAULT_AUTO_CLOSE="false"
DEFAULT_AUTO_CONTINUE="false"
DEFAULT_BATCH_MODE="false"
DEFAULT_QUIET_MODE="false"
DEFAULT_MAX_BATCH_TASKS="5"
DEFAULT_REQUIRE_APPROVAL_ON_FAILURE="true"

# Function to load config from file or environment
load_config() {
    local config_file="${1:-.speckit-beads.config.json}"
    local key="$2"
    local default_value="$3"

    # Priority: Environment Variable > Config File > Default

    # 1. Check environment variable (SPECKIT_AUTO_CLOSE, etc.)
    local env_var="SPECKIT_$(echo "$key" | tr '[:lower:]' '[:upper:]')"
    if [ -n "${!env_var:-}" ]; then
        echo "${!env_var}"
        return 0
    fi

    # 2. Check config file (if exists and has jq)
    if [ -f "$config_file" ] && command -v jq &> /dev/null; then
        local value
        value=$(jq -r ".${key} // empty" "$config_file" 2>/dev/null || echo "")
        if [ -n "$value" ] && [ "$value" != "null" ]; then
            echo "$value"
            return 0
        fi
    fi

    # 3. Use default
    echo "$default_value"
}

# Function to get all config values
get_all_config() {
    local config_file="${1:-.speckit-beads.config.json}"

    cat <<EOF
{
  "auto_close": $(load_config "$config_file" "auto_close" "$DEFAULT_AUTO_CLOSE"),
  "auto_continue": $(load_config "$config_file" "auto_continue" "$DEFAULT_AUTO_CONTINUE"),
  "batch_mode": $(load_config "$config_file" "batch_mode" "$DEFAULT_BATCH_MODE"),
  "quiet_mode": $(load_config "$config_file" "quiet_mode" "$DEFAULT_QUIET_MODE"),
  "max_batch_tasks": $(load_config "$config_file" "max_batch_tasks" "$DEFAULT_MAX_BATCH_TASKS"),
  "require_approval_on_failure": $(load_config "$config_file" "require_approval_on_failure" "$DEFAULT_REQUIRE_APPROVAL_ON_FAILURE")
}
EOF
}

# Function to create default config file
create_default_config() {
    local config_file="${1:-.speckit-beads.config.json}"

    cat > "$config_file" <<'EOF'
{
  "auto_close": false,
  "auto_continue": false,
  "batch_mode": false,
  "quiet_mode": false,
  "max_batch_tasks": 5,
  "require_approval_on_failure": true,
  "_comments": {
    "auto_close": "Automatically close tasks if tests pass and compliance check passes",
    "auto_continue": "Automatically continue to next task without prompting",
    "batch_mode": "Implement multiple tasks in sequence (up to max_batch_tasks)",
    "quiet_mode": "Reduce output verbosity (show only essential information)",
    "max_batch_tasks": "Maximum number of tasks to implement in batch mode (1-10)",
    "require_approval_on_failure": "Always ask for approval if tests fail or compliance fails"
  }
}
EOF

    echo "✅ Created default config: $config_file"
}

# Main execution (if run directly)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        "create")
            create_default_config "${2:-.speckit-beads.config.json}"
            ;;
        "get")
            if [ -n "${2:-}" ]; then
                load_config ".speckit-beads.config.json" "$2" ""
            else
                get_all_config ".speckit-beads.config.json"
            fi
            ;;
        "help"|"--help"|"-h"|"")
            cat <<'HELP'
config-loader.sh - Load SpecKit-Beads configuration

Usage:
  config-loader.sh create [file]     # Create default config file
  config-loader.sh get [key]         # Get config value (or all if no key)
  config-loader.sh help              # Show this help

Configuration Priority:
  1. Environment Variables (SPECKIT_AUTO_CLOSE, etc.)
  2. Config File (.speckit-beads.config.json)
  3. Default Values

Example:
  # Create config
  config-loader.sh create

  # Get all config
  config-loader.sh get

  # Get specific value
  config-loader.sh get auto_close

  # Override with environment variable
  SPECKIT_AUTO_CLOSE=true /speckit.implementwithbeads
HELP
            ;;
        *)
            echo "Unknown command: $1"
            echo "Run 'config-loader.sh help' for usage"
            exit 1
            ;;
    esac
fi
