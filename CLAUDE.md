# Floe Runtime

Open-source data execution layer using Apache Iceberg, dbt, Dagster, and Cube.

## Quick Start

```bash
make test          # Run all tests in Docker
make test-unit     # Unit tests only (fast)
make lint          # Linting + type checks
```

## Project Structure

```
packages/
├── floe-cli/        # CLI (Click + Rich)
├── floe-core/       # Schemas, validation (Pydantic)
├── floe-cube/       # Semantic layer (Cube)
├── floe-dagster/    # Orchestration (Dagster)
├── floe-dbt/        # SQL transforms (dbt)
├── floe-iceberg/    # Storage (PyIceberg)
└── floe-polaris/    # Catalog (Polaris REST)

charts/              # Helm charts for K8s deployment
platform/            # Environment-specific platform.yaml files
testing/docker/      # Docker Compose test infrastructure
```

## Two-Tier Configuration Architecture

Floe uses a two-tier configuration model:

| File | Audience | Contains |
|------|----------|----------|
| `floe.yaml` | Data Engineers | Pipelines: transforms, governance, logical profile references |
| `platform.yaml` | Platform Engineers | Infrastructure: storage, catalogs, compute, credentials |

**Data engineers never see credentials or infrastructure details.**

```yaml
# floe.yaml (Data Engineer) - same file works across all environments
name: customer-analytics
version: "1.0.0"
storage: default      # Logical reference
catalog: default      # Logical reference
compute: default      # Logical reference
```

See [docs/platform-config.md](docs/platform-config.md) and [docs/pipeline-config.md](docs/pipeline-config.md).

## Core Standards (Summary)

- **Pydantic v2** for ALL data validation
- **Type hints** on ALL functions (`mypy --strict`)
- **>80% test coverage** required
- **Never** use `eval()`, `exec()`, or log secrets
- **Standalone-first**: No SaaS dependencies
- **Zero secrets in code**: All credentials via secret references

@.claude/CLAUDE.md for full development standards

## Skill Usage (IMPORTANT)

When working on specific components, invoke the appropriate skill:

| Component | Skill | Invocation |
|-----------|-------|------------|
| Data models, configs | pydantic-skill | "Use pydantic-skill for..." |
| Dagster assets | dagster-skill | "Use dagster-skill for..." |
| dbt models | dbt-skill | "Use dbt-skill for..." |
| Iceberg tables | pyiceberg-skill | "Use pyiceberg-skill for..." |
| Polaris catalog | polaris-skill | "Use polaris-skill for..." |
| Cube semantic | cube-skill | "Use cube-skill for..." |
| Helm/K8s | helm-k8s-skill | "Use helm-k8s-skill for..." |

## Agent Delegation (CRITICAL)

**For log analysis and debugging, ALWAYS delegate to preserve context:**

| Task | Agent | Why |
|------|-------|-----|
| Docker/container logs | `docker-log-analyser` | Extracts errors only |
| K8s pod debugging | `helm-debugger` | Targeted extraction |
| Helm chart issues | `helm-debugger` | Validates charts first |

**Never dump full logs into the main conversation.**

Use `/project:k8s-debug` or delegate explicitly:
```
Task(docker-log-analyser, "Analyse polaris container for startup errors")
```

## Deployment Validation Architecture

Floe-runtime uses Kubernetes-native validation for production-grade deployments:

| Layer | Tool | Purpose |
|-------|------|---------|
| **Pre-Install** | Helm init jobs | Polaris warehouse/namespace setup, DB migration |
| **Pod Health** | K8s startup/readiness/liveness probes | Container lifecycle management |
| **Post-Install** | Helm validation job | Multi-component health aggregation (8 services) |
| **E2E Testing** | scripts/validate-e2e.sh | Full data pipeline validation |

### Quick Start

```bash
# Full clean deployment with validation (RECOMMENDED)
./scripts/deploy.sh --clean --validate

# Or manual deployment steps
./scripts/deploy/local.sh         # Clean + deploy all services
./scripts/validate/e2e.sh          # E2E validation

# Quick deployment (skip cleanup)
./scripts/deploy.sh --quick
```

### Architecture

```
Helm Install
├─ Pre-Install Hooks (weight: -10 to -5)
│  ├─ init-polaris: Create warehouse/namespace
│  └─ migrate-db: Run Dagster schema migrations (official chart)
├─ Deployment Resources
│  ├─ Pods with startup/readiness/liveness probes
│  └─ Services with health check endpoints
└─ Post-Install Hooks (weight: 10)
   └─ validate: Aggregate health check (8 components)
```

### Probes Reference

| Component | Startup | Readiness | Liveness | Health Endpoint |
|-----------|---------|-----------|----------|-----------------|
| Dagster Webserver | 5 min | GraphQL check | 30s interval | `/server_info` |
| Polaris | 2 min | Catalog API | 30s interval | `/q/health/ready` |
| Cube | 1.5 min | Meta endpoint | 20s interval | `/readyz` |
| LocalStack | 1.5 min | Service status | 10s interval | `/_localstack/health` |
| Marquez | 2.5 min | Namespaces API | 10s interval | `/api/v1/namespaces` |
| PostgreSQL | 1.5 min | DB exists check | 30s interval | `pg_isready` |

### Script Organization

All operational scripts are organized in `scripts/` subdirectories:

```
scripts/
├── deploy/           # Deployment automation
│   ├── local.sh      # Clean deployment (CANONICAL)
│   ├── e2e.sh        # E2E deployment with tests
│   └── quickstart.sh # Interactive wizard
├── cleanup/          # Cleanup utilities
│   ├── all.sh        # Full cleanup (RECOMMENDED)
│   ├── dagster.sh    # Dagster run history
│   ├── polaris.sh    # Polaris catalog
│   └── s3.sh         # S3 buckets
├── validate/         # Validation scripts
│   ├── e2e.sh        # Comprehensive validation
│   └── basic.sh      # Quick smoke test
└── dagster/          # Dagster operations
    ├── materialize-demo.sh  # Demo pipeline
    ├── launch-job.sh        # Job launcher
    └── monitor-run.sh       # Run monitor
```

**Common Commands:**
```bash
# Full deployment
./scripts/deploy.sh --clean --validate     # Recommended
./scripts/deploy/local.sh                  # Manual clean deployment

# Cleanup
./scripts/cleanup/all.sh                   # Full cleanup

# Validation
./scripts/validate/e2e.sh                  # E2E validation

# Dagster operations
./scripts/dagster/materialize-demo.sh      # Run demo pipeline
./scripts/dagster/launch-job.sh <job-name>   # Launch job
./scripts/dagster/monitor-run.sh <run-id>    # Monitor run
```

See [scripts/README.md](scripts/README.md) for complete reference.

## SonarQube Quality Gates

| Rule | Prevention |
|------|------------|
| S6437 (BLOCKER) | Use `os.environ.get()` for secrets |
| S1192 (CRITICAL) | Extract duplicate strings to constants |
| S108 (MAJOR) | No empty code blocks |

@.claude/rules/sonarqube-quality.md for full guidance

## Documentation

- [Platform Configuration Guide](docs/platform-config.md) - For platform engineers
- [Pipeline Configuration Guide](docs/pipeline-config.md) - For data engineers
- [Security Architecture](docs/security.md) - Credential flows and access control

## Active Technologies
- Python 3.10+ (compatible with Dagster 1.6+, dbt-core 1.7+) + Pydantic v2, pydantic-settings, PyYAML, Dagster, dbt-core, dagster-db (010-orchestration-auto-discovery)
- Iceberg tables via Polaris REST catalog; S3-compatible backends (MinIO, AWS S3) (010-orchestration-auto-discovery)

## Recent Changes
- 010-orchestration-auto-discovery: Added Python 3.10+ (compatible with Dagster 1.6+, dbt-core 1.7+) + Pydantic v2, pydantic-settings, PyYAML, Dagster, dbt-core, dagster-db
