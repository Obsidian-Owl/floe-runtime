# floe-cli

Developer CLI for floe-runtime.

## Overview

floe-cli provides the user-facing command-line interface for all floe-runtime operations.

## Installation

```bash
pip install floe-cli
```

## Commands

| Command | Purpose |
|---------|---------|
| `floe init` | Scaffold a new project |
| `floe validate` | Validate floe.yaml |
| `floe compile` | Generate CompiledArtifacts |
| `floe run` | Execute pipeline |
| `floe dev` | Start development environment |

## Usage

```bash
# Create a new project
floe init my-project

# Validate configuration
floe validate

# Compile artifacts
floe compile

# Run pipeline
floe run
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#3-floe-cli) for details.

## License

Apache 2.0
