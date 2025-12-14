# floe-dbt

dbt integration for floe-runtime.

## Overview

floe-dbt provides:

- **Profile generation**: Generate profiles.yml from CompiledArtifacts
- **Executor**: Invoke dbt CLI with proper configuration
- **Adapter selection**: Choose dbt adapter based on compute target

## Installation

```bash
# Core package
pip install floe-dbt

# With DuckDB adapter (recommended for local dev)
pip install floe-dbt[duckdb]

# With Snowflake adapter
pip install floe-dbt[snowflake]
```

## Usage

```python
from floe_dbt import generate_profiles, DbtExecutor
from floe_core import CompiledArtifacts

# Generate profiles.yml
profiles = generate_profiles(artifacts)

# Execute dbt
executor = DbtExecutor(artifacts, profiles_dir)
executor.run("build")
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#5-floe-dbt) for details.

### Component Ownership

Per `.claude/rules/component-ownership.md`:
- **dbt owns ALL SQL** - floe-dbt only generates profiles.yml and invokes dbt CLI
- We NEVER parse SQL in Python

## License

Apache 2.0
