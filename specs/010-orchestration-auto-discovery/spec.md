# Feature Specification: Orchestration Auto-Discovery

**Feature Branch**: `010-orchestration-auto-discovery`
**Created**: 2025-12-26
**Status**: Draft
**Input**: User description: "COMPREHENSIVE DESIGN VALIDATION - Feature 010"

## Clarifications

### Session 2025-12-26

- Q: Should the `orchestration` section extend the existing floe.yaml file, or should it be a separate orchestration configuration file? → A: Extend existing `floe.yaml` with new `orchestration:` section (alongside transforms, governance, observability)
- Q: Should the existing wrapper assets be immediately removed/replaced, or should there be a deprecation path allowing both patterns temporarily? → A: Immediate replacement - delete wrapper assets, implement auto-discovery (clean break, simplest migration)
- Q: Should data engineers organize assets in separate module files or keep them inline in the main definitions file? → A: Separate module files organized by layer/concern (e.g., `assets/bronze.py`, `assets/gold.py`, `assets/ops.py`) - recommended for scalability
- Q: Should `FloeDefinitions.from_compiled_artifacts()` be enhanced to auto-load assets from orchestration config, or should we create a new factory method? → A: Enhance existing `from_compiled_artifacts()` to auto-load assets when orchestration config present (single factory, simpler)
- Q: Should the demo refactoring be part of this feature's deliverables, or should it be a separate follow-up task? → A: Include demo refactoring in this feature - serves as acceptance tests and demonstrates complete workflow

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eliminate dbt Wrapper Boilerplate (Priority: P1)

As a data engineer, I want dbt models to automatically appear as individual assets in the orchestrator so that I can see per-model execution status and lineage without writing wrapper code.

**Why this priority**: This fixes a broken pattern in the current demo where dbt models are hidden inside wrapper assets, preventing visibility into individual model execution and breaking lineage tracking across the medallion architecture.

**Independent Test**: Can be fully tested using the refactored demo by verifying that each dbt model (stg_customers, stg_orders, stg_products, stg_order_items, customer_orders, revenue_by_product) appears as a separate asset in the orchestrator UI with individual execution traces and lineage events, replacing the old wrapper assets.

**Acceptance Scenarios**:

1. **Given** a pipeline definition with a dbt project path configured, **When** the orchestrator loads assets, **Then** each dbt model appears as a separate asset with its name, group, and dependencies
2. **Given** dbt models with upstream non-dbt assets, **When** the pipeline executes, **Then** lineage tracking shows connections from bronze assets through each silver model to gold models
3. **Given** a dbt model execution, **When** viewing observability data, **Then** individual spans and lineage events exist for that specific model (not a wrapper job)

---

### User Story 2 - Configure Orchestration Declaratively (Priority: P1)

As a data engineer, I want to define jobs, schedules, and sensors in a configuration file so that I can manage orchestration without writing Python code.

**Why this priority**: Reduces the 200+ lines of orchestration boilerplate currently required in demo code, enabling data engineers to focus on business logic rather than orchestration plumbing.

**Independent Test**: Can be fully tested by defining a simple job with a schedule in the configuration file and verifying that the job appears in the orchestrator UI and executes on the specified schedule without any Python code.

**Acceptance Scenarios**:

1. **Given** a configuration file with a job definition selecting bronze assets, **When** the orchestrator loads definitions, **Then** the job appears in the UI with the correct asset selection
2. **Given** a configuration file with a schedule for a job, **When** the schedule time arrives, **Then** the job executes automatically
3. **Given** a configuration file with a file watcher sensor, **When** a matching file appears, **Then** the associated job executes

---

### User Story 3 - Implement Partitioned Pipelines (Priority: P2)

As a data engineer, I want to configure time-based and static partitions for assets so that I can process data incrementally and backfill historical periods.

**Why this priority**: Enables production-grade incremental processing patterns essential for large-scale data pipelines, reducing compute costs and enabling efficient historical data processing.

**Independent Test**: Can be fully tested by defining a daily partition for bronze assets, running the pipeline for one day, verifying only that day's data is processed, then backfilling a historical range and confirming all partitions executed.

**Acceptance Scenarios**:

1. **Given** bronze assets configured with daily partitions, **When** executing for a specific date, **Then** only that date's partition is materialized
2. **Given** assets with hourly partitions, **When** viewing the orchestrator UI, **Then** each hour appears as a separate partition that can be materialized independently
3. **Given** assets with static partitions (e.g., regions), **When** executing, **Then** each region can be processed independently
4. **Given** a backfill configuration with a date range, **When** triggering the backfill, **Then** all partitions in the range execute in order with the specified batch size

---

### User Story 4 - Auto-Discover Python Assets (Priority: P2)

As a data engineer, I want to place asset definitions in Python modules and have them automatically loaded so that I don't need to manually register each asset.

**Why this priority**: Eliminates repetitive asset registration code and enables a clean file-based organization where assets are discovered based on directory structure.

**Independent Test**: Can be fully tested by creating a new Python module file (e.g., `assets/bronze.py`) with asset definitions, adding the module path to the orchestration configuration, and verifying assets appear in the orchestrator without any explicit registration code.

**Acceptance Scenarios**:

1. **Given** separate asset module files organized by layer (bronze.py, gold.py, ops.py), **When** module paths are listed in the orchestration configuration, **Then** all assets from those modules are loaded
2. **Given** multiple Python modules specified, **When** the orchestrator initializes, **Then** assets from all modules are available
3. **Given** an asset definition with group and compute kind metadata, **When** the asset is loaded, **Then** the metadata is preserved

---

### User Story 5 - Configure Event-Driven Execution (Priority: P3)

As a data engineer, I want to define sensors that trigger jobs based on file arrivals, upstream asset materializations, or job status changes so that I can build reactive pipelines.

**Why this priority**: Enables event-driven architectures for real-time data processing and automated reactions to pipeline failures, though not required for basic batch processing.

**Independent Test**: Can be fully tested by configuring a sensor that watches for asset materialization, materializing that asset, and verifying the sensor triggers the dependent job.

**Acceptance Scenarios**:

1. **Given** a sensor watching for specific asset materializations, **When** those assets are materialized, **Then** the associated job is triggered
2. **Given** a file watcher sensor configured with a path and pattern, **When** a matching file appears, **Then** the associated job executes
3. **Given** a run status sensor watching for job failures, **When** a watched job fails, **Then** the configured notification action executes

---

### User Story 6 - Configure Ops Maintenance Jobs (Priority: P3)

As a platform engineer, I want to define operational maintenance jobs (vacuum, compact, statistics) in the configuration so that I can schedule routine maintenance tasks.

**Why this priority**: Important for production operations but not critical for initial data pipeline functionality.

**Independent Test**: Can be fully tested by defining a vacuum job with a weekly schedule, waiting for the schedule time, and verifying the vacuum operation executes.

**Acceptance Scenarios**:

1. **Given** an ops job definition for vacuuming old snapshots, **When** the job executes, **Then** old snapshots are removed from the data lake
2. **Given** a maintenance schedule for weekly execution, **When** the schedule time arrives, **Then** the maintenance job runs automatically
3. **Given** an ops job with configurable parameters (e.g., retention days), **When** the job executes, **Then** the parameters are applied correctly

---

### Edge Cases

- What happens when a dbt manifest file is missing or invalid?
- How does the system handle circular dependencies in asset definitions?
- What happens when a sensor's external dependency (S3, file system) is unreachable?
- How are conflicts resolved when both schedules and automation conditions are defined for the same assets?
- What happens when a partition definition changes for an asset that already has materialized partitions?
- How does the system handle asset module paths that don't exist or contain syntax errors?
- What happens when a job references assets that don't exist?
- How are timezone differences handled across schedule execution and partition boundaries?

### Scope & Deliverables

**In Scope**:
- Core orchestration auto-discovery implementation (asset loading, dbt integration, jobs, schedules, sensors, partitions)
- Orchestration configuration schema extension to floe.yaml
- Demo refactoring as acceptance tests:
  - Remove wrapper assets (`silver_staging`, `gold_marts`)
  - Reorganize bronze assets into `demo/data_engineering/orchestration/assets/bronze.py`
  - Update `demo/data_engineering/floe.yaml` with orchestration section
  - Simplify `demo/data_engineering/orchestration/definitions.py` to just call factory
  - Verify end-to-end orchestration with per-model observability

**Out of Scope**:
- Advanced partitioning features beyond MVP (dynamic partitions deferred to P3)
- Custom sensor implementations beyond file_watcher and asset_sensor (run_status deferred to P3)
- Ops maintenance jobs (vacuum, compact) deferred to P3 unless trivial to include
- Production deployment patterns (Helm charts, K8s configurations)

### Migration Notes

- **Existing Wrapper Assets**: The current demo contains wrapper assets (`silver_staging`, `gold_marts`) that will be removed entirely and replaced with auto-discovered per-model assets from dbt manifest. No backwards compatibility layer needed as pre-release.
- **Asset Organization**: Current demo has bronze assets inline in `definitions.py`. These will be refactored into separate module files organized by layer (e.g., `assets/bronze.py`) to demonstrate scalable organization pattern.
- **FloeDefinitions Factory**: The existing `FloeDefinitions.from_compiled_artifacts()` method will be enhanced to auto-load assets from orchestration config when present. Manual asset passing (current pattern) will be removed.
- **Demo as Validation**: The refactored demo serves as the primary acceptance test for this feature, demonstrating the complete workflow from config to execution.

## Requirements *(mandatory)*

### Functional Requirements

#### Asset Auto-Discovery

- **FR-001**: System MUST load asset definitions from Python modules specified in the orchestration configuration via enhanced `FloeDefinitions.from_compiled_artifacts()` method
- **FR-002**: System MUST support specifying multiple module paths for asset discovery
- **FR-003**: System MUST preserve asset metadata (group, compute kind, description) from decorated definitions
- **FR-004**: System MUST detect and report errors for modules that don't exist or contain syntax errors
- **FR-005**: System MUST support both absolute and relative module paths

#### dbt Integration

- **FR-006**: System MUST auto-load dbt models as individual assets when a dbt manifest path is configured
- **FR-007**: System MUST create per-model observability spans and lineage events for each dbt model execution
- **FR-008**: System MUST extract asset dependencies from the dbt manifest to build the orchestrator dependency graph
- **FR-009**: System MUST support configuring dbt observability level (per-model vs job-level)
- **FR-010**: System MUST handle missing or invalid dbt manifest files gracefully with clear error messages

#### Partitioning

- **FR-011**: System MUST support time-based partitions with configurable start date and cron schedule
- **FR-012**: System MUST support static partitions with a list of values
- **FR-013**: System MUST support multi-dimensional partitions combining time and static dimensions
- **FR-014**: System MUST support dynamic partitions where keys are added at runtime
- **FR-015**: System MUST allow applying partition definitions to assets using pattern matching
- **FR-016**: System MUST support configuring backfill policies including max partitions per run
- **FR-017**: System MUST validate partition definition consistency (e.g., cron matches time window type)

#### Jobs

- **FR-018**: System MUST support defining jobs that select assets by group names
- **FR-019**: System MUST support defining jobs using asset selection expressions (union, intersection, exclusion)
- **FR-020**: System MUST support batch job type for data transformation workflows
- **FR-021**: System MUST support ops job type for maintenance operations
- **FR-022**: System MUST support specifying target module, function, and arguments for ops jobs
- **FR-023**: System MUST validate that job asset selections resolve to at least one asset

#### Schedules

- **FR-024**: System MUST support configuring cron-based schedules for jobs
- **FR-025**: System MUST support configuring timezone for schedule execution
- **FR-026**: System MUST support enabling/disabling schedules via boolean configuration
- **FR-027**: System MUST support environment variable interpolation in schedule configuration (e.g., enabled: ${SCHEDULE_ENABLED:false})
- **FR-028**: System MUST support partition selectors (latest, all) for scheduled execution of partitioned assets
- **FR-029**: System MUST validate cron expressions for correctness

#### Sensors

- **FR-030**: System MUST support file watcher sensors that monitor paths for matching files
- **FR-031**: System MUST support asset sensors that trigger when watched assets materialize
- **FR-032**: System MUST support run status sensors that react to job success or failure
- **FR-033**: System MUST support custom sensor types via module and function references
- **FR-034**: System MUST support configuring sensor polling intervals
- **FR-035**: System MUST validate sensor configuration (e.g., watched assets exist, paths are valid)

#### Automation Conditions

- **FR-036**: System MUST support eager automation condition for assets that update when upstream changes
- **FR-037**: System MUST support on_cron automation condition for scheduled asset updates
- **FR-038**: System MUST support on_missing automation condition for automatic backfilling
- **FR-039**: System MUST allow configuring automation conditions per asset using pattern matching
- **FR-040**: System MUST give precedence to automation conditions over schedules when both are defined for the same assets, as automation conditions provide more declarative and reactive orchestration patterns

#### Backfills

- **FR-041**: System MUST support defining backfill configurations with partition ranges
- **FR-042**: System MUST support configuring batch size for backfill execution
- **FR-043**: System MUST validate backfill partition ranges against partition definitions
- **FR-044**: System MUST support backfilling both time-based and static partitions

#### General

- **FR-045**: System MUST support environment variable interpolation in all configuration values using ${VAR:default} syntax
- **FR-046**: System MUST validate the orchestration configuration schema on load
- **FR-047**: System MUST provide clear error messages for configuration validation failures
- **FR-048**: System MUST support the same configuration file working across dev, staging, and prod environments via environment variable overrides

### Dependencies and Assumptions

**Dependencies**:
- Existing observability infrastructure for trace and lineage capture
- floe.yaml configuration file format (extends existing schema with orchestration section)
- Asset execution framework with decorator support for metadata
- Transformation framework (e.g., dbt) with manifest file generation

**Assumptions**:
- Asset modules follow standard Python import conventions
- Asset modules are organized in separate files by layer or concern (e.g., assets/bronze.py, assets/gold.py) rather than inline in definitions file
- Transformation model manifests are generated during build/compile phase
- Environment variables are available at application startup
- Orchestrator can poll external systems (file systems, S3) for sensor triggers
- Timezone configurations are available from the operating system
- Pre-release status allows breaking changes without migration paths

### Key Entities

- **OrchestrationConfig**: Top-level configuration containing asset modules, partitions, jobs, schedules, sensors, and backfills
- **PartitionDefinition**: Defines a partition scheme including type (time_window, static, multi, dynamic), name, and type-specific parameters
- **AssetConfig**: Pattern-based configuration applying partitions, automation conditions, and backfill policies to matching assets
- **JobDefinition**: Defines a job including name, type (batch, ops), asset selection or target function, and description
- **ScheduleDefinition**: Defines a schedule including name, job reference, cron expression, timezone, enabled status, and partition selector
- **SensorDefinition**: Defines a sensor including name, type (file_watcher, asset_sensor, run_status, custom), job reference, and type-specific configuration
- **BackfillDefinition**: Defines a backfill including name, job reference, partition range, and batch size

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Demo orchestration configuration (floe.yaml) is under 50 lines vs current 200+ lines of Python in definitions.py (95% reduction validated)
- **SC-002**: Each dbt model (stg_customers, stg_orders, stg_products, stg_order_items, customer_orders, revenue_by_product) appears as a separate asset in the orchestrator UI with individual execution status
- **SC-003**: Lineage tracking shows complete flows from bronze assets → individual silver models → individual gold models with per-model granularity
- **SC-004**: The same demo floe.yaml works across local/dev/staging/prod environments without modification (only environment variables change)
- **SC-005**: Data engineers can add new assets by creating module files (e.g., assets/ops.py) and listing in orchestration config, no registration code needed
- **SC-006**: Partitioned pipelines process only the specified partition's data (verifiable via output row counts) - validated in demo if time permits, otherwise deferred to P2
- **SC-007**: Backfills of 100+ partitions complete successfully with configurable batch processing - deferred to P2
- **SC-008**: Event-driven jobs trigger within 60 seconds of sensor condition being met - deferred to P3
- **SC-009**: Configuration validation catches schema errors before pipeline deployment, preventing runtime failures
- **SC-010**: Execution traces and data flow tracking are captured for every asset execution in demo, including dbt models, with zero code changes to asset definitions
