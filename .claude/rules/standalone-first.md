# Standalone-First Philosophy

## CRITICAL: Every Feature Works Without SaaS

**MOST IMPORTANT**: Every feature in floe-runtime MUST work without requiring the Floe SaaS Control Plane.

### Non-Negotiable Rules

❌ **NEVER** assume Control Plane availability
❌ **NEVER** hardcode SaaS endpoints or proprietary integrations
❌ **NEVER** make features dependent on SaaS-only capabilities
✅ **ALWAYS** implement features that work standalone
✅ **ALWAYS** use standard open formats (Iceberg, OpenLineage, OTel)
✅ **ALWAYS** verify examples run without SaaS dependencies

### The Control Plane is Optional

The SaaS Control Plane is an **optional value-add**, not a requirement. It provides:
- Environment management (optional)
- Multi-tenant orchestration (optional)
- Enhanced observability UI (optional)
- Managed catalog (optional)

But the core runtime MUST function completely standalone.

## Architecture Principles

### CompiledArtifacts Contract

The `CompiledArtifacts` contract includes optional SaaS enrichments:

```python
class CompiledArtifacts(BaseModel):
    """Contract between floe-core and floe-dagster."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    # REQUIRED: Core functionality (standalone)
    version: str
    metadata: ArtifactMetadata
    compute: ComputeConfig
    transforms: list[TransformConfig]
    consumption: ConsumptionConfig
    governance: GovernanceConfig
    observability: ObservabilityConfig

    # OPTIONAL: SaaS enrichments (standalone-first: these are OPTIONAL)
    lineage_namespace: Optional[str] = None  # Set by Control Plane
    environment_context: Optional[EnvironmentContext] = None  # Set by Control Plane
```

**Key principle**: Optional fields are for SaaS enrichment, NOT requirements.

### Standard Open Formats

**ALWAYS use standard formats, NEVER proprietary:**

- **Storage**: Apache Iceberg (open table format)
- **Catalog**: REST API (Polaris, not proprietary)
- **Lineage**: OpenLineage (open standard)
- **Observability**: OpenTelemetry (open standard)
- **Orchestration**: Dagster (open source)
- **Transformations**: dbt (open source)
- **Semantic Layer**: Cube (open source)

### Local Development MUST Work

```bash
# Everything should work locally without SaaS
dbt debug  # ✅ Works with local profiles.yml
dagster dev  # ✅ Works with local Dagster instance
floe compile  # ✅ Generates CompiledArtifacts locally
floe run  # ✅ Executes pipeline locally
```

**No SaaS dependencies:**
- No API keys required
- No cloud connections required
- No managed services required
- Pure open-source stack

## Testing Standalone Functionality

**Before shipping any feature, verify:**

1. **Local execution**: Can it run on a laptop?
2. **No SaaS calls**: Grep for SaaS endpoints/APIs
3. **Standard formats**: Only Iceberg, OpenLineage, OTel
4. **Documentation**: Examples work without SaaS

```bash
# Verify no SaaS dependencies
rg "api\.floe\.cloud|floe-saas|proprietary" --type py
rg "FLOE_API_KEY|FLOE_TOKEN" --type py

# Should return nothing or only optional features
```

## SaaS Integration Pattern

When adding SaaS features, follow this pattern:

```python
def execute_pipeline(artifacts: CompiledArtifacts) -> RunResult:
    """Execute pipeline - works standalone or with SaaS enrichment."""

    # Core execution (REQUIRED, works standalone)
    result = run_transformations(artifacts)

    # Optional SaaS enrichment (graceful degradation)
    if artifacts.environment_context is not None:
        send_metrics_to_control_plane(artifacts.environment_context, result)
    else:
        logger.info("Running standalone - no Control Plane context")

    return result
```

**Pattern**:
- Core functionality in main path (no SaaS)
- SaaS features in optional branches (`if context is not None`)
- Graceful degradation (log, don't fail)

## Examples of Standalone-First

### ✅ CORRECT: Optional SaaS Enrichment

```python
# Works standalone
catalog = load_catalog(
    "local_catalog",
    type="rest",
    uri="http://localhost:8181"  # Local Polaris
)

# SaaS enrichment (optional)
if config.control_plane_enabled:
    catalog = enrich_with_managed_catalog(catalog, config.tenant_id)
```

### ❌ INCORRECT: SaaS Dependency

```python
# Requires SaaS - FORBIDDEN
catalog = load_catalog(
    "floe_managed",
    type="saas",
    api_key=os.environ["FLOE_API_KEY"]  # BREAKS STANDALONE
)
```

## Open Source Commitment

floe-runtime is **Apache 2.0 licensed** and community-driven:

- All code public on GitHub
- No proprietary dependencies
- No vendor lock-in
- Pure open-source stack
- Community contributions welcome

**This is NOT:**
- ❌ A SaaS-dependent framework
- ❌ A proprietary data platform
- ❌ A replacement for dbt/Dagster (we integrate with them)

**This IS:**
- ✅ An open-source data execution layer
- ✅ A type-safe, Pydantic-validated framework
- ✅ A security-first platform
- ✅ An enterprise-grade codebase
