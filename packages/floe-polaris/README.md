# floe-polaris

Apache Polaris catalog integration for floe-runtime.

## Overview

floe-polaris provides integration with Apache Polaris for catalog management, with support for multiple credential modes and runtime secret resolution:

- **PolarisClient**: Wrapper for Polaris REST API with credential mode support
- **Catalog Factory**: Create catalog clients from resolved platform configuration
- **Credential Modes**: Static, OAuth2, IAM Role, Service Account
- **Secret Resolution**: Runtime resolution from environment variables or K8s secrets

## Installation

```bash
pip install floe-polaris
```

## Credential Modes

floe-polaris supports multiple credential modes as defined in `platform.yaml`:

| Mode | Description | Use Case |
|------|-------------|----------|
| `static` | Client ID/secret from `secret_ref` | Local development, simple deployments |
| `oauth2` | OAuth2 client credentials flow | Production, automatic token refresh |
| `iam_role` | AWS IAM role assumption | AWS deployments, no static credentials |
| `service_account` | GCP/Azure workload identity | Cloud-native deployments |

## Usage

### From CompiledArtifacts (Recommended)

```python
from floe_polaris import create_catalog_client
from floe_core import CompiledArtifacts

# Load artifacts (contains resolved platform config)
artifacts = CompiledArtifacts.model_validate_json(Path("artifacts.json").read_text())

# Create client from resolved catalog profile
client = create_catalog_client(artifacts)

# Use the catalog
tables = client.list_tables("my_namespace")
```

### Direct Configuration

```python
from floe_polaris import PolarisClient
from floe_core import CredentialConfig, SecretReference

# Create client with OAuth2 credentials
client = PolarisClient(
    uri="http://polaris:8181/api/catalog",
    warehouse="warehouse",
    credentials=CredentialConfig(
        mode="oauth2",
        client_id="my-client",
        client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
        scope="PRINCIPAL_ROLE:DATA_ENGINEER"
    )
)

# Secrets are resolved at runtime when catalog is accessed
catalog = client.catalog
```

## Secret Resolution

Credentials are resolved at **runtime**, not at compile time:

```python
# In platform.yaml
catalogs:
  default:
    credentials:
      mode: oauth2
      client_secret:
        secret_ref: polaris-oauth-secret  # K8s secret name

# Resolution order:
# 1. Environment variable: POLARIS_OAUTH_SECRET
# 2. K8s secret mount: /var/run/secrets/polaris-oauth-secret
```

## Architecture

floe-polaris integrates with Polaris via the standard Iceberg REST catalog API:

- Namespace management
- Principal and role management
- Access control policies
- Metadata storage
- OAuth2 token refresh

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#7-floe-polaris) for details.

## Development

```bash
uv sync
uv run pytest packages/floe-polaris/tests/
```

## License

Apache 2.0
