# Data Model: Two-Tier Configuration Architecture

**Date**: 2025-12-23
**Status**: Complete
**Spec**: [spec.md](./spec.md)

## Overview

This document defines the data model for the two-tier configuration architecture. The model separates platform infrastructure (PlatformSpec) from pipeline definitions (FloeSpec), with profile-based references resolved at compile time.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONFIGURATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐                     ┌──────────────────┐             │
│   │   PlatformSpec   │                     │     FloeSpec     │             │
│   │  (platform.yaml) │                     │   (floe.yaml)    │             │
│   └────────┬─────────┘                     └────────┬─────────┘             │
│            │                                        │                        │
│            │ contains                               │ references             │
│            ▼                                        ▼                        │
│   ┌────────────────────────────────────────────────────────────┐            │
│   │                        PROFILES                             │            │
│   ├────────────────────┬───────────────────┬───────────────────┤            │
│   │   StorageProfile   │   CatalogProfile  │   ComputeProfile  │            │
│   │   (dict by name)   │   (dict by name)  │   (dict by name)  │            │
│   └────────┬───────────┴─────────┬─────────┴─────────┬─────────┘            │
│            │                     │                   │                       │
│            │ uses                │ uses              │ uses                  │
│            ▼                     ▼                   ▼                       │
│   ┌──────────────────────────────────────────────────────────┐              │
│   │                    CredentialConfig                       │              │
│   │  (mode: static | oauth2 | iam_role | service_account)    │              │
│   └──────────────────────────────────────────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Compiler.compile()
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RUNTIME LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│   ┌──────────────────────────────────────────────────────────┐              │
│   │                   CompiledArtifacts                       │              │
│   │         (Resolved configuration, immutable)               │              │
│   │                                                           │              │
│   │  ├── version: "2.0.0"                                     │              │
│   │  ├── catalog: CatalogConfig (fully resolved)              │              │
│   │  ├── storage: StorageConfig (fully resolved)              │              │
│   │  ├── compute: ComputeConfig (fully resolved)              │              │
│   │  └── transforms: list[TransformConfig]                    │              │
│   └──────────────────────────────────────────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Entities

### 1. PlatformSpec

**Purpose**: Top-level configuration for platform infrastructure (platform.yaml).

**Ownership**: Platform Engineers

**File**: `packages/floe-core/src/floe_core/schemas/platform_spec.py`

```python
class PlatformSpec(BaseModel):
    """Platform infrastructure configuration.

    This is the root model for platform.yaml files. It contains
    named profiles for storage, catalogs, and compute resources.

    Attributes:
        version: Schema version for forward compatibility.
        storage: Named storage profiles (S3, MinIO, etc.).
        catalogs: Named catalog profiles (Polaris, Glue, etc.).
        compute: Named compute profiles (DuckDB, Snowflake, etc.).
        observability: Observability configuration (traces, lineage).

    Example:
        >>> spec = PlatformSpec.from_yaml(Path("platform.yaml"))
        >>> spec.catalogs["default"].uri
        'http://polaris:8181/api/catalog'
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(
        default="1.0.0",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Schema version (semver)",
    )
    storage: dict[str, StorageProfile] = Field(
        default_factory=dict,
        description="Named storage profiles",
    )
    catalogs: dict[str, CatalogProfile] = Field(
        default_factory=dict,
        description="Named catalog profiles",
    )
    compute: dict[str, ComputeProfile] = Field(
        default_factory=dict,
        description="Named compute profiles",
    )
    observability: ObservabilityConfig | None = Field(
        default=None,
        description="Observability configuration",
    )

    @classmethod
    def from_yaml(cls, path: Path) -> PlatformSpec:
        """Load PlatformSpec from YAML file."""
        ...
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| version | str | No | "1.0.0" | Schema version (semver format) |
| storage | dict[str, StorageProfile] | No | {} | Named storage profiles |
| catalogs | dict[str, CatalogProfile] | No | {} | Named catalog profiles |
| compute | dict[str, ComputeProfile] | No | {} | Named compute profiles |
| observability | ObservabilityConfig | None | None | Observability configuration |

**Validation Rules**:
- `version` must match semver pattern: `^\d+\.\d+\.\d+$`
- Profile names must be valid identifiers: `^[a-zA-Z][a-zA-Z0-9_-]*$`
- At least one profile should be defined (warning if empty)

---

### 2. FloeSpec (Modified)

**Purpose**: Pipeline configuration with profile references (floe.yaml).

**Ownership**: Data Engineers

**File**: `packages/floe-core/src/floe_core/schemas/floe_spec.py`

**Changes from Current**:
- ADD: `catalog`, `storage`, `compute` as string profile references
- REMOVE: Inline `CatalogConfig`, `ComputeConfig` fields (FR-034)

```python
class FloeSpec(BaseModel):
    """Pipeline configuration with profile references.

    Data engineers define pipelines using logical profile names
    that resolve to actual infrastructure at compile time.

    Attributes:
        name: Pipeline name (unique identifier).
        version: Pipeline version.
        catalog: Catalog profile name (resolves from platform.yaml).
        storage: Storage profile name (resolves from platform.yaml).
        compute: Compute profile name (resolves from platform.yaml).
        transforms: List of transformation configurations.
        consumption: Semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability flags (enabled/disabled).

    Example:
        >>> spec = FloeSpec.from_yaml(Path("floe.yaml"))
        >>> spec.catalog
        'default'  # Logical name, not actual config
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Required
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,99}$",
        description="Pipeline name",
    )
    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Pipeline version (semver)",
    )

    # Profile references (NEW)
    catalog: str = Field(
        default="default",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Catalog profile name from platform.yaml",
    )
    storage: str = Field(
        default="default",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Storage profile name from platform.yaml",
    )
    compute: str = Field(
        default="default",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Compute profile name from platform.yaml",
    )

    # Existing fields (unchanged)
    transforms: list[TransformConfig] = Field(default_factory=list)
    consumption: ConsumptionConfig = Field(default_factory=ConsumptionConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @model_validator(mode="after")
    def validate_no_secrets(self) -> Self:
        """Ensure floe.yaml contains no credentials."""
        ...
```

**Fields (NEW/MODIFIED)**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| catalog | str | No | "default" | Catalog profile name |
| storage | str | No | "default" | Storage profile name |
| compute | str | No | "default" | Compute profile name |

**Validation Rules**:
- Profile names must match pattern: `^[a-zA-Z][a-zA-Z0-9_-]*$`
- No credentials, secrets, or infrastructure endpoints allowed
- Validation fails if secret patterns detected (FR-013)

---

### 3. StorageProfile

**Purpose**: S3-compatible storage configuration.

**File**: `packages/floe-core/src/floe_core/schemas/storage_profile.py`

```python
class StorageProfile(BaseModel):
    """S3-compatible storage configuration.

    Attributes:
        type: Storage type (s3, gcs, azure, local).
        endpoint: S3 endpoint URL (empty for AWS S3).
        region: AWS region.
        bucket: Default bucket name.
        path_style_access: Use path-style access (for MinIO).
        credentials: Credential configuration.

    Example:
        >>> profile = StorageProfile(
        ...     type="s3",
        ...     endpoint="http://minio:9000",
        ...     bucket="iceberg-data",
        ...     credentials=CredentialConfig(mode="static", secret_ref="minio-creds"),
        ... )
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: StorageType = Field(
        default=StorageType.S3,
        description="Storage backend type",
    )
    endpoint: str | SecretReference = Field(
        default="",
        description="S3 endpoint URL (empty for AWS S3)",
    )
    region: str = Field(
        default="us-east-1",
        description="AWS region",
    )
    bucket: str = Field(
        ...,
        description="Default bucket name",
    )
    path_style_access: bool = Field(
        default=False,
        description="Use path-style S3 access (required for MinIO)",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )
```

**Enum**:
```python
class StorageType(str, Enum):
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"
    LOCAL = "local"
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| type | StorageType | No | "s3" | Storage backend type |
| endpoint | str \| SecretReference | No | "" | S3 endpoint (empty = AWS) |
| region | str | No | "us-east-1" | AWS region |
| bucket | str | Yes | - | Default bucket name |
| path_style_access | bool | No | False | Path-style S3 access |
| credentials | CredentialConfig | No | CredentialConfig() | Credential config |

---

### 4. CatalogProfile

**Purpose**: Iceberg catalog configuration.

**File**: `packages/floe-core/src/floe_core/schemas/catalog_profile.py`

```python
class CatalogProfile(BaseModel):
    """Iceberg catalog configuration.

    Attributes:
        type: Catalog type (polaris, glue, nessie, rest).
        uri: Catalog URI endpoint.
        warehouse: Warehouse/catalog name.
        namespace: Default namespace.
        credentials: Credential configuration (OAuth2, IAM, etc.).
        access_delegation: Access delegation mode for STS.

    Example:
        >>> profile = CatalogProfile(
        ...     type="polaris",
        ...     uri="http://polaris:8181/api/catalog",
        ...     warehouse="production",
        ...     credentials=CredentialConfig(mode="oauth2", scope="PRINCIPAL_ROLE:DATA_ENGINEER"),
        ... )
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: CatalogType = Field(
        default=CatalogType.POLARIS,
        description="Catalog type",
    )
    uri: str | SecretReference = Field(
        ...,
        description="Catalog URI endpoint",
    )
    warehouse: str = Field(
        ...,
        description="Warehouse/catalog name",
    )
    namespace: str = Field(
        default="default",
        description="Default namespace",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )
    access_delegation: str = Field(
        default="",
        description="Access delegation mode (vended-credentials, remote-signing)",
    )
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Additional catalog properties",
    )
```

**Enum**:
```python
class CatalogType(str, Enum):
    POLARIS = "polaris"
    GLUE = "glue"
    NESSIE = "nessie"
    REST = "rest"
    HIVE = "hive"
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| type | CatalogType | No | "polaris" | Catalog type |
| uri | str \| SecretReference | Yes | - | Catalog endpoint URI |
| warehouse | str | Yes | - | Warehouse name |
| namespace | str | No | "default" | Default namespace |
| credentials | CredentialConfig | No | CredentialConfig() | Credential config |
| access_delegation | str | No | "" | STS delegation mode |
| properties | dict[str, str] | No | {} | Additional properties |

---

### 5. ComputeProfile

**Purpose**: Compute engine configuration.

**File**: `packages/floe-core/src/floe_core/schemas/compute_profile.py`

```python
class ComputeProfile(BaseModel):
    """Compute engine configuration.

    Attributes:
        type: Compute target type.
        properties: Target-specific properties.
        credentials: Credential configuration.

    Example:
        >>> profile = ComputeProfile(
        ...     type="snowflake",
        ...     properties={"account": "acme.us-east-1", "warehouse": "ANALYTICS_WH"},
        ...     credentials=CredentialConfig(mode="static", secret_ref="snowflake-creds"),
        ... )
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ComputeTarget = Field(
        default=ComputeTarget.DUCKDB,
        description="Compute target type",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Target-specific properties",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )
```

**Enum** (existing):
```python
class ComputeTarget(str, Enum):
    DUCKDB = "duckdb"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"
    DATABRICKS = "databricks"
    POSTGRES = "postgres"
    SPARK = "spark"
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| type | ComputeTarget | No | "duckdb" | Compute target |
| properties | dict[str, Any] | No | {} | Target-specific props |
| credentials | CredentialConfig | No | CredentialConfig() | Credential config |

---

### 6. CredentialConfig

**Purpose**: Credential management configuration with multiple modes.

**File**: `packages/floe-core/src/floe_core/schemas/credential_config.py`

```python
class CredentialMode(str, Enum):
    """Credential management modes."""
    STATIC = "static"           # K8s secret or env var
    OAUTH2 = "oauth2"           # OAuth2 client credentials
    IAM_ROLE = "iam_role"       # AWS IAM role assumption
    SERVICE_ACCOUNT = "service_account"  # GCP/Azure workload identity


class CredentialConfig(BaseModel):
    """Credential configuration with multiple modes.

    Attributes:
        mode: Credential management mode.
        client_id: OAuth2 client ID (for oauth2 mode).
        client_secret: OAuth2 client secret reference.
        scope: OAuth2 scope.
        role_arn: AWS IAM role ARN (for iam_role mode).
        secret_ref: Generic secret reference name.

    Example:
        >>> config = CredentialConfig(
        ...     mode="oauth2",
        ...     client_id="data-platform-svc",
        ...     client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ... )
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: CredentialMode = Field(
        default=CredentialMode.STATIC,
        description="Credential management mode",
    )
    client_id: str | SecretReference | None = Field(
        default=None,
        description="OAuth2 client ID",
    )
    client_secret: SecretReference | None = Field(
        default=None,
        description="OAuth2 client secret (must be secret_ref)",
    )
    scope: str | None = Field(
        default=None,
        description="OAuth2 scope",
    )
    role_arn: str | None = Field(
        default=None,
        description="AWS IAM role ARN",
    )
    secret_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_PATTERN,
        description="Generic secret reference (K8s secret name)",
    )

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> Self:
        """Validate required fields per mode."""
        if self.mode == CredentialMode.OAUTH2:
            if not self.client_id or not self.client_secret:
                raise ValueError("OAuth2 mode requires client_id and client_secret")
        if self.mode == CredentialMode.IAM_ROLE:
            if not self.role_arn:
                raise ValueError("IAM role mode requires role_arn")
        return self
```

**Enum**:

| Value | Description | Required Fields |
|-------|-------------|-----------------|
| static | K8s secret or env var | secret_ref |
| oauth2 | OAuth2 client credentials | client_id, client_secret, scope |
| iam_role | AWS IAM role assumption | role_arn |
| service_account | GCP/Azure workload identity | (platform-specific) |

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| mode | CredentialMode | No | "static" | Credential mode |
| client_id | str \| SecretReference | Conditional | None | OAuth2 client ID |
| client_secret | SecretReference | Conditional | None | OAuth2 secret |
| scope | str | Conditional | None | OAuth2 scope |
| role_arn | str | Conditional | None | AWS IAM role ARN |
| secret_ref | str | Conditional | None | Generic secret name |

---

### 7. SecretReference

**Purpose**: Reference to external secret (K8s secret or env var).

**File**: `packages/floe-core/src/floe_core/schemas/credential_config.py`

```python
K8S_SECRET_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"


class SecretReference(BaseModel):
    """Reference to external secret.

    Secrets are never stored in configuration files. Instead,
    secret_ref points to a K8s secret name or environment variable.

    Attributes:
        secret_ref: K8s secret name or env var name.

    Resolution:
        1. Check environment variable: {SECRET_REF_UPPER_SNAKE_CASE}
        2. Check K8s secret mount: /var/run/secrets/{secret_ref}
        3. Fail with clear error if not found

    Example:
        >>> ref = SecretReference(secret_ref="polaris-oauth-secret")
        >>> ref.resolve()  # Returns SecretStr from env or K8s
        SecretStr('**********')
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    secret_ref: str = Field(
        ...,
        pattern=K8S_SECRET_PATTERN,
        description="K8s secret name or env var name",
    )

    def resolve(self) -> SecretStr:
        """Resolve secret at runtime."""
        env_var_name = self.secret_ref.upper().replace("-", "_")
        value = os.environ.get(env_var_name)
        if value:
            return SecretStr(value)

        # Try K8s secret mount
        secret_path = Path(f"/var/run/secrets/{self.secret_ref}")
        if secret_path.exists():
            return SecretStr(secret_path.read_text().strip())

        raise SecretNotFoundError(
            f"Secret '{self.secret_ref}' not found. "
            f"Expected in environment variable '{env_var_name}' "
            f"or K8s secret mount at '{secret_path}'"
        )
```

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| secret_ref | str | Yes | - | K8s secret or env var name |

**Validation Rules**:
- Must match K8s naming: `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$`
- Max 253 characters

---

### 8. CompiledArtifacts (Modified)

**Purpose**: Fully resolved configuration for runtime.

**File**: `packages/floe-core/src/floe_core/compiler/models.py`

**Changes**:
- Version bump to 2.0.0 (breaking)
- Add `storage` field (resolved StorageProfile)
- Ensure `catalog` and `compute` are fully resolved

```python
class CompiledArtifacts(BaseModel):
    """Compiled artifacts with resolved configuration.

    This is the sole integration contract between packages.
    Profile references are resolved to actual configurations.

    Version 2.0.0 changes:
    - Profile references replaced with resolved configurations
    - Added storage configuration
    - Added platform source tracking

    Attributes:
        version: Contract version (2.0.0).
        metadata: Compilation metadata.
        catalog: Resolved catalog configuration.
        storage: Resolved storage configuration.
        compute: Resolved compute configuration.
        transforms: Transformation configurations.
        consumption: Semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability configuration.
        platform_version: Source platform.yaml version.
        platform_source: Source platform.yaml path/registry.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(
        default="2.0.0",
        description="Contract version",
    )
    metadata: ArtifactMetadata = Field(
        ...,
        description="Compilation metadata",
    )

    # Resolved configurations (from profiles)
    catalog: CatalogConfig = Field(
        ...,
        description="Resolved catalog configuration",
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Resolved storage configuration",
    )
    compute: ComputeConfig = Field(
        ...,
        description="Resolved compute configuration",
    )

    # Pipeline configuration
    transforms: list[TransformConfig] = Field(
        default_factory=list,
        description="Transformation configurations",
    )
    consumption: ConsumptionConfig = Field(
        default_factory=ConsumptionConfig,
        description="Semantic layer configuration",
    )
    governance: GovernanceConfig = Field(
        default_factory=GovernanceConfig,
        description="Governance configuration",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration",
    )

    # Source tracking (NEW)
    platform_version: str | None = Field(
        default=None,
        description="Source platform.yaml version",
    )
    platform_source: str | None = Field(
        default=None,
        description="Source platform.yaml path or registry URL",
    )

    # dbt paths (existing)
    dbt_manifest_path: str | None = None
    dbt_project_path: str | None = None
    dbt_profiles_path: str = ".floe/profiles"

    # SaaS enrichment (optional)
    lineage_namespace: str | None = None
    environment_context: EnvironmentContext | None = None
    column_classifications: dict[str, dict[str, ColumnClassification]] | None = None
```

---

## Validation Rules Summary

### K8s Secret Naming Pattern

```python
K8S_SECRET_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"
```

Used for: `secret_ref`, `credential_secret_ref`, `connection_secret_ref`, `api_secret_ref`

### Profile Name Pattern

```python
PROFILE_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
```

Used for: `catalog`, `storage`, `compute` fields in FloeSpec

### Semver Pattern

```python
SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
```

Used for: `version` fields in PlatformSpec, FloeSpec, CompiledArtifacts

---

## State Transitions

### Compilation Flow

```
         floe.yaml                      platform.yaml
             │                               │
             ▼                               ▼
       ┌──────────┐                   ┌─────────────┐
       │ FloeSpec │                   │ PlatformSpec│
       │ (parsed) │                   │  (parsed)   │
       └────┬─────┘                   └──────┬──────┘
            │                                │
            │         Profile Resolution     │
            └───────────────┬────────────────┘
                           ▼
                   ┌───────────────┐
                   │ProfileResolver│
                   │  (resolves    │
                   │   profiles)   │
                   └───────┬───────┘
                           │
                           ▼
                   ┌───────────────┐
                   │   Compiler    │
                   │ (merges into  │
                   │  artifacts)   │
                   └───────┬───────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  CompiledArtifacts  │
                │    (version 2.0)    │
                │   (fully resolved)  │
                └─────────────────────┘
```

### Secret Resolution (Runtime)

```
    secret_ref: "polaris-oauth-secret"
                    │
                    ▼
         ┌──────────────────┐
         │ Check ENV VAR    │
         │ POLARIS_OAUTH_   │
         │ SECRET           │
         └────────┬─────────┘
                  │
          ┌───────┴───────┐
          │               │
         Found        Not Found
          │               │
          ▼               ▼
      Return        ┌──────────────────┐
      SecretStr     │ Check K8s Mount  │
                    │ /var/run/secrets/│
                    │ polaris-oauth-   │
                    │ secret           │
                    └────────┬─────────┘
                             │
                     ┌───────┴───────┐
                     │               │
                    Found        Not Found
                     │               │
                     ▼               ▼
                 Return        Raise
                 SecretStr     SecretNotFoundError
```

---

## Example YAML Configurations

### platform.yaml (Local Development)

```yaml
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: http://localhost:4566  # LocalStack
    bucket: iceberg-data
    region: us-east-1
    path_style_access: true
    credentials:
      mode: static
      secret_ref: localstack-credentials

catalogs:
  default:
    type: polaris
    uri: http://localhost:8181/api/catalog
    warehouse: demo
    namespace: bronze
    credentials:
      mode: oauth2
      client_id:
        secret_ref: POLARIS_CLIENT_ID
      client_secret:
        secret_ref: POLARIS_CLIENT_SECRET
      scope: "PRINCIPAL_ROLE:ALL"

compute:
  default:
    type: duckdb
    properties:
      threads: 4
      memory_limit: "4GB"
```

### platform.yaml (Production)

```yaml
version: "1.0.0"

storage:
  default:
    type: s3
    bucket: prod-iceberg-data
    region: us-east-1
    credentials:
      mode: iam_role
      role_arn: arn:aws:iam::123456789:role/FloeStorageRole

catalogs:
  default:
    type: polaris
    uri:
      secret_ref: POLARIS_URI  # Protect internal topology
    warehouse: production
    namespace: analytics
    credentials:
      mode: oauth2
      client_id:
        secret_ref: POLARIS_CLIENT_ID
      client_secret:
        secret_ref: POLARIS_CLIENT_SECRET
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials

compute:
  default:
    type: snowflake
    properties:
      account: acme.us-east-1
      warehouse: ANALYTICS_WH
      database: PROD
    credentials:
      mode: static
      secret_ref: snowflake-credentials
```

### floe.yaml (Data Engineer)

```yaml
name: customer-analytics
version: "1.0.0"

# Profile references only (no infrastructure details)
catalog: default
storage: default
compute: default

transforms:
  - type: dbt
    path: ./dbt
    target: prod

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  lineage: true
```

---

## Migration Checklist

### Files to Update

| File | Change | Priority |
|------|--------|----------|
| `packages/floe-core/src/floe_core/schemas/floe_spec.py` | Add profile references, remove inline config | P0 |
| `packages/floe-core/src/floe_core/compiler/models.py` | Update CompiledArtifacts v2.0 | P0 |
| `demo/orchestration/config.py` | Load from platform.yaml | P1 |
| `demo/orchestration/definitions.py` | Use resolved profiles | P1 |
| `demo/floe.yaml` | Use profile references | P1 |
| `testing/fixtures/*.py` | Update test fixtures | P1 |
| `tests/unit/schemas/*.py` | Add new schema tests | P1 |

---

## References

- [research.md](./research.md) - Design decisions and rationale
- [spec.md](./spec.md) - Feature specification
- [001-core-foundation/data-model.md](../001-core-foundation/data-model.md) - Original data model
