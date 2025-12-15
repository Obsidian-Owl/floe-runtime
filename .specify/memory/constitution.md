<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version Change: null → 1.0.0 (Initial Ratification)

Added Principles:
  - I. Standalone-First (NEW)
  - II. Type Safety Everywhere (NEW)
  - III. Technology Ownership (NEW)
  - IV. Contract-Driven Integration (NEW)
  - V. Security First (NEW)
  - VI. Quality Standards (NEW)

Added Sections:
  - Technology Constraints (NEW)
  - Quality Gates (NEW)

Removed Sections: None (initial version)

Template Alignment Status:
  - .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section)
  - .specify/templates/spec-template.md: ✅ Compatible (Requirements alignment)
  - .specify/templates/tasks-template.md: ✅ Compatible (Task categorization)
  - .specify/templates/checklist-template.md: ✅ Compatible (Checklist categories)

Follow-up TODOs: None

Source References:
  - .claude/rules/standalone-first.md → Principle I
  - .claude/rules/pydantic-contracts.md → Principles II, IV
  - .claude/rules/component-ownership.md → Principle III
  - .claude/rules/security.md → Principle V
  - .claude/rules/python-standards.md → Principle VI
================================================================================
-->

# floe-runtime Constitution

## Core Principles

### I. Standalone-First

Every feature in floe-runtime MUST work without requiring the Floe SaaS Control Plane.
The Control Plane is an optional value-add, never a requirement.

**Non-Negotiable Rules:**
- MUST NOT hardcode SaaS endpoints or proprietary integrations
- MUST NOT make features dependent on SaaS-only capabilities
- MUST use standard open formats: Iceberg (storage), OpenLineage (lineage),
  OpenTelemetry (observability), Polaris REST API (catalog)
- MUST verify all examples run without SaaS dependencies
- SaaS enrichments MUST be optional fields (e.g., `Optional[EnvironmentContext] = None`)

**Rationale:** Apache 2.0 licensing requires vendor independence. Users must trust that
the open-source runtime functions completely standalone. SaaS lock-in violates this trust.

### II. Type Safety Everywhere

All code MUST be statically typed with type hints. Pydantic v2 MUST be used for ALL
data validation, configuration, and API contracts.

**Non-Negotiable Rules:**
- MUST include `from __future__ import annotations` at top of every `.py` file
- MUST pass `mypy --strict` on all code
- MUST use modern generics (`list[str]`, `dict[str, int]`, not `List[str]`)
- MUST use Pydantic v2 syntax (`@field_validator`, `model_config`, `model_json_schema()`)
- Configuration MUST use Pydantic models with `pydantic-settings`
- Secrets MUST use `SecretStr` type (never plain `str`)

**Rationale:** Static typing catches errors at development time, not runtime. Pydantic
provides runtime validation with JSON Schema generation for IDE support and cross-system
contract validation.

### III. Technology Ownership

Each technology component owns its domain exclusively. Code MUST NOT cross ownership
boundaries.

**Non-Negotiable Rules:**
- **dbt**: MUST own ALL SQL. Python code MUST NOT parse, validate, or transform SQL
- **Dagster**: MUST own orchestration, assets, schedules, sensors
- **Iceberg**: MUST own storage format, ACID transactions, time travel, schema evolution
- **Polaris**: MUST own catalog management via REST API
- **Cube**: MUST own semantic layer and consumption APIs (REST/GraphQL/SQL)
- **OpenTelemetry/OpenLineage**: MUST own observability, traces, metrics, lineage

**Rationale:** Each tool is best-in-class at its domain. Crossing boundaries creates
maintenance burden, duplicates functionality, and introduces inconsistencies. Trust each
tool to do its job.

### IV. Contract-Driven Integration

CompiledArtifacts is the SOLE integration contract between packages. All inter-package
communication MUST flow through this immutable contract.

**Non-Negotiable Rules:**
- MUST NOT pass FloeSpec directly to runtime packages (only CompiledArtifacts)
- MUST use CompiledArtifacts as the only data exchange format between packages
- Contract changes MUST follow semantic versioning:
  - MAJOR: Breaking changes (remove field, change type, make optional → required)
  - MINOR: Additive changes (add optional field, new enum value)
  - PATCH: Documentation, internal refactoring (no schema changes)
- MUST maintain 3-version backward compatibility
- MUST export JSON Schema via `model_json_schema()` for validation
- MUST use `ConfigDict(frozen=True, extra="forbid")` for contract immutability

**Rationale:** A single, versioned, immutable contract enables independent package
development and testing. JSON Schema export allows cross-repository validation.

### V. Security First

All user input MUST be validated. Secrets MUST never be logged or exposed. Error
messages to users MUST NOT expose internal details.

**Non-Negotiable Rules:**
- MUST NOT use dangerous constructs:
  - `eval()`, `exec()`, `__import__()` (code injection)
  - `pickle.loads()` on untrusted data (deserialization attacks)
  - Raw SQL strings (SQL injection) - use parameterized queries
  - `subprocess.run(..., shell=True)` (command injection)
- MUST validate ALL user input with Pydantic before processing
- MUST use `SecretStr` for passwords, API keys, tokens
- MUST NOT log secrets, PII, or sensitive data
- Error messages to users MUST be generic; technical details logged internally only
- Dependencies MUST be updated within 7 days of critical CVE disclosure

**Rationale:** Security vulnerabilities destroy user trust and can expose sensitive data.
Defense in depth: validate at boundaries, never trust external input, fail safely.

### VI. Quality Standards

All code MUST meet strict quality standards for testing, formatting, and documentation.

**Non-Negotiable Rules:**
- MUST achieve greater than 80% test coverage
- MUST pass Black formatting (100 character line length)
- MUST pass isort import sorting (Black profile)
- MUST pass ruff linting (E, F, W, I, UP, B, SIM, C4 rules)
- MUST pass bandit security scanning
- MUST include Google-style docstrings on all public APIs with:
  - Description, Args, Returns, Raises, Examples sections
- Test pyramid: Unit tests (fast, isolated) → Integration tests (component interactions)
  → E2E tests (full workflows) → Property-based tests (edge cases via Hypothesis)

**Rationale:** Consistent quality across the codebase enables collaboration, reduces
review friction, and ensures maintainability. High test coverage catches regressions.

## Technology Constraints

**Runtime Requirements:**

| Constraint | Requirement | Rationale |
|------------|-------------|-----------|
| Python Version | 3.10+ required | Dagster and dbt minimum requirements |
| Pure Python | No compiled extensions | Cross-platform portability |
| Packaging | pyproject.toml (PEP 517/518) | Modern Python tooling |
| dbt-core | 1.7+ | Iceberg native support |
| Dagster | 1.6+ | Asset factory patterns |
| Iceberg | 1.4+, v2 table format | Industry momentum, features |
| Polaris | REST catalog API | Vendor-neutral catalog access |

**Supported Platforms:**

| Platform | Support Level |
|----------|---------------|
| macOS (Apple Silicon, Intel) | First-class |
| Linux (x86_64, ARM64) | First-class |
| Windows (WSL2) | Supported |
| Air-gapped environments | Must work without internet |

**Performance Targets:**

| Operation | Target |
|-----------|--------|
| `floe --help` | < 500ms |
| `floe validate` | < 2s |
| `floe compile` | < 5s |
| `floe run` startup | < 10s |

**Supported Compute Targets:**
DuckDB (development), Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark

## Quality Gates

**Pre-Commit Checklist (MANDATORY):**

- [ ] All type hints present (`mypy --strict` passes)
- [ ] All Pydantic models use v2 syntax
- [ ] Black formatting applied (100 char line length)
- [ ] isort applied (Black profile)
- [ ] ruff linting passes
- [ ] No secrets in code (`.env` not committed)
- [ ] No `eval()`, `exec()`, or dangerous constructs
- [ ] Error messages do not expose internals
- [ ] Logs do not contain secrets or PII
- [ ] Tests pass with > 80% coverage
- [ ] No security vulnerabilities (`bandit`, `pip-audit`, `safety`)
- [ ] Standalone verification (no SaaS dependencies)
- [ ] Google-style docstrings on public APIs

**CI Pipeline Gates:**

1. **Lint Gate**: `black --check`, `isort --check`, `ruff check` must pass
2. **Type Gate**: `mypy --strict` must pass
3. **Security Gate**: `bandit -r packages/`, `pip-audit`, `safety check` must pass
4. **Test Gate**: `pytest --cov` with > 80% coverage must pass
5. **Contract Gate**: JSON Schema validation, backward compatibility check

**Architecture Decision Records (ADRs):**

- Required for any technology ownership boundary change
- Required for any CompiledArtifacts contract modification
- Must document: Context, Decision, Alternatives Considered, Consequences

## Governance

**Constitution Supremacy**: This Constitution supersedes all other practices. When
conflicts arise between documentation, code comments, or conventions and this
Constitution, the Constitution wins.

**Amendment Process:**
1. Any principle change requires an Architecture Decision Record (ADR) documenting
   the rationale, alternatives considered, and migration plan
2. Breaking changes to principles require documented team consensus
3. Version bump required for amendments:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle added or material expansion
   - PATCH: Clarifications, wording, typo fixes
4. Migration plan required for any change affecting existing code

**Compliance Verification:**
- All PRs MUST include Constitution compliance verification
- CI pipeline enforces automated gates (formatting, typing, security, coverage)
- Code reviews MUST verify principle adherence
- Complexity violations MUST be documented in plan.md "Complexity Tracking" table
  with justification for why simpler alternative was rejected

**Reference Documents:**
- `.claude/rules/` - Detailed implementation guidance per principle
- `docs/` - Architecture documentation (arc42 format)
- `docs/adr/` - Architecture Decision Records

**Version**: 1.0.0 | **Ratified**: 2025-12-15 | **Last Amended**: 2025-12-15
