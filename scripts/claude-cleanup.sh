#!/bin/bash
# Claude Cleanup Script for Local Kubernetes Development
#
# Comprehensive cleanup and maintenance for floe-runtime local development.
# Handles Kubernetes resources, Docker volumes, and build artifacts.
#
# Usage: ./scripts/claude-cleanup.sh [OPTION]
#   daily        - Daily cleanup (safe, preserves running services)
#   weekly       - Weekly maintenance (includes old containers)
#   monthly      - Monthly deep clean (includes unused images)
#   nuclear      - Complete environment reset (destructive)
#   --dry-run    - Show what would be cleaned without making changes
#   --help       - Show this help

set -e

FLOE_NAMESPACE="floe"
DRY_RUN=false
CLEANUP_TYPE="daily"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        daily|weekly|monthly|nuclear)
            CLEANUP_TYPE="$1"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Claude Cleanup Script for Local Kubernetes Development"
            echo ""
            echo "Usage: $0 [OPTION]"
            echo "  daily        - Safe daily cleanup (default)"
            echo "  weekly       - Weekly maintenance with containers"
            echo "  monthly      - Monthly deep clean with images"
            echo "  nuclear      - Complete environment reset"
            echo "  --dry-run    - Show actions without executing"
            echo "  --help       - Show this help"
            echo ""
            echo "Daily cleanup includes:"
            echo "  • Completed/failed Dagster job pods"
            echo "  • Unused Docker volumes"
            echo "  • Build cache cleanup"
            echo ""
            echo "Weekly cleanup adds:"
            echo "  • Stopped containers"
            echo "  • Old ConfigMaps/Secrets (7+ days)"
            echo ""
            echo "Monthly cleanup adds:"
            echo "  • Unused Docker images"
            echo "  • System-wide Docker cleanup"
            echo ""
            echo "Nuclear option:"
            echo "  • Deletes entire floe namespace"
            echo "  • Removes all Docker resources"
            echo "  • Requires confirmation"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run $0 --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_action() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN] $1${NC}"
    else
        echo -e "${BLUE}🔧 $1${NC}"
    fi
}

execute() {
    if [ "$DRY_RUN" = true ]; then
        echo "  Command: $*"
    else
        eval "$@"
    fi
}

check_namespace() {
    if ! kubectl get namespace "$FLOE_NAMESPACE" >/dev/null 2>&1; then
        log_warning "Namespace '$FLOE_NAMESPACE' not found. Nothing to clean in Kubernetes."
        return 1
    fi
    return 0
}

# Cleanup functions
cleanup_completed_pods() {
    log_action "Cleaning completed and failed pods..."

    if ! check_namespace; then
        return
    fi

    # Count pods before cleanup
    local completed_count
    local failed_count
    completed_count=$(kubectl get pods -n "$FLOE_NAMESPACE" --field-selector=status.phase==Succeeded --no-headers 2>/dev/null | wc -l | tr -d ' ')
    failed_count=$(kubectl get pods -n "$FLOE_NAMESPACE" --field-selector=status.phase==Failed --no-headers 2>/dev/null | wc -l | tr -d ' ')

    if [ "$completed_count" -gt 0 ]; then
        log_info "Found $completed_count completed pods"
        execute "kubectl delete pods -n $FLOE_NAMESPACE --field-selector=status.phase==Succeeded 2>/dev/null || true"
    else
        log_info "No completed pods to clean"
    fi

    if [ "$failed_count" -gt 0 ]; then
        log_info "Found $failed_count failed pods"
        execute "kubectl delete pods -n $FLOE_NAMESPACE --field-selector=status.phase==Failed 2>/dev/null || true"
    else
        log_info "No failed pods to clean"
    fi
}

cleanup_old_jobs() {
    log_action "Cleaning old Kubernetes jobs..."

    if ! check_namespace; then
        return
    fi

    # Clean completed jobs older than 1 hour (3600 seconds)
    # This keeps recent jobs for debugging but prevents accumulation
    local old_jobs
    # macOS date command compatibility - calculate timestamp 1 hour ago
    local cutoff_time
    if date -v-1H >/dev/null 2>&1; then
        # macOS date
        cutoff_time=$(date -u -v-1H '+%Y-%m-%dT%H:%M:%SZ')
    else
        # GNU date (Linux)
        cutoff_time=$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ')
    fi
    old_jobs=$(kubectl get jobs -n "$FLOE_NAMESPACE" -o jsonpath='{range .items[?(@.status.completionTime)]}{.metadata.name}{" "}{.status.completionTime}{"\n"}{end}' 2>/dev/null | \
        awk -v cutoff="$cutoff_time" '$2 < cutoff {print $1}' || true)

    if [ -n "$old_jobs" ]; then
        local job_count
        job_count=$(echo "$old_jobs" | wc -l | tr -d ' ')
        log_info "Found $job_count old completed jobs"
        echo "$old_jobs" | while read -r job; do
            [ -n "$job" ] && execute "kubectl delete job $job -n $FLOE_NAMESPACE 2>/dev/null || true"
        done
    else
        log_info "No old jobs to clean"
    fi
}

cleanup_docker_volumes() {
    log_action "Cleaning Docker volumes..."

    # Check for dangling volumes first
    local volume_count
    volume_count=$(docker volume ls -f dangling=true -q 2>/dev/null | wc -l | tr -d ' ')

    if [ "$volume_count" -gt 0 ]; then
        log_info "Found $volume_count dangling volumes"
        execute "docker volume prune -f 2>/dev/null || true"
    else
        log_info "No dangling volumes to clean"
    fi

    # Show space reclaimed
    if [ "$DRY_RUN" = false ]; then
        local reclaimed
        reclaimed=$(docker volume prune -f 2>&1 | grep "Total reclaimed" || echo "No space reclaimed")
        [ "$reclaimed" != "No space reclaimed" ] && log_success "$reclaimed"
    fi
}

cleanup_build_artifacts() {
    log_action "Cleaning build artifacts..."

    local cleaned_dirs=0

    # Python cache directories
    while IFS= read -r -d '' dir; do
        [ -d "$dir" ] && execute "rm -rf \"$dir\"" && ((cleaned_dirs++))
    done < <(find . -type d -name "__pycache__" -print0 2>/dev/null)

    while IFS= read -r -d '' dir; do
        [ -d "$dir" ] && execute "rm -rf \"$dir\"" && ((cleaned_dirs++))
    done < <(find . -type d -name ".pytest_cache" -print0 2>/dev/null)

    while IFS= read -r -d '' dir; do
        [ -d "$dir" ] && execute "rm -rf \"$dir\"" && ((cleaned_dirs++))
    done < <(find . -type d -name ".ruff_cache" -print0 2>/dev/null)

    while IFS= read -r -d '' dir; do
        [ -d "$dir" ] && execute "rm -rf \"$dir\"" && ((cleaned_dirs++))
    done < <(find . -type d -name ".mypy_cache" -print0 2>/dev/null)

    # Temporary Dagster directories
    execute "rm -rf /tmp/dagster-* 2>/dev/null || true"

    if [ "$cleaned_dirs" -gt 0 ]; then
        log_success "Cleaned $cleaned_dirs cache directories"
    else
        log_info "No build artifacts to clean"
    fi
}

cleanup_old_configmaps_secrets() {
    log_action "Cleaning old ConfigMaps and Secrets..."

    if ! check_namespace; then
        return
    fi

    # Clean ConfigMaps older than 7 days (excluding platform config)
    local old_cms
    local cutoff_time
    if date -v-7d >/dev/null 2>&1; then
        # macOS date
        cutoff_time=$(date -u -v-7d '+%Y-%m-%dT%H:%M:%SZ')
    else
        # GNU date (Linux)
        cutoff_time=$(date -u -d '7 days ago' '+%Y-%m-%dT%H:%M:%SZ')
    fi
    old_cms=$(kubectl get configmaps -n "$FLOE_NAMESPACE" -o jsonpath='{range .items[?(@.metadata.creationTimestamp)]}{.metadata.name}{" "}{.metadata.creationTimestamp}{"\n"}{end}' 2>/dev/null | \
        grep -v "floe-infra-platform-config" | \
        awk -v cutoff="$cutoff_time" '$2 < cutoff {print $1}' || true)

    if [ -n "$old_cms" ]; then
        local cm_count
        cm_count=$(echo "$old_cms" | wc -l | tr -d ' ')
        log_info "Found $cm_count old ConfigMaps"
        echo "$old_cms" | while read -r cm; do
            [ -n "$cm" ] && execute "kubectl delete configmap $cm -n $FLOE_NAMESPACE 2>/dev/null || true"
        done
    else
        log_info "No old ConfigMaps to clean"
    fi
}

cleanup_stopped_containers() {
    log_action "Cleaning stopped containers..."

    local stopped_count
    stopped_count=$(docker ps -a -f status=exited -q 2>/dev/null | wc -l | tr -d ' ')

    if [ "$stopped_count" -gt 0 ]; then
        log_info "Found $stopped_count stopped containers"
        execute "docker container prune -f 2>/dev/null || true"
    else
        log_info "No stopped containers to clean"
    fi
}

cleanup_unused_images() {
    log_action "Cleaning unused Docker images..."

    # Remove dangling images first
    local dangling_count
    dangling_count=$(docker images -f dangling=true -q 2>/dev/null | wc -l | tr -d ' ')

    if [ "$dangling_count" -gt 0 ]; then
        log_info "Found $dangling_count dangling images"
        execute "docker image prune -f 2>/dev/null || true"
    else
        log_info "No dangling images to clean"
    fi

    # For monthly cleanup, also remove unused images
    if [ "$CLEANUP_TYPE" = "monthly" ]; then
        log_info "Performing monthly image cleanup..."
        execute "docker image prune -a -f 2>/dev/null || true"
    fi
}

nuclear_cleanup() {
    log_error "⚠️  NUCLEAR CLEANUP - This will destroy your entire environment!"
    echo ""
    echo "This will:"
    echo "  - Delete the entire '$FLOE_NAMESPACE' namespace"
    echo "  - Remove ALL Docker volumes"
    echo "  - Remove ALL stopped containers"
    echo "  - Remove ALL unused images"
    echo "  - Clean ALL build artifacts"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY-RUN: Would perform nuclear cleanup"
        return
    fi

    read -p "Type 'DESTROY' to confirm nuclear cleanup: " confirm
    if [ "$confirm" != "DESTROY" ]; then
        log_info "Nuclear cleanup cancelled"
        return
    fi

    log_action "Performing nuclear cleanup..."

    # Stop port-forwards
    pkill -f 'kubectl port-forward' 2>/dev/null || true

    # Uninstall Helm releases
    helm uninstall floe-cube -n "$FLOE_NAMESPACE" 2>/dev/null || true
    helm uninstall floe-dagster -n "$FLOE_NAMESPACE" 2>/dev/null || true
    helm uninstall floe-infra -n "$FLOE_NAMESPACE" 2>/dev/null || true

    # Delete namespace
    kubectl delete namespace "$FLOE_NAMESPACE" --timeout=120s 2>/dev/null || true

    # Docker cleanup
    docker volume prune -a -f 2>/dev/null || true
    docker container prune -f 2>/dev/null || true
    docker image prune -a -f 2>/dev/null || true

    cleanup_build_artifacts

    log_success "Nuclear cleanup complete. Run 'make deploy-local-full' to redeploy."
}

# Main cleanup logic
main() {
    echo "=============================================="
    echo "🧹 Claude Cleanup Script - $CLEANUP_TYPE cleanup"
    if [ "$DRY_RUN" = true ]; then
        echo "   (DRY RUN - no changes will be made)"
    fi
    echo "=============================================="
    echo ""

    case "$CLEANUP_TYPE" in
        daily)
            cleanup_completed_pods
            cleanup_old_jobs
            cleanup_docker_volumes
            cleanup_build_artifacts
            ;;
        weekly)
            cleanup_completed_pods
            cleanup_old_jobs
            cleanup_docker_volumes
            cleanup_build_artifacts
            cleanup_old_configmaps_secrets
            cleanup_stopped_containers
            ;;
        monthly)
            cleanup_completed_pods
            cleanup_old_jobs
            cleanup_docker_volumes
            cleanup_build_artifacts
            cleanup_old_configmaps_secrets
            cleanup_stopped_containers
            cleanup_unused_images
            ;;
        nuclear)
            nuclear_cleanup
            return
            ;;
    esac

    echo ""
    echo "=============================================="
    if [ "$DRY_RUN" = true ]; then
        log_info "Dry run complete. Run without --dry-run to execute cleanup."
    else
        log_success "$CLEANUP_TYPE cleanup complete!"
    fi
    echo "=============================================="

    # Show current resource usage
    if [ "$DRY_RUN" = false ] && check_namespace; then
        echo ""
        log_info "Current namespace status:"
        kubectl get pods -n "$FLOE_NAMESPACE" --no-headers 2>/dev/null | wc -l | xargs printf "  Pods: %s\n"
        kubectl get jobs -n "$FLOE_NAMESPACE" --no-headers 2>/dev/null | wc -l | xargs printf "  Jobs: %s\n"
        docker volume ls | tail -n +2 | wc -l | xargs printf "  Docker volumes: %s\n"
    fi
}

# Run main function
main "$@"