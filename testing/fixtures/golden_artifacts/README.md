# Golden Artifacts for Contract Testing

This directory contains **static, versioned JSON files** that represent the blessed CompiledArtifacts contract. These are the immutable reference for contract testing.

## Purpose

Golden artifacts solve a critical testing gap:

1. **Contract Drift Detection**: If someone changes the `CompiledArtifacts` model, tests loading these static files fail immediately. Dynamic fixture factories adapt to model changes - static files don't.

2. **Consumer Contract Verification**: Downstream packages (floe-dagster, floe-dbt, floe-cube) can validate that their expectations still work against these blessed artifacts.

3. **Cross-Language Interop**: Go, Rust, or JavaScript consumers can validate against these JSON files without needing Python.

4. **Backward Compatibility**: Version-specific directories ensure we can test that v1.0.0 artifacts still load correctly after model updates.

## Directory Structure

```
golden_artifacts/
├── README.md               # This file
├── __init__.py             # Loading utilities
├── v1.0.0/
│   ├── minimal.json        # Required fields only with defaults
│   ├── full.json           # All fields populated
│   ├── docker_integration.json  # Docker test environment config
│   └── production.json     # Production-like configuration
└── v1.1.0/                 # Future versions
    └── ...
```

## Artifact Types

| Artifact | Purpose |
|----------|---------|
| `minimal.json` | Tests minimum viable artifact (required fields + defaults) |
| `full.json` | Tests all optional fields populated |
| `docker_integration.json` | Docker network hostnames for integration tests |
| `production.json` | Production-like config with all governance/observability |

## Usage

```python
from testing.fixtures.golden_artifacts import load_golden_artifact
from floe_core.compiler.models import CompiledArtifacts

# Load golden artifact
data = load_golden_artifact("v1.0.0", "minimal.json")

# Validate against model - fails if contract broken
artifacts = CompiledArtifacts.model_validate(data)

# Consumer-specific expectations
assert artifacts.compute.target.value == "duckdb"
assert artifacts.dbt_profiles_path == ".floe/profiles"
```

## When to Update Golden Artifacts

**DO NOT casually update these files.** They represent the contract.

Update golden artifacts when:
1. **Intentional contract evolution** (new version with new fields)
2. **Bug fix in artifact structure** (with version bump)
3. **Adding new artifact types** (e.g., `glue_catalog.json`)

**NEVER** update to "fix" a failing test - the test is telling you the contract changed!

## Schema Validation

Golden artifacts reference the exported JSON Schema:

```json
{
  "$schema": "../../../schemas/compiled_artifacts.v1.0.0.schema.json",
  "version": "1.0.0",
  ...
}
```

The schema is exported from the Pydantic model and committed to `testing/fixtures/schemas/`.

## Contract Evolution

When adding a new contract version:

1. Create `v1.1.0/` directory
2. Copy and update artifact files
3. Update `__init__.py` with new version
4. Add migration tests from v1.0.0 → v1.1.0
5. Export new JSON Schema

## Tests Using Golden Artifacts

- `tests/contract/test_golden_artifacts.py` - Core contract validation
- `packages/floe-dagster/tests/contract/test_consumer_contract.py` - Dagster expectations
- `packages/floe-dbt/tests/contract/test_consumer_contract.py` - dbt expectations
