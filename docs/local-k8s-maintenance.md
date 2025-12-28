# Local Kubernetes Development - Cleanup and Maintenance

Comprehensive maintenance strategies for the floe-runtime local development environment running on Docker Desktop Kubernetes.

## Quick Reference

| Command | Description | Safety Level | Frequency |
|---------|-------------|--------------|-----------|
| `make dev-clean` | Daily cleanup (completed pods, volumes) | ✅ Safe | Daily |
| `make dev-clean-weekly` | Weekly maintenance (+ old containers) | ⚠️ Moderate | Weekly |
| `make dev-clean-monthly` | Monthly deep clean (+ unused images) | ⚠️ Moderate | Monthly |
| `make dev-reset` | Nuclear reset (destroys everything) | ❌ Destructive | When needed |
| `make dev-clean-dry-run` | Preview what would be cleaned | ✅ Safe | Anytime |

## Current Environment Status

Your environment shows typical accumulation patterns:

```bash
# 20 completed/failed Dagster job objects
kubectl get jobs -n floe | wc -l
# 17 Docker volumes (some potentially orphaned)
docker volume ls | wc -l
# 37 ConfigMaps/Secrets (normal for Helm)
kubectl get configmaps,secrets -n floe | wc -l
```

## Daily Maintenance Checklist

**Recommended: Run daily before/after development sessions**

```bash
# Preview what will be cleaned
make dev-clean-dry-run

# Execute safe daily cleanup
make dev-clean
```

**What it cleans:**
- ✅ Completed Dagster run pods (`status.phase==Succeeded`)
- ✅ Failed Dagster run pods (`status.phase==Failed`)
- ✅ Completed Dagster jobs (older than 1 hour)
- ✅ Dangling Docker volumes (`docker volume prune`)
- ✅ Python cache directories (`__pycache__`, `.pytest_cache`, etc.)
- ✅ Temporary Dagster directories (`/tmp/dagster-*`)

**What it preserves:**
- 🛡️ All running pods and services
- 🛡️ Recent jobs (< 1 hour old) for debugging
- 🛡️ Named Docker volumes in use
- 🛡️ ConfigMaps and Secrets
- 🛡️ Persistent data

## Weekly Maintenance Tasks

**Recommended: Run weekly during downtime**

```bash
# Preview weekly maintenance
make dev-clean-weekly-dry-run

# Execute weekly maintenance
make dev-clean-weekly
```

**Additional cleanup:**
- 🧹 Old ConfigMaps/Secrets (7+ days old, excludes platform config)
- 🧹 Stopped Docker containers (`docker container prune`)
- 🧹 All daily cleanup items

## Monthly Deep Clean

**Recommended: Run monthly or when disk space is low**

```bash
# Preview monthly cleanup
make dev-clean-monthly-dry-run

# Execute monthly cleanup
make dev-clean-monthly
```

**Additional cleanup:**
- 🗑️ Unused Docker images (`docker image prune -a`)
- 🗑️ System-wide Docker cleanup
- 🗑️ All weekly cleanup items

## Automated Cleanup (Optional)

For hands-off maintenance, deploy the automated cleanup CronJob:

```bash
# Deploy automated daily cleanup at 3 AM
kubectl apply -f k8s/cleanup-cronjob.yaml -n floe

# Check cleanup job status
kubectl get cronjobs,jobs -n floe -l app=floe-cleanup

# View cleanup logs
kubectl logs -l app=floe-cleanup -n floe --tail=50

# Remove automated cleanup
kubectl delete cronjob floe-cleanup -n floe
```

**CronJob Features:**
- 📅 Runs daily at 3 AM
- 🔒 Minimal RBAC permissions (only pods and jobs in floe namespace)
- 📝 Keeps history of last 3 successful, 1 failed job
- ⏰ Self-cleaning with `ttlSecondsAfterFinished: 3600`
- 🚫 `concurrencyPolicy: Forbid` prevents overlapping runs

## Nuclear Reset Option

**⚠️ DESTRUCTIVE - Use only when environment is completely broken**

```bash
# This destroys EVERYTHING and requires confirmation
make dev-reset
```

**What it destroys:**
- ❌ Entire `floe` namespace (all pods, services, jobs, secrets, ConfigMaps)
- ❌ All Helm releases (floe-infra, floe-dagster, floe-cube)
- ❌ ALL Docker volumes (including named volumes)
- ❌ ALL stopped containers
- ❌ ALL unused images
- ❌ All build artifacts

**Recovery:**
```bash
# Rebuild and redeploy everything
make demo-image-build
make deploy-local-full
make show-urls
```

## Safe Cleanup Guidelines

### Always Safe ✅
- Completed pods (`status.phase==Succeeded`)
- Failed pods (`status.phase==Failed`)
- Dangling Docker volumes (not attached to containers)
- Build cache directories
- Old completed jobs (1+ hours old)

### Use with Caution ⚠️
- Named Docker volumes (may contain data)
- ConfigMaps/Secrets (check for custom configs)
- Running containers (ensure they're not needed)
- Docker images (will require rebuild)

### Never Delete ❌
- Running pods with `status.phase==Running`
- Active services with endpoints
- Platform configuration ConfigMaps (`floe-infra-platform-config`)
- Secrets with credentials currently in use
- PVCs with important data (none in your current setup)

## Troubleshooting

### "No completed pods to clean"
Normal - your environment has already been cleaned or no jobs have run recently.

### "Permission denied" errors
The cleanup script needs kubectl access to the floe namespace:
```bash
kubectl auth can-i delete pods -n floe
kubectl auth can-i delete jobs -n floe
```

### Docker cleanup fails
Docker may be running as different user:
```bash
# Check Docker access
docker version
docker volume ls

# If permission issues, run with sudo (macOS unlikely)
sudo docker volume prune -f
```

### Cleanup job gets stuck
Check for pods in terminating state:
```bash
kubectl get pods -n floe | grep Terminating

# Force delete stuck pods (last resort)
kubectl delete pod <pod-name> -n floe --grace-period=0 --force
```

## Monitoring and Alerts

### Check resource usage
```bash
# Pod count in namespace
kubectl get pods -n floe --no-headers | wc -l

# Job accumulation
kubectl get jobs -n floe --no-headers | wc -l

# Docker volume usage
docker system df

# Total Docker space usage
docker system df -v
```

### Set up alerts (optional)
```bash
# Add to your shell profile for daily reminders
# .bashrc/.zshrc
alias k8s-health="kubectl get pods -n floe | grep -E '(Completed|Failed)' | wc -l | xargs echo 'Cleanup needed for pods:'"
```

## Best Practices

1. **Preview before cleanup** - Always use `--dry-run` first
2. **Regular schedule** - Daily cleanup prevents accumulation
3. **Monitor space** - Run `docker system df` regularly
4. **Keep recent jobs** - 1-hour retention allows debugging
5. **Automate safely** - CronJob only cleans pods/jobs, not volumes
6. **Document changes** - Note any custom resources before cleanup
7. **Backup critical data** - Export important configs before nuclear reset

## Integration with Development Workflow

### Before starting work
```bash
make dev-clean-dry-run  # See what needs cleaning
make dev-clean          # Clean slate for development
make demo-status        # Verify everything is running
```

### After development session
```bash
make dev-clean          # Clean up artifacts
make demo-status        # Check final state
```

### Before vacation/breaks
```bash
make dev-clean-monthly  # Deep clean unused resources
# or
make dev-reset          # Complete shutdown
```

### When returning to work
```bash
make deploy-local-full  # Redeploy if reset
make demo-validate      # Verify deployment health
```

## Advanced Cleanup Scenarios

### Clean specific resource types
```bash
# Only completed pods
kubectl delete pods -n floe --field-selector=status.phase==Succeeded

# Only failed pods
kubectl delete pods -n floe --field-selector=status.phase==Failed

# Jobs older than specific time
kubectl get jobs -n floe -o go-template --template '{{range .items}}{{.metadata.name}} {{.status.completionTime}}{{"\n"}}{{end}}' | awk '$2 < "2024-12-27T10:00:00Z" {print $1}' | xargs -r kubectl delete job -n floe

# Volumes by age (Docker 23.0+)
docker volume prune --filter "until=24h"
```

### Selective image cleanup
```bash
# Only dangling images
docker image prune -f

# Images older than 7 days
docker image prune --filter "until=168h" -f

# Specific image patterns
docker images | grep floe-demo | awk '{print $3}' | xargs docker rmi
```

### Emergency procedures
```bash
# Force delete namespace (if stuck)
kubectl delete namespace floe --grace-period=0 --force

# Reset Docker Desktop (last resort)
# Docker Desktop -> Troubleshoot -> Reset to factory defaults
```

This maintenance strategy ensures your local development environment stays clean, responsive, and doesn't consume excessive disk space while preserving important data and debugging capabilities.