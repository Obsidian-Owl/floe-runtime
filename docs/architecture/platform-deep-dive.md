# Floe Platform Architecture: Enterprise Data Infrastructure

A deep-dive into the two-tier configuration architecture that separates platform concerns from data engineering workflows.

## The Problem: Data Platform Complexity

Modern data teams face a paradox: they need enterprise-grade infrastructure (security, observability, compliance) but shouldn't have to think about it when writing pipelines. Common challenges include:

- **Infrastructure vs. Business Logic**: Data engineers waste time on credentials, endpoints, and cloud configuration instead of building value
- **Security as an Afterthought**: Secrets leak into code, credentials are hardcoded, and audit trails are missing
- **Environment Drift**: Pipelines that work locally break in staging because of configuration differences
- **Operational Overhead**: Each environment requires manual configuration of catalogs, storage, and observability

Floe solves this with a **two-tier configuration architecture** that cleanly separates concerns.

---

## The Solution: Two-Tier Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TWO-TIER CONFIGURATION                               │
├────────────────────────────────────┬────────────────────────────────────────┤
│       Platform Engineer            │         Data Engineer                  │
│       (platform.yaml)              │         (floe.yaml)                    │
├────────────────────────────────────┼────────────────────────────────────────┤
│  • Cloud infrastructure refs       │  • Pipeline definitions                │
│  • Storage endpoints               │  • dbt model configurations            │
│  • Catalog credentials             │  • Dagster schedules & sensors         │
│  • Network policies                │  • Profile references (not details)    │
│  • Security configuration          │  • Business logic                      │
│  • Observability endpoints         │  • Data transformations                │
├────────────────────────────────────┴────────────────────────────────────────┤
│                          PlatformResolver                                   │
│              (Merges platform.yaml + floe.yaml at runtime)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                         CompiledArtifacts                                   │
│        (dbt profiles, Dagster config, Iceberg catalog settings)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Matters for Teams

| Concern | Without Floe | With Floe |
|---------|--------------|-----------|
| **Credentials** | Scattered in code, env files, CI secrets | Defined once in platform.yaml, resolved at runtime |
| **Environment Parity** | Different configs per env | Same floe.yaml works everywhere |
| **Security Audit** | Grep through repos for secrets | Single source of truth in platform.yaml |
| **Onboarding** | "Ask DevOps for the credentials" | `floe run` just works |
| **Compliance** | Manual classification | Declarative governance rules |

---

## Three Layers of Infrastructure

Understanding what Floe manages vs. what it references is critical for enterprise deployments.

### Layer 1: Pre-Existing Enterprise Infrastructure (NOT Floe's Job)

These are **already provisioned** by your cloud/platform team:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTERPRISE CLOUD INFRASTRUCTURE                         │
│                     (Pre-existing, tightly controlled)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AWS Account & IAM                     Network & Security                   │
│  ├── VPC (vpc-abc123)                  ├── Private subnets                  │
│  ├── IAM Roles for IRSA                ├── Security groups                  │
│  │   └── FloeDataEngineer              ├── NAT gateways                     │
│  │   └── FloePlatformAdmin             └── VPN/DirectConnect                │
│  ├── KMS keys for encryption                                                │
│  └── Secrets Manager secrets           Identity & Auth                      │
│                                        ├── Okta/Auth0/Keycloak              │
│  EKS Cluster                           ├── OIDC provider                    │
│  ├── Node pools (managed)              └── SAML federation                  │
│  ├── Cluster autoscaler                                                     │
│  ├── AWS Load Balancer Controller      Observability                        │
│  ├── External Secrets Operator         ├── CloudWatch                       │
│  ├── Cert-manager + ACM                ├── DataDog/Splunk                   │
│  └── Ingress controller (ALB/nginx)    └── PagerDuty                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**platform.yaml role**: REFERENCE only (ARNs, endpoints, account IDs)

### Layer 2: Floe-Deployed Services (Our Helm Charts)

These are **deployed** by `floe-infrastructure` and `floe-dagster` Helm charts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FLOE-RUNTIME DEPLOYED SERVICES                         │
│                      (helm install floe-infrastructure)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Data Plane (stateful)                 Control Plane (stateless)            │
│  ├── PostgreSQL (metadata)             ├── Dagster webserver                │
│  ├── LocalStack/MinIO (local S3)       ├── Dagster daemon                   │
│  │   (or uses real S3 in prod)         ├── User deployments (workers)       │
│  └── Polaris (Iceberg catalog)         └── Code locations                   │
│                                                                             │
│  Observability (optional)              Configuration                        │
│  ├── Jaeger (tracing)                  ├── platform-configmap               │
│  ├── Marquez (lineage)                 │   └── /etc/floe/platform.yaml      │
│  └── Prometheus (metrics)              └── floe-secrets (credentials)       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer 3: Configuration Injection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONFIGURATION DATA FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Platform Engineer                      Data Engineer                       │
│  ┌──────────────────┐                   ┌──────────────────┐                │
│  │  platform.yaml   │                   │    floe.yaml     │                │
│  │  ─────────────   │                   │    ──────────    │                │
│  │  • endpoints     │                   │  • pipelines     │                │
│  │  • credentials   │────────┬──────────│  • transforms    │                │
│  │  • cloud config  │        │          │  • schedules     │                │
│  │  • security      │        │          │  • profiles ref  │                │
│  └────────┬─────────┘        │          └────────┬─────────┘                │
│           │                  │                   │                          │
│           ▼                  │                   ▼                          │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │                    PlatformResolver                      │                │
│  │         (Merges platform.yaml + floe.yaml)              │                │
│  └─────────────────────────────────────────────────────────┘                │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │                   CompiledArtifacts                      │                │
│  │   (dbt profiles, Dagster config, Iceberg catalog)       │                │
│  └─────────────────────────────────────────────────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What platform.yaml Actually Controls

| Section | What It Does | Pre-existing? | Deployed? | Configured? |
|---------|--------------|---------------|-----------|-------------|
| `infrastructure.cloud.aws` | **Reference** AWS account, VPC, ARNs | Yes | No | Reference only |
| `infrastructure.network.ingress` | Configure ingress (ALB, nginx) | Yes (controller) | No | Ingress resources |
| `infrastructure.network.local_access` | NodePort for local dev | No | Yes (Service type) | Port mappings |
| `security.authentication.oidc` | **Reference** OIDC provider | Yes | No | OAuth2-proxy config |
| `security.secret_backends` | Where to read secrets from | Yes (Vault/SM) | No | ESO config |
| `storage.*.endpoint` | S3 endpoint (LocalStack or AWS) | Yes (AWS S3) | Yes (LocalStack) | PyIceberg config |
| `catalogs.*.uri` | Polaris REST endpoint | No | Yes | PyIceberg config |
| `observability.otlp_endpoint` | Jaeger/OTel collector | No | Yes | OpenTelemetry config |

**Key Insight**: Most of `infrastructure` and `security` sections are **reference/documentation** that:
1. Tell operators where enterprise services are
2. Configure Helm values for ingress/secrets
3. Do NOT provision cloud resources

---

## Security Model: Zero Secrets in Code

### The Credential Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CREDENTIAL RESOLUTION FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Platform Engineer defines MODE                                          │
│     ┌────────────────────────────────────┐                                  │
│     │ credentials:                        │                                  │
│     │   mode: oauth2                      │  ← No secrets here!             │
│     │   client_id:                        │                                  │
│     │     secret_ref: polaris-client-id   │  ← Reference, not value         │
│     └────────────────────────────────────┘                                  │
│                                                                             │
│  2. Secrets stored in backend (Vault, AWS SM, K8s Secrets)                  │
│     ┌────────────────────────────────────┐                                  │
│     │ kubectl create secret generic ...   │                                  │
│     │ aws secretsmanager create-secret ...│                                  │
│     └────────────────────────────────────┘                                  │
│                                                                             │
│  3. Runtime resolves via SecretReference                                    │
│     ┌────────────────────────────────────┐                                  │
│     │ PlatformResolver.resolve_secret()  │                                  │
│     │   → K8s Secret mount              │                                   │
│     │   → AWS Secrets Manager API       │                                   │
│     │   → Vault API                     │                                   │
│     └────────────────────────────────────┘                                  │
│                                                                             │
│  4. Polaris vends temporary S3 credentials via STS                          │
│     ┌────────────────────────────────────┐                                  │
│     │ Polaris → STS AssumeRole           │  ← Short-lived credentials       │
│     │ PyIceberg gets temp creds          │                                  │
│     │ No static AWS keys in code         │                                  │
│     └────────────────────────────────────┘                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Credential Modes

| Mode | Use Case | How It Works |
|------|----------|--------------|
| `static` | Local dev, testing | Username/password from secret_ref |
| `oauth2` | Polaris, APIs | Client credentials flow |
| `iam_role` | AWS production | IRSA (IAM Roles for Service Accounts) |
| `vended_credentials` | S3 via Polaris | Polaris vends temp creds via STS |

---

## Persona Separation: Platform vs. Data Engineer

### Platform Engineer Responsibilities

```yaml
# platform.yaml - Managed by Platform Engineering
version: "1.1.0"

infrastructure:
  cloud:
    provider: aws
    region: us-east-1
    aws:
      account_id: "123456789012"
      iam:
        service_accounts:
          dagster:
            role_arn: "arn:aws:iam::123456789012:role/FloeDAGSTER"

security:
  authentication:
    enabled: true
    method: oidc
    oidc:
      provider_url: "https://auth.company.com"
      client_id: "floe-platform"
  secret_backends:
    primary: aws_secrets_manager

storage:
  default:
    type: s3
    bucket: prod-iceberg-data
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/IcebergStorage"

observability:
  otlp_endpoint: "https://otel-collector.company.com:4317"
```

**Platform engineers manage**: Where things are, how to authenticate, security policies.

### Data Engineer Responsibilities

```yaml
# floe.yaml - Managed by Data Engineering
name: sales-analytics
version: "1.0.0"

# Reference profiles, not configure them
profiles:
  storage: default      # Uses platform.yaml storage.default
  catalog: default      # Uses platform.yaml catalogs.default
  compute: default      # Uses platform.yaml compute.default

transforms:
  - name: raw_to_bronze
    type: dbt
    project: sales_dbt
    models:
      - path: models/bronze/*.sql

  - name: bronze_to_silver
    type: dbt
    project: sales_dbt
    models:
      - path: models/silver/*.sql

schedules:
  - name: daily_refresh
    cron: "0 6 * * *"
    transforms: [raw_to_bronze, bronze_to_silver]
```

**Data engineers manage**: What to build, when to run, business logic.

---

## Environment Progression

The same `floe.yaml` works across all environments:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENVIRONMENT PROGRESSION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  floe.yaml (unchanged)                                                      │
│       │                                                                     │
│       ├──────► LOCAL                                                        │
│       │        platform/local/platform.yaml                                 │
│       │        • LocalStack S3                                              │
│       │        • Local Polaris                                              │
│       │        • No auth                                                    │
│       │                                                                     │
│       ├──────► DEV                                                          │
│       │        platform/dev/platform.yaml                                   │
│       │        • AWS S3 (dev account)                                       │
│       │        • Polaris (dev cluster)                                      │
│       │        • OIDC auth                                                  │
│       │                                                                     │
│       ├──────► STAGING                                                      │
│       │        platform/staging/platform.yaml                               │
│       │        • AWS S3 (staging account)                                   │
│       │        • Polaris (staging cluster)                                  │
│       │        • OIDC + MFA                                                 │
│       │                                                                     │
│       └──────► PROD                                                         │
│                platform/prod/platform.yaml                                  │
│                • AWS S3 (prod account)                                      │
│                • Polaris (prod cluster)                                     │
│                • OIDC + MFA + Audit                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Observability Stack

### Integrated Observability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Dagster   │      │     dbt     │      │  PyIceberg  │                  │
│  │   Assets    │      │   Models    │      │   Tables    │                  │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘                  │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌─────────────────────────────────────────────────────────┐                │
│  │              OpenTelemetry SDK (floe-core)              │                │
│  │  • Automatic span creation                              │                │
│  │  • Context propagation                                  │                │
│  │  • Baggage for classification                           │                │
│  └─────────────────────────────────────────────────────────┘                │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌───────────┐        ┌───────────┐        ┌───────────┐                    │
│  │  Jaeger   │        │ Prometheus │        │  Marquez  │                    │
│  │ (Traces)  │        │ (Metrics)  │        │ (Lineage) │                    │
│  └───────────┘        └───────────┘        └───────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Gets Traced

| Component | Spans Generated | Metrics | Lineage Events |
|-----------|-----------------|---------|----------------|
| Dagster | Asset materializations, runs, steps | Run duration, success rate | OpenLineage RunEvents |
| dbt | Model executions, tests | Model duration, row counts | OpenLineage via dbt |
| PyIceberg | Table scans, writes | Snapshot size, file counts | Table metadata |
| Polaris | API calls, auth | Request latency | Catalog access |

---

## Quick Start: Local to Production

### 1. Local Development

```bash
# Start infrastructure with LocalStack
make deploy-local-infra

# Deploy Dagster
make deploy-local-dagster

# Access services
open http://localhost:30000    # Dagster UI
open http://localhost:30181    # Polaris API
open http://localhost:30566    # LocalStack (S3/STS)
```

### 2. AWS Deployment

```bash
# Configure AWS credentials
aws configure

# Create EKS cluster (or use existing)
eksctl create cluster --name floe-prod --region us-east-1

# Deploy with production platform.yaml
helm install floe-infra charts/floe-infrastructure \
  -n floe \
  -f platform/prod/values.yaml \
  --set-file platformConfig.content=platform/prod/platform.yaml

# Deploy Dagster
helm install floe-dagster charts/floe-dagster \
  -n floe \
  -f platform/prod/values.yaml
```

---

## Summary: Why This Architecture

| Benefit | How Floe Delivers |
|---------|-------------------|
| **Security by Default** | Zero secrets in code via SecretReference |
| **Environment Parity** | Same floe.yaml, different platform.yaml |
| **Separation of Concerns** | Platform engineers vs. data engineers |
| **Enterprise Ready** | OIDC, RBAC, audit logging, encryption |
| **Production Aligned** | LocalStack mirrors AWS credential flow |
| **Observable** | OpenTelemetry + OpenLineage built in |

The two-tier architecture means:
- **Data engineers** focus on pipelines and business logic
- **Platform engineers** manage infrastructure once
- **Security teams** audit a single configuration source
- **Operations** get consistent deployments across environments
