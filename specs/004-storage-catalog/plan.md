# Implementation Plan: Storage & Catalog Layer

**Branch**: `004-storage-catalog` | **Date**: 2025-12-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-storage-catalog/spec.md`

## Summary

Implement the storage layer for floe-runtime consisting of two packages:
- **floe-polaris**: Apache Polaris REST catalog client with OAuth2 authentication, namespace management, and configurable retry policies
- **floe-iceberg**: Iceberg table utilities via PyIceberg and Dagster IOManager for reading/writing assets to Iceberg tables

Technical approach: Leverage PyIceberg's RestCatalog for Polaris connectivity, implement ConfigurableIOManager for Dagster integration, use structlog + OpenTelemetry for observability consistent with floe-dagster.

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution: Dagster/dbt minimum)
**Primary Dependencies**:
- pyiceberg>=0.8 (Iceberg table operations, RestCatalog)
- dagster>=1.9 (IOManager integration)
- structlog>=24.0 (structured logging)
- opentelemetry-api>=1.28 (tracing)
- tenacity (retry policies with exponential backoff)
- floe-core (CompiledArtifacts, CatalogConfig)

**Storage**: Apache Iceberg tables via Polaris REST catalog (file-based metadata, Parquet data files)
**Testing**: pytest with >80% coverage, hypothesis for property-based tests, testcontainers for integration tests
**Target Platform**: Linux server (first-class), macOS (first-class), Windows WSL2 (supported)
**Project Type**: Monorepo with 2 packages (floe-iceberg, floe-polaris)
**Performance Goals**:
- Metadata operations (create, load, list): <2s
- 1M row writes: <60s (excluding network latency)
**Constraints**:
- Standalone-first (no SaaS dependencies)
- Pure Python only (no compiled extensions)
**Scale/Scope**: Production-ready packages for enterprise data pipelines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Standalone-First | ✅ PASS | All URIs configurable (FR-006), no SaaS hardcoding, standard open formats (Iceberg, Polaris REST API) |
| II. Type Safety Everywhere | ✅ PASS | Pydantic models for all config (FR-036), CatalogConfig already defined in floe-core |
| III. Technology Ownership | ✅ PASS | Iceberg owns storage format, Polaris owns catalog management - no boundary crossing |
| IV. Contract-Driven Integration | ✅ PASS | Reads catalog config from CompiledArtifacts (FR-034), immutable contract |
| V. Security First | ✅ PASS | OAuth2 credentials via SecretStr, no secrets logged (FR-037), actionable error messages (SC-006) |
| VI. Quality Standards | ✅ PASS | >80% test coverage (SC-010), structured logging, Google-style docstrings |

**Gate Result**: PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/004-storage-catalog/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/
├── floe-polaris/
│   ├── src/floe_polaris/
│   │   ├── __init__.py          # Public API exports
│   │   ├── client.py            # PolarisCatalogClient wrapper
│   │   ├── factory.py           # create_catalog() factory function
│   │   ├── config.py            # Pydantic config models (RetryConfig, etc.)
│   │   ├── namespaces.py        # Namespace management operations
│   │   ├── retry.py             # Configurable retry with tenacity
│   │   ├── observability.py     # Structured logging + OTel spans
│   │   └── errors.py            # Custom exceptions
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_client.py
│   │   │   ├── test_config.py
│   │   │   ├── test_namespaces.py
│   │   │   └── test_retry.py
│   │   └── integration/
│   │       └── test_polaris_catalog.py
│   └── pyproject.toml
│
├── floe-iceberg/
│   ├── src/floe_iceberg/
│   │   ├── __init__.py          # Public API exports
│   │   ├── io_manager.py        # IcebergIOManager (ConfigurableIOManager)
│   │   ├── tables.py            # IcebergTableManager (create, load, drop)
│   │   ├── operations.py        # Data operations (append, overwrite, scan)
│   │   ├── partitions.py        # Partition spec builders and mapping
│   │   ├── schema.py            # Schema evolution utilities
│   │   ├── snapshots.py         # Time travel and snapshot management
│   │   ├── maintenance.py       # Snapshot expiration, inspection
│   │   ├── config.py            # IcebergIOManagerConfig, WriteMode enum
│   │   ├── observability.py     # Structured logging + OTel spans
│   │   └── errors.py            # Custom exceptions
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_io_manager.py
│   │   │   ├── test_tables.py
│   │   │   ├── test_operations.py
│   │   │   ├── test_partitions.py
│   │   │   └── test_snapshots.py
│   │   └── integration/
│   │       ├── test_dagster_assets.py
│   │       └── test_iceberg_tables.py
│   └── pyproject.toml
│
└── floe-core/
    └── src/floe_core/schemas/
        └── catalog.py           # CatalogConfig (already exists, may extend)
```

**Structure Decision**: Extends existing monorepo package structure. Two packages (floe-polaris, floe-iceberg) with clear separation: floe-polaris handles catalog connectivity and namespace management, floe-iceberg handles table operations and Dagster IOManager.

## Complexity Tracking

> No constitution violations requiring justification. Design follows existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
