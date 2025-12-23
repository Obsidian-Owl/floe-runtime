---
name: dagster-orchestration
description: ALWAYS USE when working with Dagster assets, resources, IO managers, schedules, or sensors. MUST be loaded before creating @asset decorators, ConfigurableResource classes, or orchestration code. Provides SDK research steps and integration patterns.
---

# Dagster Orchestration Development (Research-Driven)

## Philosophy

This skill does NOT prescribe specific implementation patterns. Instead, it guides you to:
1. **Research** the current Dagster version and API capabilities
2. **Discover** existing asset definitions and orchestration patterns in the codebase
3. **Validate** your implementations against Dagster SDK documentation
4. **Verify** integration with dbt, Iceberg, and other components

## Pre-Implementation Research Protocol

### Step 1: Verify Runtime Environment

**ALWAYS run this first**:
```bash
python -c "import dagster; print(f'Dagster {dagster.__version__}')"
```

**Critical Questions to Answer**:
- What version is installed?
- Does it support Python 3.9-3.13? (check compatibility)
- Are there breaking changes from previous versions?

### Step 2: Research SDK State (if unfamiliar)

**When to research**: If you encounter unfamiliar Dagster features or need to validate patterns

**Research queries** (use WebSearch):
- "Dagster software-defined assets documentation 2025"
- "Dagster [feature] Python API 2025" (e.g., "Dagster IO managers Python API 2025")
- "Dagster dbt integration best practices 2025"

**Official documentation**: https://docs.dagster.io

**Key API documentation**:
- Assets: https://docs.dagster.io/api/dagster/assets
- Resources: https://docs.dagster.io/api/dagster/resources
- IO Managers: https://docs.dagster.io/api/python-api/io-managers
- Definitions: https://docs.dagster.io/api/python-api/definitions

### Step 3: Discover Existing Patterns

**BEFORE creating new assets or resources**, search for existing implementations:

```bash
# Find existing asset definitions
rg "@asset|@multi_asset|@graph_asset" --type py

# Find resource definitions
rg "ConfigurableResource|ResourceDefinition" --type py

# Find IO manager definitions
rg "IOManager|io_manager_key" --type py

# Find schedules and sensors
rg "@schedule|@sensor|ScheduleDefinition|SensorDefinition" --type py
```

**Key questions**:
- What asset patterns are already in use?
- How are resources configured?
- What IO managers exist?
- Are there existing dbt integrations?

### Step 4: Validate Against Architecture

Check architecture docs for integration requirements:
- Read `/docs/` for CompiledArtifacts contract requirements
- Understand how Dagster consumes CompiledArtifacts
- Verify dbt integration patterns (dagster-dbt library)
- Check observability requirements (OpenTelemetry, OpenLineage)

## Implementation Guidance (Not Prescriptive)

### Software-Defined Assets

**Core concept**: Assets represent logical data units (tables, datasets, ML models)

**Research questions**:
- What data products need to be materialized?
- What are the asset dependencies (data lineage)?
- How should assets be partitioned (time-based, dimension-based)?
- What metadata should be attached to assets?

**SDK features to research**:
- `@asset` decorator: Basic asset definition
- `@multi_asset`: Assets with shared computation
- `@graph_asset`: Assets composed of ops
- Asset dependencies: `deps` parameter, `AssetIn`
- Asset metadata: `metadata` parameter, `MetadataValue`
- Partitions: `PartitionsDefinition`, `DailyPartitionsDefinition`

### Resources and Configuration

**Core concept**: Resources provide external services to assets (databases, APIs, file systems)

**Research questions**:
- What external services do assets need? (databases, S3, APIs)
- How should resources be configured? (environment variables, secrets)
- Are resources shared across multiple assets?
- What resource lifecycle management is needed?

**SDK features to research**:
- `ConfigurableResource`: Structured config base class
- `ResourceDefinition`: Raw resource definitions
- `with_resources()`: Binding resources to assets
- Resource context: `ResourceContext`, `InitResourceContext`

### IO Managers

**Core concept**: IO managers control how asset data is stored and retrieved

**Research questions**:
- Where should asset outputs be stored? (filesystem, database, object storage)
- What format should be used? (Parquet, CSV, Iceberg tables)
- How should data be partitioned on storage?
- Are there performance considerations for large datasets?

**SDK features to research**:
- `IOManager` interface: `handle_output()`, `load_input()`
- `io_manager_key`: Attaching IO managers to assets
- `IOManagerDefinition`: Configuring IO managers
- Built-in IO managers: `FilesystemIOManager`, `InMemoryIOManager`
- Third-party IO managers: `dagster-aws`, `dagster-gcp`, `dagster-iceberg`

### Schedules and Sensors

**Core concept**: Automate asset materialization based on time or events

**Research questions**:
- What assets should run on a schedule? (daily ETL, hourly refresh)
- What events should trigger asset materialization? (file uploads, API events)
- How should failures be handled?
- What notifications are needed?

**SDK features to research**:
- `@schedule`: Time-based automation
- `@sensor`: Event-based automation
- `@asset_sensor`: Monitor asset materializations
- `RunRequest`: Triggering asset runs
- `RunConfig`: Parameterizing runs

### dbt Integration

**Core concept**: Dagster assets can be created from dbt models

**Research questions**:
- How should dbt models be represented as Dagster assets?
- What dbt commands should be run? (compile, run, test, build)
- How should dbt artifacts (manifest.json) be loaded?
- What metadata from dbt should be propagated?

**SDK features to research**:
- `dagster-dbt` library: dbt integration utilities
- `load_assets_from_dbt_project()`: Generate assets from dbt
- `load_assets_from_dbt_manifest()`: Generate assets from manifest.json
- `DbtCliResource`: Execute dbt CLI commands
- dbt asset metadata: `materialize_to_messages()`, lineage extraction

## Validation Workflow

### Before Implementation
1. ✅ Verified Dagster version
2. ✅ Searched for existing asset/resource patterns in codebase
3. ✅ Read architecture docs to understand CompiledArtifacts contract
4. ✅ Identified integration requirements (dbt, Iceberg, observability)
5. ✅ Researched unfamiliar Dagster features

### During Implementation
1. ✅ Using `@asset` decorator for asset definitions
2. ✅ Type hints on ALL functions and parameters
3. ✅ Proper resource binding with `with_resources()`
4. ✅ IO managers configured for storage requirements
5. ✅ Asset dependencies correctly specified
6. ✅ Metadata attached to assets for observability

### After Implementation
1. ✅ Run Dagster development server: `dagster dev`
2. ✅ Verify assets appear in Dagster UI
3. ✅ Test asset materialization manually
4. ✅ Verify data lineage in UI
5. ✅ Test schedules/sensors trigger correctly
6. ✅ Check OpenTelemetry/OpenLineage integration

## Context Injection (For Future Claude Instances)

When this skill is invoked, you should:

1. **Verify runtime state** (don't assume):
   ```bash
   python -c "import dagster; print(dagster.__version__)"
   dagster --version
   ```

2. **Discover existing patterns** (don't invent):
   ```bash
   rg "@asset" --type py
   rg "ConfigurableResource" --type py
   ```

3. **Research when uncertain** (don't guess):
   - Use WebSearch for "Dagster [feature] documentation 2025"
   - Check official docs: https://docs.dagster.io

4. **Validate against architecture** (don't assume requirements):
   - Read relevant architecture docs in `/docs/`
   - Understand CompiledArtifacts contract (input to Dagster)
   - Check for existing Dagster Definitions

5. **Check dbt integration** (if working with dbt assets):
   - Verify `dagster-dbt` is installed
   - Check for existing dbt project paths
   - Understand dbt manifest.json location

## Quick Reference: Common Research Queries

Use these WebSearch queries when encountering specific needs:

- **Assets**: "Dagster software-defined assets examples 2025"
- **Resources**: "Dagster ConfigurableResource best practices 2025"
- **IO Managers**: "Dagster IOManager custom implementation 2025"
- **dbt integration**: "Dagster dbt integration load_assets_from_dbt_project 2025"
- **Partitions**: "Dagster partitions DailyPartitionsDefinition examples 2025"
- **Schedules**: "Dagster schedule decorator cron syntax 2025"
- **Sensors**: "Dagster sensor asset_sensor examples 2025"
- **Metadata**: "Dagster asset metadata MetadataValue 2025"
- **Observability**: "Dagster OpenTelemetry OpenLineage integration 2025"

## Integration Points to Research

### CompiledArtifacts → Dagster Assets

**Key question**: How does Dagster consume CompiledArtifacts?

Research areas:
- Where are CompiledArtifacts loaded from? (file path, environment variable)
- How are dbt models converted to Dagster assets?
- How are compute targets (from CompiledArtifacts) mapped to Dagster resources?
- What metadata from CompiledArtifacts propagates to asset metadata?

### dbt → Dagster Integration

**Key question**: How are dbt models represented as Dagster assets?

Research areas:
- `load_assets_from_dbt_manifest()` vs `load_assets_from_dbt_project()`
- dbt profile configuration (connection to compute targets)
- dbt command execution (`DbtCliResource`)
- dbt test results as Dagster asset checks
- dbt metadata extraction (classifications, lineage)

### Iceberg → Dagster IO Managers

**Key question**: How should Iceberg tables be read/written by Dagster?

Research areas:
- Custom IOManager for Iceberg tables
- PyIceberg integration with Dagster
- Polaris catalog integration
- Partition mapping (Dagster partitions → Iceberg partitions)

### Observability Integration

**Key question**: How should Dagster emit telemetry and lineage?

Research areas:
- OpenTelemetry exporter configuration
- OpenLineage integration (`dagster-openlineage`)
- Custom metadata extraction
- Trace context propagation

## Dagster Development Workflow

### Local Development
```bash
# Install Dagster
pip install dagster dagster-webserver dagster-dbt

# Verify installation
dagster --version

# Run development server
dagster dev

# Access UI at http://localhost:3000
```

### Testing Assets
```bash
# Materialize specific asset
dagster asset materialize --select asset_name

# Materialize all assets
dagster asset materialize

# Run tests
pytest tests/
```

## References

- [Dagster Documentation](https://docs.dagster.io): Official documentation
- [Software-Defined Assets](https://docs.dagster.io/concepts/assets/software-defined-assets): Core concept guide
- [dagster-dbt Integration](https://docs.dagster.io/_apidocs/libraries/dagster-dbt): dbt integration library
- [API Reference - Assets](https://docs.dagster.io/api/dagster/assets): Asset decorators and classes
- [API Reference - Resources](https://docs.dagster.io/api/dagster/resources): Resource definitions
- [API Reference - IO Managers](https://docs.dagster.io/api/python-api/io-managers): IO manager interfaces

---

**Remember**: This skill provides research guidance, NOT prescriptive patterns. Always:
1. Verify the runtime environment and Dagster version
2. Discover existing codebase patterns for assets and resources
3. Research SDK capabilities when needed (use WebSearch liberally)
4. Validate against actual CompiledArtifacts contract requirements
5. Test in Dagster UI before considering implementation complete
