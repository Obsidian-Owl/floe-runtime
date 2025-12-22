# Environment Examples

Environment-specific Helm values and configurations for floe-runtime deployment.

## Directory Structure

```
environments/
├── dev/          # Development environment
├── staging/      # Staging environment
└── prod/         # Production environment
```

## Usage

Each environment directory contains:
- `values.yaml` - Environment-specific Helm values
- `secrets.yaml` - Secret references (External Secrets, Sealed Secrets, or SOPS)

### Deploy to specific environment

```bash
# Using Helm directly
helm upgrade --install floe-runtime ./charts/floe-runtime \
  -f examples/environments/dev/values.yaml \
  -n floe-dev

# Using ArgoCD
# Reference the values file in your Application manifest
```

## Environment Differences

| Setting | Dev | Staging | Prod |
|---------|-----|---------|------|
| Replicas | 1 | 2 | 3+ |
| Resources | Low | Medium | High |
| Persistence | Optional | Required | Required |
| TLS | Optional | Required | Required |

Covers: 007-FR-003 (environment promotion pipeline)
