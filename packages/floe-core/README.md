# floe-core

Core schemas and compilation for floe-runtime.

## Overview

floe-core provides the **two-tier configuration architecture** ([ADR-0002](../../docs/adr/0002-two-tier-config.md)):

- **PlatformSpec**: Infrastructure configuration (`platform.yaml`) for platform engineers
- **FloeSpec**: Pipeline configuration (`floe.yaml`) for data engineers
- **CompiledArtifacts v2.0**: Merged output contract with resolved profiles
- **Compiler**: Transform FloeSpec + PlatformSpec → CompiledArtifacts
- **JSON Schema export**: For IDE validation support

## Installation

```bash
pip install floe-core
```

## Two-Tier Configuration

The two-tier architecture separates concerns:

| Tier | File | Owner | Contents |
|------|------|-------|----------|
| **Platform** | `platform.yaml` | Platform Engineer | Storage, catalogs, compute, credentials |
| **Pipeline** | `floe.yaml` | Data Engineer | Transforms, governance, observability flags |

### Platform Configuration (Platform Engineer)

```python
from floe_core import PlatformSpec

# Load platform configuration for current environment
platform = PlatformSpec.from_yaml(Path("platform/local/platform.yaml"))

# Access profiles
catalog = platform.catalogs["default"]
storage = platform.storage["default"]
```

### Pipeline Configuration (Data Engineer)

```python
from floe_core import FloeSpec

# Parse pipeline with profile references (no infrastructure details)
spec = FloeSpec.model_validate({
    "name": "my-pipeline",
    "catalog": "default",    # Logical reference
    "storage": "default",    # Resolved at compile time
    "compute": "default",
    "transforms": [{"type": "dbt", "path": "./models"}]
})
```

### Compilation (Merge)

```python
from floe_core import Compiler, PlatformResolver

# Load platform config based on FLOE_PLATFORM_ENV
platform = PlatformResolver.load()

# Compile pipeline with platform profiles
compiler = Compiler()
artifacts = compiler.compile(
    spec_path=Path("floe.yaml"),
    platform=platform
)

# Artifacts contain resolved profiles (but secret_refs, not secrets)
print(artifacts.resolved_catalog.uri)  # "http://polaris:8181/api/catalog"
```

## Credential Security

All sensitive fields use `secret_ref` references, resolved at **runtime** (not compile time):

```python
from floe_core import SecretReference, CredentialConfig

# Secret reference pattern
secret = SecretReference(secret_ref="polaris-oauth-secret")
resolved = secret.resolve()  # From env var or K8s secret at runtime

# Credential modes
config = CredentialConfig(
    mode="oauth2",
    client_id="my-client",
    client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
    scope="PRINCIPAL_ROLE:DATA_ENGINEER"
)
```

## JSON Schema Export

```python
from floe_core import FloeSpec, PlatformSpec

# Export schemas for IDE autocomplete
FloeSpec.model_json_schema()     # For floe.yaml
PlatformSpec.model_json_schema() # For platform.yaml
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#2-floe-core) for details.

## License

Apache 2.0
