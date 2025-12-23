# Pydantic Contracts and Type Safety

## Pydantic for ALL Data Validation

**YOU MUST use Pydantic for ALL data validation and configuration:**

### 1. Configuration Models

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

### 2. API Request/Response Contracts

```python
from pydantic import BaseModel, ConfigDict

class CompiledArtifacts(BaseModel):
    """Contract between floe-core and floe-dagster."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    dbt_profiles: dict[str, Any]
    dagster_config: dict[str, Any]
```

### 3. CLI Arguments

```python
from pydantic import BaseModel, Field

class ValidateCommand(BaseModel):
    """Validate command arguments."""
    file_path: Path = Field(..., exists=True)
    strict: bool = Field(default=True)
```

### 4. Environment Variables

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

## Pydantic v2 Syntax (MANDATORY)

**IMPORTANT**: Pydantic v2 syntax only - use `@field_validator`, `model_config`, `model_json_schema()`

### Field Validators

```python
from pydantic import field_validator

class Model(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """v2 syntax: @field_validator, @classmethod, type hints."""
        return v.lower().strip()
```

### Model Validators

```python
from pydantic import model_validator
from typing import Self

class Model(BaseModel):
    start_date: str
    end_date: str

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """v2 syntax: @model_validator, mode='after', returns Self."""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self
```

### Configuration

```python
from pydantic import BaseModel, ConfigDict

class Model(BaseModel):
    """v2 syntax: model_config = ConfigDict(...)"""
    model_config = ConfigDict(
        frozen=True,
        extra="forbid"
    )
```

### JSON Schema Export

```python
# v2 syntax
schema = Model.model_json_schema()  # NOT .schema()
```

## Contract-Based Architecture

### Two-Tier Configuration Contracts

The two-tier architecture uses three primary contracts:

```python
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from typing import Any

# ============================================================
# PLATFORM TIER (Platform Engineer's Domain)
# ============================================================

class CredentialMode(str, Enum):
    """Supported credential modes."""
    STATIC = "static"           # K8s secret or env var
    OAUTH2 = "oauth2"           # OAuth2 client credentials
    IAM_ROLE = "iam_role"       # AWS IAM role assumption
    SERVICE_ACCOUNT = "service_account"  # GCP/Azure workload identity

class SecretReference(BaseModel):
    """Reference to external secret (K8s or env var)."""
    secret_ref: str = Field(
        description="K8s secret name or env var name",
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"
    )

    def resolve(self) -> str:
        """Resolve secret at runtime (NOT at compile time)."""
        import os
        env_name = self.secret_ref.upper().replace("-", "_")
        if value := os.environ.get(env_name):
            return value
        k8s_path = f"/var/run/secrets/{self.secret_ref}"
        if os.path.exists(k8s_path):
            with open(k8s_path) as f:
                return f.read().strip()
        raise ValueError(f"Secret '{self.secret_ref}' not found")

class CredentialConfig(BaseModel):
    """Credential configuration - secrets MUST use secret_ref."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: CredentialMode = CredentialMode.STATIC
    client_id: str | SecretReference | None = None
    client_secret: SecretReference | None = None  # MUST be secret_ref
    scope: str | None = None
    role_arn: str | None = None

class CatalogProfile(BaseModel):
    """Catalog profile in platform.yaml."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = Field(default="polaris")
    uri: str | SecretReference  # Can also be secret-referenced
    warehouse: str
    credentials: CredentialConfig

class PlatformSpec(BaseModel):
    """Platform configuration - platform.yaml schema."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(default="1.0.0")
    storage: dict[str, Any]  # StorageProfile dict
    catalogs: dict[str, CatalogProfile]
    compute: dict[str, Any]  # ComputeProfile dict

# ============================================================
# PIPELINE TIER (Data Engineer's Domain)
# ============================================================

class FloeSpec(BaseModel):
    """Pipeline configuration - floe.yaml schema."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="Pipeline name")
    version: str = Field(default="1.0.0")
    # Profile references ONLY - no infrastructure details
    catalog: str = Field(default="default")
    storage: str = Field(default="default")
    compute: str = Field(default="default")
    transforms: list[Any]  # TransformConfig list
    observability: Any | None = None

# ============================================================
# COMPILED OUTPUT (Result of merge)
# ============================================================

class CompiledArtifacts(BaseModel):
    """
    PRIMARY CONTRACT between floe-core (compiler) and floe-dagster (runtime).

    This is the sole integration point. Changes require:
    - Major version bump for breaking changes
    - Minor version bump for additive changes
    - 3-version backward compatibility policy
    """
    model_config = ConfigDict(
        frozen=True,  # Immutable - prevent accidental mutation
        extra="forbid",  # Reject unknown fields - strict contract
    )

    version: str = Field(default="2.0.0")  # v2 for two-tier
    metadata: Any  # ArtifactMetadata
    # RESOLVED profiles from platform.yaml
    resolved_catalog: CatalogProfile
    resolved_storage: Any  # StorageProfile
    resolved_compute: Any  # ComputeProfile
    # Pipeline configuration from floe.yaml
    transforms: list[Any]
    observability: Any | None = None
    # Provenance tracking
    platform_source: str | None = None  # e.g., "registry/v1.2.3"
    platform_version: str | None = None

    def export_json_schema(self) -> dict[str, Any]:
        """Export JSON Schema for contract validation."""
        return self.model_json_schema()
```

**Key principle**: Credentials are resolved at **runtime**, not compile time. CompiledArtifacts contains `secret_ref` references, not actual secret values.

### Backward Compatibility

```python
class CompiledArtifactsV1(BaseModel):
    """v1.0.0"""
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = Field(default="1.0.0")
    metadata: dict
    compute: dict

class CompiledArtifactsV1_1(BaseModel):
    """
    v1.1.0 (BACKWARD COMPATIBLE)

    Changes:
    - Added optional 'observability' field
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: str = Field(default="1.1.0")
    metadata: dict
    compute: dict
    observability: Optional[dict] = None  # NEW: Optional (non-breaking)
```

### Contract Versioning

**Rules:**
- **Major version** (2.0.0): Breaking changes (remove field, change type, make field required)
- **Minor version** (1.1.0): Additive changes (add optional field, new enum value)
- **Patch version** (1.0.1): Documentation, internal refactoring (no schema changes)

## Security with Pydantic

### Secret Management

```python
from pydantic import SecretStr, BaseModel

class DatabaseConfig(BaseModel):
    """ALWAYS use SecretStr for passwords/API keys."""
    password: SecretStr  # Not str!
    api_key: SecretStr

    def get_password(self) -> str:
        """Reveal secret only when needed."""
        return self.password.get_secret_value()

# ✅ Secrets are hidden in logs
config = DatabaseConfig(password="secret", api_key="key")
print(config)  # password=SecretStr('**********')
```

### Input Validation

```python
from pydantic import BaseModel, Field, field_validator

class UserInput(BaseModel):
    """Validate ALL user input."""
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    age: int = Field(..., ge=0, le=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()
```

## Testing Pydantic Models

```python
import pytest
from pydantic import ValidationError

def test_model_valid():
    """Test valid model."""
    model = MyModel(field="value")
    assert model.field == "value"

def test_model_invalid():
    """Test validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        MyModel(field="")  # Empty not allowed

    assert "field" in str(exc_info.value)

def test_model_serialization():
    """Test JSON serialization."""
    model = MyModel(field="value")
    json_str = model.model_dump_json()
    loaded = MyModel.model_validate_json(json_str)
    assert loaded == model
```

## JSON Schema Generation

```python
from pathlib import Path
import json

# Export JSON Schema for IDE autocomplete
schema = FloeSpec.model_json_schema()
Path("schemas/floe.schema.json").write_text(
    json.dumps(schema, indent=2)
)

# In floe.yaml, add:
# $schema: ./schemas/floe.schema.json
```
