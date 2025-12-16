# Feature Specification: Core Foundation Package (floe-core)

**Feature Branch**: `001-core-foundation`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Create the foundational package (floe-core) that defines FloeSpec schema for floe.yaml validation, CompiledArtifacts contract consumed by all runtime packages, Compiler to transform FloeSpec to CompiledArtifacts, and JSON Schema export for IDE autocomplete"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Pipeline Configuration (Priority: P1)

A data engineer wants to define their entire data pipeline in a single `floe.yaml` configuration file, specifying their compute target, transformations, consumption layer settings, governance policies, and observability configuration.

**Why this priority**: This is the foundational capability - without the ability to define and validate pipeline configuration, no other floe-runtime functionality can work. This enables the single-file pipeline definition that is the core promise of floe-runtime.

**Independent Test**: Can be fully tested by creating a valid `floe.yaml` file and loading it via the FloeSpec validation API. Delivers the ability to declaratively define pipelines.

**Acceptance Scenarios**:

1. **Given** a valid floe.yaml with all required fields (name, version, compute target), **When** the user loads the configuration via FloeSpec, **Then** the system returns a validated FloeSpec object with all defaults applied.

2. **Given** a floe.yaml with an invalid compute target (e.g., "oracle"), **When** the user attempts to load the configuration, **Then** the system returns a clear validation error identifying the invalid target and listing valid options.

3. **Given** a floe.yaml with nested optional sections (consumption, governance, observability), **When** the user omits these sections, **Then** the system applies sensible defaults (consumption disabled, default governance policies, observability enabled with traces/metrics/lineage).

4. **Given** a floe.yaml with secret references (connection_secret_ref, api_secret_ref), **When** the user loads the configuration, **Then** the system validates the reference follows Kubernetes naming convention (alphanumeric with hyphens/underscores, 1-253 characters) without attempting to resolve secrets (resolution happens at runtime).

---

### User Story 2 - Compile Configuration to Runtime Artifacts (Priority: P1)

A data engineer wants to compile their validated `floe.yaml` into `CompiledArtifacts` that can be consumed by downstream packages (floe-dagster, floe-dbt, floe-cube) without those packages needing to understand the raw floe.yaml format.

**Why this priority**: The compiler and CompiledArtifacts contract are the integration backbone - all other packages depend on this contract. Without compilation, there's no way to execute pipelines.

**Independent Test**: Can be fully tested by compiling a FloeSpec and verifying the resulting CompiledArtifacts JSON contains all expected sections. Delivers the integration contract between floe-core and all runtime packages.

**Acceptance Scenarios**:

1. **Given** a valid FloeSpec object, **When** the compiler processes it, **Then** the system produces a CompiledArtifacts object containing all configuration sections (compute, transforms, consumption, governance, observability) plus compilation metadata (timestamp, version, source hash).

2. **Given** a FloeSpec referencing a dbt project with models containing classification meta tags (floe.classification, floe.pii_type, floe.sensitivity), **When** the compiler processes the spec, **Then** the CompiledArtifacts includes extracted column_classifications mapping model name to column name to ColumnClassification metadata (classification, pii_type, sensitivity).

3. **Given** a FloeSpec with observability disabled, **When** the compiler processes the spec, **Then** the CompiledArtifacts reflects the disabled state for downstream packages to honor.

4. **Given** compiled artifacts, **When** serialized to JSON and deserialized back, **Then** the round-trip produces an identical CompiledArtifacts object (ensuring contract stability).

5. **Given** a valid FloeSpec object, **When** the compiler processes it, **Then** the CompiledArtifacts includes dbt_profiles_path (defaulting to `.floe/profiles/` relative to floe.yaml if not explicitly set).

---

### User Story 3 - Enable IDE Autocomplete for floe.yaml (Priority: P2)

A data engineer wants their IDE (VS Code, IntelliJ) to provide autocomplete suggestions and validation errors as they edit floe.yaml, making configuration authoring faster and less error-prone.

**Why this priority**: IDE support significantly improves developer experience but is not required for core functionality. Users can write valid YAML without IDE support.

**Independent Test**: Can be fully tested by exporting JSON Schema and validating that common IDEs recognize the schema reference and provide autocomplete. Delivers improved authoring experience.

**Acceptance Scenarios**:

1. **Given** a floe.yaml with the `$schema` directive pointing to the exported JSON Schema, **When** the user opens the file in VS Code with YAML extension, **Then** the IDE provides autocomplete for all valid configuration options.

2. **Given** the FloeSpec Pydantic model, **When** exporting to JSON Schema, **Then** the schema includes descriptions for all fields, enum values for constrained fields, and proper typing for nested objects.

3. **Given** an updated FloeSpec model with new fields, **When** re-exporting JSON Schema, **Then** the schema reflects the new fields with full documentation.

---

### User Story 4 - Validate Artifacts Contract for Cross-System Integration (Priority: P2)

A platform engineer wants to validate that CompiledArtifacts from floe-core will be compatible with the Go-based Control Plane, ensuring the contract is language-agnostic and stable.

**Why this priority**: Cross-language contract validation enables the SaaS Control Plane integration but is optional for standalone usage.

**Independent Test**: Can be fully tested by exporting CompiledArtifacts JSON Schema and validating sample artifacts against it from any language. Delivers interoperability guarantee.

**Acceptance Scenarios**:

1. **Given** the CompiledArtifacts Pydantic model, **When** exporting to JSON Schema, **Then** the schema is valid JSON Schema Draft 2020-12 that can be used by any JSON Schema validator.

2. **Given** a CompiledArtifacts object, **When** serialized to JSON, **Then** the output validates against the exported JSON Schema.

3. **Given** the CompiledArtifacts model with `extra="forbid"`, **When** attempting to create artifacts with unknown fields, **Then** validation fails with a clear error.

---

### User Story 5 - Support Multiple Compute Targets (Priority: P2)

A data engineer wants to use the same floe.yaml structure across different compute environments (DuckDB for development, Snowflake for production) with target-specific properties.

**Why this priority**: Multi-target support is essential for the development-to-production workflow but individual targets can be implemented incrementally.

**Independent Test**: Can be fully tested by creating FloeSpec configurations for each compute target and validating target-specific properties. Delivers target-agnostic pipeline definition.

**Acceptance Scenarios**:

1. **Given** a floe.yaml with `compute.target: duckdb`, **When** validating the configuration, **Then** the system accepts DuckDB-specific properties (path, extensions).

2. **Given** a floe.yaml with `compute.target: snowflake`, **When** validating the configuration, **Then** the system accepts Snowflake-specific properties (account, warehouse, role, database, schema).

3. **Given** a floe.yaml with `compute.target: bigquery`, **When** validating the configuration, **Then** the system accepts BigQuery-specific properties (project, dataset, location, method).

4. **Given** a floe.yaml with `compute.target: spark`, **When** validating the configuration, **Then** the system accepts Spark-specific properties (master, deploy_mode, configurations).

---

### User Story 6 - Configure Iceberg Catalog Integration (Priority: P2)

A data engineer wants to configure their Iceberg catalog (Polaris, Glue, or Nessie) so that floe-polaris and floe-iceberg packages can access table metadata and manage storage.

**Why this priority**: Catalog integration enables Iceberg storage but is optional for initial dbt-only workflows.

**Independent Test**: Can be fully tested by creating FloeSpec configurations with different catalog types and validating catalog-specific properties. Delivers catalog configuration for storage packages.

**Acceptance Scenarios**:

1. **Given** a floe.yaml with `catalog.type: polaris`, **When** validating the configuration, **Then** the system accepts Polaris-specific properties (uri, credential_secret_ref, warehouse).

2. **Given** a floe.yaml with `catalog.type: glue`, **When** validating the configuration, **Then** the system accepts Glue-specific properties (catalog_id, region).

3. **Given** a floe.yaml without a catalog section, **When** compiling to CompiledArtifacts, **Then** the catalog field is None and downstream packages skip Iceberg integration.

---

### Edge Cases

- What happens when floe.yaml is missing required fields? System returns clear validation error with field name and expected type.
- What happens when floe.yaml has YAML syntax errors? System catches parse errors before Pydantic validation and returns line/column location.
- What happens when dbt manifest.json doesn't exist during compilation? System gracefully skips classification extraction, logs warning, and continues.
- What happens when two transforms reference the same path? System allows it (dbt project may have multiple entrypoints).
- What happens when CompiledArtifacts version is incompatible with downstream package? Downstream packages validate version field and fail fast with upgrade instructions.
- What happens when catalog configuration is missing? System sets catalog to None; floe-polaris and floe-iceberg packages skip catalog operations gracefully.
- What happens when dbt_profiles_path is not set? Compiler defaults to `.floe/profiles/` directory relative to floe.yaml location.

## Requirements *(mandatory)*

### Functional Requirements

#### Schema Definition (FloeSpec)

- **FR-001**: System MUST define FloeSpec as an immutable configuration model that rejects unknown fields.
- **FR-002**: System MUST support seven compute targets: DuckDB, Snowflake, BigQuery, Redshift, Databricks, PostgreSQL, Spark.
- **FR-003**: System MUST validate compute target as an enum with string values matching dbt adapter names.
- **FR-004**: System MUST support transform configuration with type discriminator (initially only "dbt", extensible to "python", "flink").
- **FR-005**: System MUST define consumption configuration for Cube semantic layer (port, api_secret_ref, pre_aggregations, security).
- **FR-006**: System MUST define governance configuration with classification_source enum (dbt_meta, external) and policies mapping.
- **FR-007**: System MUST define observability configuration with toggles for traces, metrics, lineage, optional endpoint URLs, and optional attributes dictionary for custom trace context (e.g., tenant ID, environment type).
- **FR-008**: System MUST provide sensible defaults for all optional configuration sections.

#### Contract Definition (CompiledArtifacts)

- **FR-009**: System MUST define CompiledArtifacts as an immutable model that rejects unknown fields to ensure contract stability.
- **FR-010**: System MUST include metadata in CompiledArtifacts: compiled_at timestamp, floe_core_version, source_hash.
- **FR-011**: System MUST include all FloeSpec sections in CompiledArtifacts: compute, transforms, consumption, governance, observability.
- **FR-012**: System MUST support optional dbt-specific fields: dbt_manifest_path, dbt_project_path, dbt_profiles_path.
- **FR-013**: System MUST support optional SaaS enrichment fields: lineage_namespace, environment_context.
- **FR-014**: System MUST support optional governance extraction: column_classifications mapping (model name -> column name -> classification metadata containing classification string, optional pii_type string, and sensitivity string with default "medium").
- **FR-015**: System MUST version CompiledArtifacts (semantic versioning) with 3-version backward compatibility to enable contract evolution.
- **FR-028**: System MUST support optional catalog configuration for Iceberg catalog integration including catalog type (polaris, glue, nessie), URI, credential reference, warehouse name, and catalog-specific properties.

#### Compiler

- **FR-016**: System MUST compile FloeSpec to CompiledArtifacts via a Compiler class.
- **FR-017**: System MUST auto-detect dbt project location relative to floe.yaml path.
- **FR-018**: System MUST extract column classifications from dbt manifest.json meta tags when classification_source is dbt_meta.
- **FR-019**: System MUST compute SHA-256 hash of floe.yaml for change detection (source_hash).
- **FR-020**: System MUST include floe_core package version in compiled metadata.

#### JSON Schema Export

- **FR-021**: System MUST export FloeSpec to JSON Schema for IDE autocomplete support.
- **FR-022**: System MUST export CompiledArtifacts to JSON Schema for cross-language validation.
- **FR-023**: System MUST include field descriptions in exported JSON Schema (from Pydantic Field descriptions).
- **FR-024**: System MUST generate valid JSON Schema Draft 2020-12 compatible schemas.

#### Error Handling

- **FR-025**: System MUST define custom exception hierarchy: FloeError (base), ValidationError, CompilationError.
- **FR-026**: System MUST provide clear, actionable error messages that don't expose internal implementation details.
- **FR-027**: System MUST log technical error details internally while returning user-friendly messages.

### Key Entities

- **FloeSpec**: Root configuration model representing a complete floe.yaml definition. Contains name, version, compute config, transform list, consumption config, governance config, observability config.

- **ComputeTarget**: Enum of supported compute targets (duckdb, snowflake, bigquery, redshift, databricks, postgres, spark).

- **ComputeConfig**: Configuration for compute target including target enum, connection_secret_ref, and target-specific properties dictionary.

- **TransformConfig**: Configuration for a transformation step including type discriminator, path, and optional target override.

- **ConsumptionConfig**: Configuration for Cube semantic layer including enabled flag, port, security settings, pre-aggregation settings.

- **GovernanceConfig**: Configuration for data governance including classification_source enum, policies mapping, and lineage emission flag.

- **ObservabilityConfig**: Configuration for observability including trace/metric/lineage toggles and OTLP/lineage endpoint URLs.

- **CompiledArtifacts**: Output contract from compilation. Contains all config sections plus metadata, dbt paths, optional SaaS enrichments, and extracted classifications.

- **ArtifactMetadata**: Compilation metadata including compiled_at timestamp, floe_core_version string, source_hash string.

- **Compiler**: Stateless service that transforms FloeSpec to CompiledArtifacts with classification extraction.

- **CatalogConfig**: Configuration for Iceberg catalog integration including catalog type enum (polaris, glue, nessie), URI endpoint, credential_secret_ref, warehouse name, and type-specific properties dictionary.

- **EnvironmentContext**: Optional runtime context from Control Plane containing tenant_id (UUID), tenant_slug (string), project_id (UUID), project_slug (string), environment_id (UUID), environment_type (development, preview, staging, production), and governance_category (production, non_production).

- **PreAggregationConfig**: Configuration for Cube pre-aggregations including refresh_schedule (cron expression, default "*/30 * * * *") and timezone (string, default "UTC").

- **CubeSecurityConfig**: Configuration for Cube row-level security including row_level toggle (boolean, default true) and tenant_column (string, default "tenant_id").

- **ColumnClassification**: Classification metadata for a single column containing classification (string, e.g., "pii", "confidential"), optional pii_type (string, e.g., "email", "phone"), and sensitivity (string: "low", "medium", "high", default "medium").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can define a complete pipeline configuration and have it validated in under 100ms for typical floe.yaml files (< 500 lines).

- **SC-002**: 100% of FloeSpec fields have IDE autocomplete support when using exported JSON Schema with VS Code YAML extension.

- **SC-003**: Compilation from FloeSpec to CompiledArtifacts completes in under 500ms for projects with up to 200 dbt models.

- **SC-004**: Test coverage for floe-core package exceeds 80%.

- **SC-005**: All configuration models pass strict type checking with zero errors.

- **SC-006**: Users can round-trip CompiledArtifacts through JSON serialization with zero data loss.

- **SC-007**: Error messages for invalid configuration are understood by users without requiring documentation lookup, as validated by user testing.

- **SC-008**: JSON Schema export produces schemas that validate successfully with standard JSON Schema validators across multiple languages.

## Clarifications

### Session 2025-12-15

- Q: How many previous CompiledArtifacts versions should remain backward compatible? → A: 3 versions backward (current floe-runtime architecture standard)
- Q: What format should secret references (connection_secret_ref, api_secret_ref) use? → A: Alphanumeric with hyphens/underscores, 1-253 characters (Kubernetes secret naming convention)

## Assumptions

1. Users have Python 3.10+ installed.
2. dbt projects follow standard structure with manifest.json in `target/` directory.
3. Classification meta tags in dbt models follow the `floe:` namespace convention.
4. Secret resolution is handled at runtime by downstream packages, not during compilation.
5. YAML parsing uses safe loading (no arbitrary code execution).
6. All compute target property schemas will be defined as flexible structures initially, with stricter validation added per-target in future iterations.
