# Feature Specification: CLI Interface

**Feature Branch**: `002-cli-interface`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Create the developer-facing CLI (floe-cli) with commands: floe validate, floe compile, floe init, floe run, floe dev, floe schema export"

## Clarifications

### Session 2025-12-16

- Q: Should `--target` override an explicit property in the floe.yaml, or should floe.yaml support multiple target profiles that `--target` selects from? → A: CLI validates target exists in spec, uses existing config for that target

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Configuration (Priority: P1)

A developer creates or modifies a `floe.yaml` file and wants to verify it is syntactically correct and follows the schema before attempting to compile or run their pipeline.

**Why this priority**: Validation is the foundation of the developer workflow. Without quick validation feedback, developers waste time discovering errors during compilation or runtime. This is the most frequently used command in day-to-day development.

**Independent Test**: Can be fully tested by creating valid and invalid `floe.yaml` files and verifying the command correctly reports success or specific errors. Delivers immediate value for configuration authoring.

**Acceptance Scenarios**:

1. **Given** a valid `floe.yaml` file exists in the current directory, **When** the developer runs `floe validate`, **Then** the system displays a success message confirming the configuration is valid.
2. **Given** a `floe.yaml` file with schema violations exists, **When** the developer runs `floe validate`, **Then** the system displays clear error messages indicating the specific fields and issues without exposing internal stack traces.
3. **Given** no `floe.yaml` file exists in the current directory, **When** the developer runs `floe validate`, **Then** the system displays a helpful error message suggesting how to create one or specify a path.
4. **Given** a `floe.yaml` file at a custom path, **When** the developer runs `floe validate --file path/to/floe.yaml`, **Then** the system validates that specific file.

---

### User Story 2 - Compile Configuration to Artifacts (Priority: P1)

A developer wants to transform their validated `floe.yaml` into CompiledArtifacts JSON that can be consumed by downstream tools (Dagster, dbt).

**Why this priority**: Compilation is the critical transformation step in the pipeline workflow. It bridges configuration authoring and execution, making it essential for any productive use of the system.

**Independent Test**: Can be fully tested by compiling valid configurations and verifying the output JSON structure matches the CompiledArtifacts schema. Delivers the core value proposition of the tool.

**Acceptance Scenarios**:

1. **Given** a valid `floe.yaml` file, **When** the developer runs `floe compile`, **Then** the system generates `compiled_artifacts.json` in the output directory (default: `.floe/`).
2. **Given** a valid `floe.yaml` file, **When** the developer runs `floe compile --output custom/path/`, **Then** the system generates the artifacts at the specified location.
3. **Given** an invalid `floe.yaml` file, **When** the developer runs `floe compile`, **Then** the system displays validation errors and does not generate artifacts.
4. **Given** a valid `floe.yaml` with multiple compute targets, **When** the developer runs `floe compile --target snowflake`, **Then** the system generates artifacts for the specified target.

---

### User Story 3 - Export JSON Schema (Priority: P2)

A developer wants to export the JSON Schema for `floe.yaml` to enable IDE autocomplete and validation in their editor.

**Why this priority**: JSON Schema export improves developer experience significantly by enabling real-time feedback in editors, but it's a one-time setup task rather than a frequent operation.

**Independent Test**: Can be fully tested by exporting the schema and validating it against JSON Schema Draft 2020-12 specification. Delivers editor integration value.

**Acceptance Scenarios**:

1. **Given** the CLI is installed, **When** the developer runs `floe schema export`, **Then** the system outputs the FloeSpec JSON Schema to stdout.
2. **Given** the CLI is installed, **When** the developer runs `floe schema export --output schemas/floe.schema.json`, **Then** the system writes the schema to the specified file.
3. **Given** the CLI is installed, **When** the developer runs `floe schema export --type compiled-artifacts`, **Then** the system outputs the CompiledArtifacts JSON Schema instead.

---

### User Story 4 - Initialize New Project (Priority: P2)

A developer wants to quickly scaffold a new floe project with sensible defaults and example configuration.

**Why this priority**: Project initialization reduces friction for new users and ensures consistent project structure, but it's typically used only once per project.

**Independent Test**: Can be fully tested by running init in an empty directory and verifying the created files match expected templates. Delivers onboarding value.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** the developer runs `floe init`, **Then** the system creates a minimal `floe.yaml` with example configuration and a README explaining the structure.
2. **Given** an empty directory, **When** the developer runs `floe init --name my-project`, **Then** the system creates a `floe.yaml` with the project name set to "my-project".
3. **Given** a directory with an existing `floe.yaml`, **When** the developer runs `floe init`, **Then** the system warns about the existing file and does not overwrite unless `--force` is specified.
4. **Given** an empty directory, **When** the developer runs `floe init --target snowflake`, **Then** the system creates a `floe.yaml` pre-configured for Snowflake compute target.

---

### User Story 5 - Run Pipeline (Priority: P3)

A developer wants to execute their compiled pipeline through Dagster orchestration.

**Why this priority**: Pipeline execution is the ultimate goal, but it depends on Dagster integration (floe-dagster package) which is a separate implementation concern. This command orchestrates the full workflow.

**Independent Test**: Can be tested by running a compiled pipeline and verifying Dagster execution is triggered. Requires floe-dagster package to be functional.

**Acceptance Scenarios**:

1. **Given** a compiled `floe.yaml` with valid artifacts, **When** the developer runs `floe run`, **Then** the system executes the pipeline via Dagster and displays progress.
2. **Given** no compiled artifacts exist, **When** the developer runs `floe run`, **Then** the system automatically compiles first, then executes.
3. **Given** a compiled pipeline, **When** the developer runs `floe run --select model_name`, **Then** the system executes only the specified model and its dependencies.
4. **Given** a running pipeline, **When** execution fails, **Then** the system displays clear error messages indicating which step failed and why.

---

### User Story 6 - Start Development Environment (Priority: P3)

A developer wants to start a local development environment for iterative development and testing.

**Why this priority**: Development mode is valuable for iterative workflows but depends on multiple integrations (Dagster dev server, dbt, etc.) making it a later priority.

**Independent Test**: Can be tested by starting dev mode and verifying local services are accessible. Requires floe-dagster integration.

**Acceptance Scenarios**:

1. **Given** a valid `floe.yaml`, **When** the developer runs `floe dev`, **Then** the system starts a local Dagster development server and opens the UI.
2. **Given** the dev environment is running, **When** the developer modifies `floe.yaml`, **Then** the system automatically recompiles and reloads.
3. **Given** the dev environment is running, **When** the developer presses Ctrl+C, **Then** the system gracefully shuts down all services.
4. **Given** a valid `floe.yaml`, **When** the developer runs `floe dev --port 3001`, **Then** the system starts the dev server on the specified port.

---

### User Story 7 - Get Help and Version (Priority: P1)

A developer wants to quickly understand available commands and check the installed version.

**Why this priority**: Help and version information are fundamental to any CLI tool and essential for debugging and support.

**Independent Test**: Can be fully tested by running help commands and verifying output format and content. Delivers immediate utility.

**Acceptance Scenarios**:

1. **Given** the CLI is installed, **When** the developer runs `floe --help`, **Then** the system displays all available commands with brief descriptions in under 500ms.
2. **Given** the CLI is installed, **When** the developer runs `floe validate --help`, **Then** the system displays detailed help for the validate command including all options.
3. **Given** the CLI is installed, **When** the developer runs `floe --version`, **Then** the system displays the version number in a standard format.

---

### Edge Cases

- What happens when `floe.yaml` contains syntax errors (invalid YAML)?
  - System displays YAML parsing errors with line numbers, not internal exceptions.
- What happens when the user lacks write permissions to the output directory?
  - System displays a permission error with a clear message.
- What happens when compilation partially succeeds?
  - System rolls back partial outputs and reports which step failed.
- How does the system handle very large `floe.yaml` files (>1000 models)?
  - System processes efficiently without excessive memory usage; performance targets remain met.
- What happens when running `floe run` without Dagster installed?
  - System displays a clear error indicating the missing dependency and how to install it.
- What happens when `--target` specifies a target not defined in floe.yaml?
  - System displays an error listing the valid targets available in the spec.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `floe validate` command that validates `floe.yaml` against the FloeSpec schema.
- **FR-002**: System MUST provide a `floe compile` command that transforms FloeSpec into CompiledArtifacts JSON.
- **FR-003**: System MUST provide a `floe init` command that scaffolds a new project with template files.
- **FR-004**: System MUST provide a `floe run` command that executes pipelines via Dagster orchestration.
- **FR-005**: System MUST provide a `floe dev` command that starts a local development environment.
- **FR-006**: System MUST provide a `floe schema export` command that outputs JSON Schema for FloeSpec or CompiledArtifacts.
- **FR-007**: System MUST provide `--help` for the root command and all subcommands.
- **FR-008**: System MUST provide `--version` to display the installed version.
- **FR-009**: System MUST display user-friendly error messages without internal stack traces or implementation details.
- **FR-010**: System MUST support `--file` option for validate and compile commands to specify alternate config paths.
- **FR-011**: System MUST support `--output` option for compile and schema export commands to specify output location.
- **FR-012**: System MUST support `--target` option for compile command to select a compute target defined in floe.yaml; the CLI validates the target exists in the spec before compilation.
- **FR-013**: System MUST use colored terminal output for success, warning, and error states.
- **FR-014**: System MUST support `--no-color` option to disable colored output for CI/CD environments.
- **FR-015**: System MUST exit with code 0 on success and non-zero codes on failure.

### Key Entities

- **Command**: A CLI subcommand (validate, compile, init, run, dev, schema) with its options and arguments.
- **Configuration File**: The `floe.yaml` file containing pipeline configuration (FloeSpec).
- **Compiled Artifacts**: The JSON output produced by compilation (CompiledArtifacts).
- **Project Template**: Starter files created by `floe init` including example configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can see all available commands and options by running help in under 500 milliseconds.
- **SC-002**: Developers can validate a typical configuration file (50 models) in under 2 seconds.
- **SC-003**: 100% of validation errors display human-readable messages with specific field locations.
- **SC-004**: Developers can scaffold a new project and have a working configuration in under 1 minute.
- **SC-005**: All error messages are actionable - they indicate what went wrong and how to fix it.
- **SC-006**: The CLI works consistently across macOS, Linux, and Windows environments.
- **SC-007**: Zero internal exceptions or stack traces are exposed to end users under normal operation.
- **SC-008**: Developers can export JSON Schema and have working IDE autocomplete immediately.

## Assumptions

- Developers have Python 3.10+ installed in their environment.
- The floe-core package is installed as a dependency providing FloeSpec, Compiler, and CompiledArtifacts.
- For `floe run` and `floe dev` commands, the floe-dagster package will be required as an optional dependency.
- The default output directory for compiled artifacts is `.floe/` in the current working directory.
- Terminal color support detection follows standard practices (respects NO_COLOR environment variable, detects TTY).
- The CLI entry point will be installed as `floe` in the user's PATH via the package installation.

## Dependencies

- **floe-core**: Provides FloeSpec, Compiler, CompiledArtifacts, and JSON Schema export functions.
- **floe-dagster** (optional): Required for `floe run` and `floe dev` commands.

## Out of Scope

- GUI or web-based interfaces - this feature focuses solely on the command-line interface.
- Direct dbt or SQL execution - that is handled by floe-dbt package via Dagster orchestration.
- Remote/cloud deployment - this is for local development workflows.
- Plugin system for custom commands - may be considered for future iterations.
