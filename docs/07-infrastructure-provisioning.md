# 07. Infrastructure Provisioning

This document describes how to provision external infrastructure for floe-runtime deployments.

**Note**: floe-runtime deploys the **orchestration layer** (Dagster, dbt, Cube). External services must be provisioned separately.

---

## 1. Overview

### Self-Hosted vs. Managed

| Component | Self-Hosted | Managed |
|-----------|-------------|---------|
| **Compute Engine** | DuckDB (embedded), Trino | MotherDuck, Snowflake, BigQuery |
| **Object Storage** | MinIO, LocalStack (dev) | S3, GCS, ADLS |
| **Iceberg Catalog** | Apache Polaris, Nessie | Snowflake Polaris, AWS Glue |
| **PostgreSQL** | K8s StatefulSet | RDS, Cloud SQL, Azure DB |
| **Observability** | Jaeger, Marquez | Grafana Cloud, Datadog |

### Minimum Viable Infrastructure

For development and small-scale production with DuckDB:

```
REQUIRED:
├── Object Storage (S3/GCS/MinIO)
├── Iceberg Catalog (Polaris)
└── PostgreSQL (Dagster metadata)

OPTIONAL:
├── OTel Collector + Jaeger (tracing)
├── Marquez (lineage)
└── Cube (semantic layer)
```

---

## 2. Object Storage

### AWS S3

```bash
# Create bucket for Iceberg data
aws s3 mb s3://my-iceberg-warehouse

# Create bucket for Cube pre-aggregations (if using Cube)
aws s3 mb s3://my-cube-preaggs

# Set lifecycle policy (optional)
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-iceberg-warehouse \
  --lifecycle-configuration file://lifecycle.json
```

### Google Cloud Storage

```bash
# Create bucket for Iceberg data
gsutil mb gs://my-iceberg-warehouse

# Set IAM permissions
gsutil iam ch serviceAccount:floe@project.iam.gserviceaccount.com:objectAdmin gs://my-iceberg-warehouse
```

### LocalStack (Development)

```yaml
# docker-compose.yml
localstack:
  image: localstack/localstack:latest
  ports:
    - "4566:4566"
  environment:
    SERVICES: s3,sts,iam
    DEFAULT_REGION: us-east-1
```

---

## 3. Iceberg Catalog

### Apache Polaris (Self-Hosted)

```yaml
# docker-compose.yml
polaris:
  image: apache/polaris:latest
  ports:
    - "8181:8181"
  environment:
    AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
    AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    AWS_REGION: ${AWS_REGION:-us-east-1}
    CATALOG_DEFAULT_LOCATION: s3://my-iceberg-warehouse/
  depends_on:
    - localstack  # or real S3
```

### Polaris Configuration

```python
# PyIceberg connection
from pyiceberg.catalog import load_catalog

catalog = load_catalog(
    "polaris",
    **{
        "type": "rest",
        "uri": "http://polaris:8181/api/catalog",
        "warehouse": "my-warehouse",
        "credential": "client_id:client_secret",
    }
)
```

### Alternative Catalogs

| Catalog | Use Case | Notes |
|---------|----------|-------|
| **Polaris** | Open source, standalone | Apache 2.0, REST API |
| **Nessie** | Git-like versioning | Apache 2.0, OSS |
| **Snowflake** | Managed Polaris | Snowflake ecosystem |
| **AWS Glue** | AWS-native | Proprietary API |

---

## 4. Compute Engines

### DuckDB (Default)

No external provisioning required - DuckDB is embedded in Dagster workers.

**Kubernetes Configuration:**

```yaml
# values.yaml
dagster:
  workers:
    resources:
      requests:
        memory: 8Gi
        cpu: 4
      limits:
        memory: 8Gi
        cpu: 4
    env:
      - name: DUCKDB_MEMORY_LIMIT
        value: "8GB"  # Match container memory
```

### Trino (Self-Hosted)

```yaml
# docker-compose.yml
trino:
  image: trinodb/trino:479
  ports:
    - "8080:8080"
  volumes:
    - ./trino-config:/etc/trino:ro
  environment:
    TRINO_ENVIRONMENT: production
```

**Trino Catalog Configuration:**

```properties
# trino-config/catalog/iceberg.properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://polaris:8181/api/catalog
iceberg.rest-catalog.warehouse=my-warehouse
```

### Snowflake

```sql
-- Create warehouse
CREATE WAREHOUSE floe_wh WITH WAREHOUSE_SIZE = 'SMALL';

-- Create database
CREATE DATABASE floe_db;

-- Create role
CREATE ROLE floe_role;
GRANT USAGE ON WAREHOUSE floe_wh TO ROLE floe_role;
GRANT ALL ON DATABASE floe_db TO ROLE floe_role;

-- Create user
CREATE USER floe_user PASSWORD = 'secret' DEFAULT_ROLE = floe_role;
GRANT ROLE floe_role TO USER floe_user;
```

---

## 5. PostgreSQL

### Kubernetes StatefulSet (Development)

```yaml
# Included in floe-dagster Helm chart
dagster:
  postgresql:
    enabled: true
    auth:
      password: "dev-password"
    primary:
      persistence:
        size: 10Gi
```

### AWS RDS (Production)

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier dagster-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16 \
  --master-username dagster \
  --master-user-password secret \
  --allocated-storage 20 \
  --multi-az \
  --storage-encrypted

# Create database
psql -h dagster-postgres.xxx.rds.amazonaws.com -U dagster -c "CREATE DATABASE dagster;"
```

### GCP Cloud SQL

```bash
# Create Cloud SQL instance
gcloud sql instances create dagster-postgres \
  --database-version=POSTGRES_16 \
  --tier=db-custom-2-4096 \
  --region=us-central1 \
  --availability-type=regional

# Create database
gcloud sql databases create dagster --instance=dagster-postgres
```

---

## 6. Observability Stack

### OpenTelemetry Collector

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s

exporters:
  # Local Jaeger
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true

  # Grafana Cloud (production)
  otlp/grafana:
    endpoint: tempo-us-central1.grafana.net:443
    headers:
      authorization: "Basic ${GRAFANA_API_KEY}"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger]
```

### Jaeger (Development)

```yaml
# docker-compose.yml
jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "16686:16686"  # UI
    - "4317:4317"    # OTLP gRPC
    - "4318:4318"    # OTLP HTTP
  environment:
    COLLECTOR_OTLP_ENABLED: "true"
```

### Marquez (Data Lineage)

```yaml
# docker-compose.yml
marquez:
  image: marquezproject/marquez:latest
  ports:
    - "5000:5000"
    - "5001:5001"
  environment:
    MARQUEZ_PORT: 5000
    POSTGRES_HOST: postgres
    POSTGRES_DB: marquez
```

---

## 7. Infrastructure as Code

### Terraform Modules (Reference)

```hcl
# main.tf - Example structure
module "s3_bucket" {
  source = "./modules/s3"
  bucket_name = "my-iceberg-warehouse"
}

module "rds" {
  source = "./modules/rds"
  instance_class = "db.t3.medium"
  database_name = "dagster"
}

module "eks" {
  source = "./modules/eks"
  cluster_name = "floe-runtime"
  node_groups = {
    workers = {
      instance_types = ["m5.xlarge"]
      min_size = 2
      max_size = 10
    }
  }
}
```

### Pulumi (Reference)

```python
# __main__.py
import pulumi
import pulumi_aws as aws

# S3 bucket for Iceberg
bucket = aws.s3.Bucket("iceberg-warehouse")

# RDS for Dagster
rds = aws.rds.Instance("dagster-postgres",
    engine="postgres",
    engine_version="16",
    instance_class="db.t3.medium",
)

pulumi.export("bucket_name", bucket.id)
pulumi.export("rds_endpoint", rds.endpoint)
```

---

## 8. Security Considerations

### Secrets Management

| Approach | Use Case | Tools |
|----------|----------|-------|
| **External Secrets Operator** | K8s + AWS/GCP/Azure | ESO + Secrets Manager |
| **Sealed Secrets** | GitOps | Bitnami Sealed Secrets |
| **SOPS** | GitOps | Mozilla SOPS + Age |
| **Vault** | Enterprise | HashiCorp Vault |

### Network Security

```yaml
# NetworkPolicy for Dagster
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dagster-network-policy
spec:
  podSelector:
    matchLabels:
      app: dagster
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: floe-runtime
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: floe-runtime
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - port: 443  # External services (S3, etc.)
```

---

## 9. Cost Optimization

### Right-Sizing Guidelines

| Component | Dev | Staging | Production |
|-----------|-----|---------|------------|
| **DuckDB workers** | 4GB RAM | 8GB RAM | 16-32GB RAM |
| **Trino workers** | 2 nodes | 3 nodes | 5+ nodes |
| **PostgreSQL** | t3.micro | t3.small | t3.medium + Multi-AZ |
| **S3 storage** | Standard | Standard | Standard + Lifecycle |

### Spot/Preemptible Instances

```yaml
# EKS node group with spot instances
nodeGroups:
  workers-spot:
    instanceTypes: ["m5.xlarge", "m5a.xlarge"]
    capacityType: SPOT
    labels:
      node-type: spot
```

---

## 10. Migration Paths

### DuckDB → MotherDuck

1. Export Iceberg table metadata (unchanged)
2. Update floe.yaml compute target to `motherduck`
3. Configure MotherDuck credentials
4. Same Iceberg tables, different compute engine

### DuckDB → Trino

1. Deploy Trino cluster
2. Configure Trino Iceberg catalog
3. Update floe.yaml compute target to `trino`
4. Same Iceberg tables, different compute engine

### Self-Hosted → Managed

1. Migrate PostgreSQL to RDS/Cloud SQL
2. Migrate Polaris to Snowflake Polaris (if desired)
3. Update Helm values with external endpoints
4. Re-deploy with `--values values-prod.yaml`

---

## References

- [Apache Polaris Documentation](https://polaris.apache.org/)
- [PyIceberg REST Catalog](https://py.iceberg.apache.org/configuration/)
- [Trino Iceberg Connector](https://trino.io/docs/current/connector/iceberg.html)
- [Dagster Kubernetes Deployment](https://docs.dagster.io/deployment/guides/kubernetes/deploying-with-helm)
- [External Secrets Operator](https://external-secrets.io/)
