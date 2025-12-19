# Python Development Standards

## Type Safety (MANDATORY)

**YOU MUST include type hints on ALL functions, methods, and variables:**

```python
from __future__ import annotations  # REQUIRED at top of every .py file

from typing import Any
from pathlib import Path

def process_data(
    input_path: Path,
    config: dict[str, Any],
    strict: bool = True
) -> dict[str, Any]:
    """Process data with strict type checking.

    Args:
        input_path: Path to input file
        config: Configuration dictionary
        strict: Enable strict validation

    Returns:
        Processed data dictionary

    Raises:
        ValidationError: If validation fails
    """
    result: dict[str, Any] = {}
    # ...
    return result
```

**Requirements:**
- `from __future__ import annotations` at top of every file
- Modern generics: `list[str]`, `dict[str, int]` (not `List[str]`, `Dict[str, int]`)
- Run `mypy --strict` on all code
- No `Any` types except when interfacing with untyped third-party libraries

## Code Quality Standards

### Formatting: Black (100 char line length)
```bash
black --line-length 100 .
```

### Import Sorting: isort
```bash
isort .
```

### Linting: Ruff
```bash
ruff check .
```

### Security Scanning: Bandit
```bash
bandit -r packages/
```

## Code Organization

```python
"""Module docstring explaining purpose."""

from __future__ import annotations  # REQUIRED

# Standard library imports
import logging
from pathlib import Path
from typing import Any

# Third-party imports
from pydantic import BaseModel, Field

# Local imports
from floe_core.schemas import FloeSpec
from floe_core.errors import CompilationError

# Module constants
DEFAULT_VERSION = "1.0.0"
MAX_RETRIES = 3

# Logger setup
logger = logging.getLogger(__name__)


class MyClass:
    """Class with clear docstrings."""

    def __init__(self, value: str) -> None:
        """Initialize class.

        Args:
            value: Initial value
        """
        self.value = value
```

## Testing Requirements

**YOU MUST achieve > 80% code coverage:**

```python
import pytest
from hypothesis import given, strategies as st

def test_function_valid():
    """Test successful execution."""
    result = my_function("valid_input")
    assert result.success is True

def test_function_invalid():
    """Test validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        my_function("")
    assert "required" in str(exc_info.value)

@given(st.text(min_size=1, max_size=100))
def test_property_based(input_str: str):
    """Property-based test."""
    result = my_function(input_str)
    assert result is not None
```

**Testing standards:**
- Unit tests: Fast, isolated, mock external dependencies
- Integration tests: Use testcontainers for databases
- Property-based tests: Use `hypothesis` for edge cases
- > 80% coverage required

## Test Execution Model (MANDATORY)

| Test Type | Location | Execution Environment |
|-----------|----------|----------------------|
| Unit tests | `packages/*/tests/unit/` | Host (`uv run pytest`) |
| Contract tests | `packages/*/tests/contract/` | Host (`uv run pytest`) |
| **Integration tests** | `packages/*/tests/integration/` | **Docker (test-runner)** |
| **E2E tests** | `packages/*/tests/e2e/` | **Docker (test-runner)** |

**Rules:**
- Unit/contract tests: Fast, isolated, mock external dependencies, run on host
- Integration tests: Require Docker services (DB, S3, Polaris), MUST run inside test-runner container
- E2E tests: End-to-end workflows, MUST run inside test-runner container

**Local development:**
```bash
# Unit tests (host)
uv run pytest packages/<package>/tests/unit/ -v

# Integration tests (Docker)
./testing/docker/scripts/run-integration-tests.sh
```

**Why Docker for integration tests?**
- Docker networking resolves service hostnames (localstack, polaris, etc.)
- Consistent environment between local development and CI
- Tests that require S3, databases, or external services work reliably

## Documentation: Google-Style Docstrings

```python
def compile_spec(
    spec: FloeSpec,
    target: str | None = None,
    strict: bool = True
) -> CompiledArtifacts:
    """Compile FloeSpec into CompiledArtifacts.

    Args:
        spec: Validated FloeSpec from floe.yaml
        target: Optional compute target override
        strict: Enable strict validation mode

    Returns:
        CompiledArtifacts containing dbt profiles and Dagster config

    Raises:
        ValidationError: If spec validation fails
        CompilationError: If compilation fails

    Examples:
        >>> spec = FloeSpec.parse_file("floe.yaml")
        >>> artifacts = compile_spec(spec)
        >>> artifacts.dbt_profiles["default"]["target"]
        'dev'
    """
    pass
```

## Dependency Management

```bash
# Check for security vulnerabilities
pip-audit

# Check for outdated packages
pip list --outdated

# Use safety for known CVEs
safety check
```

**Dependency rules:**
- Pin exact versions in production (`package==1.2.3`)
- Use version ranges in libraries (`package>=1.2,<2.0`)
- Update dependencies within 7 days of CVE disclosure
- Pure Python only (no compiled extensions)

## Pre-Commit Checklist

Before committing, verify:
- [ ] All type hints present (`mypy --strict` passes)
- [ ] Black formatting applied (100 char)
- [ ] isort applied
- [ ] Ruff linting passes
- [ ] Bandit security scan passes
- [ ] Tests pass with > 80% coverage
- [ ] No secrets in code
