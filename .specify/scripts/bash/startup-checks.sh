#!/bin/bash
# startup-checks.sh
# Automated startup checks for /speckit.implementwithbeads workflow
# Combines all Section 0 checks into a single script

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 SpecKit Beads Implementation - Startup Checks"
echo "================================================"
echo ""

# ==============================================================================
# CHECK 1: Verify Beads is installed
# ==============================================================================

echo "🔍 Check 1/3: Beads Installation"
echo "--------------------------------"

if ! command -v bd &> /dev/null; then
  echo "${RED}❌ ERROR: Beads is not installed${NC}"
  echo ""
  echo "This command requires Beads for task tracking."
  echo ""
  echo "📦 Install Beads:"
  echo "   brew install beadlabs/tap/beads"
  echo ""
  echo "   Or visit: https://github.com/beadlabs/beads"
  exit 1
fi

BEADS_VERSION=$(bd --version 2>&1)
echo "${GREEN}✅ Beads detected: $BEADS_VERSION${NC}"
echo ""

# ==============================================================================
# CHECK 2: Verify Beads issues exist
# ==============================================================================

echo "🔍 Check 2/3: Beads Issues"
echo "-------------------------"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

if [ ! -f "$REPO_ROOT/.beads/issues.jsonl" ]; then
  echo "${RED}❌ ERROR: No Beads issues found${NC}"
  echo ""
  echo "This command requires Beads issues to be created from tasks.md"
  echo ""
  echo "📦 Create Beads issues from tasks:"
  echo "   /speckit.taskstobeads"
  echo ""
  echo "💡 This will:"
  echo "   - Read tasks.md from your feature branch"
  echo "   - Create Beads issues with dependencies"
  echo "   - Enable incremental task tracking"
  exit 1
fi

ISSUE_COUNT=$(bd list 2>/dev/null | wc -l | tr -d ' ')

if [ "$ISSUE_COUNT" = "0" ] || [ -z "$ISSUE_COUNT" ]; then
  echo "${RED}❌ ERROR: No Beads issues available${NC}"
  echo ""
  echo "Run /speckit.taskstobeads to create issues from tasks.md"
  exit 1
fi

echo "${GREEN}✅ Beads issues available: ${ISSUE_COUNT} total${NC}"
echo ""

# ==============================================================================
# CHECK 3: Verify prerequisites (feature dir, tasks.md, etc.)
# ==============================================================================

echo "🔍 Check 3/3: Prerequisites"
echo "---------------------------"

# Run prerequisites check script
PREREQ_SCRIPT="$REPO_ROOT/.specify/scripts/bash/check-prerequisites.sh"

if [ ! -f "$PREREQ_SCRIPT" ]; then
  echo "${YELLOW}⚠️  WARNING: Prerequisites check script not found${NC}"
  echo "   Expected: $PREREQ_SCRIPT"
  echo ""
  echo "Continuing without prerequisites validation..."
  echo ""

  # Set minimal defaults
  echo '{"FEATURE_DIR":"'$(pwd)'","AVAILABLE_DOCS":[]}'
  exit 0
fi

# Run prerequisites check and capture output
if ! PREREQ_OUTPUT=$("$PREREQ_SCRIPT" --json --require-tasks --include-tasks 2>&1); then
  echo "${RED}❌ ERROR: Prerequisites check failed${NC}"
  echo ""
  echo "$PREREQ_OUTPUT"
  exit 1
fi

# Parse JSON output
FEATURE_DIR=$(echo "$PREREQ_OUTPUT" | jq -r '.FEATURE_DIR' 2>/dev/null || echo "")
AVAILABLE_DOCS=$(echo "$PREREQ_OUTPUT" | jq -r '.AVAILABLE_DOCS[]' 2>/dev/null || echo "")

if [ -z "$FEATURE_DIR" ]; then
  echo "${RED}❌ ERROR: Could not determine feature directory${NC}"
  exit 1
fi

# Check if tasks.md exists
if ! echo "$AVAILABLE_DOCS" | grep -q "tasks.md"; then
  echo "${RED}❌ ERROR: tasks.md not found in feature directory${NC}"
  echo ""
  echo "Feature directory: $FEATURE_DIR"
  echo ""
  echo "Run /speckit.tasks to generate tasks from plan.md"
  exit 1
fi

# Check if Beads mapping file exists
MAPPING_FILE="$FEATURE_DIR/.beads-mapping.json"
if [ ! -f "$MAPPING_FILE" ]; then
  echo "${YELLOW}⚠️  WARNING: Beads mapping file not found${NC}"
  echo ""
  echo "Tasks not yet migrated to Beads."
  echo ""
  echo "📦 Run /speckit.taskstobeads to create Beads issues from tasks.md"
  echo ""
  exit 1
fi

echo "${GREEN}✅ Prerequisites verified${NC}"
echo "   Feature dir: $FEATURE_DIR"
echo "   Available docs: $(echo "$AVAILABLE_DOCS" | tr '\n' ', ' | sed 's/,$//')"
echo "   Beads mapping: $MAPPING_FILE"
echo ""

# ==============================================================================
# SUCCESS - Output JSON for workflow consumption
# ==============================================================================

echo "================================================"
echo "${GREEN}✅ All startup checks passed!${NC}"
echo ""

# Output JSON for workflow to parse
cat <<EOF
{
  "status": "success",
  "beads_version": "$BEADS_VERSION",
  "issue_count": $ISSUE_COUNT,
  "feature_dir": "$FEATURE_DIR",
  "mapping_file": "$MAPPING_FILE",
  "available_docs": ["$AVAILABLE_DOCS"]
}
EOF

exit 0
