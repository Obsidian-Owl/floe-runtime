# ADR-0002: Two-Tier Configuration Architecture

> **Status**: T010 Placeholder - Full content in Phase 5 (T083)

## Status

Accepted

## Context

The original FloeSpec was monolithic, mixing infrastructure concerns (endpoints, credentials) with pipeline concerns (transforms, schedules). This caused:

1. Data engineers needed to know infrastructure details
2. Same pipeline couldn't deploy across environments without modification
3. Credentials referenced at wrong abstraction level
4. No clear security boundary between personas

## Decision

Adopt a two-tier configuration architecture:

1. **platform.yaml** - Platform Engineer domain
   - Storage profiles (S3, GCS, ADLS)
   - Catalog profiles (Polaris, Glue, Unity)
   - Compute profiles (dbt adapters)
   - Credential configurations
   - Observability endpoints

2. **floe.yaml** - Data Engineer domain
   - Pipeline name and version
   - Logical profile references (`compute: default`)
   - Transform definitions
   - Governance policies
   - Observability settings (what to enable, not where to send)

## Consequences

### Positive

- Clear separation of concerns by persona
- Same `floe.yaml` works across all environments
- Data engineers never see credentials
- Platform changes don't require pipeline changes
- Enterprise-grade security by design

### Negative

- Two files to manage instead of one
- Requires compilation step to merge
- Platform config must be available at compile/deploy time

## Related

- [Platform Configuration](../platform-config.md)
- [Pipeline Configuration](../pipeline-config.md)
- [Security Architecture](../security.md)

---

*TODO(T083): Expand with full architectural rationale and alternatives considered*
