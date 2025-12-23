# Feature Specification: Two-Tier Configuration Architecture

**Feature Branch**: `009-two-tier-config`
**Created**: 2025-12-23
**Status**: Draft
**Input**: User description: "Two-tier configuration architecture: platform.yaml for platform engineers (infrastructure, credentials, endpoints) + floe.yaml for data engineers (pipelines, transforms). Enterprise-grade security by design. Zero secrets in code. Environment injection pattern - same floe.yaml works across dev/staging/prod."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Platform Engineer Configures Infrastructure (Priority: P1)

A Platform Engineer wants to configure the data platform infrastructure (storage backends, catalog endpoints, observability services) in a single configuration file that can be version-controlled separately from pipeline code. This allows them to manage infrastructure without touching data pipeline definitions.

**Why this priority**: Without platform configuration, no pipelines can run. This is the foundational layer that enables all other functionality. Platform engineers must be able to work independently from data engineers.

**Independent Test**: Can be fully tested by creating a `platform.yaml` file with storage, catalog, and observability profiles, then validating the configuration loads correctly and all referenced secrets are accessible.

**Acceptance Scenarios**:

1. **Given** a platform engineer has access to infrastructure credentials, **When** they create a `platform.yaml` file with storage profiles (S3/MinIO endpoints), **Then** the system validates the configuration and confirms all profiles are accessible
2. **Given** a `platform.yaml` exists with catalog profiles, **When** a data pipeline references `catalog: default`, **Then** the system resolves the reference to the actual catalog endpoint configured by the platform engineer
3. **Given** credentials are stored in external secrets, **When** the platform engineer references them via `secret_ref:` in platform.yaml, **Then** the system retrieves credentials at runtime without exposing them in any configuration file

---

### User Story 2 - Data Engineer Deploys Same Pipeline to Multiple Environments (Priority: P1)

A Data Engineer wants to write a pipeline definition once and deploy it to development, staging, and production environments without modification. The pipeline uses logical references (e.g., `catalog: default`, `storage: default`) that resolve to environment-specific infrastructure at deploy time.

**Why this priority**: Environment portability is a core value proposition. If data engineers must modify pipelines for each environment, the architecture fails its primary goal.

**Independent Test**: Can be fully tested by deploying the same `floe.yaml` to two different environments with different `platform.yaml` files and verifying the pipeline runs correctly in both.

**Acceptance Scenarios**:

1. **Given** a data engineer creates a `floe.yaml` with `catalog: default`, **When** deployed to dev environment (with dev platform.yaml), **Then** the pipeline writes to the development catalog
2. **Given** the same `floe.yaml` is deployed to production (with prod platform.yaml), **When** the pipeline runs, **Then** it writes to the production catalog without any modification to floe.yaml
3. **Given** a floe.yaml with only logical references, **When** reviewed for security, **Then** it contains zero credentials, endpoints, or environment-specific configuration

---

### User Story 3 - Security Team Validates Zero Secrets in Code (Priority: P2)

A Security Engineer wants to audit the pipeline codebase to ensure no credentials or sensitive configuration exist in version-controlled files. All secrets must be referenced by name only, with actual values injected at runtime from secure storage.

**Why this priority**: Security is a core design principle. While not blocking basic functionality, enterprise adoption requires passing security audits.

**Independent Test**: Can be fully tested by running automated security scans on the repository and verifying zero hardcoded credentials are found in any configuration file.

**Acceptance Scenarios**:

1. **Given** a repository with platform.yaml and floe.yaml files, **When** a security scanner checks for hardcoded secrets, **Then** zero credentials are found in configuration files
2. **Given** platform.yaml references secrets via `secret_ref:`, **When** the system loads the configuration, **Then** credentials are retrieved from secure storage (environment variables, secrets manager) at runtime
3. **Given** an OAuth2 credential mode is configured, **When** a pipeline authenticates to a catalog, **Then** access tokens are short-lived and automatically refreshed

---

### User Story 4 - DevOps Engineer Reviews Credential Modes (Priority: P3)

A DevOps Engineer wants to choose the appropriate credential management strategy for each environment: static credentials for local development, IAM roles for cloud, OAuth2 for catalog access.

**Why this priority**: Flexible credential management enables secure deployments across diverse infrastructure, but reasonable defaults work for most cases.

**Independent Test**: Can be fully tested by configuring each credential mode in platform.yaml and verifying the system authenticates correctly.

**Acceptance Scenarios**:

1. **Given** a platform.yaml with `credentials.mode: static` and a `secret_ref`, **When** the system authenticates, **Then** it retrieves credentials from the referenced secret
2. **Given** a platform.yaml with `credentials.mode: oauth2`, **When** the system authenticates to a catalog, **Then** it obtains an access token using the client credentials flow
3. **Given** a platform.yaml with `credentials.mode: iam_role`, **When** the system accesses cloud storage, **Then** it assumes the specified IAM role without static credentials

---

### User Story 5 - Platform Engineer Troubleshoots Configuration Errors (Priority: P2)

A Platform Engineer wants to quickly identify and fix configuration errors when deploying a new environment or updating an existing one. Error messages must clearly indicate which file, line, and field caused the problem.

**Why this priority**: Configuration errors are inevitable during initial setup and ongoing changes. Clear diagnostics reduce time-to-resolution from hours to minutes.

**Independent Test**: Can be fully tested by introducing deliberate configuration errors (missing profile, invalid secret_ref, schema violations) and verifying error messages are actionable.

**Acceptance Scenarios**:

1. **Given** a floe.yaml references `catalog: analytics`, **When** platform.yaml has no `analytics` profile, **Then** the system fails with error: "Profile 'analytics' not found in platform.catalogs. Available profiles: [default, production]"
2. **Given** a platform.yaml has a typo in YAML syntax, **When** the system validates configuration, **Then** it shows the file name, line number, and specific parsing error
3. **Given** a secret_ref points to a non-existent secret, **When** the system starts, **Then** it fails fast with: "Secret 'polaris-oauth' not found. Expected in environment variable or K8s secret."
4. **Given** a platform.yaml contains a plaintext credential where secret_ref is required, **When** schema validation runs, **Then** it fails with: "Field 'client_secret' must use secret_ref, not plaintext value"

---

### Edge Cases

- What happens when a floe.yaml references a profile not defined in platform.yaml? → System fails fast with clear error: "Profile 'X' not found in platform configuration"
- What happens when secret_ref points to a non-existent secret? → System fails at startup with clear error indicating which secret is missing
- What happens when platform.yaml is missing entirely? → System checks for environment variables as fallback, then fails with actionable error
- What happens when the same floe.yaml is used without a platform.yaml in local development? → System uses sensible defaults (localhost endpoints, test credentials from environment)
- What happens when credential refresh fails mid-pipeline? → System retries with exponential backoff, then fails the pipeline with clear error

## Requirements *(mandatory)*

### Functional Requirements

**Configuration Schema**

- **FR-001**: System MUST support a `platform.yaml` file for platform infrastructure configuration (storage, catalogs, compute, observability)
- **FR-002**: System MUST support a `floe.yaml` file for pipeline configuration (transforms, governance, observability flags)
- **FR-003**: System MUST validate both configuration files against versioned schemas with clear error messages
- **FR-004**: System MUST merge platform.yaml and floe.yaml at compile/deploy time into a single resolved configuration

**Profile References**

- **FR-005**: floe.yaml MUST use logical profile names (e.g., `catalog: default`) instead of direct configuration
- **FR-006**: System MUST resolve profile references from floe.yaml to actual configurations in platform.yaml
- **FR-007**: System MUST support multiple named profiles per category (e.g., `catalogs.production`, `catalogs.analytics`)

**Credential Management**

- **FR-008**: platform.yaml MUST support multiple credential modes: static, oauth2, iam_role, service_account
- **FR-009**: Credentials MUST be referenced via `secret_ref:` names, never stored directly in configuration files
- **FR-010**: System MUST support OAuth2 client credentials flow with configurable scope
- **FR-011**: System MUST support automatic token refresh for OAuth2 credentials

**Security (Zero-Trust Model)**

- **FR-012**: floe.yaml MUST NOT contain any credentials, secrets, or infrastructure endpoints
- **FR-013**: System MUST fail validation if credentials are detected in floe.yaml
- **FR-014**: All credential retrieval MUST happen at runtime, not at configuration load time
- **FR-015**: System MUST support least-privilege OAuth2 scopes per profile
- **FR-022**: The following MUST be managed via secret_ref (never plaintext): OAuth client_secret, S3 secret_access_key, database passwords, TLS certificates, API bearer tokens
- **FR-023**: Endpoint URIs (catalog, storage, observability) MUST support secret_ref to protect internal network topology
- **FR-024**: System MUST validate that all sensitive fields use secret_ref at schema validation time

**Environment Portability**

- **FR-016**: The same floe.yaml MUST work across dev/staging/prod environments without modification
- **FR-017**: Environment-specific configuration MUST be isolated in platform.yaml
- **FR-018**: System MUST support environment variable fallbacks for platform configuration

**Multi-Repository CI/CD**

- **FR-019**: Platform.yaml MUST be publishable to an artifact registry (OCI, Helm-style) with semantic versioning
- **FR-020**: floe.yaml MUST be able to reference a platform configuration by registry location and version
- **FR-021**: System MUST support resolution of platform configuration from remote artifact registry at compile/deploy time

**Environment Structure**

- **FR-025**: Each environment MUST have its own platform.yaml in a dedicated directory (`platform/dev/`, `platform/staging/`, `platform/prod/`)
- **FR-026**: Environment directories MUST be independently version-controlled and deployable
- **FR-027**: System MUST support arbitrary environment names beyond dev/staging/prod (e.g., `platform/sandbox-team-a/`)

**CI/CD Promotion Model**

- **FR-028**: System MUST support GitOps-style deployment where environment branches/tags trigger deployments
- **FR-029**: Production deployments MUST support mandatory approval gates via branch protection or equivalent
- **FR-030**: System MUST support rollback via git revert (no special rollback mechanism required)

**Environment Flexibility**

- **FR-031**: System MUST provide sensible default environment names (dev, staging, prod) in scaffolding/templates
- **FR-032**: System MUST NOT hard-code environment names - arbitrary names (sandbox-team-a, dr-region-2) MUST work
- **FR-033**: System MUST validate environment naming conventions (alphanumeric, hyphens, lowercase) without restricting count or naming

**Schema Migration**

- **FR-034**: FloeSpec MUST remove inline infrastructure fields (catalog, compute, storage with direct URIs/credentials) and replace with profile references
- **FR-035**: Demo and test code MUST be updated to use new profile-based configuration as part of this feature
- **FR-036**: No backwards compatibility layer required (pre-release, clean break acceptable)

**Configuration Validation & Diagnostics**

- **FR-037**: Validation errors MUST include file name, line number (when available), and field path
- **FR-038**: Profile resolution errors MUST list available profiles to aid troubleshooting
- **FR-039**: Secret resolution errors MUST indicate expected secret location (env var name, K8s secret name)
- **FR-040**: Schema violations for sensitive fields MUST explicitly state "use secret_ref" in error message

**Documentation**

- **FR-041**: System MUST include an Architecture Decision Record (ADR) documenting the two-tier configuration design rationale
- **FR-042**: System MUST provide a Platform Configuration Guide for platform engineers (platform.yaml structure, profile types, credential modes, secret_ref usage)
- **FR-043**: System MUST provide a Pipeline Configuration Guide for data engineers (floe.yaml structure, profile references, environment portability)
- **FR-044**: System MUST provide a Security Architecture document (zero-trust model, credential flow, threat mitigations, audit guidance)
- **FR-045**: System MUST update CLAUDE.md and project documentation to reflect two-tier configuration patterns
- **FR-046**: System MUST export JSON Schema files for platform.yaml and floe.yaml to enable IDE autocomplete and validation

**Tech Debt & Refactoring**

- **FR-047**: All deprecated configuration patterns (inline URIs, direct credentials) MUST be removed from floe-core, floe-polaris, and floe-iceberg packages
- **FR-048**: All type hints MUST be updated to use new PlatformSpec and profile models (no legacy type annotations)
- **FR-049**: All unit tests MUST be updated to use profile-based configuration fixtures
- **FR-050**: All integration tests MUST validate profile resolution and secret_ref injection
- **FR-051**: All modified packages MUST pass linting (ruff, black) and type checking (mypy --strict)
- **FR-052**: Test coverage MUST remain above 80% for all packages after refactoring

### Key Entities

- **PlatformSpec**: Top-level configuration for infrastructure (storage profiles, catalog profiles, compute profiles, observability config)
- **FloeSpec**: Top-level configuration for pipelines (transforms, governance rules, observability flags) - references PlatformSpec profiles by name
- **StorageProfile**: S3-compatible storage configuration (endpoint, region, bucket, credentials)
- **CatalogProfile**: Iceberg catalog configuration (type, URI, warehouse, credentials, access delegation)
- **ComputeProfile**: Compute engine configuration (type, connection properties, credentials)
- **CredentialConfig**: Credential configuration with mode (static, oauth2, iam_role, service_account) and secret reference
- **CompiledArtifacts**: Merged output from FloeSpec + PlatformSpec resolution, used by runtime

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Platform engineers can update infrastructure configuration without modifying any pipeline files (100% separation)
- **SC-002**: Data engineers can deploy the same pipeline to 3+ environments (dev/staging/prod) without modification
- **SC-003**: Security scans find zero hardcoded credentials in configuration files across the entire repository
- **SC-004**: Configuration validation catches missing or invalid profiles within 2 seconds at startup
- **SC-005**: Credential refresh happens automatically without pipeline interruption for sessions lasting up to 24 hours
- **SC-006**: New platform engineers can configure a working environment within 30 minutes using documentation

## Assumptions

1. **Secret Storage**: Organizations have existing secret management (K8s secrets, AWS Secrets Manager, environment variables)
2. **OAuth2 Support**: Catalog services support OAuth2 client credentials flow for authentication
3. **Schema Versioning**: Configuration schemas will be versioned to support future evolution
4. **Local Development**: Developers can use simplified local configurations with environment variable fallbacks
5. **No Prior Releases**: This is a greenfield implementation with no backwards compatibility requirements

## Clarifications

### Session 2025-12-23

- Q: Should backwards compatibility with existing FloeSpec be maintained? A: No - no prior releases exist, clean break is acceptable
- Q: Should platform.yaml be optional for local development? A: Yes - environment variables can serve as fallback for simple cases
- Q: What credential modes should be supported initially? A: static, oauth2, iam_role, service_account (comprehensive from day one)
- Q: Should platform engineers and data engineers be able to operate from separate git repositories? A: Yes - platform.yaml is published to a shared artifact registry (like Helm charts); data teams reference by version
- Q: Which config items MUST be managed as secrets? A: Full zero-trust - all credentials (OAuth client_secret, S3 secret_access_key, passwords, TLS certs, API tokens) AND endpoint URIs (to protect internal topology)
- Q: How should data teams discover available platform configurations? A: CLI command (`floe platform list-profiles`) that queries artifact registry - no separate UI required
- Q: How should multiple environments be structured? A: One platform.yaml per environment in separate directories (`platform/dev/`, `platform/staging/`, `platform/prod/`) - Helm-style explicit separation
- Q: How should pipelines be promoted across environments? A: GitOps with environment-specific branches/tags (`release/staging`, `release/prod`) - CI/CD triggers on merge, enables approvals and rollback via git
- Q: Should environment design be opinionated or flexible? A: Convention with escape hatches - sensible defaults (dev/staging/prod) but arbitrary custom environments allowed (sandbox-team-a, dr-region-2)
- Q: How should existing FloeSpec code (demo, tests) transition to profile references? A: Hard break - remove old fields immediately, update all demo/test code as part of this feature (no migration tool needed for pre-release)
- Q: Should configuration error handling be a dedicated user story? A: Yes - added User Story 5 (P2) for configuration troubleshooting with clear diagnostics
- Q: What documentation is required for this architectural shift? A: Comprehensive - ADR for design decision, configuration guides for both personas, security architecture doc, CLAUDE.md updates, and JSON schema reference for IDE autocomplete
- Q: Should the spec require comprehensive tech debt cleanup? A: Yes - add explicit FRs for removing deprecated patterns from all packages, updating type hints to use new models, ensuring comprehensive test coverage, and validating linting passes on all modified packages
