# Floe Demo - E-Commerce Analytics Pipeline

This demo showcases a complete lakehouse data platform using floe-runtime.

## Repository Structure

This demo uses a **monorepo structure for simplicity**, but demonstrates **clear separation of concerns**:

```
demo/
├── platform/              # 🔐 Platform Engineering (Infrastructure)
│   └── platform.yaml      # Storage, catalog, observability config
│                          # Credentials, endpoints, infrastructure
│
└── data_engineering/      # 📊 Data Engineering (Pipelines)
    ├── floe.yaml          # Pipeline config (NO credentials)
    ├── orchestration/     # Dagster assets
    ├── dbt/               # SQL transformations
    └── semantic/          # Cube models (moved to /cube for now)
```

### Production Recommendations

In a **production environment**, we recommend one of these structures:

#### Option 1: Multi-Repo (Strongest Isolation)
```
platform-config/          # Private repo - Platform team only
  └── platform.yaml       # All infrastructure + credentials

data-pipelines/           # Shared repo - Data engineers
  ├── floe.yaml
  ├── orchestration/
  └── dbt/
```

**Benefits:**
- Complete credential isolation
- Independent access controls
- Separate CI/CD pipelines
- Clearer blast radius

#### Option 2: Monorepo with Path-Based Access Controls
```
monorepo/
  ├── platform/           # CODEOWNERS: @platform-team
  │   └── platform.yaml   # Protected branch rules
  └── pipelines/          # CODEOWNERS: @data-team
      ├── floe.yaml
      └── dbt/
```

**Benefits:**
- Single source of truth
- Atomic commits across layers
- Simplified dependency management

**Required:**
- GitHub CODEOWNERS or GitLab Code Owners
- Branch protection rules
- Separate CI/CD jobs with different credentials

## Two-Tier Configuration Architecture

### Platform Team Owns:
- `platform/platform.yaml`
  - Storage endpoints (S3, buckets)
  - Catalog endpoints (Polaris, warehouses)
  - Observability (Jaeger, Marquez)
  - **All credentials** (via secret references)

### Data Team Owns:
- `data-engineering/floe.yaml`
  - Pipeline definitions
  - Table schemas
  - Transformation logic
  - **Zero credentials** (references profiles by name)

### Security Model

```yaml
# platform/platform.yaml (Platform team - NEVER in data team repo)
storage:
  default:
    type: s3
    endpoint: "http://production-s3.internal"
    credentials:
      secret_ref: s3-credentials  # ← Resolved at runtime

# data_engineering/floe.yaml (Data team - NO secrets)
name: customer-analytics
storage: default  # ← Logical reference only
```

**Data engineers never see:**
- Storage endpoints
- Catalog credentials
- Service URLs
- Secret values

## Demo Pipeline

### Medallion Architecture

```
Raw Data → Bronze → Silver → Gold → Semantic Layer
```

**Bronze** (Raw + Light Cleaning):
- `demo.bronze_customers` (1,000 records)
- `demo.bronze_orders` (5,000 records)
- `demo.bronze_products` (100 records)
- `demo.bronze_order_items` (10,000 records)

**Silver** (Cleaned + Enriched):
- `stg_customers` (deduplicated, standardized)
- `stg_orders` (validated, enriched)
- `stg_products` (categorized)
- `stg_order_items` (joined, calculated)

**Gold** (Aggregated Marts):
- `mart_customer_orders` (customer analytics)
- `mart_revenue` (revenue analytics with trends)
- `mart_product_performance` (product analytics)

**Semantic** (BI Layer):
- Cube models: Customers, Orders, Products
- REST, GraphQL, SQL APIs

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Storage** | Apache Iceberg + S3 | ACID lakehouse tables |
| **Catalog** | Polaris REST | Metadata + governance |
| **Transform** | dbt + DuckDB | SQL transformations |
| **Orchestration** | Dagster | Asset-based pipelines |
| **Semantic** | Cube | BI semantic layer |
| **Observability** | Jaeger + Marquez | Tracing + lineage |

## Deployment

### Kubernetes (Recommended)
```bash
# Deploy complete stack (uses demo/platform/platform.yaml)
make deploy-local-full

# Access services
Dagster UI:  http://localhost:30000
Cube API:    http://localhost:30400
Jaeger UI:   http://localhost:30686
Marquez UI:  http://localhost:30301
```

### Docker Compose (Development)
```bash
cd testing/docker
docker compose --profile demo up -d

# Access services
Dagster UI:  http://localhost:3000
Cube API:    http://localhost:4000
Jaeger UI:   http://localhost:16686
```

## Key Files

### Platform Configuration
- `platform/platform.yaml` - Infrastructure config (Platform team)

### Data Engineering
- `data_engineering/floe.yaml` - Pipeline config (Data team)
- `data_engineering/orchestration/definitions.py` - Dagster assets
- `data_engineering/dbt/models/` - SQL transformations

### Semantic Layer
- `cube/schema/` - Cube models (will move to data-engineering/semantic/)

## Security Notes

⚠️ **This demo uses hardcoded credentials for simplicity.**

In production:
1. **Never commit credentials to Git**
2. Use secret managers (Vault, AWS Secrets Manager, K8s Secrets)
3. Use CODEOWNERS / branch protection for `platform/`
4. Separate CI/CD pipelines with different IAM roles
5. Audit `platform.yaml` changes (requires approval from security team)

## Next Steps

- See [docs/demo-quickstart.md](../docs/demo-quickstart.md) for detailed deployment guide
- See [docs/platform-config.md](../docs/platform-config.md) for platform.yaml reference
- See [docs/pipeline-config.md](../docs/pipeline-config.md) for floe.yaml reference
