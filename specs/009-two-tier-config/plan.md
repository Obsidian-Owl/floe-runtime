# Implementation Plan: Two-Tier Configuration Architecture

**Branch**: `009-two-tier-config` | **Date**: 2025-12-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-two-tier-config/spec.md`

## Summary

Implement a two-tier configuration architecture that separates platform infrastructure (platform.yaml) from pipeline definitions (floe.yaml). Platform engineers configure storage, catalogs, compute, and observability with secure credential references (`secret_ref:`). Data engineers write pipelines using logical profile names (`catalog: default`) that resolve to environment-specific infrastructure at deploy time. This enables the same floe.yaml to work across dev/staging/prod without modification, with zero secrets in code.

## Technical Context

**Language/Version**: Python 3.10+ (compatible with Dagster 1.6+, dbt-core 1.7+)
**Primary Dependencies**: Pydantic v2, pydantic-settings, PyYAML, Click (CLI), Dagster, dbt-core
**Storage**: Iceberg tables via Polaris REST catalog; S3-compatible backends (MinIO, AWS S3, LocalStack)
**Testing**: pytest with pytest-cov (>80% coverage), mypy --strict, ruff, black (100 char)
**Target Platform**: macOS (Apple Silicon, Intel), Linux (x86_64, ARM64), Windows (WSL2)
**Project Type**: Monorepo with 7 packages (floe-core, floe-dagster, floe-dbt, floe-cube, floe-polaris, floe-iceberg, floe-cli)
**Performance Goals**: `floe validate` < 2s, `floe compile` < 5s, profile resolution < 100ms
**Constraints**: Standalone-first (no SaaS dependencies), pure Python only, secrets via SecretStr
**Scale/Scope**: 5 User Stories, 52 Functional Requirements, 6 Key Entities

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Standalone-First** | ✅ PASS | Feature explicitly requires environment variable fallbacks (FR-018), no SaaS dependencies |
| **II. Type Safety Everywhere** | ✅ PASS | All models will use Pydantic v2 with SecretStr for secrets (FR-009, FR-022, FR-048) |
| **III. Technology Ownership** | ✅ PASS | dbt owns SQL (unchanged), Dagster owns orchestration (unchanged), Polaris owns catalog (unchanged) |
| **IV. Contract-Driven Integration** | ✅ PASS | CompiledArtifacts remains the sole integration contract; profile resolution happens before compilation |
| **V. Security First** | ✅ PASS | Zero secrets in floe.yaml (FR-012), secret_ref pattern (FR-009), validation for hardcoded credentials (FR-013, FR-024) |
| **VI. Quality Standards** | ✅ PASS | 80%+ coverage required (FR-052), linting must pass (FR-051), comprehensive tests (FR-049, FR-050) |

**Gate Result**: ✅ PASS - All constitution principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/009-two-tier-config/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
│   ├── platform-spec.schema.json
│   └── floe-spec.schema.json
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/
├── floe-core/
│   └── src/floe_core/
│       ├── schemas/
│       │   ├── platform_spec.py      # NEW: PlatformSpec model
│       │   ├── credential_config.py  # NEW: CredentialConfig with modes
│       │   ├── storage_profile.py    # NEW: StorageProfile model
│       │   ├── catalog_profile.py    # NEW: CatalogProfile model
│       │   ├── compute_profile.py    # NEW: ComputeProfile model
│       │   └── floe_spec.py          # MODIFIED: Add profile references
│       └── compiler/
│           ├── platform_resolver.py  # NEW: Resolve platform.yaml + env fallback
│           ├── profile_resolver.py   # NEW: Resolve profile names to configs
│           ├── compiler.py           # MODIFIED: Merge FloeSpec + PlatformSpec
│           └── models.py             # MODIFIED: CompiledArtifacts v2.0
├── floe-polaris/
│   └── src/floe_polaris/
│       └── config.py                 # MODIFIED: Support CredentialConfig
├── floe-dagster/
│   └── src/floe_dagster/
│       └── resources.py              # MODIFIED: Use resolved profiles
├── floe-iceberg/
│   └── src/floe_iceberg/
│       └── config.py                 # MODIFIED: Support profile-based config
└── floe-cli/
    └── src/floe_cli/
        └── commands/
            └── platform.py           # NEW: `floe platform list-profiles`

demo/
├── orchestration/
│   ├── config.py                     # MODIFIED: Load from platform.yaml
│   └── definitions.py                # MODIFIED: Use profile-based config
└── floe.yaml                         # MODIFIED: Use logical references

platform/                             # NEW: Environment-specific configs
├── local/
│   └── platform.yaml                 # Local development platform config
├── dev/
│   └── platform.yaml                 # Example dev environment
├── staging/
│   └── platform.yaml                 # Example staging environment
└── prod/
    └── platform.yaml                 # Example prod environment

docs/
├── adr/
│   └── 0002-two-tier-config.md       # NEW: ADR for this design
├── platform-config.md                # NEW: Platform Configuration Guide
├── pipeline-config.md                # NEW: Pipeline Configuration Guide
└── security.md                       # NEW: Security Architecture

charts/
└── floe-dagster/
    ├── templates/
    │   └── platform-configmap.yaml   # NEW: ConfigMap from Helm values
    └── values.yaml                   # MODIFIED: Add platform.spec section

tests/
├── unit/
│   ├── test_platform_spec.py         # NEW: PlatformSpec unit tests
│   ├── test_profile_resolver.py      # NEW: Profile resolution tests
│   └── test_credential_config.py     # NEW: Credential mode tests
├── integration/
│   ├── test_platform_injection.py    # NEW: E2E with platform injection
│   └── test_profile_resolution.py    # NEW: Profile resolution integration
└── contract/
    ├── platform-spec.schema.json     # NEW: PlatformSpec JSON Schema
    └── floe-spec.schema.json         # MODIFIED: Profile-based FloeSpec
```

**Structure Decision**: Monorepo with 7 focused packages. New schemas added to floe-core (the schema owner). Platform environment directories follow Helm-style convention (`platform/<env>/platform.yaml`).

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Post-Design Constitution Re-Check

*Completed after Phase 1 design artifacts were generated.*

| Principle | Status | Post-Design Evidence |
|-----------|--------|---------------------|
| **I. Standalone-First** | ✅ PASS | PlatformResolver supports env var fallback when platform.yaml missing (research.md §3.6); all credential modes work without SaaS |
| **II. Type Safety Everywhere** | ✅ PASS | All schemas use Pydantic v2 with ConfigDict(frozen=True, extra="forbid"); SecretStr for all secrets; JSON Schema export for IDE support |
| **III. Technology Ownership** | ✅ PASS | Profile resolution in floe-core (owns schemas); no SQL parsing; dbt/Dagster/Polaris boundaries unchanged |
| **IV. Contract-Driven Integration** | ✅ PASS | CompiledArtifacts v2.0 defined with resolved profiles; contract version bump to 2.0.0 signals breaking change; JSON Schema published |
| **V. Security First** | ✅ PASS | SecretReference pattern validates secret_ref at schema level; sensitive field validation blocks plaintext; zero secrets in floe.yaml enforced |
| **VI. Quality Standards** | ✅ PASS | Test strategy defined in research.md §7; all packages must pass mypy --strict, ruff, black; >80% coverage requirement documented |

**Post-Design Gate Result**: ✅ PASS - All design artifacts comply with constitution.

---

## Phase 1 Completion Summary

**Artifacts Generated**:

| Artifact | Status | Description |
|----------|--------|-------------|
| [research.md](./research.md) | ✅ Complete | 10 design decisions documented with rationale |
| [data-model.md](./data-model.md) | ✅ Complete | 8 entities defined with relationships and examples |
| [contracts/platform-spec.schema.json](./contracts/platform-spec.schema.json) | ✅ Complete | JSON Schema for IDE autocomplete |
| [contracts/floe-spec.schema.json](./contracts/floe-spec.schema.json) | ✅ Complete | JSON Schema for IDE autocomplete |
| [contracts/compiled-artifacts.schema.json](./contracts/compiled-artifacts.schema.json) | ✅ Complete | Integration contract v2.0 schema |
| [quickstart.md](./quickstart.md) | ✅ Complete | Getting started guide for both personas |

**Ready for**: `/speckit.tasks` to generate implementation tasks.

---

## Phase 2: Batteries-Included floe-dagster

**Added 2025-12-24**: Architectural analysis revealed that Two-Tier Configuration solves **configuration separation** but not **developer experience**. The demo codebase contained ~65% boilerplate (740 of 1150 LOC) for observability, config loading, and resource management.

### Problem Discovered

Even with clean `floe.yaml` files, data engineers still wrote:
- 56 LOC for module-level observability initialization
- 280 LOC for per-asset span/lineage ceremony (70 LOC x 4 assets)
- 155 LOC for platform config loading functions
- 33 LOC for catalog resource creation (repeated 5 times)

**Root cause**: floe-dagster lacked high-level abstractions to consume CompiledArtifacts.

### Solution: Batteries-Included Abstractions

| Component | Location | Purpose |
|-----------|----------|---------|
| `ObservabilityOrchestrator` | `floe_dagster/observability/orchestrator.py` | Unified tracing + lineage context manager |
| `@floe_asset` | `floe_dagster/decorators.py` | Auto-instrumented asset decorator (replaces @asset) |
| `PolarisCatalogResource` | `floe_dagster/resources/catalog.py` | Dagster resource from CompiledArtifacts |
| `FloeDefinitions.from_compiled_artifacts()` | `floe_dagster/definitions.py` | One-line Definitions factory |

### New User Stories (added to spec.md)

- **US6 (P1)**: Data Engineer Writes Assets Without Observability Boilerplate
- **US7 (P1)**: Data Engineer's Code Contains Zero Platform Concerns

### New Requirements (FR-053 through FR-063)

See [spec.md](./spec.md) for full requirements.

### Delivery via Beads

| Bead ID | Title | Priority | Dependencies |
|---------|-------|----------|--------------|
| `floe-runtime-5qrc` | ObservabilityOrchestrator | P1 | None |
| `floe-runtime-5u2y` | @floe_asset + PolarisCatalogResource | P1 | 5qrc |
| `floe-runtime-0c7j` | FloeDefinitions.from_compiled_artifacts() | P1 | 5qrc, 5u2y |
| `floe-runtime-i43l` | Demo refactoring | P2 | 0c7j |

### Success Metrics

- Demo reduced from ~1,150 to ~400 LOC (60% reduction)
- Zero observability boilerplate in data engineer code
- Same demo code works in Docker Compose and K8s

