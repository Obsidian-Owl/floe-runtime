# 10. Glossary

This document defines terms used throughout the floe-runtime documentation.

---

## A

### Asset (Dagster)
A Software-Defined Asset (SDA) in Dagster—a declarative representation of a data artifact. In floe-runtime, each dbt model becomes an asset.

### Artifacts
See [CompiledArtifacts](#compiledartifacts).

---

## C

### Catalog
A metadata service that tracks Iceberg table locations and schemas. floe-runtime uses Apache Polaris as the default catalog.

### Catalog Profile
A configuration block in `platform.yaml` defining how to connect to an Iceberg catalog. Includes URI, warehouse name, and credential configuration. Data engineers reference profiles by name (e.g., `catalog: default`) in `floe.yaml`. See [Two-Tier Configuration](#two-tier-configuration).

### Classification
Metadata identifying the sensitivity of data columns. Types include `pii`, `financial`, `identifier`, and `public`. Defined in dbt meta tags using the `floe:` namespace. See [ADR-0012](../architecture/adr/0012-data-classification-governance.md).

### CLI
Command-Line Interface. The `floe` command provides user interaction with floe-runtime.

### CompiledArtifacts
The JSON structure produced by merging `floe.yaml` (pipeline) with `platform.yaml` (infrastructure). Contains fully resolved configuration needed for runtime execution, including compute target, transforms, observability settings, and resolved profile configurations. Version 2.0 includes `resolved_catalog`, `resolved_storage`, and `resolved_compute` from platform profiles. Secrets remain as `secret_ref` references until runtime resolution. See [ADR-0002](adr/0002-two-tier-config.md).

### Compute Profile
A configuration block in `platform.yaml` defining compute engine settings (DuckDB, Snowflake, BigQuery). Data engineers reference profiles by name in `floe.yaml`. See [Two-Tier Configuration](#two-tier-configuration).

### Contract
A formal interface specification between Floe repositories (floe-runtime and Control Plane). Contracts ensure compatibility without tight coupling. See [contracts documentation](../contracts/index.md).

### Compute Target
The database or engine where SQL transformations execute. Examples: DuckDB, Snowflake, BigQuery.

### Control Plane
The optional Floe SaaS backend that provides managed infrastructure, multi-tenancy, and enhanced developer experience. Not required for standalone operation.

### Cube
Open-source semantic layer for data analytics. floe-runtime uses Cube to expose transformed data via REST, GraphQL, and SQL APIs. See [floe-cube](#floe-cube).

### Cube Store
Cube's built-in caching engine. Stores pre-aggregated data for sub-second query response.

### cube_dbt
Python package that integrates Cube with dbt. Loads dbt manifest and generates Cube data model definitions.

### Credential Config
Pydantic model (`CredentialConfig`) defining how credentials are provided. Supports multiple [Credential Modes](#credential-mode). All sensitive fields use [Secret Reference](#secret-reference) patterns instead of plaintext values.

### Credential Mode
The method used to authenticate with services. Defined in `platform.yaml`:
- `static`: Client ID/secret from environment variables or K8s secrets
- `oauth2`: OAuth2 client credentials flow with automatic token refresh
- `iam_role`: AWS IAM role assumption (no static credentials)
- `service_account`: GCP/Azure workload identity

---

## D

### Dagster
Open-source data orchestrator used by floe-runtime. Treats data as first-class assets rather than tasks.

### Data Plane (Deprecated)
Deprecated term for floe-runtime. Please use "floe-runtime" instead. See [floe-runtime](#floe-runtime).

### dbt
Data Build Tool—SQL transformation framework. floe-runtime delegates all SQL handling to dbt.

### dbt Adapter
A plugin that allows dbt to connect to a specific database. Examples: dbt-duckdb, dbt-snowflake.

---

## E

### Entry Point
Python packaging mechanism for plugin discovery. floe-runtime uses entry points for transforms, targets, and catalogs.

### Environment
A deployment context (dev, preview, staging, production). Each environment can have different compute targets and data.

---

## F

### floe.yaml
The declarative configuration file that defines a data pipeline. Written by **data engineers**. Contains pipeline logic: transforms, governance policies, and observability flags. Uses profile references (`catalog: default`) instead of infrastructure details. Part of the [Two-Tier Configuration](#two-tier-configuration) architecture.

### Floe Spec (FloeSpec)
The Pydantic model representing a parsed and validated `floe.yaml` file. Contains profile references that are resolved against [Platform Spec](#platform-spec) during compilation.

---

## G

### Governance
The framework for managing data classification, access control, and policy enforcement in floe-runtime. See [ADR-0012](../architecture/adr/0012-data-classification-governance.md).

### Governance Policy
A rule in `floe.yaml` defining how classified data should be handled. Actions include `restrict`, `synthesize`, `mask`, `redact`, and `hash`.

---

## H

### Helm
Kubernetes package manager. floe-runtime provides Helm charts for production deployment.

### Hybrid Distribution
floe-runtime's distribution strategy: PyPI packages as source of truth, container images for convenience, Helm charts for Kubernetes.

---

## I

### Iceberg
Apache Iceberg—open table format for huge analytic datasets. Provides ACID transactions, time travel, and schema evolution.

---

## J

### JSON Schema
Schema format generated from Pydantic models. Used for validation and IDE support.

---

## L

### Lineage
The tracking of data flow—which datasets are inputs to a transformation and which are outputs. floe-runtime uses OpenLineage.

---

## M

### Manifest
The `manifest.json` file produced by `dbt compile`. Contains the compiled project including models, tests, and dependencies.

### Marquez
Open-source metadata service for data lineage. Default backend for OpenLineage events in floe-runtime.

### MCP (Model Context Protocol)
Standard protocol for AI agent tool integration. Cube exposes an MCP server for AI-powered data queries.

### Materialization
The process of executing a transformation and persisting results. Dagster "materializes" assets.

---

## O

### OpenLineage
Open standard for data lineage. Events describe job runs, inputs, and outputs.

### OpenTelemetry (OTel)
Vendor-neutral observability framework. floe-runtime uses OTel for traces, metrics, and logs.

### OTLP
OpenTelemetry Protocol—the wire format for exporting telemetry data.

---

## P

### Pipeline
A sequence of data transformations defined in `floe.yaml`.

### platform.yaml
The infrastructure configuration file managed by **platform engineers**. Contains storage profiles, catalog profiles, compute profiles, and credential configurations. Environment-specific files stored in `platform/<env>/platform.yaml`. Part of the [Two-Tier Configuration](#two-tier-configuration) architecture.

### Platform Resolver
Component in floe-core that loads `platform.yaml` based on the `FLOE_PLATFORM_ENV` environment variable. Resolves platform configuration from local files or artifact registry.

### Platform Spec (PlatformSpec)
The Pydantic model representing a parsed and validated `platform.yaml` file. Contains storage, catalog, compute, and observability profiles. Merged with [Floe Spec](#floe-spec-floespec) during compilation.

### Plugin
An extension to floe-runtime discovered via Python entry points. Can add custom transforms, targets, or catalogs.

### Pre-aggregation
Materialized rollup tables in Cube Store. Pre-computed aggregations that provide sub-second query performance.

### Polaris
Apache Polaris—open-source REST catalog for Apache Iceberg. Default catalog for floe-runtime.

### Profiles.yml
dbt configuration file specifying database connections. Generated by floe-dbt based on compute target.

### Profile Reference
A logical name in `floe.yaml` that references a profile in `platform.yaml`. Examples: `catalog: default`, `storage: production`. Resolved at compile time by the [Profile Resolver](#profile-resolver).

### Profile Resolver
Component in floe-core that resolves profile references in `floe.yaml` to actual configurations from `platform.yaml`. Validates that referenced profiles exist.

### Pydantic
Python library for data validation using type hints. floe-runtime uses Pydantic for all schemas.

---

## R

### Runtime
See [floe-runtime](#floe-runtime).

### floe-runtime
The open-source Data Execution Layer (Apache 2.0). Integrates Dagster, dbt, Iceberg, Polaris, and Cube into a cohesive framework. This is the canonical name for the execution layer. See [Shared Glossary](../contracts/glossary.md) for cross-repository terms.

> **Terminology Note:** "floe-runtime" (lowercase, hyphenated) is the canonical term. "Runtime" is acceptable shorthand. The terms "Data Plane" and "Data Runtime" are deprecated.

### floe-cube
floe-runtime package that wraps Cube configuration and dbt model sync. Provides semantic layer capabilities.

---

## S

### Semantic Layer
An abstraction layer that defines business-friendly metrics, dimensions, and entities on top of physical data models. Cube provides the semantic layer for floe-runtime.

### SDA
Software-Defined Asset. See [Asset](#asset-dagster).

### Secret Reference (secret_ref)
A pattern for referencing secrets without including them in configuration files. Format: `secret_ref: my-secret-name`. Resolved at **runtime** (not compile time) from:
1. Environment variable: `MY_SECRET_NAME` (uppercase, underscores)
2. K8s secret mount: `/var/run/secrets/my-secret-name`

### Span
A unit of work in distributed tracing. Spans are nested to form traces.

### Standalone Mode
Operating floe-runtime without the Control Plane. User manages all infrastructure.

### Storage Profile
A configuration block in `platform.yaml` defining S3-compatible storage settings. Includes endpoint, bucket, region, and credentials. Data engineers reference profiles by name in `floe.yaml`. See [Two-Tier Configuration](#two-tier-configuration).

### Synthetic Data
Artificially generated data that preserves statistical properties of real data while protecting privacy. Generated by the Control Plane (not runtime).

---

## T

### Two-Tier Configuration
The floe-runtime architecture pattern that separates infrastructure configuration (`platform.yaml`) from pipeline logic (`floe.yaml`). Key benefits:
- **Persona separation**: Platform engineers own infrastructure; data engineers own pipelines
- **Environment portability**: Same `floe.yaml` works across dev/staging/prod
- **Zero secrets in code**: All credentials use [Secret Reference](#secret-reference-secret_ref) patterns

See [ADR-0002](adr/0002-two-tier-config.md) for design rationale.

### Target
See [Compute Target](#compute-target).

### Telemetry
Observability data: traces, metrics, and logs.

### Trace
A collection of spans representing an end-to-end operation across services.

### Transform
A data transformation step. Currently supports `dbt` type only. Python transforms are deferred to future scope due to integration complexity with telemetry and lineage.

---

## V

### Validation
The process of checking `floe.yaml` against the schema. Performed by floe-core.

---

## Z

### Zero Secrets in Code
A security principle enforced by the [Two-Tier Configuration](#two-tier-configuration) architecture. Data engineers never handle credentials directly—all sensitive fields use [Secret Reference](#secret-reference-secret_ref) patterns that are resolved at runtime from environment variables or K8s secrets.

---

## Abbreviations

| Abbreviation | Meaning |
|--------------|---------|
| API | Application Programming Interface |
| CI/CD | Continuous Integration / Continuous Deployment |
| CLI | Command-Line Interface |
| dbt | Data Build Tool |
| DX | Developer Experience |
| GHCR | GitHub Container Registry |
| HA | High Availability |
| K8s | Kubernetes |
| OSS | Open Source Software |
| OTel | OpenTelemetry |
| OTLP | OpenTelemetry Protocol |
| PyPI | Python Package Index |
| RBAC | Role-Based Access Control |
| REST | Representational State Transfer |
| SaaS | Software as a Service |
| SDA | Software-Defined Asset |
| SDK | Software Development Kit |
| SQL | Structured Query Language |
| TLS | Transport Layer Security |
| UI | User Interface |
| UUID | Universally Unique Identifier |

---

## Package Names

| Package | Description |
|---------|-------------|
| `floe-core` | Schema definitions, parsing, validation |
| `floe-cli` | Command-line interface |
| `floe-dagster` | Dagster integration and asset factory |
| `floe-dbt` | dbt profile generation and execution |
| `floe-iceberg` | Iceberg table utilities |
| `floe-polaris` | Polaris catalog client |
| `floe-cube` | Cube semantic layer integration |
