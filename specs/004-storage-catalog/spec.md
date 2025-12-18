# Feature Specification: Storage & Catalog Layer

**Feature Branch**: `004-storage-catalog`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Create the storage layer (floe-iceberg + floe-polaris) that connects to Apache Polaris REST catalog, manages namespaces and table registration, provides Iceberg table utilities, and implements Dagster IOManager for Iceberg writes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect to Polaris Catalog (Priority: P1)

As a data engineer, I want to connect to an Apache Polaris REST catalog so that I can manage Iceberg tables in a centralized, vendor-neutral metadata store.

**Why this priority**: Catalog connectivity is the foundation for all storage operations. Without a working catalog connection, no tables can be created, loaded, or written to.

**Independent Test**: Can be fully tested by configuring catalog credentials in floe.yaml, running `floe compile`, and verifying the catalog connection succeeds. Delivers immediate value by enabling metadata management.

**Acceptance Scenarios**:

1. **Given** a floe.yaml with Polaris catalog configuration (URI, warehouse, credentials), **When** I run the application, **Then** a catalog connection is established using OAuth2 authentication
2. **Given** valid catalog credentials, **When** I attempt to list namespaces, **Then** the system returns the available namespaces from the catalog
3. **Given** invalid or expired credentials, **When** I attempt to connect, **Then** the system provides a clear authentication error message without exposing sensitive details
4. **Given** a catalog configuration with token refresh enabled, **When** the access token expires during a long-running operation, **Then** the system automatically refreshes the token and continues

---

### User Story 2 - Create and Manage Namespaces (Priority: P2)

As a data engineer, I want to create and manage hierarchical namespaces so that I can organize my Iceberg tables logically (e.g., bronze.events, silver.customers, gold.metrics).

**Why this priority**: Namespace management is required before tables can be created, as tables belong to namespaces. This enables the organizational structure for the data lake.

**Independent Test**: Can be fully tested by creating namespaces via the API, listing them, and verifying properties are persisted. Delivers value by enabling logical data organization.

**Acceptance Scenarios**:

1. **Given** a valid catalog connection, **When** I create a namespace with a name and properties, **Then** the namespace is created in the catalog with the specified properties
2. **Given** an existing namespace, **When** I attempt to create a namespace with the same name, **Then** the system either succeeds idempotently or returns a clear "already exists" message
3. **Given** nested namespace support (e.g., "bronze.raw.events"), **When** I create a nested namespace, **Then** parent namespaces are created automatically if they don't exist
4. **Given** a namespace with tables, **When** I attempt to delete the namespace, **Then** the system prevents deletion and returns a clear error message

---

### User Story 3 - Create and Load Iceberg Tables (Priority: P2)

As a data engineer, I want to create Iceberg tables with schemas and partition specifications so that I can define the structure for my data storage.

**Why this priority**: Table creation is essential for storing data. This is equally important as namespace management and enables actual data operations.

**Independent Test**: Can be fully tested by creating a table with a schema, loading it back, and verifying the schema matches. Delivers value by enabling schema-managed data storage.

**Acceptance Scenarios**:

1. **Given** a namespace and a table schema definition, **When** I create a table, **Then** the table is registered in the catalog with the correct schema and default properties
2. **Given** a schema with partition specification (e.g., daily partitioning on timestamp), **When** I create a table, **Then** the table is created with hidden partitioning configured
3. **Given** an existing table identifier, **When** I load the table, **Then** the system returns the table object with full schema and metadata
4. **Given** a table identifier that doesn't exist, **When** I attempt to load it, **Then** the system returns a clear "table not found" error
5. **Given** the need for safe table creation, **When** I use create-if-not-exists, **Then** the operation succeeds idempotently without errors if the table already exists

---

### User Story 4 - Write Data via Dagster IOManager (Priority: P1)

As a data engineer, I want Dagster assets to automatically write their outputs to Iceberg tables so that I can leverage Dagster's orchestration with Iceberg's storage benefits.

**Why this priority**: The IOManager integration is the primary interface for data pipeline execution. This enables the actual data flow and is required for floe-dagster integration.

**Independent Test**: Can be fully tested by defining a Dagster asset, materializing it, and verifying the data appears in the Iceberg table. Delivers value by enabling automated data pipeline storage.

**Acceptance Scenarios**:

1. **Given** a Dagster asset that returns data, **When** the asset is materialized, **Then** the data is written to an Iceberg table named after the asset key
2. **Given** a partitioned Dagster asset, **When** a partition is materialized, **Then** only that partition's data is written to the corresponding Iceberg partition
3. **Given** data with a schema that matches the existing table, **When** I write data, **Then** the data is appended to the table
4. **Given** data with an evolved schema (new columns), **When** I write data with schema evolution enabled, **Then** the table schema is automatically updated to include new columns
5. **Given** an asset materialization, **When** the write completes, **Then** metadata is attached including row count, snapshot ID, and table identifier

---

### User Story 5 - Read Data via Dagster IOManager (Priority: P2)

As a data engineer, I want Dagster assets to automatically read their inputs from Iceberg tables so that I can chain assets in a data pipeline.

**Why this priority**: Reading data is essential for multi-step pipelines where downstream assets depend on upstream outputs. This completes the IOManager contract.

**Independent Test**: Can be fully tested by defining an upstream and downstream asset, materializing both, and verifying the downstream asset receives the correct data. Delivers value by enabling data pipeline chaining.

**Acceptance Scenarios**:

1. **Given** a downstream asset that depends on an upstream asset, **When** the downstream asset is executed, **Then** it receives the data from the upstream asset's Iceberg table
2. **Given** a partitioned upstream asset, **When** the downstream asset requests a specific partition, **Then** only that partition's data is loaded
3. **Given** column projection metadata on the input, **When** data is loaded, **Then** only the specified columns are read (predicate pushdown)
4. **Given** a filter expression on the input, **When** data is loaded, **Then** only matching rows are returned (filter pushdown)

---

### User Story 6 - Time Travel Queries (Priority: P3)

As a data engineer, I want to query historical versions of my data so that I can debug issues, audit changes, or recover from errors.

**Why this priority**: Time travel is an advanced Iceberg feature that provides significant value but is not required for basic operations. It enhances data governance and debugging capabilities.

**Independent Test**: Can be fully tested by writing data, writing again, then querying the previous snapshot. Delivers value by enabling data audit and recovery.

**Acceptance Scenarios**:

1. **Given** a table with multiple snapshots, **When** I query with a specific snapshot ID, **Then** I receive the data as it existed at that snapshot
2. **Given** a table with historical data, **When** I query with an "as of" timestamp, **Then** I receive the data as it existed at that point in time
3. **Given** a table, **When** I list snapshots, **Then** I receive a list of all snapshots with their IDs, timestamps, and operation types

---

### User Story 7 - Table Maintenance Operations (Priority: P3)

As a data engineer, I want to perform maintenance operations like snapshot expiration so that I can control storage costs and metadata growth.

**Why this priority**: Maintenance is important for production systems but not required for initial functionality. This enables cost management and performance optimization.

**Independent Test**: Can be fully tested by creating snapshots, expiring old ones, and verifying they are removed. Delivers value by enabling storage cost control.

**Acceptance Scenarios**:

1. **Given** a table with old snapshots, **When** I expire snapshots older than a specified time, **Then** the old snapshots and their unreachable data files are removed
2. **Given** a table with many small files, **When** compaction is triggered externally (e.g., Spark), **Then** the table continues to function correctly with floe-runtime
3. **Given** snapshot expiration, **When** I specify retention period, **Then** the system respects the retention period and keeps recent snapshots

---

### Edge Cases

- What happens when the catalog is temporarily unavailable? The system uses a configurable retry policy (via floe.yaml) with sensible defaults: exponential backoff with jitter, capped maximum wait, and circuit breaker pattern. Clear timeout errors are provided after retries are exhausted.
- How does the system handle concurrent writes to the same table? Iceberg's optimistic concurrency ensures ACID compliance; conflicts result in retry or clear error messages.
- What happens when storage credentials are invalid? The system provides a clear error distinguishing catalog auth failure from storage auth failure.
- How does the system handle very large writes that exceed memory? The IOManager should support streaming/batched writes for large datasets.
- What happens when a table's schema is incompatible with the data being written? The system provides a clear schema mismatch error with details on incompatible fields.

## Requirements *(mandatory)*

### Functional Requirements

**Catalog Connection (floe-polaris)**

- **FR-001**: System MUST connect to Apache Polaris REST catalogs using the Iceberg REST Catalog specification
- **FR-002**: System MUST support OAuth2 client credentials authentication (client_id + client_secret)
- **FR-003**: System MUST support bearer token authentication for pre-fetched tokens
- **FR-004**: System MUST support automatic token refresh for long-running operations
- **FR-005**: System MUST support credential vending via `X-Iceberg-Access-Delegation: vended-credentials` header
- **FR-006**: System MUST NOT hardcode any SaaS-specific endpoints; all URIs MUST be configurable
- **FR-006a**: System MUST support configurable retry policies for catalog operations with sensible defaults (exponential backoff with jitter, capped maximum wait, circuit breaker pattern)

**Namespace Management (floe-polaris)**

- **FR-007**: System MUST support creating namespaces with custom properties
- **FR-008**: System MUST support listing namespaces at any level of the hierarchy
- **FR-009**: System MUST support deleting empty namespaces
- **FR-010**: System MUST support nested (hierarchical) namespaces (e.g., "bronze.raw.events")
- **FR-011**: System MUST support updating namespace properties

**Table Operations (floe-iceberg)**

- **FR-012**: System MUST support creating Iceberg tables with schema definitions
- **FR-013**: System MUST support partition specifications using Iceberg hidden partitioning (day, month, year, bucket, truncate, identity transforms)
- **FR-014**: System MUST support loading existing tables by identifier
- **FR-015**: System MUST support create-if-not-exists semantics for idempotent operations
- **FR-016**: System MUST support registering external tables by metadata location
- **FR-017**: System MUST support dropping tables (with optional purge of data)

**Data Operations (floe-iceberg)**

- **FR-018**: System MUST support appending data to tables
- **FR-019**: System MUST support overwriting data (full table or partition-level)
- **FR-020**: System MUST support schema evolution (add columns, widen types)
- **FR-021**: System MUST support time travel queries by snapshot ID or timestamp
- **FR-022**: System MUST support reading with column projection (predicate pushdown)
- **FR-023**: System MUST support reading with row filters (filter pushdown)

**Dagster Integration (floe-iceberg)**

- **FR-024**: System MUST provide a Dagster IOManager that writes asset outputs to Iceberg tables
- **FR-025**: System MUST provide a Dagster IOManager that reads asset inputs from Iceberg tables
- **FR-026**: System MUST support mapping Dagster asset keys to Iceberg table identifiers
- **FR-027**: System MUST support Dagster time-based partitions mapped to Iceberg partitions
- **FR-028**: System MUST support Dagster static partitions mapped to Iceberg partitions
- **FR-029**: System MUST attach metadata to materializations (row count, snapshot ID, table name)
- **FR-030**: System MUST support write modes: append, overwrite (configurable via asset metadata)

**Maintenance (floe-iceberg)**

- **FR-031**: System MUST support listing table snapshots with metadata
- **FR-032**: System MUST support expiring snapshots older than a specified time
- **FR-033**: System MUST support inspecting table files and partitions

**Integration with floe-core**

- **FR-034**: System MUST read catalog configuration from CompiledArtifacts (catalog.type, catalog.uri, catalog.warehouse, catalog.credentials)
- **FR-035**: System MUST respect the standalone-first philosophy; all features MUST work without SaaS Control Plane
- **FR-036**: System MUST use Pydantic models for all configuration and data validation
- **FR-037**: System MUST emit structured logs for catalog and table operations (using structlog, consistent with floe-dagster)
- **FR-038**: System MUST emit OpenTelemetry spans for catalog connection, namespace operations, and table read/write operations

### Key Entities

- **Catalog**: Represents a connection to a Polaris REST catalog. Contains URI, warehouse name, authentication credentials, and connection properties. One catalog can contain many namespaces.

- **Namespace**: A hierarchical container for tables (analogous to database schema). Has a name (potentially nested like "bronze.raw") and custom properties. Contains zero or more tables.

- **Table**: An Iceberg table with schema, partition spec, sort order, and properties. Has a unique identifier within a namespace. Contains snapshots representing versions of the data.

- **Schema**: The structure of a table including field names, types, nullability, and documentation. Supports evolution (adding fields, widening types).

- **PartitionSpec**: Defines how data is physically organized using hidden partitioning transforms (day, month, year, bucket, truncate, identity).

- **Snapshot**: A point-in-time version of a table's data. Has an ID, timestamp, operation type (append/overwrite/delete), and summary statistics.

- **IcebergIOManager**: A Dagster resource that handles reading and writing Iceberg tables for software-defined assets. Maps asset keys to table identifiers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure catalog connection and establish connectivity in under 5 minutes using documented configuration
- **SC-002**: Namespace and table operations complete within 2 seconds for metadata-only operations (create, load, list)
- **SC-003**: Data writes of 1 million rows complete within 60 seconds (excluding network latency to object storage)
- **SC-004**: Data reads with column projection reduce data scanned proportionally to columns selected
- **SC-005**: Time travel queries return results with the same latency as current snapshot queries (metadata lookup only)
- **SC-006**: 100% of authentication errors provide actionable error messages (no generic "authentication failed" without context)
- **SC-007**: IOManager integration passes 100% of Dagster's standard IOManager contract tests
- **SC-008**: All features work in standalone mode without any SaaS Control Plane dependencies
- **SC-009**: Configuration changes (catalog URI, credentials) do not require code changes; only floe.yaml updates
- **SC-010**: Package test coverage exceeds 80% for both floe-iceberg and floe-polaris

## Clarifications

### Session 2025-12-17

- Q: What retry behavior should the system use when the catalog is temporarily unavailable? → A: Configurable retry policy via floe.yaml with sensible defaults (exponential backoff with jitter, capped maximum, circuit breaker pattern)
- Q: What observability signals should the storage layer emit? → A: Structured logging + OpenTelemetry spans for catalog/table operations (aligns with floe-dagster observability architecture)

## Assumptions

Based on the feature description and project architecture, the following reasonable defaults are assumed:

1. **PyIceberg version**: 0.8+ as specified (the API is stable for this major version)
2. **Authentication scope**: Default to `PRINCIPAL_ROLE:ALL` for simplicity; users can override
3. **Token refresh**: Enabled by default for long-running operations
4. **Default write mode**: Append (can be overridden via asset metadata to "overwrite")
5. **Schema evolution**: Enabled by default; new columns are automatically added
6. **Namespace creation**: Creates parent namespaces automatically if they don't exist
7. **Table location**: Derived from warehouse + namespace + table name unless explicitly specified
8. **File format**: Parquet with default compression (configurable via table properties)
9. **IOManager data type**: Supports PyArrow Tables and Pandas DataFrames
10. **Asset key mapping**: Asset key path maps to namespace.table (e.g., `["bronze", "customers"]` -> `bronze.customers`)
