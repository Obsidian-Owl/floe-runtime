# floe-runtime Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-18

## Active Technologies
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Pydantic v2, pydantic-settings, PyYAML, structlog (001-core-foundation)
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts) (002-cli-interface)
- File-based (floe.yaml input, compiled_artifacts.json output to `.floe/`) (002-cli-interface)
- File-based (profiles.yml generated to `.floe/profiles/`, reads dbt manifest.json) (003-orchestration-layer)
- Apache Iceberg tables via Polaris REST catalog (file-based metadata, Parquet data files) (004-storage-catalog)
- PyIceberg 0.9+ for Iceberg table operations (004-storage-catalog)
- Apache Polaris REST catalog for Iceberg metadata management (004-storage-catalog)
- File-based configuration generation (.floe/cube/), S3 for pre-aggregations (005-consumption-layer)
- Python 3.10+ (Dagster/dbt minimum), Helm 3.x, Docker + Dagster 1.6+, dbt-core 1.7+, Cube v0.36+, Helm, Docker, ArgoCD/Flux (007-deployment-automation)
- Iceberg tables (via Polaris REST catalog), PostgreSQL (Dagster metadata), S3/GCS/ADLS (object storage) (007-deployment-automation)

## Project Structure

```text
packages/
├── floe-cli/        # CLI entry point (Click + Rich)
├── floe-core/       # Schemas, validation, compilation (Pydantic)
├── floe-cube/       # Semantic layer (Cube integration)
├── floe-dagster/    # Orchestration, assets (Dagster)
├── floe-dbt/        # SQL transformations (dbt)
├── floe-iceberg/    # Storage layer (PyIceberg)
└── floe-polaris/    # Catalog management (Polaris REST)

testing/
├── docker/          # E2E test infrastructure (Docker Compose)
│   ├── docker-compose.yml
│   ├── Dockerfile.test-runner
│   ├── scripts/
│   │   └── run-integration-tests.sh
│   ├── init-scripts/
│   ├── trino-config/
│   ├── cube-schema/
│   └── README.md
└── fixtures/        # Shared test fixtures
    ├── artifacts.py # CompiledArtifacts factories
    └── services.py  # Docker service lifecycle
```

## Commands

### Test Execution Model (CRITICAL)

**ALL tests run in Docker** for consistent hostname resolution and reliable execution.

| Command | Description |
|---------|-------------|
| `make test` | Run ALL tests (unit + integration) in Docker |
| `make test-unit` | Run unit tests only (no Docker required, fast) |
| `make test-integration` | Run integration tests only in Docker |

```bash
# Run ALL tests (recommended)
make test

# Or directly via script
./testing/docker/scripts/run-all-tests.sh

# Run specific tests
./testing/docker/scripts/run-all-tests.sh -k "test_append"
./testing/docker/scripts/run-all-tests.sh -v --tb=short
```

**Why Docker?** Integration tests require Docker network for hostname resolution
(localstack, polaris, etc.). Running ALL tests in Docker ensures consistency.

### Code Quality

```bash
# Linting
uv run ruff check packages/

# Type checking
uv run mypy --strict packages/
```

## Code Style

Python 3.10+ (per Constitution: Dagster/dbt minimum): Follow standard conventions

## SonarQube Quality Gates

This project enforces SonarQube Quality Gate on all PRs. Common issues to avoid:

| Rule | Severity | Prevention |
|------|----------|------------|
| S6437 | BLOCKER | Never hardcode secrets - use `os.environ.get()` |
| S1192 | CRITICAL | Extract duplicate strings (3+) to module constants |
| S1244 | MAJOR | Use `pytest.approx()` for float comparison |
| S108 | MAJOR | No empty code blocks - add content or remove |
| S5727 | CRITICAL | Don't assert `is not None` on non-nullable values |
| S1481 | MINOR | Remove unused variables or prefix with `_` |

See `.claude/rules/sonarqube-quality.md` for comprehensive guidance.

## Packages

### floe-polaris (004-storage-catalog)
- `PolarisCatalog`: Thread-safe catalog wrapper with retry logic
- `PolarisConfig`: Pydantic configuration for Polaris connection
- Observability: structlog logging, OTel tracing support
- Integration tests: `pytest -m integration packages/floe-polaris/tests/`

### floe-iceberg (004-storage-catalog)
- `IcebergTableManager`: Table creation, schema evolution, data operations
- `IcebergIOManager`: Dagster IOManager for Iceberg table assets
- Arrow/Polars/Pandas DataFrame support
- Integration tests: `pytest -m integration packages/floe-iceberg/tests/`

## Test Infrastructure

### Zero-Config Integration Tests

The recommended way to run integration tests is via the test runner script:

```bash
# Run all integration tests (62 tests total)
./testing/docker/scripts/run-integration-tests.sh
```

This script:
1. Starts test infrastructure (LocalStack, Polaris)
2. Waits for Polaris initialization to complete
3. Loads dynamically-generated credentials
4. Builds and runs tests inside Docker network
5. Handles all hostname resolution automatically

### Docker Compose Profiles

Docker Compose profiles for local testing:
- `(none)`: PostgreSQL, Jaeger (unit tests, dbt-postgres)
- `storage`: + LocalStack (S3+STS+IAM), Polaris, polaris-init (62 Iceberg storage tests)
- `compute`: + Trino 479, Spark (compute engine tests)
- `full`: + Cube v0.36, cube-init, Marquez (21 Cube tests, semantic layer)

```bash
# Manual service startup (if needed)
cd testing/docker
docker compose --profile storage up -d

# Check service health
curl http://localhost:8181/api/catalog/v1/config  # Polaris
curl http://localhost:4566/_localstack/health     # LocalStack
curl http://localhost:4000/readyz                 # Cube
```

### floe-cube (005-consumption-layer)
- `CubeConfig`: Pydantic configuration for Cube connection
- `CubeRESTClient`: REST API client for Cube queries
- Integration tests: 21 tests (T036-T039)
- Pre-aggregations: Uses `external: false` for Trino storage (GCS not available)

## Recent Changes
- 007-deployment-automation: Added Python 3.10+ (Dagster/dbt minimum), Helm 3.x, Docker + Dagster 1.6+, dbt-core 1.7+, Cube v0.36+, Helm, Docker, ArgoCD/Flux
- 005-consumption-layer: Added floe-cube with 21 integration tests passing
- 005-consumption-layer: Cube pre-aggregations using internal Trino storage


<!-- MANUAL ADDITIONS START -->

# Floe Runtime: Open-Source Data Execution Layer

## Architecture Documentation (via @import)

@../../docs/00-overview.md
@../../docs/01-constraints.md
@../../docs/03-solution-strategy.md
@../../docs/04-building-blocks.md
@../../docs/10-glossary.md
@../../docs/adr/0001-cube-semantic-layer.md

---

## CRITICAL: Enterprise Development Standards

### Runtime Environment Verification

**YOU MUST verify Python version and dependencies before implementing:**

```bash
# Check Python version (3.10+ required)
python --version

# Verify core dependencies
python -c "import pydantic; print(f'Pydantic {pydantic.__version__}')"
python -c "import dagster; print(f'Dagster {dagster.__version__}')"
```

---

## CRITICAL: Standalone-First Philosophy

**MOST IMPORTANT**: Every feature in floe-runtime MUST work without requiring the Floe SaaS Control Plane.

- ❌ **NEVER** assume Control Plane availability
- ❌ **NEVER** hardcode SaaS endpoints or proprietary integrations
- ❌ **NEVER** make features dependent on SaaS-only capabilities
- ✅ **ALWAYS** implement features that work standalone
- ✅ **ALWAYS** use standard open formats (Iceberg, OpenLineage, OTel)
- ✅ **ALWAYS** verify examples run without SaaS dependencies

The Control Plane is an **optional value-add**, not a requirement.

---

## CRITICAL: Type Safety & Pydantic Standards

### Pydantic Usage (NON-NEGOTIABLE)

**YOU MUST use Pydantic for ALL data validation and configuration:**

1. **Configuration Models**: ALL configuration MUST be Pydantic models
   ```python
   from __future__ import annotations

   from pydantic import BaseModel, Field, field_validator
   from pydantic_settings import BaseSettings

   class FloeConfig(BaseSettings):
       """Floe configuration with strict validation."""
       project_name: str = Field(..., min_length=1, max_length=100)
       python_version: str = Field(default="3.10", pattern=r"^3\.(10|11|12)$")

       @field_validator("project_name")
       @classmethod
       def validate_project_name(cls, v: str) -> str:
           if not v.replace("-", "").replace("_", "").isalnum():
               raise ValueError("Project name must be alphanumeric")
           return v
   ```

2. **API Request/Response**: ALL API contracts MUST use Pydantic
   ```python
   from pydantic import BaseModel, ConfigDict

   class CompiledArtifacts(BaseModel):
       """Contract between floe-core and floe-dagster."""
       model_config = ConfigDict(frozen=True, extra="forbid")

       version: str
       dbt_profiles: dict[str, Any]
       dagster_config: dict[str, Any]
   ```

3. **CLI Arguments**: Use Pydantic for argument validation
   ```python
   from pydantic import BaseModel, Field

   class ValidateCommand(BaseModel):
       """Validate command arguments."""
       file_path: Path = Field(..., exists=True)
       strict: bool = Field(default=True)
   ```

4. **Environment Variables**: Use `pydantic-settings`
   ```python
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class Settings(BaseSettings):
       model_config = SettingsConfigDict(
           env_prefix="FLOE_",
           env_file=".env",
           extra="ignore"
       )

       database_url: str
       log_level: str = "INFO"
   ```

**IMPORTANT**: Pydantic v2 syntax only - use `@field_validator`, `model_config`, `model_json_schema()`

---

## CRITICAL: Type Hints Everywhere

**YOU MUST include type hints on ALL functions, methods, and variables:**

```python
from __future__ import annotations  # REQUIRED at top of every .py file

from typing import Any
from pathlib import Path

def compile_floe_spec(
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
        CompiledArtifacts containing dbt profiles, Dagster config

    Raises:
        ValidationError: If spec validation fails
        CompilationError: If compilation fails
    """
    artifacts: dict[str, Any] = {}
    profile_path: Path = Path("profiles.yml")
    # ...
    return CompiledArtifacts(**artifacts)
```

**Type checking requirements:**
- Run `mypy --strict` on all code
- No `Any` types except when interfacing with untyped third-party libraries
- Use `typing.Protocol` for structural typing
- Use generics (`list[str]`, `dict[str, int]`) not old-style (`List[str]`)

---

## CRITICAL: Security Standards

### Input Validation

**YOU MUST validate ALL user input - NEVER trust external data:**

```python
from pydantic import BaseModel, Field, field_validator

class UserInput(BaseModel):
    """ALWAYS validate user input with Pydantic."""
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    age: int = Field(..., ge=0, le=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()
```

### Dangerous Constructs (FORBIDDEN)

**NEVER use these dangerous Python constructs:**

- ❌ `eval()` - code injection vulnerability
- ❌ `exec()` - code injection vulnerability
- ❌ `__import__()` - use `importlib` instead
- ❌ `pickle.loads()` on untrusted data - deserialization vulnerability
- ❌ Raw SQL strings - use parameterized queries
- ❌ `shell=True` in subprocess - command injection vulnerability

```python
# ❌ FORBIDDEN
user_input = request.get("code")
eval(user_input)  # NEVER DO THIS

# ✅ CORRECT - Validate with Pydantic
from pydantic import BaseModel, field_validator

class CodeInput(BaseModel):
    expression: str

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v: str) -> str:
        # Validate against whitelist
        if not all(c in "0123456789+-*/(). " for c in v):
            raise ValueError("Invalid characters in expression")
        return v
```

### Secret Management

**YOU MUST handle secrets securely:**

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class DatabaseConfig(BaseSettings):
    """Secrets MUST use SecretStr."""
    database_url: SecretStr  # Not str!
    api_key: SecretStr

    def get_connection_string(self) -> str:
        """Reveal secret only when needed."""
        return self.database_url.get_secret_value()

# ❌ NEVER log secrets
logger.info(f"API key: {config.api_key}")  # FORBIDDEN

# ✅ Log without exposing secrets
logger.info("Database configured successfully")
```

**Secret handling rules:**
- Use `.env` files (NEVER commit to git)
- Use environment variables in production
- Use `SecretStr` for password fields
- NEVER log secrets or PII
- Mask secrets in error messages

---

## CRITICAL: Error Handling

### Exception Handling Standards

**YOU MUST handle errors properly - NEVER expose internals to users:**

```python
from typing import NoReturn
import logging

logger = logging.getLogger(__name__)

class FloeError(Exception):
    """Base exception for floe-runtime."""
    pass

class ValidationError(FloeError):
    """Validation failed."""
    pass

class CompilationError(FloeError):
    """Compilation failed."""
    pass

def compile_spec(spec_path: Path) -> CompiledArtifacts:
    """Compile floe.yaml with proper error handling."""
    try:
        spec = FloeSpec.parse_file(spec_path)
        return compile_floe_spec(spec)
    except FileNotFoundError:
        # Log technical details internally
        logger.error(f"Spec file not found: {spec_path}", exc_info=True)
        # Show generic message to user
        raise CompilationError(f"Configuration file not found: {spec_path.name}")
    except pydantic.ValidationError as e:
        # Log full error internally
        logger.error(f"Validation failed: {e}", exc_info=True)
        # Show user-friendly message
        raise ValidationError(f"Invalid configuration in {spec_path.name}")
    except Exception as e:
        # Log unexpected errors
        logger.exception("Unexpected error during compilation")
        # Generic message to user (no technical details!)
        raise CompilationError("Compilation failed - check logs for details")
```

**Error handling rules:**
- Catch specific exceptions (not bare `except:`)
- Log technical details internally with `logger.exception()`
- Return generic error messages to users
- NEVER expose stack traces, file paths, or internals to end users
- Use custom exception hierarchy

---

## CRITICAL: Logging Standards

### Structured Logging

**YOU MUST use structured logging with trace context:**

```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

def process_pipeline(pipeline_id: str) -> None:
    """Process pipeline with structured logging."""
    log = logger.bind(pipeline_id=pipeline_id)

    log.info("pipeline_started")

    try:
        # Process pipeline
        log.info("pipeline_completed", duration_ms=1234)
    except Exception as e:
        log.error("pipeline_failed", error=str(e))
        raise
```

**Logging rules:**
- Use structured logging (JSON format)
- Include trace IDs and correlation IDs
- NEVER log secrets, passwords, API keys, PII
- Mask sensitive data in logs
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include context (pipeline_id, user_id, etc.)

### What NOT to Log

**FORBIDDEN in logs:**
- ❌ Passwords, API keys, tokens
- ❌ PII (email, phone, SSN, address)
- ❌ Credit card numbers
- ❌ Session tokens
- ❌ Full SQL queries with user data
- ❌ Raw exception messages in production (log internally only)

```python
# ❌ FORBIDDEN
logger.info(f"User email: {user.email}")  # PII exposure
logger.info(f"API key: {api_key}")  # Secret exposure

# ✅ CORRECT
logger.info("User authenticated", user_id=user.id)
logger.info("API configured successfully")
```

---

## CRITICAL: Testing Requirements

### Test Coverage

**YOU MUST achieve > 80% code coverage:**

```python
import pytest
from hypothesis import given, strategies as st

def test_compile_spec_valid():
    """Test successful compilation."""
    spec = FloeSpec(
        name="test-project",
        version="1.0.0",
        transforms=[...],
    )

    artifacts = compile_floe_spec(spec)

    assert artifacts.version == spec.version
    assert "dbt_profiles" in artifacts.model_dump()

def test_compile_spec_invalid():
    """Test validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        FloeSpec(name="", version="invalid")

    assert "name" in str(exc_info.value)

@given(st.text(min_size=1, max_size=100))
def test_project_name_validation(name: str):
    """Property-based test for project names."""
    if name.replace("-", "").replace("_", "").isalnum():
        spec = FloeSpec(name=name, version="1.0.0")
        assert spec.name == name
```

**Testing standards:**
- Unit tests: Fast, isolated, mock external dependencies
- Integration tests: Test component interactions with testcontainers
- Property-based tests: Use `hypothesis` for edge cases
- Contract tests: Validate API contracts
- > 80% coverage required
- **Tests FAIL, never skip** - see below

### Tests FAIL, Never Skip (MANDATORY)

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

---

## CRITICAL: Code Quality Standards

### Python Conventions (MANDATORY)

**YOU MUST follow these conventions:**

1. **Formatting**: Black (100 char line length)
   ```bash
   black --line-length 100 .
   ```

2. **Import sorting**: isort
   ```bash
   isort .
   ```

3. **Type checking**: mypy strict mode
   ```bash
   mypy --strict packages/
   ```

4. **Linting**: ruff
   ```bash
   ruff check .
   ```

5. **Security scanning**: bandit
   ```bash
   bandit -r packages/
   ```

### Code Organization

```python
"""Module docstring explaining purpose.

This module implements floe.yaml compilation.
"""

from __future__ import annotations  # REQUIRED

# Standard library imports
import logging
from pathlib import Path
from typing import Any

# Third-party imports
import pydantic
from pydantic import BaseModel, Field

# Local imports
from floe_core.schemas import FloeSpec
from floe_core.errors import CompilationError

# Module constants
DEFAULT_VERSION = "1.0.0"
MAX_RETRIES = 3

# Logger setup
logger = logging.getLogger(__name__)


class Compiler:
    """Compiler class with clear docstrings."""

    def __init__(self, strict: bool = True) -> None:
        """Initialize compiler.

        Args:
            strict: Enable strict validation mode
        """
        self.strict = strict
```

---

## CRITICAL: Dependency Management

### Dependency Auditing

**YOU MUST regularly audit dependencies:**

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
- NEVER use packages with known critical vulnerabilities
- Pure Python only (no compiled extensions)

---

## Contract-Based Architecture

**CompiledArtifacts** is the sole integration contract between components:

- floe.yaml → floe-core Compiler → CompiledArtifacts (JSON)
- CompiledArtifacts contains: dbt profiles, Dagster config, classification rules, target configs
- Contract changes require version bumping (semantic versioning)
- Backward compatibility: 3-version deprecation policy
- Export JSON Schema for validation

**Contract validation:**
```python
from pydantic import BaseModel, ConfigDict

class CompiledArtifacts(BaseModel):
    """Contract between components - NEVER break backward compatibility."""
    model_config = ConfigDict(
        frozen=True,  # Immutable
        extra="forbid",  # No extra fields
    )

    version: str
    dbt_profiles: dict[str, Any]
    dagster_config: dict[str, Any]

    def export_json_schema(self) -> dict[str, Any]:
        """Export JSON Schema for validation."""
        return self.model_json_schema()
```

---

## Package Boundaries

Seven focused packages with clear responsibilities:

```
floe-cli (entry point)
  ├─► floe-core (schemas, validation, compilation)
  ├─► floe-dagster (orchestration, assets)
  ├─► floe-dbt (SQL transformations)
  │    ├─► floe-iceberg (storage)
  │    └─► floe-polaris (catalog)
  └─► floe-cube (consumption APIs)
```

**Key Rules**:
- floe-core defines Pydantic schemas and CompiledArtifacts
- floe-dagster creates assets from CompiledArtifacts
- floe-dbt generates profiles.yml and executes dbt
- dbt **owns SQL** - never parse or validate SQL in Python
- Each package is independently testable

---

## Technology Ownership

- **dbt**: Owns all SQL and SQL dialect translation
- **Dagster**: Owns orchestration and asset management
- **Iceberg**: Owns storage format (ACID, time-travel)
- **Polaris**: Owns catalog management (REST API)
- **Cube**: Owns semantic layer and consumption APIs
- **OpenTelemetry/OpenLineage**: Owns observability and lineage
- **Pydantic**: Owns ALL data validation and configuration

---

## Documentation Standards

### Google-Style Docstrings (REQUIRED)

```python
def compile_floe_spec(
    spec: FloeSpec,
    target: str | None = None,
    strict: bool = True
) -> CompiledArtifacts:
    """Compile FloeSpec into CompiledArtifacts.

    This function validates the FloeSpec and generates all artifacts
    needed for pipeline execution including dbt profiles and Dagster config.

    Args:
        spec: Validated FloeSpec from floe.yaml. Must pass Pydantic validation.
        target: Optional compute target override (e.g., "snowflake", "bigquery").
            Defaults to spec.default_target if not provided.
        strict: Enable strict validation mode. When True, raises on warnings.
            When False, logs warnings but continues.

    Returns:
        CompiledArtifacts containing:
            - dbt_profiles: Generated dbt profiles.yml content
            - dagster_config: Dagster pipeline configuration
            - metadata: Compilation metadata and timestamps

    Raises:
        ValidationError: If spec validation fails or required fields missing.
        CompilationError: If artifact generation fails.
        TargetNotFoundError: If specified target doesn't exist in spec.

    Examples:
        >>> spec = FloeSpec.parse_file("floe.yaml")
        >>> artifacts = compile_floe_spec(spec)
        >>> artifacts.dbt_profiles["default"]["target"]
        'dev'

        >>> # Override target
        >>> artifacts = compile_floe_spec(spec, target="prod")
        >>> artifacts.dbt_profiles["default"]["target"]
        'prod'
    """
    pass
```

---

## Common Workflows

### Development Workflow

1. **Initialize**: Create floe.yaml with project configuration
2. **Validate**: `floe validate` - check schema compliance
3. **Compile**: `floe compile` - generate CompiledArtifacts
4. **Run**: `floe run` - execute via Dagster orchestration
5. **Test**: Run pytest suite for modified packages

### Contract Validation

When modifying CompiledArtifacts schema:
1. Update Pydantic model in floe-core
2. Export JSON Schema: `model_json_schema()`
3. Validate backward compatibility
4. Update version number (major for breaking, minor for additive)
5. Document changes in CHANGELOG.md

---

## Data Governance

### Classification System

Classifications defined in dbt meta tags (source of truth):

```yaml
# dbt model with classification
models:
  - name: customers
    columns:
      - name: email
        meta:
          floe:
            classification: pii
            pii_type: email
            sensitivity: high
```

---

## Quality Gates (PRE-COMMIT CHECKLIST)

**Before committing, YOU MUST verify:**

- [ ] All type hints present (`mypy --strict` passes)
- [ ] All Pydantic models validated
- [ ] Black formatting applied (100 char)
- [ ] isort applied
- [ ] No secrets in code (`.env` not committed)
- [ ] No `eval()`, `exec()`, or dangerous constructs
- [ ] Error messages don't expose internals
- [ ] Logs don't contain secrets or PII
- [ ] Tests pass with > 80% coverage
- [ ] No security vulnerabilities (`bandit`, `safety`)
- [ ] Standalone verification (no SaaS dependencies)

---

## IMPORTANT: What This Project Is NOT

This is **NOT**:
- ❌ A SaaS-dependent framework (it's standalone-first)
- ❌ A replacement for dbt (dbt is a core component)
- ❌ A proprietary data platform (Apache 2.0 open source)

This **IS**:
- ✅ An open-source data execution layer
- ✅ A type-safe, Pydantic-validated framework
- ✅ A security-first platform (input validation, secret management)
- ✅ An enterprise-grade codebase (80%+ coverage, strict typing)

---

## Quick Reference

| Task | Command | Package |
|------|---------|---------|
| Validate floe.yaml | `floe validate` | floe-cli → floe-core |
| Compile artifacts | `floe compile` | floe-core |
| Type check | `mypy --strict packages/` | all |
| Security scan | `bandit -r packages/` | all |
| Run tests | `pytest --cov=packages` | all |

---

**Remember**:
- Pydantic for ALL data validation
- Type hints EVERYWHERE
- NEVER expose secrets or internals
- > 80% test coverage
- Standalone-first (no SaaS)
- Security-first mindset


<!-- MANUAL ADDITIONS END -->
