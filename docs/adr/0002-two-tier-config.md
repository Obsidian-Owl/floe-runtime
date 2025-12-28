# ADR-0002: Three-Tier Configuration Architecture

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

Adopt a **three-tier configuration architecture** that separates concerns across three layers:

### Tier 1: floe.yaml (Data Engineer Domain)

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

### Tier 2: platform.yaml (Platform Engineer Domain)

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

### Tier 3: values.yaml (Kubernetes/DevOps Domain)

Kubernetes operators define infrastructure deployment configuration:

```yaml
# values-prod.yaml - Owned by DevOps/Platform Ops
# Kubernetes-specific configuration only

# Platform config from Tier 2 (mounted as ConfigMap)
externalPlatformConfig:
  enabled: true
  configMapName: "floe-platform-config"
  configMapKey: "platform.yaml"

# Credentials via Kubernetes Secrets (references, not values)
dagster:
  dagster-user-deployments:
    deployments:
      - name: "customer-analytics"
        env:
          # ✅ TIER 3: Secret references, not values
          - name: POLARIS_CLIENT_ID
            valueFrom:
              secretKeyRef:
                name: polaris-credentials
                key: client-id
          - name: POLARIS_CLIENT_SECRET
            valueFrom:
              secretKeyRef:
                name: polaris-credentials
                key: client-secret

# Kubernetes resource configuration
resources:
  webserver:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

# High availability for production
replicaCount: 3
```

### Three-Tier Compilation and Deployment Model

```
TIER 1: floe.yaml          TIER 2: platform.yaml       TIER 3: values.yaml
(Data Engineer)            (Platform Engineer)         (K8s/DevOps)
─────────────────          ─────────────────────       ───────────────
Logical references         Infrastructure endpoints    K8s config + secrets
• storage: default         • S3 endpoint              • secretKeyRef
• catalog: default         • Polaris URI              • resource limits
• transforms: dbt          • secret_ref names         • replica count
                          • credential modes          • nodePort config
        │                           │                           │
        └───────────────┬───────────┘                           │
                        ▼                                       │
            ┌──────────────────────────┐                        │
            │   PlatformResolver       │                        │
            │ • Load platform.yaml     │                        │
            │ • Validate secret refs   │                        │
            └──────────┬───────────────┘                        │
                       ▼                                        │
            ┌──────────────────────────┐                        │
            │      Compiler            │                        │
            │ • Merge Tier 1 + Tier 2  │                        │
            │ • Generate artifacts     │                        │
            └──────────┬───────────────┘                        │
                       ▼                                        │
            ┌──────────────────────────┐                        │
            │   CompiledArtifacts      │                        │
            │ • Baked into Docker img  │                        │
            └──────────┬───────────────┘                        │
                       │                                        │
                       └────────────────┬───────────────────────┘
                                        ▼
                            ┌───────────────────────────┐
                            │   Helm Deployment         │
                            │ • Mount platform ConfigMap│
                            │ • Inject K8s Secrets      │
                            │ • Apply resource limits   │
                            └───────────────────────────┘
                                        │
                                        ▼
                            ┌───────────────────────────┐
                            │   Dagster Pod Running     │
                            │ • CompiledArtifacts       │
                            │ • Platform config mounted │
                            │ • Secrets injected        │
                            └───────────────────────────┘
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

## Multi-Repo Directory Structure

### Recommended: Two-Repo Architecture

```
platform-config/                    # 🔐 Platform Engineering Repo
├── platform/
│   ├── local/
│   │   └── platform.yaml          # LocalStack, Docker Desktop
│   ├── dev/
│   │   └── platform.yaml          # AWS dev, EKS
│   └── prod/
│       └── platform.yaml          # Production HA
├── charts/                         # Helm charts (Tier 3)
│   ├── floe-dagster/
│   │   ├── values.yaml            # BASE K8s defaults
│   │   ├── values-dev.yaml        # Dev overrides
│   │   └── values-prod.yaml       # Prod overrides
│   └── floe-infrastructure/
│       └── ...
└── secrets/
    ├── dev/
    │   └── sealed-secrets.yaml    # Encrypted credentials
    └── prod/
        └── sealed-secrets.yaml

customer-analytics/                # 📊 Data Engineering Repo
├── floe.yaml                      # Tier 1: Pipeline config
├── orchestration/
│   └── assets.py                  # Dagster assets
├── dbt/
│   └── models/                    # SQL transformations
├── Dockerfile                     # Builds image with CompiledArtifacts
└── .floe/
    └── compiled_artifacts.json    # Generated at build time
```

### Alternative: Monorepo (Demo Structure)

```
floe-runtime/demo/
├── platform-config/               # Simulates platform repo
│   ├── platform/
│   ├── charts/
│   └── secrets/
└── data-engineering/              # Simulates data repo
    ├── floe.yaml
    ├── orchestration/
    └── dbt/
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

Three-tier configuration separates **what to configure** (Tier 1), **where to deploy** (Tier 2), and **how to deploy** (Tier 3). Batteries-included floe-dagster hides the complexity of using that configuration.

## Multi-Repo CI/CD Workflow

### Platform Config Repo Release

```yaml
# .github/workflows/release.yaml (in platform-config repo)
name: Release Platform Config

on:
  push:
    tags:
      - 'platform-config-v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate platform configs
        run: |
          for env in local dev prod; do
            floe validate platform/\${env}/platform.yaml
          done

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            platform/*/platform.yaml
            charts/**/values-*.yaml
          body: |
            Platform configuration release \${{ github.ref_name }}

            **Changes**: See commit history
            **Compatibility**: floe-runtime >= v1.0.0
```

### Data Engineering Repo Build

```yaml
# .github/workflows/build-deploy.yaml (in data-engineering repo)
name: Build & Deploy

on:
  push:
    branches: [main]

env:
  PLATFORM_CONFIG_VERSION: "platform-config-v1.2.3"  # Pin platform version

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download platform config artifact
        run: |
          gh release download \$PLATFORM_CONFIG_VERSION \\
            --repo myorg/platform-config \\
            --pattern "platform-\${{ env.ENVIRONMENT }}.yaml" \\
            --dir .floe/

      - name: Compile artifacts
        run: |
          floe compile \\
            --floe-yaml=floe.yaml \\
            --platform-yaml=.floe/platform-\${{ env.ENVIRONMENT }}.yaml \\
            --output=.floe/compiled_artifacts.json

      - name: Build Docker image
        run: |
          docker build -t ghcr.io/myorg/customer-analytics:\${{ github.sha }} .

      - name: Push image
        run: docker push ghcr.io/myorg/customer-analytics:\${{ github.sha }}

      - name: Deploy with Helm
        run: |
          # Fetch Helm values from platform config
          gh release download \$PLATFORM_CONFIG_VERSION \\
            --repo myorg/platform-config \\
            --pattern "values-\${{ env.ENVIRONMENT }}.yaml"

          helm upgrade --install customer-analytics oci://ghcr.io/myorg/floe-dagster \\
            --values values-\${{ env.ENVIRONMENT }}.yaml \\
            --set image.tag=\${{ github.sha }}
```

### Artifact Version Pinning

Data engineering repos pin platform config versions:

```yaml
# .floe/platform-version.yaml (in data-engineering repo)
platform_config_version: "platform-config-v1.2.3"
compatibility:
  min_version: "platform-config-v1.2.0"
  max_version: "platform-config-v1.3.0"
```

**Benefits:**
- Data engineers control when to upgrade platform dependencies
- Platform engineers can release backward-compatible updates
- Easy rollback: change version pin, rebuild image

## Migration

Since floe-runtime has no prior releases, no migration is required. New projects should:

1. Create `platform-config/` repo with environment-specific configs
2. Create `charts/` directory with BASE values.yaml + overrides
3. Update `floe.yaml` to use profile references only
4. Use `floe compile` in CI/CD to generate `CompiledArtifacts`
5. Pin platform-config version in data engineering repos

## References

- [Platform Configuration Guide](../platform-config.md)
- [Pipeline Configuration Guide](../pipeline-config.md)
- [Security Architecture](../security.md)
- [Yelp detect-secrets](https://github.com/Yelp/detect-secrets)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [OAuth2 Client Credentials](https://oauth.net/2/grant-types/client-credentials/)
