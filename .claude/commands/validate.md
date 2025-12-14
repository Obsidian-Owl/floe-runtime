---
description: Validate floe.yaml schema and run all quality checks
allowed-tools: Bash(python:*), Bash(mypy:*), Bash(pytest:*), Bash(black:*), Bash(ruff:*), Read, Grep, Glob
argument-hint: [file_path]
model: sonnet
---

# Validate floe.yaml and Code Quality

Run comprehensive validation on floe.yaml (if provided) and all code quality checks.

## Arguments

- `$ARGUMENTS`: Optional path to floe.yaml file (default: search for floe.yaml in project)

## Tasks

### 1. Find and Validate floe.yaml

If `$ARGUMENTS` provided:
- Use that path
Otherwise:
- Search for floe.yaml: `find . -name "floe.yaml" -not -path "*/venv/*" -not -path "*/.venv/*"`

If floe.yaml found:
- **Read the file** to understand its structure
- **Validate schema** using Pydantic (if FloeSpec exists in packages/floe-core)
  - Search for FloeSpec definition: `rg "class FloeSpec" --type py`
  - If exists, run validation script
  - If not exists, inform user schema validation not yet implemented
- **Check required fields**: project, targets, default_target
- **Validate target references**: Ensure default_target exists in targets
- Report any validation errors with clear explanations

### 2. Run Type Checking

- **Find Python packages**: `find packages -name "*.py" -not -path "*/venv/*" | head -1` to verify packages exist
- **Run mypy strict**: `mypy --strict packages/`
- Report any type errors with file:line references
- If mypy not installed, inform user to run `/init-dev-env`

### 3. Run Code Quality Checks

- **Black formatting check**: `black --check --line-length 100 packages/`
- **isort import sorting check**: `isort --check-only packages/`
- **Ruff linting**: `ruff check packages/`
- **Bandit security scan**: `bandit -r packages/`

For each check:
- Show command being run
- Report results (pass/fail)
- If failures, show how to fix (e.g., `black packages/` to auto-fix)

### 4. Run Tests (if they exist)

- **Find test files**: `find . -name "test_*.py" -o -name "*_test.py"`
- If tests exist: `pytest --cov=packages --cov-report=term-missing`
- Report coverage percentage
- Highlight if coverage < 80% (goal is > 80%)

### 5. Summary Report

Provide a final summary:

```
✅ Validation Summary
==================
floe.yaml:       [PASS/FAIL]
Type checking:   [PASS/FAIL]
Code formatting: [PASS/FAIL]
Linting:         [PASS/FAIL]
Security scan:   [PASS/FAIL]
Tests:           [PASS/FAIL] (XX% coverage)

[Action items if any failures]
```

## Error Handling

- If floe.yaml not found, clearly state that and skip schema validation
- If tools not installed, provide installation commands
- If no packages/ directory exists, inform user implementation hasn't started yet
