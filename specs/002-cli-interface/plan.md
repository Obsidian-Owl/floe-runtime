# Implementation Plan: CLI Interface

**Branch**: `002-cli-interface` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-cli-interface/spec.md`

## Summary

Implement the floe-cli package with 6 commands (validate, compile, init, run, dev, schema export) that provide developer-facing operations for the floe-runtime system. The CLI uses Click for command structure and Rich for terminal formatting, integrating with floe-core's Compiler, FloeSpec, and export functions.

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution: Dagster/dbt minimum)
**Primary Dependencies**: Click 8.1+, Rich 13.9+, floe-core (FloeSpec, Compiler, CompiledArtifacts)
**Storage**: File-based (floe.yaml input, compiled_artifacts.json output to `.floe/`)
**Testing**: pytest with click.testing.CliRunner for CLI testing
**Target Platform**: macOS, Linux, Windows (WSL2) - cross-platform
**Project Type**: Package within uv workspace monorepo
**Performance Goals**: `floe --help` < 500ms, `floe validate` < 2s, `floe compile` < 5s
**Constraints**: No SaaS dependencies (standalone-first), user-friendly errors (no stack traces)
**Scale/Scope**: 6 commands, ~15 CLI options, integration with floe-core only (P1/P2 scope)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I. Standalone-First | ✅ PASS | CLI operates fully offline, no SaaS endpoints |
| II. Type Safety | ✅ PASS | All code uses type hints, Pydantic v2 via floe-core |
| III. Technology Ownership | ✅ PASS | CLI owns command interface, delegates to floe-core for compilation |
| IV. Contract-Driven | ✅ PASS | Uses CompiledArtifacts from floe-core, no direct FloeSpec passing to runtime |
| V. Security First | ✅ PASS | No eval/exec, user errors via FloeError (no stack traces), secrets via pydantic-settings |
| VI. Quality Standards | ✅ PASS | >80% coverage target, Black/isort/ruff/bandit compliance |

**Gate Status**: ✅ PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/002-cli-interface/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI argument schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/floe-cli/
├── pyproject.toml                     # Package config (exists, needs update)
├── README.md                          # Package docs
└── src/floe_cli/
    ├── __init__.py                    # Package exports
    ├── py.typed                       # PEP 561 marker
    ├── main.py                        # CLI entry point (@click.group)
    ├── commands/
    │   ├── __init__.py                # Command registration
    │   ├── validate.py                # floe validate command
    │   ├── compile.py                 # floe compile command
    │   ├── init.py                    # floe init command
    │   ├── run.py                     # floe run command (P3 stub)
    │   ├── dev.py                     # floe dev command (P3 stub)
    │   └── schema.py                  # floe schema export command
    ├── output.py                      # Rich console output utilities
    ├── errors.py                      # CLI error handling (wraps FloeError)
    └── templates/                     # floe init templates
        ├── floe.yaml.jinja2           # Default project template
        └── README.md.jinja2           # Project README template

packages/floe-cli/tests/
├── conftest.py                        # Shared fixtures (CliRunner, temp dirs)
├── unit/
│   ├── test_validate.py               # Validate command tests
│   ├── test_compile.py                # Compile command tests
│   ├── test_init.py                   # Init command tests
│   ├── test_schema.py                 # Schema export tests
│   └── test_output.py                 # Output utilities tests
├── integration/
│   ├── test_cli_workflow.py           # End-to-end CLI workflows
│   └── test_error_handling.py         # Error message quality tests
└── fixtures/
    ├── valid_floe.yaml                # Valid test config
    └── invalid_floe.yaml              # Invalid test config
```

**Structure Decision**: Single package within existing uv workspace monorepo. The floe-cli package scaffold already exists with stub files. Implementation will fill in the stubs and add new modules (output.py, errors.py, schema.py, templates/).

## Complexity Tracking

> No Constitution violations requiring justification. Design follows minimal complexity principles.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Template Engine | Jinja2 | Standard Python templating, already a transitive dependency |
| Output Formatting | Rich | Already in dependencies, provides tables, colors, progress |
| Error Handling | Wrap FloeError | Reuse floe-core exception hierarchy, don't duplicate |
| P3 Commands | Stubs Only | run/dev depend on floe-dagster, implement when that package exists |
