# AI-Assisted Development Guide

This guide explains how to use AI tools (Claude Code, Cursor, Google Antigravity) effectively when developing floe-runtime.

## Overview

floe-runtime is optimized for AI-assisted development with:
- **Claude Code Skills**: Context-injecting guides for component SDKs
- **Slash Commands**: Workflow automation for common tasks
- **Modular Rules**: Focused coding standards and patterns
- **Type Safety**: Pydantic schemas guide AI code generation

## Quick Start

### Using Claude Code

1. **Initialize environment**:
   ```
   /init-dev-env
   ```

2. **Validate code**:
   ```
   /validate floe.yaml
   ```

3. **Compile spec**:
   ```
   /compile floe.yaml --target dev
   ```

4. **View lineage**:
   ```
   /lineage orders
   ```

### Using Skills

Skills automatically inject research steps and validation protocols:

- **Pydantic schemas**: Invoke `pydantic-schemas` skill when working with data models
- **Dagster assets**: Invoke `dagster-orchestration` skill for pipeline code
- **dbt models**: Invoke `dbt-transformations` skill for SQL transformations
- **Iceberg tables**: Invoke `pyiceberg-storage` skill for table operations
- **Polaris catalog**: Invoke `polaris-catalog` skill for catalog management
- **Cube semantic layer**: Invoke `cube-semantic-layer` skill for metrics/dimensions

## Directory Structure

```
floe-runtime/
├── .claude/
│   ├── CLAUDE.md              # Main project context (@imports architecture docs)
│   ├── settings.json          # Permissions, hooks, environment
│   ├── commands/              # Slash commands
│   │   ├── init-dev-env.md
│   │   ├── validate.md
│   │   ├── compile.md
│   │   ├── trace.md
│   │   └── lineage.md
│   ├── skills/                # Component SDK guides
│   │   ├── pydantic-skill/
│   │   ├── dagster-skill/
│   │   ├── dbt-skill/
│   │   ├── pyiceberg-skill/
│   │   ├── polaris-skill/
│   │   └── cube-skill/
│   └── rules/                 # Modular standards
│       ├── python-standards.md
│       ├── security.md
│       ├── standalone-first.md
│       ├── pydantic-contracts.md
│       └── component-ownership.md
├── .cursorrules               # Cursor AI configuration
├── .cursorignore              # Cursor context exclusions
└── docs/                      # Architecture documentation
```

## Skills System

### How Skills Work

Skills use **progressive disclosure** - they inject research steps rather than prescribing patterns:

1. **Verify runtime environment** (don't assume versions)
2. **Discover existing patterns** (search codebase)
3. **Research when uncertain** (use WebSearch)
4. **Validate against architecture** (read docs)

Example skill invocation:
```markdown
When working with Pydantic schemas, the pydantic-schemas skill will:
1. Verify Pydantic version: python -c "import pydantic; print(pydantic.__version__)"
2. Search for existing models: rg "class.*\(BaseModel\)" --type py
3. Research v2 syntax if needed
4. Guide you through validation workflow
```

### When to Use Which Skill

| Task | Skill | Description |
|------|-------|-------------|
| Define FloeSpec or CompiledArtifacts | `pydantic-schemas` | Schema validation, type safety |
| Create Dagster assets | `dagster-orchestration` | Software-defined assets, resources, IO managers |
| Write dbt models/tests | `dbt-transformations` | SQL transformations, dbtRunner API |
| Manage Iceberg tables | `pyiceberg-storage` | Table operations, ACID transactions |
| Configure Polaris catalog | `polaris-catalog` | Catalog, namespaces, access control |
| Define semantic layer | `cube-semantic-layer` | Metrics, dimensions, dbt integration |

## Slash Commands

### Development Lifecycle Commands

**`/init-dev-env`** - Set up development environment
- Verifies Python 3.10+
- Creates/activates venv
- Installs dependencies
- Initializes dbt and Dagster

**`/validate [file_path]`** - Run all quality checks
- Validates floe.yaml schema
- Runs mypy type checking
- Checks Black/isort formatting
- Runs Ruff linting
- Executes Bandit security scan
- Runs pytest with coverage

**`/compile [floe.yaml] [--target TARGET]`** - Compile floe.yaml
- Parses and validates FloeSpec
- Generates CompiledArtifacts JSON
- Creates dbt profiles.yml
- Exports JSON schemas

**`/trace [run_id]`** - Show execution traces
- Displays Dagster run timeline
- Shows OpenTelemetry spans
- Formats error details
- Links to Dagster UI

**`/lineage [asset_name]`** - Display data lineage
- Shows upstream/downstream dependencies
- Displays dbt DAG
- Shows classification propagation
- Generates Mermaid diagrams

**`/traceability [--feature-id ID] [--threshold N]`** - Generate coverage report
- Shows requirement-to-test traceability matrix
- Verifies 100% coverage requirement
- Identifies gaps for remediation
- JSON output for CI integration (`--format json`)

## Modular Rules

Rules are modular and can be @imported into CLAUDE.md or referenced independently:

### `.claude/rules/python-standards.md`
- Type safety requirements (`mypy --strict`)
- Code quality tools (Black, isort, Ruff)
- Testing standards (100% requirement traceability)
- Google-style docstrings

### `.claude/rules/security.md`
- Input validation (Pydantic for ALL inputs)
- Forbidden constructs (`eval`, `exec`, `pickle.loads`)
- Secret management (`SecretStr`)
- Error handling (never expose internals)

### `.claude/rules/standalone-first.md`
- Philosophy: Every feature works without SaaS
- Standard open formats (Iceberg, OpenLineage, OTel)
- Local development verification
- SaaS integration patterns (optional enrichments)

### `.claude/rules/pydantic-contracts.md`
- Pydantic v2 syntax (mandatory)
- CompiledArtifacts contract
- Backward compatibility rules
- JSON schema generation

### `.claude/rules/component-ownership.md`
- Technology ownership (dbt owns SQL, etc.)
- Package boundaries
- Integration contracts
- Testing isolation

## AI Development Workflow

### 1. Planning Phase

When starting a new feature:

```bash
# 1. Read architecture docs
cat docs/04-building-blocks.md

# 2. Understand the contract
cat docs/04-building-blocks.md | grep -A20 "CompiledArtifacts"

# 3. Check existing patterns
rg "class.*BaseModel" --type py
```

**AI Prompt**:
```
I need to implement [feature]. Please:
1. Read the architecture docs to understand requirements
2. Search for existing patterns in the codebase
3. Design the implementation following component ownership
4. Use appropriate Skills for each component
```

### 2. Implementation Phase

**Use Skills for context injection**:
```
When implementing the FloeSpec schema:
- Invoke pydantic-schemas skill
- Verify Pydantic version
- Search for existing schemas
- Follow v2 syntax strictly
```

**Use slash commands for validation**:
```
# After implementation
/validate

# Check type safety
mypy --strict packages/floe-core/
```

### 3. Testing Phase

```bash
# Unit tests (run on host - fast, no external deps)
uv run pytest packages/*/tests/unit/ --cov=packages --cov-report=term-missing

# Integration tests (MUST run in Docker)
./testing/docker/scripts/run-integration-tests.sh
# Or: make test-integration

# Check coverage and traceability
# Goal: 100% requirement coverage
python -m testing.traceability --all --threshold 100
```

**IMPORTANT**: Integration tests MUST run inside Docker. Running from host will fail
with `Could not resolve host: localstack` errors because Docker service hostnames
(localstack, polaris, trino, etc.) only resolve inside the Docker network.

**AI Prompt**:
```
Write comprehensive tests for [feature]:
1. Unit tests with mocks
2. Integration tests
3. Property-based tests with hypothesis
4. Edge cases and error conditions
```

### 4. Documentation Phase

```bash
# Generate JSON schemas
python -c "from floe_core.schemas import FloeSpec; print(FloeSpec.model_json_schema())"
```

**AI Prompt**:
```
Document [feature] with:
1. Google-style docstrings
2. Type hints on all signatures
3. Usage examples in docstrings
4. Update architecture docs if needed
```

### 5. Traceability Phase

After implementing and testing, verify requirement coverage:

```bash
# 1. Identify requirements: Which FR-XXX requirements does this feature address?
# Review the spec file for your feature (e.g., specs/006-integration-testing/spec.md)

# 2. Add markers: Ensure all tests have @pytest.mark.requirement() markers
# Example:
# @pytest.mark.requirement("006-FR-012")  # Feature 006, Requirement FR-012
# def test_polaris_catalog_connection():
#     ...

# 3. Verify coverage: Run traceability report
python -m testing.traceability --feature-id 006 --threshold 100

# 4. Multi-feature report (all features 001-006)
python -m testing.traceability --all --threshold 100
```

**Requirement ID Format**: Use feature-scoped format `{feature}-FR-{id}`:
- `006-FR-012` = Feature 006 (Integration Testing), Requirement FR-012
- `004-FR-001` = Feature 004 (Storage Catalog), Requirement FR-001

**Multi-Marker Pattern**: A single test can satisfy requirements from multiple features:
```python
@pytest.mark.requirement("006-FR-012")  # Meta: tests exist
@pytest.mark.requirement("004-FR-001")  # Functional: REST connection
@pytest.mark.requirement("004-FR-002")  # Functional: OAuth2 auth
def test_polaris_connection():
    """Test that covers multiple requirements from multiple features."""
    pass
```

**AI Prompt**:
```
Verify traceability for [feature]:
1. Which FR-XXX requirements does this implementation cover?
2. Add @pytest.mark.requirement() markers to all tests
3. Run /traceability to verify 100% coverage
4. Fix any gaps before marking work complete
```

## Best Practices for AI Assistance

### 1. Be Specific About Context

❌ **Vague**: "Add validation to the model"
✅ **Specific**: "Add Pydantic field validators to FloeSpec.project_name to ensure it's alphanumeric with max 100 chars"

### 2. Reference Architecture Docs

❌ **Assume**: "Create a new integration format"
✅ **Verify**: "Read docs/04-building-blocks.md to understand the CompiledArtifacts contract before implementing"

### 3. Use Skills Proactively

❌ **Generic**: "How do I use Dagster?"
✅ **Skill-based**: "Invoke dagster-orchestration skill and guide me through creating assets from CompiledArtifacts"

### 4. Validate Incrementally

❌ **Batch**: Write 500 lines, then validate
✅ **Incremental**: Write function → `/validate` → Next function

### 5. Search Before Creating

❌ **Assume**: "Create a new schema"
✅ **Discover**: `rg "class.*BaseModel" --type py` to find existing patterns first

## Common AI Workflows

### Creating a New Schema

```markdown
1. Invoke pydantic-schemas skill
2. Verify Pydantic v2 installed
3. Search for existing schemas: rg "class.*BaseModel"
4. Read architecture docs for requirements
5. Implement schema with:
   - from __future__ import annotations
   - Type hints on ALL fields
   - field_validator for validation
   - ConfigDict for configuration
6. Run /validate to check
7. Export JSON schema
```

### Creating Dagster Assets

```markdown
1. Invoke dagster-orchestration skill
2. Read CompiledArtifacts to understand inputs
3. Search for existing assets: rg "@asset" --type py
4. Implement assets with:
   - @asset decorator
   - Type hints on parameters
   - Proper dependencies (deps, AssetIn)
   - Metadata for observability
5. Test with dagster dev
6. Run /lineage to verify dependencies
```

### Writing dbt Models

```markdown
1. Invoke dbt-transformations skill
2. Verify dbt installed: dbt --version
3. Find existing models: find . -path "*/models/*.sql"
4. Implement models with:
   - Jinja templating ({{ ref() }}, {{ source() }})
   - Proper materialization
   - Tests in schema.yml
   - Meta tags for governance
5. Run dbt compile
6. Run dbt test
7. Use /lineage to verify DAG
```

## Troubleshooting AI Assistance

### "AI is not following standards"

→ Check if rules are properly @imported in `.claude/CLAUDE.md`
→ Use explicit references: "Follow .claude/rules/python-standards.md"

### "AI is inventing patterns instead of discovering"

→ Use Skills: They enforce discovery before invention
→ Remind: "Search for existing patterns with rg before creating new ones"

### "AI is using outdated syntax"

→ Invoke appropriate Skill: "Use pydantic-schemas skill to verify v2 syntax"
→ Reference: "Check .claude/skills/pydantic-skill/API-REFERENCE.md"

### "AI is crossing component boundaries"

→ Reference: ".claude/rules/component-ownership.md"
→ Remind: "dbt owns SQL - never parse SQL in Python"

## Integration with Other AI Tools

### Cursor

Cursor reads `.cursorrules` for project-specific guidance:
- Type safety requirements
- Pydantic v2 syntax
- Standalone-first philosophy
- Forbidden patterns

### Google Antigravity

Antigravity can leverage:
- Architecture docs in `/docs/`
- Modular rules in `.claude/rules/`
- Component boundaries
- Testing standards

## Continuous Improvement

The AI development configuration is version-controlled and evolves:

1. **Skills evolve**: Research-driven, not prescriptive
2. **Commands expand**: Add new workflows as needed
3. **Rules clarify**: Update based on common issues
4. **Documentation improves**: Add examples from real usage

**Contribute improvements**:
- Update Skills with new SDK patterns discovered
- Add slash commands for common workflows
- Refine rules based on code review feedback
- Document AI assistance patterns that worked well

## Summary

floe-runtime's AI development setup provides:

✅ **Research-driven Skills** - Context injection, not prescription
✅ **Workflow Commands** - Automate common development tasks
✅ **Modular Rules** - Focused, reusable coding standards
✅ **Type Safety** - Pydantic guides AI code generation
✅ **Progressive Disclosure** - Load context only as needed

This enables rapid, high-quality development while maintaining architectural integrity and security standards.
