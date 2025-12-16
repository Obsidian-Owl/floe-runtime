# Research: Core Foundation Package (floe-core)

**Feature**: 001-core-foundation
**Date**: 2025-12-15
**Status**: Complete

## Executive Summary

All technical unknowns resolved. floe-core will use:
- Pydantic v2.12.5 with `ConfigDict(frozen=True, extra="forbid")` for immutable contracts
- `@field_validator` with regex pattern for secret reference validation
- `model_json_schema()` for JSON Schema Draft 2020-12 export
- Discriminated unions for compute target-specific properties
- Direct JSON parsing of dbt manifest.json for classification extraction

---

## Research Topic 1: Pydantic v2 Immutable Configuration Models

### Decision
Use Pydantic v2 with `ConfigDict(frozen=True, extra="forbid")` for all contract models.

### Rationale
- **Immutability** (`frozen=True`): Prevents accidental mutations to CompiledArtifacts after compilation, ensuring contract stability for downstream packages
- **Strict validation** (`extra="forbid"`): Rejects unknown fields, catching contract drift early and enforcing 3-version backward compatibility policy
- **Pydantic 2.12.5** confirmed installed: Full v2 syntax support (`@field_validator`, `model_config`, `model_json_schema()`)

### Alternatives Considered
1. **`frozen=False`**: Rejected - allows mutation which would break contract guarantees
2. **`extra="allow"`**: Rejected - would allow undocumented fields to creep into contracts
3. **Dataclasses**: Rejected - lacks validation, JSON Schema export, and pydantic-settings integration

### Code Pattern
```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

class CompiledArtifacts(BaseModel):
    """Immutable contract - all downstream packages depend on this schema."""
    model_config = ConfigDict(
        frozen=True,      # Immutable after creation
        extra="forbid",   # Reject unknown fields
        validate_assignment=True,  # Validate on any assignment attempt
    )

    version: str = Field(default="1.0.0", description="Contract version (semver)")
    # ... other fields
```

---

## Research Topic 2: Secret Reference Validation

### Decision
Use `@field_validator` with regex pattern matching Kubernetes secret naming convention: alphanumeric, hyphens, underscores, 1-253 characters.

### Rationale
- **Kubernetes compatibility**: Secret references will resolve to K8s secrets at runtime
- **Validation only, no resolution**: floe-core validates format; downstream packages resolve secrets
- **Clarification confirmed**: User specified K8s naming convention in clarification session

### Alternatives Considered
1. **No validation**: Rejected - invalid secret names would fail at runtime with unclear errors
2. **Pydantic `constr()`**: Rejected - less readable than explicit validator with custom error message
3. **DNS-1123 subdomain format**: More restrictive than needed; K8s secrets allow underscores

### Code Pattern
```python
import re
from pydantic import field_validator

SECRET_REF_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$")

class ComputeConfig(BaseModel):
    connection_secret_ref: str | None = None

    @field_validator("connection_secret_ref")
    @classmethod
    def validate_secret_ref(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not SECRET_REF_PATTERN.match(v):
            raise ValueError(
                f"Secret reference '{v}' must be alphanumeric with hyphens/underscores, "
                "1-253 characters, starting with alphanumeric"
            )
        return v
```

---

## Research Topic 3: JSON Schema Export for IDE Autocomplete

### Decision
Use `model_json_schema()` with explicit `$schema` URI for JSON Schema Draft 2020-12.

### Rationale
- **Pydantic v2 default**: Generates Draft 2020-12 by default (per API-REFERENCE.md)
- **VS Code YAML extension**: Requires `$schema` directive in YAML file pointing to schema URL/file
- **Field descriptions**: Automatically included from `Field(description=...)` annotations

### Alternatives Considered
1. **Manual JSON Schema**: Rejected - error-prone, falls out of sync with models
2. **OpenAPI 3.0 schema**: Rejected - uses Draft 7, not as feature-rich as 2020-12
3. **JSON Schema Draft 7**: Rejected - older, fewer features for discriminated unions

### Code Pattern
```python
from pathlib import Path
import json

def export_floe_spec_schema(output_path: Path) -> None:
    """Export FloeSpec JSON Schema for IDE autocomplete."""
    schema = FloeSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://floe.dev/schemas/floe.schema.json"

    output_path.write_text(json.dumps(schema, indent=2))

# In floe.yaml users add:
# $schema: https://floe.dev/schemas/floe.schema.json
# OR for local development:
# $schema: ./schemas/floe.schema.json
```

---

## Research Topic 4: Discriminated Unions for Compute Targets

### Decision
Use `Literal` type discriminator with target-specific property models.

### Rationale
- **Type safety**: Each compute target has distinct properties (DuckDB: path, Snowflake: account/warehouse)
- **JSON Schema support**: Pydantic generates proper `anyOf` schemas with discriminator
- **Extensibility**: New targets added by creating new property model classes

### Alternatives Considered
1. **Single `dict[str, Any]` properties**: Rejected - loses type safety and IDE support
2. **Generic `Dict` with validation**: Rejected - no per-target validation
3. **Inheritance hierarchy**: Rejected - overly complex for simple property bags

### Code Pattern
```python
from typing import Literal
from pydantic import BaseModel, Field

class DuckDBProperties(BaseModel):
    path: str = Field(default=":memory:", description="Database path")
    extensions: list[str] = Field(default_factory=list)

class SnowflakeProperties(BaseModel):
    account: str = Field(..., description="Snowflake account identifier")
    warehouse: str = Field(..., description="Virtual warehouse name")
    role: str | None = None
    database: str | None = None
    schema_: str | None = Field(default=None, alias="schema")

class ComputeConfig(BaseModel):
    target: Literal["duckdb", "snowflake", "bigquery", "redshift", "databricks", "postgres", "spark"]
    connection_secret_ref: str | None = None
    properties: DuckDBProperties | SnowflakeProperties | BigQueryProperties | ... = Field(default_factory=dict)
```

---

## Research Topic 5: dbt Manifest.json Classification Extraction

### Decision
Parse `target/manifest.json` directly with standard `json` module, extracting column-level `meta` tags with `floe:` namespace.

### Rationale
- **dbt owns SQL**: We extract metadata from manifest, never parse SQL (per Technology Ownership principle)
- **Standard location**: dbt generates manifest at `target/manifest.json` after `dbt compile` or `dbt run`
- **Column meta structure**: Available under `nodes.{model_id}.columns.{col_name}.meta`

### Alternatives Considered
1. **dbt Python API**: Rejected - overly complex, adds heavy dependency
2. **dagster-dbt manifest parsing**: Rejected - we need column-level meta, not just model metadata
3. **External metadata file**: Rejected - breaks single-source-of-truth (dbt meta tags)

### Code Pattern
```python
import json
from pathlib import Path
from typing import Any

def extract_classifications(
    manifest_path: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Extract column classifications from dbt manifest.json.

    Returns:
        Nested dict: model_name -> column_name -> {classification, pii_type, sensitivity}
    """
    if not manifest_path.exists():
        # Graceful skip per edge case requirement
        return {}

    manifest = json.loads(manifest_path.read_text())
    classifications: dict[str, dict[str, dict[str, Any]]] = {}

    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue

        model_name = node.get("name", "")
        columns = node.get("columns", {})

        for col_name, col_info in columns.items():
            meta = col_info.get("meta", {})
            floe_meta = {k.replace("floe.", ""): v for k, v in meta.items() if k.startswith("floe.")}

            if "classification" in floe_meta:
                if model_name not in classifications:
                    classifications[model_name] = {}
                classifications[model_name][col_name] = {
                    "classification": floe_meta["classification"],
                    "pii_type": floe_meta.get("pii_type"),
                    "sensitivity": floe_meta.get("sensitivity", "medium"),
                }

    return classifications
```

### dbt Model Meta Tag Example
```yaml
# models/customers.yml
models:
  - name: customers
    columns:
      - name: email
        meta:
          floe.classification: pii
          floe.pii_type: email
          floe.sensitivity: high
      - name: customer_id
        meta:
          floe.classification: identifier
```

---

## Research Topic 6: Exception Hierarchy Design

### Decision
Three-level hierarchy: `FloeError` (base) → `ValidationError`, `CompilationError` with user-friendly messages and internal logging.

### Rationale
- **Separation of concerns**: User messages are generic; technical details logged internally
- **Security**: No file paths, stack traces, or internal state exposed to users (per Security First principle)
- **Structured logging**: Use structlog for JSON-formatted internal logs

### Alternatives Considered
1. **Single exception class**: Rejected - can't distinguish validation vs compilation failures
2. **Pydantic ValidationError passthrough**: Rejected - exposes internal field names and paths
3. **Exception chaining only**: Rejected - still risks exposing internal details

### Code Pattern
```python
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class FloeError(Exception):
    """Base exception for floe-runtime.

    All floe exceptions inherit from this class. User-facing messages
    are safe to display; technical details are logged internally.
    """

    def __init__(self, user_message: str, *, internal_details: str | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        if internal_details:
            logger.error(
                "floe_error",
                error_type=self.__class__.__name__,
                user_message=user_message,
                internal_details=internal_details,
            )


class ValidationError(FloeError):
    """Raised when configuration validation fails."""
    pass


class CompilationError(FloeError):
    """Raised when compilation fails."""
    pass
```

---

## Dependencies Confirmed

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.12.5 | Schema validation, JSON Schema export |
| pydantic-settings | 2.6+ | Environment variable configuration |
| pyyaml | 6.0+ | YAML parsing (safe_load) |
| structlog | 24.4+ | Structured logging |

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Pydantic version? | 2.12.5 confirmed |
| Secret ref format? | K8s naming: alphanumeric, hyphens/underscores, 1-253 chars |
| JSON Schema draft? | 2020-12 (Pydantic v2 default) |
| Backward compatibility? | 3 versions (per clarification) |
| dbt manifest location? | `target/manifest.json` |
| Classification namespace? | `floe.` prefix in meta tags |

---

## Next Steps

1. **Phase 1**: Generate `data-model.md` with entity definitions
2. **Phase 1**: Generate `contracts/` with JSON Schema files
3. **Phase 1**: Generate `quickstart.md` with usage examples
4. **Phase 2**: Generate `tasks.md` via `/speckit.tasks`
