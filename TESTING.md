# Testing Guide for floe-runtime

This document describes the testing strategy, patterns, and workflows for floe-runtime.

## Quick Start

```bash
# Run ALL unit tests across all packages (669 tests)
uv run pytest packages/floe-core/tests/ packages/floe-dbt/tests/unit/ packages/floe-dagster/tests/unit/ tests/contract/ -v

# Run all unit tests for a single package
uv run pytest packages/floe-core/tests/ -v

# Run adapter profile tests
uv run pytest packages/floe-dbt/tests/unit/test_profiles/ -v

# Run with specific markers
uv run pytest -m "not slow and not integration" -v

# Run tests for a specific adapter
uv run pytest -k "snowflake" -v
```

## Important: No `__init__.py` in Test Directories

**CRITICAL**: Test directories (`packages/*/tests/`) must NOT contain `__init__.py` files.

pytest uses `--import-mode=importlib` which causes namespace collisions when multiple
packages have `tests/__init__.py` files (all resolve to `tests.conftest` module name).

```
# CORRECT - No __init__.py in test directories
packages/floe-core/tests/conftest.py     # OK - namespace package
packages/floe-dbt/tests/conftest.py      # OK - namespace package

# WRONG - __init__.py causes collision
packages/floe-core/tests/__init__.py     # BAD - causes "tests.conftest" collision
```

This is why `floe-core` tests work correctly (no `__init__.py`) while other packages
previously had issues.

## Test Structure

```
floe-runtime/
├── testing/                           # Shared testing infrastructure
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── artifacts.py               # CompiledArtifacts factory
│   ├── base_classes/
│   │   ├── __init__.py
│   │   └── adapter_test_base.py       # Base test classes
│   └── markers/
│       └── __init__.py                # Marker documentation
├── tests/                             # Root-level tests
│   └── conftest.py
└── packages/
    ├── floe-core/tests/
    │   ├── unit/                      # Fast, isolated tests
    │   └── contract/                  # Schema stability tests
    ├── floe-dbt/tests/
    │   ├── unit/                      # Profile generator tests
    │   │   └── test_profiles/         # Adapter-specific tests
    │   └── integration/               # Real dbt execution tests
    └── floe-dagster/tests/
        ├── unit/                      # Asset factory tests
        └── integration/               # Real Dagster tests
```

## Testing Pyramid

```
        /\          E2E (5-10%): Full pipeline with containers
       /  \
      /____\        Integration (20-30%): Real dbt, testcontainers
     /      \
    /________\      Contract (10%): Cross-package validation
   /          \
  /____________\    Unit (60%): Mocks, fast feedback
```

## pytest Markers

Available markers (defined in `pyproject.toml`):

| Marker | Description | Example |
|--------|-------------|---------|
| `slow` | Tests taking > 1 second | `@pytest.mark.slow` |
| `integration` | Require external services | `@pytest.mark.integration` |
| `contract` | Cross-package validation | `@pytest.mark.contract` |
| `e2e` | End-to-end pipeline tests | `@pytest.mark.e2e` |
| `adapter` | Specific compute adapter | `@pytest.mark.adapter("snowflake")` |
| `requires_dbt` | Require dbt-core installed | `@pytest.mark.requires_dbt` |
| `requires_container` | Require Docker | `@pytest.mark.requires_container` |

### Running by Marker

```bash
# Skip slow tests
uv run pytest -m "not slow" -v

# Only integration tests
uv run pytest -m integration -v

# Only contract tests
uv run pytest -m contract -v

# Exclude integration and slow
uv run pytest -m "not integration and not slow" -v
```

## Base Test Classes

### BaseProfileGeneratorTests

All profile generator adapter tests inherit from `BaseProfileGeneratorTests`:

```python
from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests

class TestMyAdapterProfileGenerator(BaseProfileGeneratorTests):
    """Test suite for MyAdapter profile generation."""

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        from floe_dbt.profiles.myadapter import MyAdapterProfileGenerator
        return MyAdapterProfileGenerator()

    @property
    def target_type(self) -> str:
        return "myadapter"

    @property
    def required_fields(self) -> set[str]:
        return {"type", "host", "port", "threads"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        return {
            "version": "1.0.0",
            "compute": {
                "target": "myadapter",
                "properties": {"host": "localhost"},
            },
            "transforms": [],
        }

    # Adapter-specific tests go here...
    def test_myadapter_specific_feature(self, generator, config):
        ...
```

**Inherited tests** (automatically run for all adapters):
1. `test_implements_protocol` - Verifies ProfileGenerator Protocol
2. `test_generate_returns_dict` - Validates return type
3. `test_generate_includes_target_name` - Target name in output
4. `test_generate_has_correct_type` - Correct adapter type
5. `test_generate_has_required_fields` - All required fields present
6. `test_generate_uses_config_threads` - Thread configuration
7. `test_generate_custom_target_name` - Custom target naming
8. `test_generate_with_different_environments` - Environment support

### BaseCredentialProfileGeneratorTests

For adapters with credentials (user/password, API tokens):

```python
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests

class TestSnowflakeProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for Snowflake profile generation."""

    @property
    def credential_fields(self) -> set[str]:
        return {"user", "password"}  # Fields that must use env_var()

    # ... other required properties and methods
```

**Additional inherited tests**:
1. `test_credentials_use_env_var_template` - Verifies `{{ env_var(...) }}`
2. `test_never_hardcodes_credentials` - Security validation

## Fixture Factories

### make_compiled_artifacts

Create test CompiledArtifacts:

```python
from testing.fixtures.artifacts import make_compiled_artifacts

def test_something():
    artifacts = make_compiled_artifacts(
        target="snowflake",
        environment="prod",
        include_transforms=True,
    )
    # Use artifacts in test...
```

### COMPUTE_CONFIGS

Pre-defined configurations for all adapters:

```python
from testing.fixtures.artifacts import COMPUTE_CONFIGS

def test_all_adapters():
    for adapter_name, config in COMPUTE_CONFIGS.items():
        artifacts = make_compiled_artifacts(target=adapter_name)
        # Test with each adapter...
```

## Adding a New Adapter

1. **Create the generator** in `packages/floe-dbt/src/floe_dbt/profiles/`:
   ```python
   # myadapter.py
   class MyAdapterProfileGenerator:
       def generate(self, artifacts: dict, config: ProfileGeneratorConfig) -> dict:
           ...
   ```

2. **Create the test file** in `packages/floe-dbt/tests/unit/test_profiles/`:
   ```python
   # test_myadapter.py
   class TestMyAdapterProfileGenerator(BaseProfileGeneratorTests):
       # Implement required abstract methods...
   ```

3. **Add config to COMPUTE_CONFIGS** in `testing/fixtures/artifacts.py`:
   ```python
   COMPUTE_CONFIGS: dict[str, dict[str, Any]] = {
       # ... existing configs
       "myadapter": {
           "target": "myadapter",
           "properties": {"host": "localhost"},
       },
   }
   ```

4. **Run tests**:
   ```bash
   uv run pytest packages/floe-dbt/tests/unit/test_profiles/test_myadapter.py -v
   ```

## Contract Tests

Contract tests validate cross-package integration:

```python
# packages/floe-core/tests/contract/test_compiled_artifacts_stability.py

@pytest.mark.contract
def test_schema_backward_compatible():
    """Verify schema changes are backward compatible."""
    current = CompiledArtifacts.model_json_schema()
    # Compare with baseline schema...
```

## Integration Tests

Integration tests require external dependencies:

```python
@pytest.mark.integration
@pytest.mark.requires_dbt
def test_dbt_debug_with_generated_profile(tmp_path):
    """Test generated profile works with real dbt."""
    # Generate profile
    artifacts = make_compiled_artifacts(target="duckdb")
    profile = generator.generate(artifacts, config)

    # Write to file
    write_profile(profile, tmp_path / "profiles.yml")

    # Run dbt debug
    result = subprocess.run(
        ["dbt", "debug", "--profiles-dir", str(tmp_path)],
        capture_output=True,
    )
    assert result.returncode == 0
```

### Skip Patterns

```python
import pytest

try:
    import dbt.cli.main
    HAS_DBT = True
except ImportError:
    HAS_DBT = False

@pytest.mark.skipif(not HAS_DBT, reason="dbt-core not installed")
def test_requires_dbt():
    ...
```

## Mock vs Real Services Matrix

| Service | Unit Tests | Integration | E2E |
|---------|------------|-------------|-----|
| dbt | Mock dbtRunner | Real subprocess | Real |
| DuckDB | Real (fast) | Real | Real |
| Snowflake | Mock adapter | Skip (no creds) | Skip |
| PostgreSQL | Mock adapter | Testcontainer | Real |
| OpenLineage | Mock emit() | Local HTTP | Marquez |
| OpenTelemetry | InMemorySpanExporter | InMemory | Jaeger |

### OpenTelemetry Testing

Use the `in_memory_span_exporter` fixture to verify spans without requiring an external collector:

```python
def test_tracing_creates_spans(in_memory_span_exporter):
    """Test that operations create correct OTel spans."""
    exporter, provider = in_memory_span_exporter
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("transform") as span:
        span.set_attribute("model", "customers")
        span.set_attribute("status", "success")

    # Verify spans
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "transform"
    assert spans[0].attributes["model"] == "customers"

    exporter.clear()  # Clean up for next test
```

This approach:
- Requires no Docker or external collector
- Verifies span names, attributes, and parent/child relationships
- Runs fast in CI/CD
- Uses the built-in `InMemorySpanExporter` from `opentelemetry-sdk`

## CI/CD Pipeline

Tests run in stages:

1. **Lint & Type Check** (< 2 min)
   ```bash
   ruff check .
   black --check .
   mypy --strict packages/
   ```

2. **Unit Tests** (< 5 min, parallel by Python version)
   ```bash
   uv run pytest -m "not integration and not slow" --cov
   ```

3. **Contract Tests** (< 3 min)
   ```bash
   uv run pytest -m contract
   ```

4. **Integration Tests** (< 10 min)
   ```bash
   uv run pytest -m integration
   ```

5. **Adapter Tests** (parallel per adapter)
   ```bash
   uv run pytest -k duckdb
   uv run pytest -k postgres
   ```

## Coverage Requirements

- **Minimum**: 80% coverage required
- **Unit tests**: Fast, isolated, mock external dependencies
- **Integration tests**: Test component interactions
- **Contract tests**: Validate API contracts between packages

## Troubleshooting

### Missing Adapters

Some tests skip when adapters aren't installed:

```bash
# Install specific adapter for testing
uv pip install dbt-snowflake
uv run pytest -k snowflake -v
```

### OpenTelemetry Warnings

Expected when running locally without OTel collector:

```
Transient error StatusCode.UNAVAILABLE encountered while exporting traces
```

This is harmless - the NoOp tracer handles this gracefully.

## Plugin Author Checklist

For third-party plugins implementing ProfileGenerator:

- [ ] Inherits from `BaseProfileGeneratorTests` and passes all inherited tests
- [ ] Implements `ProfileGenerator` Protocol (runtime-checkable)
- [ ] Generates valid profiles.yml structure
- [ ] Uses `ProfileGeneratorConfig.get_secret_env_var()` for secrets
- [ ] Handles missing optional properties gracefully
- [ ] Includes integration test with `dbt debug` validation
- [ ] Documents required vs optional properties
