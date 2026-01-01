# Deployment Requirements

## Critical Constraint

**Infrastructure MUST be deployed with release name `floe-infra`**:

```bash
helm install floe-infra demo/platform-config/charts/floe-infrastructure -n floe
```

**Do NOT use any other release name** - the Dagster and Cube charts will fail.

## Why This Matters

The Dagster and Cube charts have hard-coded service references that assume the infrastructure release is named `floe-infra`:

**Hard-coded service names**:
- `floe-infra-postgresql` - Database for Dagster and Marquez
- `floe-infra-polaris` - Iceberg REST catalog
- `floe-infra-localstack` - S3-compatible storage (local development)
- `floe-infra-jaeger-collector` - OpenTelemetry trace collector
- `floe-infra-marquez` - OpenLineage metadata server

**Affected files**:
- `demo/platform-config/charts/floe-dagster/values-local.yaml` - Line references to PostgreSQL, Polaris, LocalStack
- `demo/platform-config/charts/floe-cube/values-local.yaml` - References to LocalStack, Jaeger, Marquez

## Deployment Order

The charts **must** be deployed in this order:

1. **floe-infrastructure** (release name: `floe-infra`)
   ```bash
   helm install floe-infra demo/platform-config/charts/floe-infrastructure -n floe
   ```

2. **floe-dagster** (release name: `floe-dagster`)
   ```bash
   helm install floe-dagster demo/platform-config/charts/floe-dagster -f demo/platform-config/charts/floe-dagster/values-local.yaml -n floe
   ```

3. **floe-cube** (release name: `floe-cube`)
   ```bash
   helm install floe-cube demo/platform-config/charts/floe-cube -f demo/platform-config/charts/floe-cube/values-local.yaml -n floe
   ```

## Recommended Deployment Method

**Use the provided deployment scripts** instead of manual Helm commands:

```bash
# Clean deployment (recommended)
./scripts/deploy-local-clean.sh

# Or use Makefile targets
make deploy-local
```

These scripts handle the correct release names, deployment order, and wait for readiness.

## Future Improvement

**TODO**: Make service discovery dynamic using Helm chart dependencies or templating.

Current implementation uses hard-coded service names for simplicity, but this should be refactored to use:
- Helm chart dependencies (subchart pattern)
- Templated service names based on release name
- Service discovery via DNS with configurable release names

## Troubleshooting

### "Service not found" errors in Dagster or Cube

**Problem**: Pods can't connect to infrastructure services

**Cause**: Infrastructure was deployed with wrong release name

**Fix**:
```bash
# Check infrastructure release name
helm list -n floe

# If it's not "floe-infra", redeploy with correct name
helm uninstall <wrong-name> -n floe
helm install floe-infra demo/platform-config/charts/floe-infrastructure -n floe
```

### ConfigMap not found errors

**Problem**: `floe-infra-platform-config` ConfigMap not found

**Cause**: Infrastructure release name mismatch

**Fix**: Same as above - ensure release name is exactly `floe-infra`
