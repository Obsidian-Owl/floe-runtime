---
description: Compile floe.yaml into CompiledArtifacts (dbt profiles, Dagster config)
allowed-tools: Bash(python:*), Read, Write, Glob, Grep
argument-hint: [floe.yaml path] [--target TARGET]
model: sonnet
---

# Compile floe.yaml to CompiledArtifacts

Compile a floe.yaml specification into CompiledArtifacts JSON containing dbt profiles, Dagster configuration, and metadata.

## Arguments

- `$ARGUMENTS`: Optional arguments
  - First argument: Path to floe.yaml (default: search for floe.yaml)
  - `--target TARGET`: Override default target (e.g., `--target prod`)

## Pre-requisites Check

1. **Verify compiler exists**:
   - Search for compiler implementation: `rg "def compile_floe_spec|class Compiler" --type py`
   - Search for FloeSpec schema: `rg "class FloeSpec" --type py`
   - Search for CompiledArtifacts schema: `rg "class CompiledArtifacts" --type py`

2. **If compiler not implemented**:
   - Inform user: "Compiler not yet implemented. Would you like me to implement it?"
   - Provide guidance on what needs to be built (based on docs/04-building-blocks.md)
   - Stop here

## Compilation Process

### 1. Locate floe.yaml

- Parse `$ARGUMENTS` for file path
- If not provided, search: `find . -name "floe.yaml" -not -path "*/venv/*"`
- If multiple found, ask user which one
- If none found, error: "floe.yaml not found. Please provide path."

### 2. Parse and Validate floe.yaml

- **Read floe.yaml** using Read tool
- **Load as Python object** (YAML → dict → Pydantic)
- **Validate using FloeSpec schema**:
  ```python
  from floe_core.schemas import FloeSpec
  spec = FloeSpec.from_yaml_file("path/to/floe.yaml")
  ```
- **Check for validation errors**
- If errors, display clearly and stop

### 3. Extract Target

- **Determine target**:
  - If `--target TARGET` in `$ARGUMENTS`, use that
  - Else use `spec.default_target`
- **Validate target exists** in `spec.targets`
- **Extract compute configuration** for target

### 4. Compile Artifacts

Run the compiler (exact implementation depends on what exists):

```python
from floe_core.compiler import compile_floe_spec
from floe_core.contracts import CompiledArtifacts

artifacts: CompiledArtifacts = compile_floe_spec(
    spec=spec,
    target=target,
    strict=True
)
```

### 5. Generate Outputs

**CompiledArtifacts JSON**:
- Write to: `target/compiled_artifacts.json`
- Format: Pretty-printed JSON with indent=2
- Include: version, metadata, compute, transforms, consumption, governance, observability

**dbt profiles.yml** (if applicable):
- Write to: `$DBT_PROFILES_DIR/profiles.yml` or `packages/floe-dbt/profiles.yml`
- Extract from `artifacts.compute` configuration
- Format as valid dbt profiles YAML

**Dagster config** (if applicable):
- Include in CompiledArtifacts
- Document paths to dbt project, manifest, profiles

**Metadata files**:
- JSON Schema: Export `FloeSpec.model_json_schema()` to `schemas/floe.schema.json`
- JSON Schema: Export `CompiledArtifacts.model_json_schema()` to `schemas/compiled-artifacts.schema.json`

### 6. Verification

- **Verify outputs exist**:
  - `ls -lh target/compiled_artifacts.json`
  - `ls -lh $DBT_PROFILES_DIR/profiles.yml`
- **Validate JSON**:
  - Load compiled_artifacts.json and verify it parses
  - Check structure matches CompiledArtifacts schema
- **Summary**:
  ```
  ✅ Compilation successful

  Outputs:
  - CompiledArtifacts: target/compiled_artifacts.json (X.X KB)
  - dbt profiles:      packages/floe-dbt/profiles.yml
  - JSON Schemas:      schemas/*.schema.json

  Target: <target_name> (<compute_type>)
  Transforms: X models
  ```

## Error Handling

- **Schema validation errors**: Show field-level errors with context
- **Target not found**: List available targets
- **Compiler errors**: Show stack trace and suggest fixes
- **File write errors**: Check permissions, suggest alternatives

## Next Steps

After successful compilation:
1. Review CompiledArtifacts: `cat target/compiled_artifacts.json`
2. Verify dbt connection: `dbt debug`
3. Run transformations: Use Dagster or dbt commands
4. View lineage: `/trace` or `/lineage` commands
