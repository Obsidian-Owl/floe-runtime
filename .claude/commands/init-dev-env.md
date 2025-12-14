---
description: Initialize development environment for floe-runtime
allowed-tools: Bash(python:*), Bash(pip:*), Bash(dbt:*), Bash(dagster:*), Read, Write
model: sonnet
---

# Initialize Development Environment

Set up the complete development environment for floe-runtime, including Python dependencies, dbt, Dagster, and development tools.

## Tasks

1. **Verify Python version** (3.10+ required):
   - Run `python --version`
   - Ensure Python 3.10, 3.11, or 3.12 is installed

2. **Create/activate virtual environment**:
   - Check if venv exists: `ls -la venv/` or `.venv/`
   - If not exists, create: `python -m venv .venv`
   - Provide activation instructions (don't activate in shell, just inform user)

3. **Install core dependencies** (if requirements files exist):
   - Check for `requirements.txt`, `pyproject.toml`, `setup.py`
   - Install using pip: `pip install -e .` or `pip install -r requirements.txt`
   - Or use package manager if detected (poetry, pdm)

4. **Verify critical packages**:
   - pydantic (>= 2.0)
   - dagster
   - dbt-core
   - pyiceberg
   - All with version checks

5. **Set up development tools**:
   - Install: black, isort, mypy, ruff, pytest, bandit
   - Show installation commands

6. **Initialize dbt** (if dbt project exists):
   - Find dbt_project.yml
   - Verify profiles directory: `echo $DBT_PROFILES_DIR`
   - Run `dbt debug` to test connection

7. **Initialize Dagster** (if Dagster code exists):
   - Verify DAGSTER_HOME: `echo $DAGSTER_HOME`
   - Show how to run `dagster dev`

8. **Provide next steps**:
   - How to run tests: `pytest`
   - How to run type checking: `mypy --strict packages/`
   - How to format code: `black . && isort .`
   - Development workflow summary

## Output

Provide clear, numbered steps with actual commands the user should run. Format as:

```bash
# Step 1: Verify Python
python --version

# Step 2: Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Step 3: Install dependencies
pip install -e ".[dev]"

# ... etc
```

At the end, confirm what was verified and what the user needs to do manually.
