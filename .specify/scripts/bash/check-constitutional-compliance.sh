#!/bin/bash
# check-constitutional-compliance.sh
# Automated constitutional compliance checker

set -euo pipefail

REPO_ROOT="${1:-$(git rev-parse --show-toplevel)}"
CONSTITUTION_FILE="${REPO_ROOT}/.specify/memory/constitution.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS="PASSED"
VIOLATIONS=()
WARNINGS=()

echo "⚖️  Constitutional Compliance Check"
echo "======================================"
echo ""

# Check Principle I: Test-First Development (TDD)
check_principle_i() {
    echo "📋 Principle I: Test-First Development (TDD)"

    # Check if test files were modified
    TEST_FILES=$(git diff --name-only --cached | grep "_test.go$" || true)
    IMPL_FILES=$(git diff --name-only --cached | grep -v "_test.go$" | grep ".go$" || true)

    if [ -n "$IMPL_FILES" ] && [ -z "$TEST_FILES" ]; then
        echo "   ${YELLOW}⚠️  WARNING${NC}: Implementation files modified without test files"
        WARNINGS+=("Implementation without corresponding tests")
        return 1
    fi

    if [ -n "$TEST_FILES" ]; then
        # Check for Given-When-Then naming
        for file in $TEST_FILES; do
            if [ -f "$file" ]; then
                if ! grep -q "Given.*When.*Then" "$file" 2>/dev/null; then
                    echo "   ${YELLOW}⚠️  WARNING${NC}: $file may not use Given-When-Then naming"
                    WARNINGS+=("Test file may not follow BDD naming: $file")
                fi

                # Check for AAA comments
                if ! grep -q "// 1. ARRANGE\|// 2. ACT\|// 3. ASSERT" "$file" 2>/dev/null; then
                    echo "   ${YELLOW}⚠️  WARNING${NC}: $file may not have AAA comments"
                    WARNINGS+=("Test file may not have AAA structure comments: $file")
                fi
            fi
        done

        echo "   ${GREEN}✅ PASSED${NC}: Test files detected"
        return 0
    fi

    echo "   ${GREEN}✅ PASSED${NC}: No implementation changes"
    return 0
}

# Check Principle V: Small Atomic Commits
check_principle_v() {
    echo ""
    echo "📋 Principle V: Small Atomic Commits (300-600 lines)"

    # Count staged changes
    LINES_ADDED=$(git diff --cached --numstat | awk '{s+=$1} END {print s+0}')
    LINES_REMOVED=$(git diff --cached --numstat | awk '{s+=$2} END {print s+0}')
    TOTAL_LINES=$((LINES_ADDED + LINES_REMOVED))

    echo "   Lines added: $LINES_ADDED"
    echo "   Lines removed: $LINES_REMOVED"
    echo "   Total changed: $TOTAL_LINES"

    if [ "$TOTAL_LINES" -gt 600 ]; then
        echo "   ${YELLOW}⚠️  WARNING${NC}: Commit size ($TOTAL_LINES lines) exceeds recommended 600"
        WARNINGS+=("Commit size ${TOTAL_LINES} lines exceeds recommended 600")
        return 1
    elif [ "$TOTAL_LINES" -lt 10 ]; then
        echo "   ${YELLOW}⚠️  WARNING${NC}: Very small commit ($TOTAL_LINES lines) - may be incomplete"
        WARNINGS+=("Very small commit: $TOTAL_LINES lines")
        return 1
    fi

    echo "   ${GREEN}✅ PASSED${NC}: Commit size within target (300-600 lines)"
    return 0
}

# Check Principle XIII: Pattern Consistency
check_principle_xiii() {
    echo ""
    echo "📋 Principle XIII: Pattern Consistency & Discovery"

    # Check if new test files follow existing patterns
    NEW_TEST_FILES=$(git diff --cached --name-only | grep "_test.go$" || true)

    if [ -n "$NEW_TEST_FILES" ]; then
        for file in $NEW_TEST_FILES; do
            if [ -f "$file" ]; then
                # Check for table-driven tests
                if ! grep -q "tests := \[\]struct" "$file" 2>/dev/null; then
                    echo "   ${YELLOW}⚠️  WARNING${NC}: $file may not use table-driven test pattern"
                    WARNINGS+=("Test file may not follow table-driven pattern: $file")
                fi
            fi
        done

        echo "   ${GREEN}✅ PASSED${NC}: Pattern consistency checked"
        return 0
    fi

    echo "   ${GREEN}✅ PASSED${NC}: No new test files"
    return 0
}

# Check for uncommitted changes
check_uncommitted() {
    echo ""
    echo "📋 Uncommitted Changes Check"

    if ! git diff --quiet || ! git diff --cached --quiet; then
        UNSTAGED=$(git diff --name-only | wc -l | tr -d ' ')
        STAGED=$(git diff --cached --name-only | wc -l | tr -d ' ')

        if [ "$UNSTAGED" -gt 0 ]; then
            echo "   ${YELLOW}⚠️  WARNING${NC}: $UNSTAGED unstaged file(s)"
            WARNINGS+=("Uncommitted changes: $UNSTAGED unstaged files")
        fi

        if [ "$STAGED" -eq 0 ]; then
            echo "   ${RED}❌ FAILED${NC}: No files staged for commit"
            VIOLATIONS+=("No files staged - run 'git add' first")
            OVERALL_STATUS="FAILED"
            return 1
        fi

        echo "   ${GREEN}✅ PASSED${NC}: $STAGED file(s) staged for commit"
        return 0
    fi

    echo "   ${GREEN}✅ PASSED${NC}: No changes detected"
    return 0
}

# Main execution
main() {
    if [ ! -f "$CONSTITUTION_FILE" ]; then
        echo "${YELLOW}⚠️  constitution.md not found - using basic checks${NC}"
        echo ""
    fi

    check_principle_i || true
    check_principle_v || true
    check_principle_xiii || true
    check_uncommitted || true

    echo ""
    echo "======================================"
    echo "Overall Status: ${OVERALL_STATUS}"

    if [ "$OVERALL_STATUS" = "PASSED" ] && [ ${#WARNINGS[@]} -eq 0 ]; then
        echo "${GREEN}✅ ALL CHECKS PASSED${NC}"
        echo ""
        return 0
    fi

    if [ ${#VIOLATIONS[@]} -gt 0 ]; then
        echo ""
        echo "${RED}❌ Violations:${NC}"
        for violation in "${VIOLATIONS[@]}"; do
            echo "   - $violation"
        done
    fi

    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo ""
        echo "${YELLOW}⚠️  Warnings:${NC}"
        for warning in "${WARNINGS[@]}"; do
            echo "   - $warning"
        done
    fi

    echo ""

    if [ "$OVERALL_STATUS" = "FAILED" ]; then
        return 1
    fi

    return 0
}

main
