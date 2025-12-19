# 08. Quality

This document describes quality requirements, testing strategy, and CI/CD for floe-runtime.

---

## 1. Quality Goals

| Quality | Target | Measurement |
|---------|--------|-------------|
| **Reliability** | Zero data loss | Integration tests, property tests |
| **Portability** | Works on macOS, Linux, Windows | CI matrix |
| **Performance** | CLI startup < 500ms | Benchmark suite |
| **Maintainability** | < 30 min to fix typical bug | Code review metrics |
| **Testability** | > 80% code coverage | Coverage reports |
| **Usability** | < 5 min to first run | User testing |

---

## 2. Testing Strategy

### 2.1 Test Pyramid

```
                    ┌─────────┐
                    │   E2E   │  ← Few, slow, high confidence
                    │  Tests  │
                    ├─────────┤
                    │ Integr- │
                    │  ation  │  ← Some, medium speed
                    │  Tests  │
                    ├─────────┤
                    │         │
                    │  Unit   │  ← Many, fast, isolated
                    │  Tests  │
                    │         │
                    └─────────┘
```

### 2.2 Test Types

| Type | Scope | Tools | Speed |
|------|-------|-------|-------|
| **Unit** | Single function/class | pytest, hypothesis | < 1s |
| **Integration** | Component interactions | pytest, testcontainers | < 30s |
| **E2E** | Full workflows | pytest, Docker Compose | < 5min |
| **Performance** | Benchmarks | pytest-benchmark | varies |

### 2.3 Tests FAIL, Never Skip (MANDATORY)

**Skipped tests hide problems. If a test can't run, FIX the underlying issue.**

```python
# ❌ FORBIDDEN - Skipping hides the real problem
@pytest.mark.skip("Service not available")
def test_something():
    ...

# ❌ FORBIDDEN - pytest.skip() in test body
def test_something():
    if not service_available():
        pytest.skip("Service not available")  # NO!
    ...

# ✅ CORRECT - Test FAILS if infrastructure missing
def test_something(service_client):
    """Test requires service - FAILS if not available."""
    response = service_client.query(...)
    assert response.status_code == 200
```

**Why this matters:**
- Skipped tests are invisible failures
- "Just one skip" becomes 50 skipped tests over time
- Skips hide infrastructure rot
- False confidence: "All tests pass!" when half are skipped

**The ONLY acceptable uses of skip:**
1. `pytest.importorskip("optional_library")` - genuinely optional dependencies
2. `@pytest.mark.skipif(sys.platform == "win32")` - test literally cannot run on platform

If you find yourself writing skips, ask: "What's the real problem here?"

### 2.4 Test Execution Model

| Test Type | Location | Execution Environment |
|-----------|----------|----------------------|
| Unit tests | `packages/*/tests/unit/` | Host (`uv run pytest`) |
| Contract tests | `packages/*/tests/contract/` | Host (`uv run pytest`) |
| **Integration tests** | `packages/*/tests/integration/` | **Docker (test-runner)** |
| **E2E tests** | `packages/*/tests/e2e/` | **Docker (test-runner)** |

**IMPORTANT**: Integration tests MUST run inside Docker. Running from host will fail
with `Could not resolve host: localstack` errors due to Docker network hostname resolution.

---

## 3. Unit Testing

### 3.1 Structure

```
tests/
├── unit/
│   ├── floe_core/
│   │   ├── test_compiler.py
│   │   ├── test_schemas.py
│   │   └── test_validation.py
│   ├── floe_cli/
│   │   ├── test_commands.py
│   │   └── test_init.py
│   ├── floe_dagster/
│   │   ├── test_asset_factory.py
│   │   └── test_lineage.py
│   └── floe_dbt/
│       ├── test_profiles.py
│       └── test_executor.py
├── integration/
│   └── ...
└── e2e/
    └── ...
```

### 3.2 Unit Test Examples

```python
# tests/unit/floe_core/test_schemas.py
import pytest
from pydantic import ValidationError
from floe_core.schemas import FloeSpec, ComputeConfig, ComputeTarget

class TestFloeSpec:
    """Tests for FloeSpec schema."""

    def test_valid_spec(self):
        """Valid spec should parse successfully."""
        spec = FloeSpec(
            name="test-pipeline",
            version="1.0",
            compute=ComputeConfig(target=ComputeTarget.DUCKDB),
        )
        assert spec.name == "test-pipeline"
        assert spec.compute.target == ComputeTarget.DUCKDB

    def test_missing_name_fails(self):
        """Missing name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                version="1.0",
                compute=ComputeConfig(target=ComputeTarget.DUCKDB),
            )
        assert "name" in str(exc_info.value)

    def test_invalid_target_fails(self):
        """Invalid compute target should raise ValidationError."""
        with pytest.raises(ValidationError):
            FloeSpec(
                name="test",
                compute=ComputeConfig(target="invalid"),
            )

    @pytest.mark.parametrize("target", list(ComputeTarget))
    def test_all_targets_valid(self, target: ComputeTarget):
        """All defined targets should be valid."""
        spec = FloeSpec(
            name="test",
            compute=ComputeConfig(target=target),
        )
        assert spec.compute.target == target
```

```python
# tests/unit/floe_dbt/test_profiles.py
import pytest
from floe_core.schemas import CompiledArtifacts, ComputeConfig, ComputeTarget
from floe_dbt.profiles import generate_profiles

class TestProfileGeneration:
    """Tests for dbt profile generation."""

    def test_duckdb_profile(self):
        """DuckDB profile should be generated correctly."""
        artifacts = create_artifacts(
            target=ComputeTarget.DUCKDB,
            properties={"path": "/tmp/test.duckdb"},
        )

        profiles = generate_profiles(artifacts)

        assert profiles["floe"]["outputs"]["default"]["type"] == "duckdb"
        assert profiles["floe"]["outputs"]["default"]["path"] == "/tmp/test.duckdb"

    def test_snowflake_profile_uses_env_vars(self):
        """Snowflake profile should use environment variable references."""
        artifacts = create_artifacts(target=ComputeTarget.SNOWFLAKE)

        profiles = generate_profiles(artifacts)

        output = profiles["floe"]["outputs"]["default"]
        assert "{{ env_var('SNOWFLAKE_ACCOUNT') }}" in output["account"]
        assert "{{ env_var('SNOWFLAKE_PASSWORD') }}" in output["password"]

def create_artifacts(**kwargs) -> CompiledArtifacts:
    """Helper to create test artifacts."""
    return CompiledArtifacts(
        metadata={"compiled_at": "2024-01-01", "floe_core_version": "0.1.0", "source_hash": "abc"},
        compute=ComputeConfig(**kwargs),
        transforms=[],
        observability={},
    )
```

### 3.3 Property-Based Testing

```python
# tests/unit/floe_core/test_compiler_properties.py
from hypothesis import given, strategies as st
from floe_core.compiler import Compiler
from floe_core.schemas import FloeSpec

class TestCompilerProperties:
    """Property-based tests for compiler."""

    @given(
        name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        version=st.sampled_from(["1.0", "1.1", "2.0"]),
    )
    def test_compile_produces_valid_artifacts(self, name: str, version: str):
        """Compiling any valid spec should produce valid artifacts."""
        spec = FloeSpec(
            name=name.strip(),
            version=version,
            compute={"target": "duckdb"},
        )

        compiler = Compiler()
        artifacts = compiler.compile_spec(spec)

        # Artifacts should always contain the original spec values
        assert artifacts.compute.target.value == "duckdb"

    @given(st.binary())
    def test_invalid_yaml_raises_error(self, data: bytes):
        """Invalid YAML should raise ConfigurationError."""
        from floe_core.errors import ConfigurationError

        compiler = Compiler()
        try:
            compiler.compile_bytes(data)
            # If no error, data happened to be valid YAML + valid spec
        except ConfigurationError:
            pass  # Expected
        except Exception as e:
            pytest.fail(f"Unexpected exception type: {type(e)}")
```

---

## 4. Integration Testing

### 4.1 Test Containers

```python
# tests/integration/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def postgres():
    """PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture(scope="session")
def compose_stack():
    """Full Docker Compose stack for integration tests."""
    with DockerCompose(
        filepath="tests/integration",
        compose_file_name="docker-compose.test.yml",
        pull=True,
    ) as compose:
        compose.wait_for("http://localhost:3000/health")
        yield compose
```

### 4.2 Integration Test Examples

```python
# tests/integration/test_dagster_assets.py
import pytest
from dagster import materialize
from floe_dagster.asset_factory import create_definitions
from floe_core.schemas import CompiledArtifacts

class TestDagsterAssets:
    """Integration tests for Dagster asset creation."""

    def test_dbt_assets_created(self, temp_dbt_project):
        """dbt models should be converted to Dagster assets."""
        artifacts = CompiledArtifacts(
            dbt_project_path=str(temp_dbt_project),
            dbt_manifest_path=str(temp_dbt_project / "target/manifest.json"),
            compute={"target": "duckdb"},
            transforms=[{"type": "dbt", "path": "models/"}],
            observability={},
        )

        defs = create_definitions(artifacts)

        # Should have assets for each dbt model
        asset_keys = [a.key for a in defs.get_all_asset_specs()]
        assert len(asset_keys) > 0

    def test_assets_execute_successfully(self, temp_dbt_project, duckdb_path):
        """Assets should execute without errors."""
        artifacts = create_test_artifacts(temp_dbt_project, duckdb_path)
        defs = create_definitions(artifacts)

        result = materialize(
            defs.get_all_asset_specs(),
            resources=defs.resources,
        )

        assert result.success
```

```python
# tests/integration/test_full_pipeline.py
import pytest
from pathlib import Path
from floe_cli.commands.run import execute_pipeline

class TestFullPipeline:
    """Integration tests for full pipeline execution."""

    @pytest.fixture
    def sample_project(self, tmp_path) -> Path:
        """Create a sample project for testing."""
        # Create floe.yaml
        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text("""
name: test-pipeline
version: "1.0"
compute:
  target: duckdb
  properties:
    path: ./test.duckdb
transforms:
  - type: dbt
    path: models/
""")

        # Create dbt project
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "test_model.sql").write_text("""
SELECT 1 as id, 'test' as name
""")

        # Create dbt_project.yml
        (tmp_path / "dbt_project.yml").write_text("""
name: test_project
version: "1.0"
profile: floe
""")

        return tmp_path

    def test_pipeline_runs_successfully(self, sample_project):
        """Full pipeline should execute without errors."""
        result = execute_pipeline(
            config_path=sample_project / "floe.yaml",
            environment="dev",
        )

        assert result.success
        assert (sample_project / "test.duckdb").exists()
```

---

## 5. End-to-End Testing

### 5.1 E2E Test Structure

```python
# tests/e2e/test_workflows.py
import pytest
import subprocess
from pathlib import Path

class TestCLIWorkflows:
    """End-to-end tests for CLI workflows."""

    def test_init_validate_run_workflow(self, tmp_path):
        """Test complete init → validate → run workflow."""

        # 1. Initialize project
        result = subprocess.run(
            ["floe", "init", "test-project"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        project_path = tmp_path / "test-project"
        assert project_path.exists()

        # 2. Validate configuration
        result = subprocess.run(
            ["floe", "validate"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "valid" in result.stdout.lower()

        # 3. Run pipeline
        result = subprocess.run(
            ["floe", "run", "--env", "dev"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0

    def test_dev_environment_starts(self, tmp_path, sample_project):
        """Test that dev environment starts correctly."""
        import requests
        import time

        # Start dev environment in background
        proc = subprocess.Popen(
            ["floe", "dev"],
            cwd=sample_project,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Wait for services to start
            time.sleep(30)

            # Check Dagster is accessible
            response = requests.get("http://localhost:3000/health")
            assert response.status_code == 200

        finally:
            proc.terminate()
            proc.wait(timeout=10)
```

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install ruff mypy

      - name: Lint with ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy floe_core floe_cli floe_dagster floe_dbt

  test-unit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=floe_core --cov=floe_cli --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: coverage.xml

  test-integration:
    runs-on: ubuntu-latest
    needs: [lint, test-unit]
    # Integration tests run inside Docker for reliable hostname resolution
    # (localstack, polaris, etc. only resolve inside Docker network)
    steps:
      - uses: actions/checkout@v4

      - name: Start Docker infrastructure
        working-directory: testing/docker
        run: docker compose --profile full up -d

      - name: Wait for polaris-init to complete
        working-directory: testing/docker
        run: |
          echo "Waiting for polaris-init to complete..."
          timeout 60 bash -c 'until docker inspect -f "{{.State.Status}}" floe-polaris-init 2>/dev/null | grep -q "exited"; do sleep 2; done'

      - name: Wait for all services
        run: |
          echo "Waiting for Polaris..."
          timeout 120 bash -c 'until curl -sf http://localhost:8181/api/catalog/v1/config; do sleep 2; done'
          echo "Waiting for Cube..."
          timeout 120 bash -c 'until curl -sf http://localhost:4000/readyz; do sleep 2; done'
          echo "All services ready"

      - name: Build test-runner container
        working-directory: testing/docker
        run: docker compose --profile full --profile test build test-runner

      - name: Run integration tests inside Docker
        working-directory: testing/docker
        run: |
          docker compose --profile full --profile test run --rm test-runner \
            uv run pytest packages/*/tests/integration/ -v --tb=short

      - name: Show Docker logs on failure
        if: failure()
        working-directory: testing/docker
        run: docker compose --profile full logs --tail=100

      - name: Stop Docker infrastructure
        if: always()
        working-directory: testing/docker
        run: docker compose --profile full down -v

  test-e2e:
    runs-on: ubuntu-latest
    needs: [test-integration]
    # E2E tests also run inside Docker for consistency
    steps:
      - uses: actions/checkout@v4

      - name: Start Docker infrastructure
        working-directory: testing/docker
        run: docker compose --profile full up -d

      - name: Build test-runner container
        working-directory: testing/docker
        run: docker compose --profile full --profile test build test-runner

      - name: Run E2E tests inside Docker
        working-directory: testing/docker
        run: |
          docker compose --profile full --profile test run --rm test-runner \
            uv run pytest packages/*/tests/e2e/ -v --timeout=600

      - name: Stop Docker infrastructure
        if: always()
        working-directory: testing/docker
        run: docker compose --profile full down -v

  build-container:
    runs-on: ubuntu-latest
    needs: [test-unit]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build container
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: floe-runtime/dagster:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

  test-platforms:
    runs-on: ${{ matrix.os }}
    needs: [lint]
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install and test CLI
        run: |
          pip install -e .
          floe --version
          floe --help
```

### 6.2 Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - "v*"

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build packages
        run: |
          pip install build
          python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}

  build-and-push-container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          platforms: linux/amd64,linux/arm64
          tags: |
            ghcr.io/floe-runtime/dagster:${{ github.ref_name }}
            ghcr.io/floe-runtime/dagster:latest
```

---

## 7. Code Quality Standards

### 7.1 Style Guide

| Tool | Config | Purpose |
|------|--------|---------|
| **ruff** | pyproject.toml | Linting, formatting |
| **mypy** | pyproject.toml | Type checking |
| **pre-commit** | .pre-commit-config.yaml | Git hooks |

### 7.2 pyproject.toml Configuration

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "dagster.*"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.coverage.run]
branch = true
source = ["floe_core", "floe_cli", "floe_dagster", "floe_dbt"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### 7.3 Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: detect-private-key

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: mypy
        language: system
        types: [python]
        pass_filenames: false
        args: [floe_core, floe_cli, floe_dagster, floe_dbt]
```

---

## 8. Documentation Standards

### 8.1 Docstring Format

```python
def compile_spec(
    self,
    spec_path: Path,
    *,
    validate: bool = True,
) -> CompiledArtifacts:
    """Compile a floe.yaml specification to CompiledArtifacts.

    Args:
        spec_path: Path to the floe.yaml file.
        validate: Whether to validate the spec before compilation.
            Defaults to True.

    Returns:
        The compiled artifacts ready for runtime execution.

    Raises:
        ConfigurationError: If the spec is invalid.
        FileNotFoundError: If spec_path does not exist.

    Example:
        >>> compiler = Compiler()
        >>> artifacts = compiler.compile_spec(Path("floe.yaml"))
        >>> print(artifacts.compute.target)
        duckdb
    """
```

### 8.2 README Requirements

Each package must have a README with:

1. **Description**: What the package does
2. **Installation**: How to install
3. **Quick Start**: Minimal example
4. **API Reference**: Link to docs
5. **Contributing**: Link to guidelines
