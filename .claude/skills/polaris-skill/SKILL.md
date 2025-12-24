---
name: polaris-catalog
description: Research-driven Apache Polaris catalog management. Injects research steps for catalog operations, namespaces, principals, roles, and access control. Use when working with Iceberg catalog management, metadata organization, or access governance.
---

# Apache Polaris Catalog Management (Research-Driven)

## Philosophy

This skill does NOT prescribe specific catalog structures or access patterns. Instead, it guides you to:
1. **Research** the current Polaris version and REST API capabilities
2. **Discover** existing catalog, namespace, and role configurations
3. **Validate** your implementations against Polaris documentation
4. **Verify** integration with PyIceberg clients and compute engines

## Pre-Implementation Research Protocol

### Step 1: Verify Runtime Environment

**ALWAYS run this first**:
```bash
# Check if Polaris Python client is installed (v1.1.0+)
python -c "import polaris; print(f'Polaris {polaris.__version__}')" 2>/dev/null || echo "Polaris Python client not found"

# Check REST API availability (if running locally or remote)
curl -s http://localhost:8181/healthcheck || echo "Polaris API not reachable"
```

**Critical Questions to Answer**:
- Is Polaris running locally or remotely?
- What version is available? (1.1.0+ recommended for Python client)
- What authentication is configured? (OAuth, service principals)
- Is this Snowflake Polaris or open-source Apache Polaris?

### Step 2: Research SDK State (if unfamiliar)

**When to research**: If you encounter unfamiliar Polaris features or need to validate patterns

**Research queries** (use WebSearch):
- "Apache Polaris [feature] documentation 2025" (e.g., "Apache Polaris catalog roles 2025")
- "Apache Polaris Python client 2025"
- "Apache Polaris REST API catalog management 2025"

**Official documentation**: https://polaris.apache.org

**Key documentation sections**:
- Entities: https://polaris.apache.org/releases/1.0.1/entities/
- Getting Started: https://polaris.apache.org/releases/1.0.0/getting-started/using-polaris/
- REST API: OpenAPI specifications for management and catalog APIs

### Step 3: Discover Existing Patterns

**BEFORE creating new catalogs or roles**, search for existing implementations:

```bash
# Find Polaris client usage
rg "polaris|Polaris" --type py

# Find catalog configurations
rg "catalog.*polaris|REST.*catalog" --type py --type yaml

# Find principal/role management
rg "principal|role|privilege" --type py
```

**Key questions**:
- What catalogs already exist?
- What namespace structure is used?
- What principal roles are defined?
- What access control patterns are in place?

### Step 4: Validate Against Architecture

Check architecture docs for integration requirements:
- Read `/docs/` for catalog requirements and governance model
- Understand namespace organization strategy
- Verify compute target mappings to catalogs
- Check access control requirements

## Implementation Guidance (Not Prescriptive)

### Polaris Entities

**Core concept**: Polaris organizes metadata into hierarchical entities

**Entity hierarchy**:
```
Polaris Instance
├── Catalogs (top-level, map to Iceberg catalogs)
│   ├── Namespaces (logical grouping within catalogs)
│   │   ├── Tables (Iceberg tables)
│   │   └── Views (Iceberg views)
│   └── Storage Configuration (S3, Azure, GCS)
├── Principals (users or services)
├── Principal Roles (labels assigned to principals)
└── Catalog Roles (privilege sets scoped to catalogs)
```

**Research questions**:
- How should catalogs be organized? (by environment, by domain, by team)
- What namespace structure makes sense?
- How should principals map to users/services?
- What role hierarchy is needed?

### Catalog Management

**Core concept**: Catalogs are top-level containers for Iceberg metadata

**Research questions**:
- What catalogs should be created? (dev, staging, prod)
- What storage type? (S3, Azure, GCS)
- What catalog properties are needed?
- How should catalogs be configured for PyIceberg clients?

**SDK features to research**:
- Catalog creation via REST API or CLI
- Catalog properties: storage configuration, default namespace
- Catalog deletion and lifecycle management
- Storage types: S3, Azure Blob Storage, Google Cloud Storage

### Namespace Management

**Core concept**: Namespaces are logical groupings within catalogs

**Research questions**:
- What namespace hierarchy? (flat, nested, by domain)
- What naming conventions?
- What namespace properties?
- How should namespaces map to dbt schemas?

**SDK features to research**:
- Namespace creation: Single-level or nested
- Namespace properties: Custom metadata
- Namespace listing and discovery
- Namespace deletion

### Principal and Role Management

**Core concept**: Access control via principals, principal roles, and catalog roles

**Research questions**:
- What principals exist? (users, services, applications)
- What principal roles should be defined? (data_engineer, data_analyst, admin)
- What catalog roles? (read_only, read_write, admin)
- What privileges for each role? (table_read, table_write, namespace_create)

**SDK features to research**:
- Principal creation and management
- Principal roles: Assigning roles to principals
- Catalog roles: Defining privilege sets
- Privilege grants: Attaching roles to catalog entities
- Access delegation: Vended credentials model

### Access Control Model

**Core concept**: Multi-level access control via role-based permissions

**Access control flow**:
```
Principal → Principal Role → Catalog Role → Privileges → Entity
```

**Research questions**:
- What privilege model? (least privilege, role-based)
- What catalog-level permissions?
- What namespace-level permissions?
- What table-level permissions?

**SDK features to research**:
- Privileges: `TABLE_READ_DATA`, `TABLE_WRITE_DATA`, `NAMESPACE_CREATE`, etc.
- Catalog role grants: Assigning catalog roles to principal roles
- Inheritance: How permissions cascade
- Access delegation: `X-Iceberg-Access-Delegation` header

### REST API Integration

**Core concept**: Polaris exposes management and catalog APIs via REST

**Research questions**:
- What API authentication is needed?
- How should API clients be configured?
- What endpoints are needed? (catalog CRUD, namespace CRUD, role management)
- How should errors be handled?

**SDK features to research**:
- Management API: Catalog, principal, role operations
- Catalog API: Iceberg REST specification
- Authentication: OAuth tokens, service principals
- OpenAPI specifications: REST API documentation

## Validation Workflow

### Before Implementation
1. ✅ Verified Polaris availability (local or remote)
2. ✅ Searched for existing catalog and role configurations
3. ✅ Read architecture docs for governance requirements
4. ✅ Identified storage layer (S3, Azure, GCS)
5. ✅ Researched unfamiliar Polaris features

### During Implementation
1. ✅ Using Polaris REST API or Python client
2. ✅ Type hints on ALL functions and parameters (if using Python)
3. ✅ Proper error handling for API operations
4. ✅ Access control following least privilege principle
5. ✅ Namespace organization aligned with data domains
6. ✅ Storage configuration correct for cloud provider

### After Implementation
1. ✅ Verify catalog appears in Polaris
2. ✅ Test namespace creation and listing
3. ✅ Test principal and role creation
4. ✅ Verify PyIceberg client can connect using catalog
5. ✅ Test access control (permissions work as expected)
6. ✅ Check integration with compute engines (Spark, dbt)

## Context Injection (For Future Claude Instances)

When this skill is invoked, you should:

1. **Verify runtime state** (don't assume):
   ```bash
   curl -s http://localhost:8181/healthcheck
   python -c "import polaris; print(polaris.__version__)"
   ```

2. **Discover existing patterns** (don't invent):
   ```bash
   rg "polaris" --type py --type yaml
   ```

3. **Research when uncertain** (don't guess):
   - Use WebSearch for "Apache Polaris [feature] documentation 2025"
   - Check official docs: https://polaris.apache.org

4. **Validate against architecture** (don't assume requirements):
   - Read relevant architecture docs in `/docs/`
   - Understand catalog organization strategy
   - Check governance and access control requirements

5. **Check PyIceberg integration** (if applicable):
   - Verify REST catalog configuration points to Polaris
   - Check vended credentials configuration
   - Understand access delegation model

## Quick Reference: Common Research Queries

Use these WebSearch queries when encountering specific needs:

- **Catalog setup**: "Apache Polaris catalog creation REST API 2025"
- **Namespaces**: "Apache Polaris namespace management 2025"
- **Principals**: "Apache Polaris principal roles documentation 2025"
- **Access control**: "Apache Polaris catalog roles privileges 2025"
- **Python client**: "Apache Polaris Python client SDK 2025"
- **REST API**: "Apache Polaris REST API OpenAPI specification 2025"
- **Storage**: "Apache Polaris S3 Azure GCS storage configuration 2025"
- **PyIceberg integration**: "PyIceberg Polaris REST catalog 2025"
- **CLI**: "Apache Polaris CLI catalog management 2025"

## Integration Points to Research

### PyIceberg → Polaris Integration

**Key question**: How does PyIceberg connect to Polaris catalogs?

Research areas:
- REST catalog configuration in PyIceberg
- Polaris endpoint URL structure
- Credential management (OAuth, service principals)
- Access delegation headers (`X-Iceberg-Access-Delegation: vended-credentials`)
- Warehouse parameter (catalog name in Polaris)

### CompiledArtifacts → Polaris Configuration

**Key question**: How does floe-runtime configure Polaris catalogs?

Research areas:
- Catalog creation from CompiledArtifacts
- Namespace creation for dbt schemas
- Storage configuration from compute targets
- Principal/role setup for environments

### Governance Integration

**Key question**: How does Polaris enforce data governance?

Research areas:
- Column-level access control
- Row-level security (if supported)
- Audit logging
- Metadata tags and properties
- Integration with classification systems

## Polaris Development Workflow

### Local Development (Docker)
```bash
# Run Polaris locally
docker run -d -p 8181:8181 \
  --name polaris \
  apache/polaris:latest

# Check health
curl http://localhost:8181/healthcheck

# Access Polaris UI (if available)
open http://localhost:8181
```

### Using Polaris CLI
```bash
# Install Polaris CLI (if available)
pip install apache-polaris-cli

# List catalogs
polaris catalog list

# Create catalog
polaris catalog create my_catalog \
  --storage-type S3 \
  --default-base-location s3://my-bucket/data
```

### Using Python Client (v1.1.0+)
```python
from polaris import PolarisClient

# Initialize client
client = PolarisClient(
    host="localhost:8181",
    credentials={"client_id": "...", "client_secret": "..."}
)

# Create catalog
client.create_catalog(
    name="my_catalog",
    storage_type="S3",
    properties={"default-base-location": "s3://my-bucket/data"}
)

# Create namespace
client.create_namespace(
    catalog="my_catalog",
    namespace=["analytics", "staging"]
)
```

### Using REST API
```bash
# Create catalog via REST API
curl -X POST http://localhost:8181/api/management/v1/catalogs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_catalog",
    "storageType": "S3",
    "properties": {
      "default-base-location": "s3://my-bucket/data"
    }
  }'
```

## Access Control Example

### Creating Role Hierarchy
```
Principal: data_engineer_service
  ↓
Principal Role: data_engineer
  ↓
Catalog Role: analytics_writer
  ↓
Privileges:
  - NAMESPACE_CREATE (on catalog 'analytics')
  - TABLE_READ_DATA (on namespace 'analytics.staging')
  - TABLE_WRITE_DATA (on namespace 'analytics.staging')
```

### Implementation
```python
# Create principal
client.create_principal("data_engineer_service")

# Create principal role
client.create_principal_role("data_engineer")

# Assign principal role to principal
client.assign_principal_role("data_engineer_service", "data_engineer")

# Create catalog role
client.create_catalog_role(
    catalog="analytics",
    name="analytics_writer"
)

# Grant privileges to catalog role
client.grant_privilege(
    catalog="analytics",
    catalog_role="analytics_writer",
    privilege="NAMESPACE_CREATE"
)

# Assign catalog role to principal role
client.assign_catalog_role(
    principal_role="data_engineer",
    catalog="analytics",
    catalog_role="analytics_writer"
)
```

## Critical: S3 Storage Configuration for LocalStack/MinIO

### Storage Config API Schema (OpenAPI Spec)

**CRITICAL**: The Polaris management API uses **flat keys**, NOT nested objects:

```python
# ✅ CORRECT - Flat keys per OpenAPI spec (AwsStorageConfigInfo schema)
storage_config = {
    "storageType": "S3",
    "allowedLocations": ["s3://bucket-name/"],
    "endpoint": "http://localstack:4566",      # Flat key
    "pathStyleAccess": True,                    # Flat key (CRITICAL for LocalStack/MinIO)
    "roleArn": "arn:aws:iam::000000000000:role/my-role",  # Flat key
    "region": "us-east-1"
}

# ❌ WRONG - Some docs show dot-notation or nested, but API uses flat keys
storage_config = {
    "storageType": "S3",
    "s3.endpoint": "...",        # WRONG - Not accepted
    "s3.pathStyleAccess": True,  # WRONG - Not accepted
    "s3": {"endpoint": "..."}    # WRONG - Nested structure not accepted
}
```

### Path-Style Access

**Why it matters**: Without `pathStyleAccess: true`, Polaris tries virtual-hosted style URLs:
- Virtual-hosted: `http://bucket.localstack:4566/key` (fails DNS for LocalStack)
- Path-style: `http://localstack:4566/bucket/key` (works for LocalStack/MinIO)

**Error you'll see without it**:
```
UnknownHostException: iceberg-data.floe-infra-localstack: Name or service not known
```

### Catalog Storage Config Cannot Be Updated

**Known limitation**: Polaris does NOT allow updating storage config after catalog creation.
The PUT `/api/management/v1/catalogs/{name}` endpoint returns 400 if you try to change storage settings.

**Workaround**: Delete and recreate the catalog (requires deleting all namespaces/tables first).

**Helm init job pattern**: Check if catalog exists, create if not:
```python
# Check if catalog exists
status, resp = api_request("GET", f"/api/management/v1/catalogs/{CATALOG_NAME}", token=token)
if status == 200:
    # Catalog exists - cannot update storage config
    print(f"Catalog exists, continuing with existing config")
elif status == 404:
    # Create new catalog with correct storage config
    api_request("POST", "/api/management/v1/catalogs", {...}, token)
```

### Helm Chart Best Practices

The `floe-infrastructure` chart's `polaris-init-job.yaml` demonstrates:

1. **Wait for Polaris readiness** using init container:
   ```yaml
   initContainers:
     - name: wait-for-polaris
       image: busybox:1.36
       command:
         - sh
         - -c
         - |
           until wget -q --spider http://polaris:8182/q/health/ready; do
             sleep 5
           done
   ```

2. **OAuth2 authentication** for API calls:
   ```python
   def get_oauth_token():
       data = urllib.parse.urlencode({
           "grant_type": "client_credentials",
           "client_id": CLIENT_ID,
           "client_secret": CLIENT_SECRET,
           "scope": "PRINCIPAL_ROLE:ALL"
       }).encode()
       req = urllib.request.Request(
           f"{POLARIS_URI}/api/catalog/v1/oauth/tokens",
           data=data, method="POST"
       )
   ```

3. **Idempotent operations** - handle existing resources:
   ```python
   if status == 409:  # Conflict - already exists
       print("Already exists, continuing")
   ```

4. **Hierarchical namespace creation** - parent before child:
   ```python
   # Create parent "demo" first
   api_request("POST", f"/api/catalog/v1/{CATALOG_NAME}/namespaces",
               {"namespace": ["demo"]}, token)
   # Then create child "demo.bronze"
   api_request("POST", f"/api/catalog/v1/{CATALOG_NAME}/namespaces",
               {"namespace": ["demo", "bronze"]}, token)
   ```

### Polaris Environment Variables for AWS SDK

The Polaris container supports these AWS SDK environment variables:

```yaml
env:
  # Credentials for LocalStack (any value works)
  - name: AWS_ACCESS_KEY_ID
    value: "test"
  - name: AWS_SECRET_ACCESS_KEY
    value: "test"
  # Custom S3 endpoint
  - name: AWS_ENDPOINT_URL
    value: "http://localstack:4566"
  # Force path-style S3 access (for LocalStack/MinIO)
  # Note: This may not work in all cases - use catalog storageConfigInfo instead
  - name: AWS_S3_USE_PATH_STYLE_ACCESS
    value: "true"
  # AWS region
  - name: AWS_REGION
    value: "us-east-1"
```

**Important**: The `AWS_S3_USE_PATH_STYLE_ACCESS` env var may not be respected by Polaris.
Always set `pathStyleAccess: true` in the catalog's `storageConfigInfo` as the authoritative source.

### Credential Vending with IAM Role

For Polaris to vend temporary credentials via STS AssumeRole:

1. **Create IAM role in LocalStack** (via init job):
   ```bash
   aws --endpoint-url=http://localstack:4566 iam create-role \
     --role-name polaris-storage-role \
     --assume-role-policy-document '{"Version":"2012-10-17"...}'
   ```

2. **Attach S3 permissions** to the role:
   ```bash
   aws --endpoint-url=http://localstack:4566 iam attach-role-policy \
     --role-name polaris-storage-role \
     --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
   ```

3. **Configure catalog with roleArn**:
   ```python
   storage_config = {
       "storageType": "S3",
       "roleArn": "arn:aws:iam::000000000000:role/polaris-storage-role",
       "pathStyleAccess": True,
       "endpoint": "http://localstack:4566",
       "region": "us-east-1",
       "allowedLocations": ["s3://iceberg-data/"]
   }
   ```

4. **Disable vended credentials in PyIceberg client** if not using STS:
   ```python
   catalog = load_catalog(
       "polaris",
       type="rest",
       uri="http://polaris:8181/api/catalog",
       warehouse="demo_catalog",
       # Explicitly disable vended credentials to use static credentials
       header.X-Iceberg-Access-Delegation="none"
   )
   ```

## References

- [Apache Polaris Documentation](https://polaris.apache.org): Official documentation
- [Polaris Entities](https://polaris.apache.org/releases/1.0.1/entities/): Entity model reference
- [Using Polaris](https://polaris.apache.org/releases/1.0.0/getting-started/using-polaris/): Getting started guide
- [GitHub Repository](https://github.com/apache/polaris): Apache Polaris source
- [Polaris Blog](https://polaris.incubator.apache.org/blog/): Release announcements and updates
- [OpenAPI Spec](https://github.com/apache/polaris/blob/main/spec/polaris-management-service.yml): Authoritative API schema
- [Known Issue: roleArn update](https://github.com/apache/polaris/issues/582): Storage config cannot be updated

---

**Remember**: This skill provides research guidance, NOT prescriptive catalog structures. Always:
1. Verify Polaris availability and version
2. Discover existing catalog, namespace, and role configurations
3. Research Polaris capabilities when needed (use WebSearch liberally)
4. Validate against actual governance and access control requirements
5. Test catalog operations and PyIceberg integration before considering complete
6. Follow least privilege principle for access control
