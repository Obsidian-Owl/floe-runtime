# Flux Examples

Flux HelmRelease examples for deploying floe-runtime to Kubernetes.

## Contents

- `helmrelease.yaml` - HelmRelease for floe-runtime
- `kustomization.yaml` - Flux Kustomization

## Usage

```bash
# Apply Flux resources
kubectl apply -f helmrelease.yaml

# Or use with Flux GitOps
flux create source git floe-runtime \
  --url=https://github.com/your-org/floe-project \
  --branch=main
```

## Prerequisites

- Flux v2 installed in your cluster
- floe-runtime Helm charts available
- Kubernetes cluster with required resources

## Related Documentation

- [Deployment View](../../../docs/06-deployment-view.md)
- [Flux Documentation](https://fluxcd.io/docs/)

Covers: 007-FR-004 (GitOps deployment with ArgoCD/Flux)
