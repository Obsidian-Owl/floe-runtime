# Floe Runtime Scripts

Quick reference for operational scripts.

## Deployment

**Full clean deployment** (recommended):
```bash
./scripts/deploy/local.sh          # Clean + deploy + validate
```

**E2E deployment with validation**:
```bash
./scripts/deploy/e2e.sh            # Deploy with comprehensive E2E tests
```

**Interactive quickstart**:
```bash
./scripts/deploy/quickstart.sh     # Interactive deployment wizard
```


## Validation

**Comprehensive E2E validation** (with evidence generation):
```bash
./scripts/validate/e2e.sh          # Full pipeline validation + evidence
```

**Quick health check**:
```bash
./scripts/validate/basic.sh        # Quick smoke test
```


## Cleanup

**Full cleanup** (recommended - cleans everything):
```bash
./scripts/cleanup/all.sh           # Polaris + Dagster + Marquez + S3 + K8s
```

**Component-specific cleanup**:
```bash
./scripts/cleanup/dagster.sh       # Clean Dagster run history only
./scripts/cleanup/polaris.sh       # Clean Polaris catalog only
./scripts/cleanup/marquez.sh       # Clean Marquez lineage only
./scripts/cleanup/s3.sh            # Clean S3 buckets only
```


## Dagster Operations

**Run demo materialization pipeline**:
```bash
./scripts/dagster/materialize-demo.sh          # Execute full demo pipeline
```

**Launch specific Dagster job**:
```bash
./scripts/dagster/launch-job.sh <job-name>     # Launch and monitor job
```

**Monitor Dagster run**:
```bash
./scripts/dagster/monitor-run.sh <run-id>      # Monitor run status
```


## Development Setup

**Bootstrap development environment**:
```bash
./scripts/bootstrap.sh             # Install dependencies, setup tools
```

## Directory Structure

```
scripts/
├── deploy/
│   ├── local.sh                   # Clean deployment (CANONICAL)
│   ├── e2e.sh                     # E2E deployment with tests
│   └── quickstart.sh              # Interactive wizard
├── cleanup/
│   ├── all.sh                     # Full cleanup (RECOMMENDED)
│   ├── dagster.sh                 # Dagster run history
│   ├── polaris.sh                 # Polaris catalog
│   ├── marquez.sh                 # Marquez lineage
│   └── s3.sh                      # S3 buckets
├── validate/
│   ├── e2e.sh                     # Comprehensive validation
│   └── basic.sh                   # Quick smoke test
├── dagster/
│   ├── materialize-demo.sh        # Demo pipeline
│   ├── launch-job.sh              # Job launcher
│   └── monitor-run.sh             # Run monitor
├── bootstrap.sh                   # Dev environment setup
└── README.md                      # This file
```

## Requirements

**CRITICAL**: Infrastructure MUST be deployed with release name `floe-infra`.

See [../demo/platform-config/DEPLOYMENT-REQUIREMENTS.md](../demo/platform-config/DEPLOYMENT-REQUIREMENTS.md) for details.

## Troubleshooting

**Deployment stuck in `pending-install`**:
```bash
helm uninstall floe-infra -n floe --no-hooks
kubectl delete namespace floe
./scripts/deploy/local.sh
```

**Orphaned resources in default namespace**:
```bash
kubectl delete deployment floe-infra-polaris -n default
```

**Image pull failures**:
```bash
# Check image tags in values.yaml
grep "tag:" demo/platform-config/charts/*/values*.yaml

# Verify image exists
docker pull <image>:<tag>
```

**Polaris namespace errors**:
```bash
# Check Polaris init logs
kubectl logs -n floe job/floe-infra-polaris-init

# Clean Polaris catalog
./scripts/cleanup/polaris.sh
```

**Seed data job failures**:
```bash
# Check seed data logs
kubectl logs -n floe job/floe-infra-seed-data

# Verify namespaces exist
kubectl exec -n floe deployment/floe-infra-polaris -- \
  curl -s http://localhost:8181/api/catalog/v1/demo_catalog/namespaces
```

