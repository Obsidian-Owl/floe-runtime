# floe-core

Core schemas and compilation for floe-runtime.

## Overview

floe-core provides:

- **FloeSpec**: Pydantic schema for `floe.yaml` configuration
- **CompiledArtifacts**: Output contract consumed by other packages
- **Compiler**: Transform FloeSpec → CompiledArtifacts
- **JSON Schema export**: For IDE validation support

## Installation

```bash
pip install floe-core
```

## Usage

```python
from floe_core import FloeSpec, CompiledArtifacts, Compiler

# Parse and validate floe.yaml
spec = FloeSpec.model_validate(yaml_dict)

# Compile to artifacts
compiler = Compiler()
artifacts = compiler.compile(Path("floe.yaml"))

# Export JSON Schema for IDE support
schema = FloeSpec.model_json_schema()
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#2-floe-core) for details.

## License

Apache 2.0
