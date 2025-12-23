# Research: Two-Tier Configuration Architecture

**Date**: 2025-12-23
**Status**: Complete
**Source**: Codebase exploration, pydantic-settings documentation

## Executive Summary

This document consolidates research findings for implementing the two-tier configuration architecture. All technical unknowns have been resolved, and design decisions are documented with rationale.

---

## 1. Runtime Environment

### Verified Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.10+ | Via pyproject.toml |
| Pydantic | 2.12.5 | v2 syntax required |
| pydantic-settings | 2.12.0 | BaseSettings available |
| PyYAML | Latest | YAML parsing |

### Implications

- Use Pydantic v2 syntax: `@field_validator`, `model_config = ConfigDict(...)`, `model_json_schema()`
- Use `pydantic_settings.BaseSettings` for environment variable integration
- Use `SecretStr` for all sensitive fields

---

## 2. Existing Patterns in Codebase

### 2.1 Secret Reference Pattern

**Current Implementation**: The codebase uses `*_secret_ref` suffix for K8s secret names.

**Locations Found**:
- `packages/floe-core/src/floe_core/schemas/compute.py`: `connection_secret_ref`
- `packages/floe-core/src/floe_core/schemas/consumption.py`: `api_secret_ref`
- `packages/floe-core/src/floe_core/schemas/catalog.py`: `credential_secret_ref`

**Pattern**:
```python
connection_secret_ref: str | None = Field(
    default=None,
    description="K8s secret name for credentials",
    pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$",  # K8s naming
)
```

**Decision**: Adopt the same `secret_ref` naming pattern. The `secret_ref:` YAML syntax is a new addition that maps to these fields.

---

### 2.2 Configuration Loading Patterns

**Pattern A: Direct Environment Variable Reading (Demo)**

```python
# demo/orchestration/config.py
class DemoPolarisConfig(BaseModel):
    uri: str = Field(default_factory=lambda: os.environ.get("POLARIS_URI", "..."))
    client_secret: SecretStr | None = Field(
        default_factory=lambda: SecretStr(os.environ["POLARIS_CLIENT_SECRET"]) if ...
    )
```

**Pattern B: Explicit Parameter Passing (Libraries)**

```python
# packages/floe-polaris/src/floe_polaris/config.py
class PolarisCatalogConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    uri: str = Field(...)
    client_secret: SecretStr | None = Field(default=None)
```

**Pattern C: Factory from CompiledArtifacts**

```python
# packages/floe-dagster/src/floe_dagster/observability/config.py
class TracingConfig(BaseModel):
    @classmethod
    def from_artifacts(cls, artifacts: dict[str, Any]) -> TracingConfig:
        observability = artifacts.get("observability", {})
        return cls(...)
```

**Decision**: Use Pattern B for PlatformSpec/FloeSpec schemas. Pattern C for runtime resolution from CompiledArtifacts. Pattern A deprecated in favor of platform.yaml loading.

---

### 2.3 SecretStr Usage

**Current Usage** (all correct):
- `packages/floe-polaris/src/floe_polaris/config.py`: `client_secret: SecretStr | None`
- `packages/floe-iceberg/src/floe_iceberg/config.py`: `client_secret: SecretStr | None`
- `demo/orchestration/config.py`: `s3_secret_access_key: SecretStr`

**Decision**: Continue SecretStr pattern. All credential fields in profiles MUST use `SecretStr`.

---

## 3. Design Decisions

### 3.1 PlatformSpec Structure

**Decision**: Create `PlatformSpec` as top-level Pydantic model for platform.yaml.

**Rationale**:
- Matches FloeSpec pattern for consistency
- Enables JSON Schema export for IDE autocomplete
- Supports versioned schema evolution

**Schema Design**:
```python
class PlatformSpec(BaseModel):
    """Platform infrastructure configuration (platform.yaml)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")

    storage: dict[str, StorageProfile] = Field(default_factory=dict)
    catalogs: dict[str, CatalogProfile] = Field(default_factory=dict)
    compute: dict[str, ComputeProfile] = Field(default_factory=dict)
    observability: ObservabilityConfig | None = None
```

**Alternatives Considered**:
- Single flat config: Rejected - doesn't support multiple named profiles
- Nested BaseSettings: Rejected - platform.yaml is a file, not env vars

---

### 3.2 Profile Reference Resolution

**Decision**: Resolve profile names during compilation, before runtime.

**Rationale**:
- Fail-fast validation at compile time, not runtime
- Clear separation of concerns (compiler owns resolution)
- CompiledArtifacts contains fully resolved config (no indirection at runtime)

**Resolution Flow**:
```
floe.yaml (catalog: default)
    +
platform.yaml (catalogs.default: {...})
    ↓ Compiler.compile()
CompiledArtifacts (catalog: CatalogConfig with resolved values)
```

**Alternatives Considered**:
- Runtime resolution: Rejected - delays error detection
- Lazy resolution: Rejected - adds complexity, hides failures

---

### 3.3 Credential Modes

**Decision**: Support four credential modes from day one.

| Mode | Use Case | Implementation |
|------|----------|----------------|
| `static` | Local dev, test | K8s secret or env var |
| `oauth2` | Polaris catalog | OAuth2 client credentials flow |
| `iam_role` | AWS production | STS AssumeRole |
| `service_account` | GCP/Azure | Workload identity |

**Schema**:
```python
class CredentialMode(str, Enum):
    STATIC = "static"
    OAUTH2 = "oauth2"
    IAM_ROLE = "iam_role"
    SERVICE_ACCOUNT = "service_account"

class CredentialConfig(BaseModel):
    mode: CredentialMode = Field(default=CredentialMode.STATIC)
    secret_ref: str | None = Field(default=None, pattern=K8S_SECRET_PATTERN)
    scope: str | None = None  # OAuth2 scope
    role_arn: str | None = None  # IAM role
```

**Rationale**: Cover all common enterprise deployment patterns. Allow local dev with static mode, cloud prod with IAM/OAuth2.

---

### 3.4 Secret Reference Pattern

**Decision**: Use `secret_ref:` field for all sensitive values in platform.yaml.

**Pattern**:
```yaml
# platform.yaml
catalogs:
  production:
    credentials:
      mode: oauth2
      client_id: "data-platform-svc"
      client_secret:
        secret_ref: polaris-oauth-secret  # K8s secret name
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
```

**Resolution**:
1. At validation time: Check secret_ref follows K8s naming
2. At runtime: Resolve secret from env var `{SECRET_REF}` or K8s secret

**Implementation**:
```python
class SecretReference(BaseModel):
    """Reference to external secret."""
    secret_ref: str = Field(..., pattern=K8S_SECRET_PATTERN)

    def resolve(self) -> SecretStr:
        """Resolve at runtime from environment or K8s."""
        value = os.environ.get(self.secret_ref.upper().replace("-", "_"))
        if value is None:
            raise SecretNotFoundError(f"Secret '{self.secret_ref}' not found")
        return SecretStr(value)
```

**Alternatives Considered**:
- Inline secrets: Rejected - security violation (FR-012)
- Direct env var names: Rejected - couples config to deployment
- Vault integration: Deferred - can add via pydantic-settings sources later

---

### 3.5 FloeSpec Profile References

**Decision**: Add string fields for profile references to FloeSpec.

**Schema Changes**:
```python
class FloeSpec(BaseModel):
    # NEW: Profile references (logical names)
    catalog: str = Field(default="default", description="Catalog profile name")
    storage: str = Field(default="default", description="Storage profile name")
    compute: str = Field(default="default", description="Compute profile name")

    # REMOVED: Inline configurations (breaking change)
    # catalog: CatalogConfig | None  # OLD - REMOVE
```

**Migration**: Hard break - no backwards compatibility (FR-036). Update all demo/test code.

---

### 3.6 Environment Variable Fallback

**Decision**: Support env var fallback when platform.yaml is missing.

**Implementation**:
```python
class PlatformResolver:
    def resolve(self, platform_path: Path | None = None) -> PlatformSpec:
        if platform_path and platform_path.exists():
            return PlatformSpec.from_yaml(platform_path)

        # Fallback to environment variables
        return self._resolve_from_env()

    def _resolve_from_env(self) -> PlatformSpec:
        """Build minimal PlatformSpec from environment variables."""
        return PlatformSpec(
            catalogs={
                "default": CatalogProfile(
                    type="polaris",
                    uri=os.environ.get("POLARIS_URI", "http://localhost:8181"),
                    warehouse=os.environ.get("POLARIS_WAREHOUSE", "demo"),
                    # ... more env vars
                )
            }
        )
```

**Rationale**: Enables quick local development without platform.yaml file (FR-018).

---

### 3.7 Configuration Validation Errors

**Decision**: Provide actionable error messages with file/line context.

**Error Message Format**:
```
ConfigurationError: Profile 'analytics' not found in platform.catalogs
  File: /app/floe.yaml, field: catalog
  Available profiles: [default, production]

  Hint: Add 'analytics' profile to platform.yaml under 'catalogs:' section
```

**Implementation**: Use Pydantic v2 validation with custom error handlers. Capture YAML line numbers during parsing.

---

### 3.8 CompiledArtifacts v2.0

**Decision**: Bump CompiledArtifacts version to 2.0.0 (breaking change).

**Changes**:
```python
class CompiledArtifacts(BaseModel):
    version: str = "2.0.0"  # BREAKING: Major version bump

    # CHANGED: Resolved profiles (not profile names)
    catalog: CatalogConfig  # Was: catalog name string
    storage: StorageConfig  # NEW: Resolved storage
    compute: ComputeConfig  # Fully resolved

    # NEW: Source tracking
    platform_version: str | None = None
    platform_source: str | None = None  # File path or registry URL
```

**Rationale**: CompiledArtifacts is the integration contract. Major version change signals breaking change to consumers.

---

## 4. pydantic-settings Integration

### 4.1 BaseSettings for Runtime Config

**Decision**: Use BaseSettings only for runtime configuration, not for YAML-loaded schemas.

**Pattern**:
```python
# For environment-based runtime config
class RuntimeConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLOE_",
        env_file=".env",
        extra="ignore",
    )

    platform_path: Path | None = None
    floe_path: Path = Path("floe.yaml")
    environment: str = "local"

# For YAML-loaded schemas
class PlatformSpec(BaseModel):  # NOT BaseSettings
    model_config = ConfigDict(frozen=True, extra="forbid")
    # ... schema fields
```

**Rationale**: YAML files are explicit configuration, not environment-based. BaseSettings used for deployment-time configuration.

### 4.2 Secrets Directory Support

**Decision**: Support K8s secrets directory pattern via pydantic-settings.

**Pattern**:
```python
class SecretResolver(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir="/var/run/secrets",  # K8s secret mount point
        env_nested_delimiter="__",
    )

    polaris_client_secret: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
```

**Rationale**: Native K8s secret mounting. Secrets appear as files in `/var/run/secrets/` directory.

---

## 5. File Structure

### 5.1 Environment Directories

**Decision**: One platform.yaml per environment directory.

```
platform/
├── local/
│   └── platform.yaml     # LocalStack/MinIO endpoints
├── dev/
│   └── platform.yaml     # Dev AWS/GCP endpoints
├── staging/
│   └── platform.yaml     # Staging endpoints
└── prod/
    └── platform.yaml     # Production endpoints
```

**Rationale**: Helm-style explicit separation. Each environment independently version-controlled.

### 5.2 Artifact Registry Publishing

**Decision**: Support OCI-style artifact publishing (future scope).

**Pattern**:
```yaml
# floe.yaml can reference remote platform config
platform:
  source: oci://registry.example.com/platform-configs:v1.2.3
```

**Rationale**: Enables platform team to publish versioned configs. Data teams reference by version.

**Note**: Full registry implementation deferred to post-MVP. Initial implementation uses local files.

---

## 6. Security Considerations

### 6.1 Zero-Trust Validation

**Decision**: Validate floe.yaml contains no secrets at schema level.

**Implementation**:
```python
class FloeSpec(BaseModel):
    @model_validator(mode="after")
    def validate_no_secrets(self) -> Self:
        """Ensure no credentials leak into floe.yaml."""
        # Check for common secret patterns
        yaml_content = self.model_dump_json()
        secret_patterns = [
            r"password\s*[:=]",
            r"secret\s*[:=]",
            r"api.key\s*[:=]",
            r"access.key\s*[:=]",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, yaml_content, re.IGNORECASE):
                raise ValueError(
                    f"Potential secret detected in floe.yaml. "
                    f"Use secret_ref in platform.yaml instead."
                )
        return self
```

### 6.2 Sensitive Field Validation

**Decision**: Require secret_ref for all sensitive fields in platform.yaml.

**Fields requiring secret_ref**:
- `client_secret` (OAuth2)
- `s3_secret_access_key` (S3)
- `password` (databases)
- `token` (API tokens)
- `tls_cert` / `tls_key` (certificates)

**Implementation**:
```python
SENSITIVE_FIELD_NAMES = {
    "client_secret", "secret_access_key", "password",
    "token", "api_key", "tls_key", "tls_cert"
}

@field_validator("*", mode="before")
@classmethod
def validate_sensitive_fields(cls, v: Any, info: ValidationInfo) -> Any:
    if info.field_name in SENSITIVE_FIELD_NAMES:
        if isinstance(v, str):
            raise ValueError(
                f"Field '{info.field_name}' must use secret_ref, not plaintext value"
            )
    return v
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Test Suite | Purpose | Location |
|------------|---------|----------|
| `test_platform_spec.py` | PlatformSpec schema validation | `packages/floe-core/tests/unit/schemas/` |
| `test_credential_config.py` | Credential mode validation | `packages/floe-core/tests/unit/schemas/` |
| `test_profile_resolver.py` | Profile name resolution | `packages/floe-core/tests/unit/compiler/` |
| `test_secret_resolver.py` | Secret reference resolution | `packages/floe-core/tests/unit/compiler/` |

### 7.2 Integration Tests

| Test Suite | Purpose | Location |
|------------|---------|----------|
| `test_platform_injection.py` | E2E with platform.yaml | `testing/docker/tests/` |
| `test_profile_resolution.py` | Full resolution pipeline | `packages/floe-core/tests/integration/` |
| `test_environment_fallback.py` | Env var fallback behavior | `packages/floe-core/tests/integration/` |

### 7.3 Contract Tests

| Test Suite | Purpose |
|------------|---------|
| Schema stability | Verify JSON Schema backward compatibility |
| Secret validation | Verify secrets blocked in floe.yaml |
| Profile resolution | Verify profile names resolve correctly |

---

## 8. Migration Approach

### 8.1 Demo Code Updates

**Files to Update**:
1. `demo/orchestration/config.py` - Load from platform.yaml instead of env vars
2. `demo/orchestration/definitions.py` - Use resolved profiles
3. `demo/floe.yaml` - Use profile references

**Before**:
```yaml
# demo/floe.yaml (OLD)
catalog:
  type: polaris
  uri: http://localhost:8181
  warehouse: demo
```

**After**:
```yaml
# demo/floe.yaml (NEW)
catalog: default  # Profile reference
```

```yaml
# platform/local/platform.yaml (NEW)
version: "1.0.0"
catalogs:
  default:
    type: polaris
    uri: http://localhost:8181
    warehouse: demo
    credentials:
      mode: oauth2
      client_id:
        secret_ref: POLARIS_CLIENT_ID
      client_secret:
        secret_ref: POLARIS_CLIENT_SECRET
```

### 8.2 Test Fixture Updates

All test fixtures using inline catalog/storage/compute config must be updated to use profile-based config.

**Priority**: High - tests must pass before merge.

---

## 9. Future Extensibility: Cloud Provider Integration

### 9.1 Research Summary (2025-12-23)

Conducted deep research into cloud provider credential patterns to ensure design flexibility:

**AWS IRSA/EKS Pod Identities**:
- Token TTL: 1 hour default, configurable up to 12 hours via role trust policy
- Renewal: SDK auto-refreshes at 80% expiry
- Best practice: Prefer EKS Pod Identities (newer) over IRSA for new clusters
- Future fields: `token_ttl_seconds`, `external_id`, `session_name`, `regional_sts_endpoint`

**GCP Workload Identity Federation**:
- Pattern: KSA → Workload Identity Pool → GSA binding
- Token format: Short-lived OAuth2 access tokens (no JSON keys)
- Future fields: `workload_identity_provider`, `service_account_email`, `token_format`, `audience`

**Azure Workload Identity**:
- Pattern: Microsoft Entra Workload ID (replaces pod-managed identity, deprecated Sept 2025)
- Requires: Pod label `azure.workload.identity/use: "true"`
- Future fields: `client_id`, `tenant_id`, `federated_token_file`

**HashiCorp Vault**:
- Three integration patterns validated:
  1. **Vault Agent Injector**: Sidecar injects secrets to file paths (K8s-native)
  2. **Vault Secrets Operator (VSO)**: Operator syncs Vault secrets to K8s secrets
  3. **Direct API**: Application authenticates and retrieves secrets directly
- Recommendation: VSO is most K8s-native; our `secret_ref` pattern works unchanged

### 9.2 Extensibility Design

Current `CredentialConfig` schema supports future extension without breaking changes:

```python
# Current schema (v1.0.0)
class CredentialConfig(BaseModel):
    mode: CredentialMode  # static, oauth2, iam_role, service_account
    secret_ref: str | None
    scope: str | None
    role_arn: str | None  # AWS
    client_id: str | SecretReference | None
    client_secret: SecretReference | None

# Future extension (v1.1.0 - non-breaking, additive)
class CredentialConfig(BaseModel):
    # ... existing fields ...

    # Optional cloud-specific configuration (added in v1.1.0)
    aws_config: AwsIamConfig | None = None  # token_ttl, external_id, etc.
    gcp_config: GcpWorkloadIdentityConfig | None = None  # provider, audience, etc.
    azure_config: AzureWorkloadIdentityConfig | None = None  # tenant_id, etc.
    vault_config: VaultConfig | None = None  # role, path, auth_method, etc.
```

### 9.3 SecretReference Future Extension

Current pattern resolves from environment variables or K8s secrets:

```python
# Current
class SecretReference(BaseModel):
    secret_ref: str  # Env var name or K8s secret name
```

Future extension for multi-source secret resolution:

```python
# Future (v1.1.0 - non-breaking)
class SecretSource(str, Enum):
    ENV_VAR = "env_var"           # Default
    K8S_SECRET = "k8s_secret"
    VAULT_AGENT = "vault_agent"   # File path from Vault Agent
    VAULT_OPERATOR = "vault_operator"  # Synced K8s secret
    VAULT_API = "vault_api"       # Direct Vault call
    CSI_DRIVER = "csi_driver"     # Secrets Store CSI Driver

class SecretReference(BaseModel):
    secret_ref: str
    source: SecretSource = SecretSource.ENV_VAR  # Backward compatible default
```

### 9.4 Token TTL Defaults

Standard TTLs by provider (deployment-time configuration, not schema):

| Provider | Default | Maximum | Notes |
|----------|---------|---------|-------|
| AWS STS | 1 hour | 12 hours | Set via role trust policy |
| GCP WIF | 1 hour | 12 hours | SDK auto-refresh |
| Azure | 1 hour | 24 hours | SDK auto-refresh |
| Polaris OAuth2 | Varies | Provider-specific | `token_refresh_enabled: true` |

### 9.5 Breaking Change Risk Assessment

| Future Integration | Schema Change Type | Risk |
|-------------------|-------------------|------|
| AWS IRSA enhancements | Additive (optional `aws_config`) | 🟢 None |
| GCP Workload Identity | Additive (optional `gcp_config`) | 🟢 None |
| Azure Workload Identity | Additive (optional `azure_config`) | 🟢 None |
| Vault Agent Injector | None (existing `secret_ref` works) | 🟢 None |
| Vault Secrets Operator | None (syncs to K8s secrets) | 🟢 None |
| Vault Direct API | Additive (`SecretReference.source`) | 🟢 None |

**Conclusion**: Current design is extensible without breaking changes. All future cloud provider integrations can be added as optional fields with backward-compatible defaults.

---

## 10. Open Items (None)

All research questions have been resolved. Future extensibility documented above.

---

## 11. References

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [pydantic-settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Helm Values Best Practices](https://helm.sh/docs/chart_best_practices/values/)
- [K8s Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Spec: 001-core-foundation/data-model.md](../001-core-foundation/data-model.md)
