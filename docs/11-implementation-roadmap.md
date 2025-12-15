# 11. Implementation Roadmap

This document provides a structured breakdown for implementing floe-runtime using SpecKit and Beads. It serves as a tracker to guide spec definition and build sequencing.

---

## 1. Current State Assessment

| Aspect | Status |
|--------|--------|
| Architecture Documentation | Complete (arc42 format) |
| Package Scaffolding | Complete (7 packages) |
| Constitution | Ratified v1.0.0 |
| SpecKit Templates | Configured |
| Beads Tracking | Initialized (empty) |
| Implementation | Not started (~325 lines, mostly TODOs) |
| Tests | Not started (0 tests) |

---

## 2. Epic Overview

Five epics organized by dependency order:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Epic 1: Core Foundation                       │
│                         (floe-core)                              │
│                         [CRITICAL PATH]                          │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Epic 2: CLI     │  │ Epic 3: Orch.   │  │ Epic 4: Storage │
│ (floe-cli)      │  │ (dagster + dbt) │  │ (iceberg+polaris│
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Epic 5: Consume │
                    │ (floe-cube)     │
                    └─────────────────┘
```

---

## 3. Epic 1: Core Foundation

**Package**: `packages/floe-core/`
**Status**: [ ] Not Started
**Spec Location**: `features/core-foundation/`

### Features

| ID | Feature | Description | Spec Status | Build Status |
|----|---------|-------------|-------------|--------------|
| E1-F1 | FloeSpec Schema | Pydantic models for floe.yaml | [ ] | [ ] |
| E1-F2 | CompiledArtifacts Schema | Runtime contract | [ ] | [ ] |
| E1-F3 | Compiler | FloeSpec → CompiledArtifacts | [ ] | [ ] |
| E1-F4 | Error Hierarchy | FloeError, ValidationError, CompilationError | [ ] | [ ] |
| E1-F5 | JSON Schema Export | IDE support + validation | [ ] | [ ] |
| E1-F6 | Classification Extraction | dbt manifest → classifications | [ ] | [ ] |

### User Stories (for spec.md)

| Priority | Story | Acceptance Test |
|----------|-------|-----------------|
| P1 | As a developer, I can define my pipeline in floe.yaml and have it validated | `floe validate` succeeds on valid YAML |
| P2 | As a developer, I can compile floe.yaml to CompiledArtifacts | `floe compile` produces valid JSON |
| P3 | As a developer, I get IDE autocomplete via JSON Schema | VS Code shows completions |
| P4 | As a developer, I see clear error messages for invalid configuration | Errors include field + reason |

### Key Files to Create

```
packages/floe-core/src/floe_core/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── floe_spec.py          # FloeSpec, ComputeConfig, TransformConfig, etc.
│   └── compiled_artifacts.py  # CompiledArtifacts, ArtifactMetadata, etc.
├── compiler.py               # Compiler class
├── errors.py                 # Exception hierarchy
└── schema_export.py          # JSON Schema export functions
```

### Spec Definition Prompt

```
Feature: Core Foundation

Create the foundational package (floe-core) that defines:
1. FloeSpec schema for floe.yaml validation (Pydantic v2)
2. CompiledArtifacts contract consumed by all runtime packages
3. Compiler to transform FloeSpec → CompiledArtifacts
4. JSON Schema export for IDE autocomplete

Constraints:
- Pydantic v2 syntax (@field_validator, model_config, model_json_schema())
- Type hints everywhere (mypy --strict)
- CompiledArtifacts: frozen=True, extra="forbid"
- >80% test coverage
- Google-style docstrings

Compute targets: DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark

Configuration sections: name, version, compute, transforms, consumption, governance, observability
```

---

## 4. Epic 2: CLI Interface

**Package**: `packages/floe-cli/`
**Status**: [ ] Not Started
**Spec Location**: `features/cli-interface/`
**Depends On**: Epic 1

### Features

| ID | Feature | Description | Spec Status | Build Status |
|----|---------|-------------|-------------|--------------|
| E2-F1 | CLI Framework | Click group with version | [ ] | [ ] |
| E2-F2 | validate Command | Validate floe.yaml | [ ] | [ ] |
| E2-F3 | compile Command | Generate CompiledArtifacts | [ ] | [ ] |
| E2-F4 | init Command | Scaffold new project | [ ] | [ ] |
| E2-F5 | run Command | Execute pipeline via Dagster | [ ] | [ ] |
| E2-F6 | dev Command | Start dev environment | [ ] | [ ] |
| E2-F7 | schema export Command | Export JSON Schema | [ ] | [ ] |

### User Stories (for spec.md)

| Priority | Story | Acceptance Test |
|----------|-------|-----------------|
| P1 | As a developer, I can run `floe validate` to check my configuration | Exit 0 on valid, exit 1 on invalid |
| P2 | As a developer, I can run `floe compile` to generate artifacts | Creates .floe/artifacts.json |
| P3 | As a developer, I can run `floe init myproject` to scaffold | Creates project directory with templates |
| P4 | As a developer, I can run `floe run` to execute pipeline | Dagster materializes assets |
| P5 | As a developer, I can run `floe dev` for local environment | Docker Compose starts services |

### Spec Definition Prompt

```
Feature: CLI Interface

Create the developer-facing CLI (floe-cli) with commands:
- floe validate: Check floe.yaml against schema
- floe compile: Generate CompiledArtifacts JSON
- floe init: Scaffold new project from templates
- floe run: Execute pipeline via Dagster
- floe dev: Start local development environment
- floe schema export: Export JSON Schema

Constraints:
- Click 8.1+ for CLI framework
- Rich for terminal formatting
- Performance: floe --help < 500ms, floe validate < 2s
- Clear error messages (no stack traces to users)

Dependencies: floe-core (FloeSpec, Compiler, CompiledArtifacts)
```

---

## 5. Epic 3: Orchestration Layer

**Packages**: `packages/floe-dagster/`, `packages/floe-dbt/`
**Status**: [ ] Not Started
**Spec Location**: `features/orchestration-layer/`
**Depends On**: Epic 1

### Features

| ID | Feature | Description | Spec Status | Build Status |
|----|---------|-------------|-------------|--------------|
| E3-F1 | Profile Generation | CompiledArtifacts → profiles.yml | [ ] | [ ] |
| E3-F2 | DuckDB Profile | Local development target | [ ] | [ ] |
| E3-F3 | Snowflake/BigQuery Profile | Cloud targets | [ ] | [ ] |
| E3-F4 | Asset Factory | CompiledArtifacts → Dagster SDAs | [ ] | [ ] |
| E3-F5 | dbt Integration | dagster-dbt asset creation | [ ] | [ ] |
| E3-F6 | OpenLineage Emission | Lineage events during execution | [ ] | [ ] |
| E3-F7 | OpenTelemetry Tracing | Span creation per asset | [ ] | [ ] |

### User Stories (for spec.md)

| Priority | Story | Acceptance Test |
|----------|-------|-----------------|
| P1 | As a developer, I can run pipelines locally with DuckDB | Assets materialize to DuckDB |
| P2 | As a developer, I can see dbt models as Dagster assets | Dagster UI shows asset graph |
| P3 | As a developer, I can connect to Snowflake/BigQuery | Assets materialize to cloud warehouse |
| P4 | As a developer, I can view execution traces in Jaeger | Spans visible with correct parent-child |
| P5 | As a developer, I can view data lineage in Marquez | OpenLineage events recorded |

### Key Files to Create

```
packages/floe-dbt/src/floe_dbt/
├── profiles.py    # Profile generation (DuckDB, Snowflake, BigQuery, etc.)
└── executor.py    # DbtExecutor class

packages/floe-dagster/src/floe_dagster/
├── asset_factory.py   # create_definitions(), create_assets()
├── definitions.py     # Entry point for Dagster
├── lineage.py         # OpenLineage emission
└── tracing.py         # OpenTelemetry integration
```

### Spec Definition Prompt

```
Feature: Orchestration Layer

Create the orchestration layer (floe-dagster + floe-dbt) that:
1. Generates dbt profiles.yml from CompiledArtifacts
2. Creates Dagster Software-Defined Assets from dbt models
3. Emits OpenLineage events for data lineage
4. Creates OpenTelemetry spans for observability

Constraints:
- dagster 1.9+, dagster-dbt 0.25+
- dbt owns ALL SQL (no parsing/validation in Python)
- Dagster owns orchestration, assets, schedules
- OpenLineage events: START, COMPLETE, FAIL
- OpenTelemetry: span per asset materialization

Profile targets: DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark

Dependencies: floe-core (CompiledArtifacts)
```

---

## 6. Epic 4: Storage & Catalog

**Packages**: `packages/floe-iceberg/`, `packages/floe-polaris/`
**Status**: [ ] Not Started
**Spec Location**: `features/storage-catalog/`
**Depends On**: Epic 1, partially Epic 3

### Features

| ID | Feature | Description | Spec Status | Build Status |
|----|---------|-------------|-------------|--------------|
| E4-F1 | Polaris Client | REST API client | [ ] | [ ] |
| E4-F2 | Namespace Management | Create/list namespaces | [ ] | [ ] |
| E4-F3 | Iceberg Table Manager | Create/load tables | [ ] | [ ] |
| E4-F4 | Dagster IOManager | Iceberg IOManager for Dagster | [ ] | [ ] |
| E4-F5 | Compaction Manager | Table maintenance | [ ] | [ ] |
| E4-F6 | Snapshot Management | Time travel operations | [ ] | [ ] |

### User Stories (for spec.md)

| Priority | Story | Acceptance Test |
|----------|-------|-----------------|
| P1 | As a platform engineer, I can connect to Polaris catalog | Client authenticates successfully |
| P2 | As a platform engineer, I can create namespaces | Namespace appears in catalog |
| P3 | As a developer, I can write data to Iceberg tables | Table contains expected rows |
| P4 | As a developer, I can query historical snapshots | Time travel returns correct data |
| P5 | As an operator, I can compact small files | File count reduced |

### Spec Definition Prompt

```
Feature: Storage & Catalog

Create the storage layer (floe-iceberg + floe-polaris) that:
1. Connects to Apache Polaris REST catalog
2. Manages namespaces and table registration
3. Provides Iceberg table utilities (create, load, compact)
4. Implements Dagster IOManager for Iceberg writes

Constraints:
- pyiceberg 0.8+
- Polaris REST API (vendor-neutral)
- Iceberg owns storage format, ACID, time travel, schema evolution
- Polaris owns catalog management
- No hardcoded SaaS endpoints

Dependencies: floe-core (CompiledArtifacts)
```

---

## 7. Epic 5: Consumption Layer

**Package**: `packages/floe-cube/`
**Status**: [ ] Not Started
**Spec Location**: `features/consumption-layer/`
**Depends On**: Epics 1, 3, 4

### Features

| ID | Feature | Description | Spec Status | Build Status |
|----|---------|-------------|-------------|--------------|
| E5-F1 | Cube Config Generation | CompiledArtifacts → Cube config | [ ] | [ ] |
| E5-F2 | Model Sync | dbt models → Cube cubes (via cube_dbt) | [ ] | [ ] |
| E5-F3 | Security Context | Row-level security | [ ] | [ ] |
| E5-F4 | OpenLineage for Queries | Query lineage emission | [ ] | [ ] |
| E5-F5 | MCP Server Interface | AI agent integration | [ ] | [ ] |

### User Stories (for spec.md)

| Priority | Story | Acceptance Test |
|----------|-------|-----------------|
| P1 | As a developer, I can configure Cube from floe.yaml | Cube starts with correct config |
| P2 | As a developer, dbt models appear as Cube cubes | REST API returns cube metadata |
| P3 | As an analyst, I can query via REST API | JSON response with correct data |
| P4 | As an analyst, I can query via SQL (Postgres wire) | Connects via psql |
| P5 | As a platform engineer, row-level security filters data | Queries filtered by tenant_id |

### Spec Definition Prompt

```
Feature: Consumption Layer

Create the consumption layer (floe-cube) that:
1. Generates Cube configuration from CompiledArtifacts
2. Syncs dbt models to Cube cubes via cube_dbt package
3. Implements row-level security via security context
4. Emits OpenLineage events for query lineage
5. Exposes REST, GraphQL, and SQL (Postgres wire) APIs

Constraints:
- Cube owns semantic layer and consumption APIs
- cube_dbt package for dbt → Cube sync
- Security context: tenant_id column filtering
- OpenLineage events for query audit

See ADR-0001: Cube Semantic Layer for decision rationale.

Dependencies: floe-core, floe-dagster (for dbt manifest), floe-iceberg (for table access)
```

---

## 8. Implementation Phases

### Phase 1: Foundation (First Sprint)

```
[ ] E1-F1: FloeSpec Schema
[ ] E1-F2: CompiledArtifacts Schema
[ ] E1-F3: Compiler
[ ] E1-F4: Error Hierarchy
[ ] E2-F1: CLI Framework
[ ] E2-F2: validate Command
[ ] E2-F3: compile Command
```

**Milestone**: `floe validate` and `floe compile` work end-to-end

### Phase 2: Local Development (Second Sprint)

```
[ ] E3-F1: Profile Generation
[ ] E3-F2: DuckDB Profile
[ ] E3-F4: Asset Factory
[ ] E3-F5: dbt Integration
[ ] E2-F5: run Command
```

**Milestone**: `floe run` materializes assets to DuckDB

### Phase 3: Production Readiness (Third Sprint)

```
[ ] E1-F5: JSON Schema Export
[ ] E3-F3: Snowflake/BigQuery Profile
[ ] E3-F6: OpenLineage Emission
[ ] E3-F7: OpenTelemetry Tracing
[ ] E2-F4: init Command
[ ] E2-F6: dev Command
```

**Milestone**: Production-ready with observability

### Phase 4: Advanced Features (Fourth Sprint+)

```
[ ] E1-F6: Classification Extraction
[ ] E4-F1 through E4-F6: Storage & Catalog
[ ] E5-F1 through E5-F5: Consumption Layer
```

**Milestone**: Full feature set

---

## 9. Quality Checklist (Per Feature)

Before marking any feature complete, verify:

- [ ] Type Safety: `mypy --strict` passes
- [ ] Formatting: `black --check` passes
- [ ] Linting: `ruff check` passes
- [ ] Security: `bandit -r` passes
- [ ] Coverage: `pytest --cov --cov-fail-under=80` passes
- [ ] Docstrings: All public APIs documented (Google style)
- [ ] Constitution: All 6 principles verified

---

## 10. Beads Workflow

### Creating Work Items

```bash
# Create epic
bd create --title="Epic: Core Foundation" --type=epic

# Create features under epic
bd create --title="Feature: FloeSpec Schema" --type=feature
bd create --title="Feature: CompiledArtifacts Schema" --type=feature

# Add dependencies
bd dep add <compiled-id> <floespec-id>  # Compiled depends on FloeSpec

# Start work
bd update <id> --status=in_progress

# Complete work
bd close <id>
```

### Daily Workflow

```bash
bd ready            # Find available work
bd show <id>        # Review issue details
bd update <id> --status=in_progress  # Claim it
# ... implement ...
bd close <id>       # Mark complete
bd sync             # Push to remote
```

---

## 11. SpecKit Workflow

For each epic:

```bash
# 1. Create specification
/speckit.specify "Feature: [Epic Name] - [Description]"

# 2. Generate implementation plan
/speckit.plan

# 3. Generate task breakdown
/speckit.tasks

# 4. Convert to Beads issues
/speckit.taskstobeads

# 5. Implement (use Beads to track)
bd ready
bd update <id> --status=in_progress
# ... implement ...
bd close <id>
```

---

## 12. Reference Documents

| Document | Purpose |
|----------|---------|
| [00-overview.md](00-overview.md) | Project vision and scope |
| [01-constraints.md](01-constraints.md) | Technical and business constraints |
| [03-solution-strategy.md](03-solution-strategy.md) | Architecture decisions |
| [04-building-blocks.md](04-building-blocks.md) | Package responsibilities |
| [05-runtime-view.md](05-runtime-view.md) | Execution flows |
| [adr/0001-cube-semantic-layer.md](adr/0001-cube-semantic-layer.md) | Cube decision |
| [.specify/memory/constitution.md](../.specify/memory/constitution.md) | v1.0.0 principles |

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2025-12-15 | 1.0.0 | Initial roadmap created |
