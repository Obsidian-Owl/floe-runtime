# 00. Overview

## Document Purpose

This is the architecture documentation for **floe-runtime**, the open-source Data Execution Layer. It follows the [arc42](https://arc42.org/) template and serves as the authoritative reference for understanding, extending, and contributing to the runtime.

---

## 1. What is floe-runtime?

floe-runtime is an **open-source data pipeline execution framework** that integrates best-in-class tools into a cohesive, developer-friendly experience:

- **Dagster** for asset-centric orchestration
- **dbt** for SQL transformations
- **Apache Iceberg** for open table format storage
- **Apache Polaris** for catalog management
- **OpenTelemetry** for observability
- **OpenLineage** for data lineage

### The Core Promise

Define your data pipeline in `floe.yaml`, and let platform engineers configure infrastructure in `platform.yaml`. The same pipeline works across all environments—dev, staging, production—without modification.

**Two-Tier Configuration** ([ADR-0002](adr/0002-two-tier-config.md)):

```yaml
# floe.yaml - Data Engineer (pipeline logic only)
name: customer-analytics
version: "1.0.0"

# Logical references - resolved at deploy time
storage: default
catalog: default
compute: default

transforms:
  - type: dbt
    path: ./dbt

observability:
  traces: true
  lineage: true
```

```yaml
# platform.yaml - Platform Engineer (infrastructure)
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    bucket: iceberg-data

catalogs:
  default:
    type: polaris
    uri: "http://polaris:8181/api/catalog"
    credentials:
      mode: oauth2
      client_secret:
        secret_ref: polaris-oauth-secret  # K8s secret reference
```

---

## 2. Open Source Philosophy

### 2.1 Apache 2.0 License

floe-runtime is licensed under Apache 2.0, providing:

- **Freedom to use** in any project, commercial or personal
- **Freedom to modify** and create derivative works
- **Freedom to distribute** original or modified versions
- **Patent protection** from contributors

### 2.2 Standalone-First Design

Every feature in floe-runtime works **without requiring the Floe SaaS Control Plane**. The SaaS offering enhances the experience but is never required.

| What floe-runtime provides | What SaaS adds |
|----------------------------|----------------|
| Pipeline execution | Multi-tenant infrastructure |
| Local development environment | Git-push-to-deploy |
| Manual environment management | Automated environment lifecycle |
| Self-managed observability | Managed Grafana Cloud |
| DIY test data | Synthetic data generation |
| CLI-based workflow | Web UI + team collaboration |

### 2.3 Community-Driven Development

We believe in:

- **Transparency**: All architectural decisions documented as ADRs
- **Extensibility**: Clear extension points for custom integrations
- **Contribution-friendly**: Comprehensive test coverage and documentation
- **No vendor lock-in**: Standard formats (Iceberg, OpenLineage, OTel)

---

## 3. Business Goals

| Priority | Goal | Description |
|----------|------|-------------|
| 1 | **Developer Experience** | Simple CLI, instant feedback, minimal configuration |
| 2 | **Tool Integration** | Seamless integration of Dagster, dbt, Iceberg, Polaris |
| 3 | **Portability** | Run anywhere: laptop, Docker, Kubernetes, any cloud |
| 4 | **Observability** | Built-in tracing, metrics, and lineage from day one |
| 5 | **Extensibility** | Clear interfaces for custom transforms and targets |

---

## 4. Quality Goals

| Quality | Target | How Measured |
|---------|--------|--------------|
| **Portability** | Works on macOS, Linux, Windows | CI matrix testing |
| **Simplicity** | < 5 min from install to first run | User testing |
| **Performance** | < 1s CLI startup time | Benchmark tests |
| **Reliability** | Zero data loss during execution | Integration tests |
| **Extensibility** | Custom transforms without forking | Plugin architecture |

---

## 5. Stakeholders

### 5.1 Open Source Users

| Persona | Goals | Key Concerns |
|---------|-------|--------------|
| **Data Engineer** | Build and run pipelines locally | Ease of use, debugging |
| **Analytics Engineer** | Develop dbt models with orchestration | dbt compatibility |
| **Platform Engineer** | Deploy to Kubernetes | Helm charts, observability |
| **Contributor** | Add features, fix bugs | Code quality, documentation |

### 5.2 Enterprise Self-Hosters

| Persona | Goals | Key Concerns |
|---------|-------|--------------|
| **Data Platform Team** | Run floe-runtime on internal K8s | Security, air-gapped support |
| **DevOps** | Maintain infrastructure | Monitoring, upgrades |
| **Security Team** | Ensure compliance | No external dependencies |

### 5.3 SaaS Customers (via Control Plane)

| Persona | Goals | Key Concerns |
|---------|-------|--------------|
| **Data Team Lead** | Team productivity | Collaboration features |
| **Data Engineer** | Focus on pipelines, not infra | Managed infrastructure |
| **Compliance Officer** | Data privacy | Synthetic data, audit trails |

---

## 6. Architecture Principles

### 6.1 Core Principles

1. **Two-tier configuration** — Pipeline logic (`floe.yaml`) is separated from infrastructure (`platform.yaml`). Data engineers focus on data; platform engineers own infrastructure.

2. **Zero secrets in code** — Credentials never appear in `floe.yaml`. Only logical profile references. Secrets are managed via K8s secrets and resolved at runtime.

3. **dbt owns SQL** — Floe never parses, transpiles, or validates SQL. dbt handles all SQL operations.

4. **Target agnostic** — Users choose their compute target. DuckDB for development, Snowflake for production—Floe doesn't prescribe.

5. **Observability first** — Every operation emits traces, metrics, and lineage. Built-in, not bolted-on.

6. **Standard formats** — Iceberg for storage, OpenLineage for lineage, OTel for observability. No proprietary formats.

7. **Explicit over implicit** — Configuration is declarative. No magic, no hidden behavior.

### 6.2 Design Guidelines

- Keep packages focused and single-purpose
- Prefer composition over inheritance
- Use type hints everywhere
- Document public APIs with docstrings
- Test at integration boundaries, not just units

---

## 7. Technology Summary

| Component | Technology | Rationale |
|-----------|------------|-----------|
| CLI | Python (Click) | Native to data engineering ecosystem |
| Orchestration | Dagster | Asset-centric, OpenLineage native |
| Transformation | dbt | Industry standard, target-agnostic |
| Storage | Apache Iceberg | Open table format, multi-engine |
| Catalog | Apache Polaris | REST API, vendor-neutral |
| Observability | OpenTelemetry | Vendor-neutral standard |
| Lineage | OpenLineage | Industry standard, Marquez backend |

See [03-solution-strategy](03-solution-strategy.md) for detailed rationale.

---

## 8. Document Conventions

### Diagrams

- **ASCII art** for inline diagrams (version-controllable)
- **C4 Model** for system architecture
- **Sequence diagrams** for runtime flows

### Code Examples

All code examples are tested and runnable:

```python
# Examples use type hints
from floe_core import CompiledArtifacts

def process(artifacts: CompiledArtifacts) -> None:
    ...
```

### Links

- External links point to stable documentation
- Internal links use relative paths

---

## 9. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | 2024-12 | Floe Team | Initial runtime documentation |
