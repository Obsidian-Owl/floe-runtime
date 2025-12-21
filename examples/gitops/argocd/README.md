# ArgoCD Examples

ArgoCD Application examples for deploying floe-runtime to Kubernetes.

## Contents

- `application.yaml` - Single Application deployment
- `applicationset.yaml` - Multi-environment ApplicationSet

## Usage

```bash
# Deploy to ArgoCD
kubectl apply -f application.yaml

# Or use ApplicationSet for multi-environment
kubectl apply -f applicationset.yaml
```

## Prerequisites

- ArgoCD installed in your cluster
- floe-runtime Helm charts available (charts/ directory)
- Kubernetes cluster with required resources

## Related Documentation

- [Deployment View](../../../docs/06-deployment-view.md)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)

Covers: 007-FR-004 (GitOps deployment with ArgoCD/Flux)
