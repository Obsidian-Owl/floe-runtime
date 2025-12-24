# ADR-0002: Two-Tier Configuration Architecture

## Status

Accepted

## Context

The original floe-runtime architecture used a **monolithic FloeSpec** where data engineers defined everything in a single `floe.yaml` file:

```yaml
# Original monolithic floe.yaml (DEPRECATED PATTERN)
name: customer-analytics
version: "1.0.0"
polaris:
  uri: "http://polaris:8181/api/catalog"
  warehouse: production_catalog
  credentials:
    client_id: "service-account"
    client_secret_ref: "polaris-prod-secret"
    scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
storage:
  endpoint: "https://s3.amazonaws.com"
  bucket: "iceberg-data"
  region: "us-east-1"
transforms:
  - type: dbt
    path: ./dbt
```

This approach caused significant problems:

### Problem 1: Persona Mismatch

**Data engineers** care about:
- Pipeline logic (transforms, schedules, data flows)
- Data quality and governance
- Business metrics and observability

**Platform engineers** care about:
- Infrastructure endpoints (S3, Polaris, compute clusters)
- Credential management (OAuth2, IAM roles, secrets)
- Network security and access control
- Environment-specific configuration

The monolithic model forced data engineers to understand and configure infrastructure concerns.

### Problem 2: Environment Portability

The same pipeline should work across environments without modification:
- **Local development**: LocalStack, Docker Compose
- **Staging**: AWS with dev credentials
- **Production**: AWS with IAM roles, strict security

With the monolithic model, data engineers had to maintain separate `floe.yaml` files per environment, leading to:
- Configuration drift between environments
- Duplicated pipeline definitions
- Higher risk of production misconfiguration

### Problem 3: Security Anti-Patterns

The monolithic model encouraged insecure patterns:
- Credentials referenced directly in pipeline configs
- Data engineers exposed to production secrets
- No clear audit boundary between personas
- Secrets scattered across multiple config files

### Problem 4: Kubernetes Integration Complexity

Kubernetes deployments required:
- Hardcoded endpoints in ConfigMaps
- Manual credential injection per environment
- No standard pattern for environment variation

### Requirements

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Persona Separation | P0 | Data engineers never see infrastructure details |
| Environment Portability | P0 | Same `floe.yaml` works across all environments |
| Zero Secrets in Code | P0 | Credentials never in pipeline configuration |
| Kubernetes Native | P1 | First-class support for K8s secrets and ConfigMaps |
| Credential Modes | P1 | Support static, OAuth2, IAM role, service account |
| Compile-Time Resolution | P1 | Merge configs at compile/deploy time |
| Standalone-First | P2 | Works without SaaS Control Plane |

## Decision

Adopt a **two-tier configuration architecture** that separates concerns between personas:

### Tier 1: platform.yaml (Platform Engineer Domain)

Platform engineers define infrastructure in `platform.yaml`:

```yaml
# platform.yaml - Owned by Platform Engineering
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: ""  # Empty = AWS S3, else MinIO/LocalStack
    region: us-east-1
    bucket: iceberg-data
    path_style_access: false
    credentials:
      mode: iam_role
      role_arn: arn:aws:iam::123456789:role/FloeStorageRole

catalogs:
  default:
    type: polaris
    uri: "https://polaris.internal:8181/api/catalog"
    warehouse: production_catalog
    credentials:
      mode: oauth2
      client_id: "floe-service-account"
      client_secret:
        secret_ref: polaris-oauth-credentials  # K8s secret name
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: duckdb
    properties:
      threads: 4

observability:
  traces: true
  lineage: true
  otlp_endpoint: "http://jaeger:4317"
  lineage_endpoint: "http://marquez:5000"
```

### Tier 2: floe.yaml (Data Engineer Domain)

Data engineers define pipelines with **logical references** only:

```yaml
# floe.yaml - Owned by Data Engineering
name: customer-analytics
version: "1.0.0"

# Logical references - resolved at compile time
storage: default
catalog: default
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
  attributes:
    service.name: customer-analytics
```

### Compilation Model

At compile/deploy time, `FloeSpec` and `PlatformSpec` are merged into `CompiledArtifacts`:

```
┌─────────────────────┐     ┌─────────────────────┐
│     floe.yaml       │     │   platform.yaml     │
│   (Data Engineer)   │     │ (Platform Engineer) │
└─────────────────────┘     └─────────────────────┘
          │                           │
          │                           │
          ▼                           ▼
    ┌─────────────────────────────────────────┐
    │           PlatformResolver               │
    │  • Load platform.yaml by FLOE_PLATFORM_ENV
    │  • Resolve secret references            │
    │  • Validate credential modes            │
    └─────────────────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────┐
    │              Compiler                    │
    │  • Merge FloeSpec + PlatformSpec        │
    │  • Resolve profile references           │
    │  • Generate CompiledArtifacts           │
    └─────────────────────────────────────────┘
                      │
                      ▼
    ┌─────────────────────────────────────────┐
    │          CompiledArtifacts              │
    │  • Fully resolved configuration         │
    │  • All secrets injected                 │
    │  • Ready for Dagster execution          │
    └─────────────────────────────────────────┘
```

## Alternatives Considered

### Alternative 1: Environment Variables Only

**Approach**: Use environment variables for all configuration, no YAML files.

```bash
export POLARIS_URI="http://polaris:8181/api/catalog"
export POLARIS_CLIENT_ID="service-account"
export AWS_ACCESS_KEY_ID="..."
```

**Rejected because**:
- Poor developer experience (many variables)
- No schema validation
- Difficult to document and maintain
- No type safety

### Alternative 2: Single File with Overlays

**Approach**: Keep single `floe.yaml` with environment-specific overlays.

```yaml
# floe.yaml
polaris:
  uri: ${POLARIS_URI}  # Variable substitution
  credentials:
    client_id: ${POLARIS_CLIENT_ID}
```

**Rejected because**:
- Data engineers still see infrastructure structure
- Variable substitution is error-prone
- No clear persona boundary
- Credentials still referenced in pipeline config

### Alternative 3: Kustomize/Helm-Only Configuration

**Approach**: Use Kubernetes tooling for all configuration.

**Rejected because**:
- Doesn't work for non-K8s environments
- Violates standalone-first principle
- Poor local development experience
- Tight coupling to K8s concepts

### Alternative 4: SaaS Control Plane Integration

**Approach**: Require SaaS Control Plane for configuration management.

**Rejected because**:
- Violates standalone-first principle
- Vendor lock-in
- Not suitable for air-gapped environments
- Open-source users can't use it

## Consequences

### Positive

#### Clear Persona Separation
- Data engineers focus on pipeline logic
- Platform engineers own infrastructure
- Reduced cognitive load for both personas
- Clear ownership and audit boundaries

#### Environment Portability
- Same `floe.yaml` works in dev, staging, production
- Platform config injected at deploy time
- Reduced configuration drift
- Easier testing (same pipeline everywhere)

#### Enterprise-Grade Security
- Zero credentials in pipeline configuration
- Credential modes support modern patterns (OAuth2, IAM roles)
- Secret references, not secret values
- Defense in depth (K8s secrets, vended credentials)

#### Kubernetes Native
- Platform config as ConfigMap
- Secrets via K8s Secret resources
- Helm values map to platform.yaml
- Works with GitOps (ArgoCD, Flux)

#### Standalone-First
- Works without SaaS Control Plane
- Local development via `platform/local/platform.yaml`
- Full control over configuration
- No vendor dependencies

### Negative

#### Two Files to Manage
- Platform engineers maintain `platform.yaml`
- Data engineers maintain `floe.yaml`
- Requires coordination for new profiles

**Mitigation**: Clear documentation, schema validation, CLI tooling.

#### Compilation Step Required
- Cannot run directly without compilation
- Adds complexity to development workflow
- Requires tooling support

**Mitigation**: `floe compile` is fast, can be integrated into CI/CD.

#### Learning Curve
- New concepts (profiles, credential modes)
- Documentation required for both personas
- Training for existing teams

**Mitigation**: Comprehensive documentation, examples, migration guide.

### Neutral

#### Profile Reference Pattern
- Profiles are named resources (`default`, `production`, etc.)
- Flexible but requires naming conventions
- Similar to Kubernetes resource references

#### Credential Mode Complexity
- Multiple modes (static, oauth2, iam_role, service_account)
- Platform engineers must understand options
- Enables advanced security patterns

## Implementation

### Schema Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `PlatformSpec` | `floe_core/schemas/platform_spec.py` | Platform configuration schema |
| `FloeSpec` | `floe_core/schemas/floe_spec.py` | Pipeline configuration with profile refs |
| `CredentialConfig` | `floe_core/schemas/credential_config.py` | Credential mode configuration |
| `SecretReference` | `floe_core/schemas/credential_config.py` | K8s secret reference |
| `PlatformResolver` | `floe_core/compiler/platform_resolver.py` | Load and resolve platform config |

### Credential Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `static` | K8s secret with static credentials | Simple deployments |
| `oauth2` | OAuth2 client credentials flow | Polaris, enterprise systems |
| `iam_role` | AWS IAM role assumption | AWS-native, no static creds |
| `service_account` | GCP/Azure workload identity | Cloud-native |

### Secret Resolution

Secrets are resolved at runtime using this priority:
1. Environment variable: `{SECRET_REF_UPPER_SNAKE_CASE}`
2. K8s secret mount: `/var/run/secrets/{secret_ref}`
3. Fail with clear error

### Security Validation

The `CredentialDetector` (using Yelp's `detect-secrets` library) scans `floe.yaml` to reject any embedded credentials:

```python
# Fails validation - credential patterns are detected and rejected
storage: "aws_access_key_here"  # High-entropy string detected!

# Passes validation
storage: default  # Logical reference only
```

## Directory Structure

```
floe-runtime/
├── platform/
│   ├── local/
│   │   └── platform.yaml     # Local development (Docker Compose)
│   ├── dev/
│   │   └── platform.yaml     # Development environment
│   └── prod/
│       └── platform.yaml     # Production template
├── demo/
│   └── floe.yaml             # Demo pipeline (logical refs only)
└── packages/
    └── floe-core/
        └── src/floe_core/
            ├── schemas/
            │   ├── platform_spec.py
            │   ├── credential_config.py
            │   └── floe_spec.py
            └── compiler/
                └── platform_resolver.py
```

## Batteries-Included floe-dagster

The two-tier architecture addresses **configuration separation**, but without corresponding runtime abstractions, data engineers still face significant boilerplate. This section documents the companion decision to make floe-dagster "batteries-included".

### Problem: Boilerplate Despite Configuration Separation

Even with clean `floe.yaml` files, the demo codebase revealed ~65% boilerplate in asset definitions:

| Boilerplate Category | Lines per Asset | Impact |
|---------------------|-----------------|--------|
| OpenTelemetry span creation | 10-15 | Repeated 5x |
| OpenLineage event emission | 15-20 | START/COMPLETE/FAIL per asset |
| Exception handling with observability | 10-15 | Try/except/finally ceremony |
| Platform config loading | 40+ | Module-level initialization |
| Catalog resource creation | 10 | Repeated per asset function |

**Result**: A 740-line definitions.py where only ~200 lines were business logic.

### Decision: @floe_asset as Primary API

floe-dagster provides a `@floe_asset` decorator that replaces Dagster's `@asset`:

```python
# BEFORE: Manual observability (740 LOC)
@asset(group_name="bronze")
def bronze_customers(context):
    job_name = "bronze_customers"
    run_id = _emit_lineage_start(job_name)
    span_context = None
    if _tracing_manager is not None:
        span_context = _tracing_manager.start_span("generate_customers", {...})
    try:
        span = span_context.__enter__() if span_context else None
        # ... business logic ...
        if span:
            span.set_attribute("data.rows", customers.num_rows)
            _tracing_manager.set_status_ok(span)
        _emit_lineage_complete(run_id, job_name, outputs=[...])
        return {...}
    except Exception as e:
        if span and _tracing_manager:
            _tracing_manager.record_exception(span, e)
        _emit_lineage_fail(run_id, job_name, str(e))
        raise
    finally:
        if span_context:
            span_context.__exit__(None, None, None)

# AFTER: Zero boilerplate (~300 LOC total)
@floe_asset(group="bronze", outputs=["demo.bronze_customers"])
def bronze_customers(context, catalog: PolarisCatalog) -> dict:
    generator = EcommerceGenerator(seed=42)
    customers = generator.generate_customers(count=1000)
    manager = IcebergTableManager(catalog)
    manager.overwrite("demo.bronze_customers", customers)
    return {"rows": customers.num_rows}
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ObservabilityOrchestrator` | `floe_dagster/observability/orchestrator.py` | Unified tracing + lineage context manager |
| `@floe_asset` | `floe_dagster/decorators.py` | Auto-instrumented asset decorator |
| `PolarisCatalogResource` | `floe_dagster/resources/catalog.py` | Dagster resource from CompiledArtifacts |
| `FloeDefinitions.from_compiled_artifacts()` | `floe_dagster/definitions.py` | One-line Definitions factory |

### Design Principles

1. **Observability failures never break pipelines**: If Jaeger/Marquez unavailable, log warning and continue
2. **Resource injection via signature**: `def my_asset(context, catalog: PolarisCatalog)` auto-injects catalog
3. **@floe_asset is the primary API**: Replaces raw @asset for all floe projects
4. **Zero platform code in assets**: No endpoints, credentials, or config loading visible to data engineers

### Relationship to Two-Tier Configuration

```
┌───────────────────────────────────────────────────────────────────────┐
│                     Two-Tier Configuration                            │
│                                                                       │
│  ┌─────────────────────┐           ┌─────────────────────┐            │
│  │   platform.yaml     │           │     floe.yaml       │            │
│  │ (endpoints, creds)  │           │  (profiles, logic)  │            │
│  └──────────┬──────────┘           └──────────┬──────────┘            │
│             │                                  │                       │
│             └──────────────┬───────────────────┘                       │
│                            ▼                                           │
│               ┌─────────────────────────────────┐                      │
│               │       CompiledArtifacts         │                      │
│               │   (merged, resolved config)     │                      │
│               └────────────────┬────────────────┘                      │
└────────────────────────────────┼───────────────────────────────────────┘
                                 │
┌────────────────────────────────┼───────────────────────────────────────┐
│                                ▼                                       │
│               ┌─────────────────────────────────┐                      │
│               │   FloeDefinitions.from_        │                      │
│               │   compiled_artifacts()          │                      │
│               └────────────────┬────────────────┘                      │
│                                │                                       │
│     ┌──────────────────────────┼──────────────────────────┐            │
│     ▼                          ▼                          ▼            │
│ ┌───────────────┐   ┌──────────────────────┐   ┌───────────────┐       │
│ │TracingManager │   │PolarisCatalogResource│   │LineageEmitter │       │
│ └───────────────┘   └──────────────────────┘   └───────────────┘       │
│                                │                                       │
│                                ▼                                       │
│              ┌────────────────────────────────────┐                    │
│              │         @floe_asset                │                    │
│              │  (auto-instruments all above)      │                    │
│              └────────────────────────────────────┘                    │
│                                                                        │
│                     Batteries-Included floe-dagster                    │
└────────────────────────────────────────────────────────────────────────┘
```

Two-tier configuration separates **what to configure**. Batteries-included floe-dagster hides **how to use that configuration**.

## Migration

Since floe-runtime has no prior releases, no migration is required. New projects should:

1. Create `platform/` directory with environment-specific configs
2. Update `floe.yaml` to use profile references
3. Set `FLOE_PLATFORM_ENV` for environment selection
4. Use `floe compile` to generate `CompiledArtifacts`

## References

- [Platform Configuration Guide](../platform-config.md)
- [Pipeline Configuration Guide](../pipeline-config.md)
- [Security Architecture](../security.md)
- [Yelp detect-secrets](https://github.com/Yelp/detect-secrets)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [OAuth2 Client Credentials](https://oauth.net/2/grant-types/client-credentials/)
