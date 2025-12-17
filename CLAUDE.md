# floe-runtime Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-15

## Active Technologies
- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts) (002-cli-interface)
- File-based (floe.yaml input, compiled_artifacts.json output to `.floe/`) (002-cli-interface)
- File-based (profiles.yml generated to `.floe/profiles/`, reads dbt manifest.json) (003-orchestration-layer)

- Python 3.10+ (per Constitution: Dagster/dbt minimum) + Pydantic v2, pydantic-settings, PyYAML, structlog (001-core-foundation)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+ (per Constitution: Dagster/dbt minimum): Follow standard conventions

## Recent Changes
- 003-orchestration-layer: Added Python 3.10+ (per Constitution: Dagster/dbt minimum)
- 002-cli-interface: Added Python 3.10+ (per Constitution: Dagster/dbt minimum) + Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts)

- 001-core-foundation: Added Python 3.10+ (per Constitution: Dagster/dbt minimum) + Pydantic v2, pydantic-settings, PyYAML, structlog

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
