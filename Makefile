# floe-runtime Makefile
# Provides consistent commands that mirror CI exactly

.PHONY: check lint typecheck security test test-unit test-contract test-integration test-helm helm-lint format install hooks docker-up docker-down docker-logs deploy-local-infra deploy-local-dagster deploy-local-cube deploy-local-full undeploy-local port-forward-all port-forward-stop show-urls demo-status demo-cleanup demo-logs demo-image-build demo-image-push demo-clean demo-validate demo-materialize demo-e2e demo-full-e2e demo-quickstart help

# Default target
help:
	@echo "floe-runtime development commands:"
	@echo ""
	@echo "Code Quality:"
	@echo "  make check           - Run all CI checks (lint, type, security, helm, test)"
	@echo "  make lint            - Run linting (ruff check + format)"
	@echo "  make typecheck       - Run mypy strict type checking"
	@echo "  make security        - Run security scans (bandit)"
	@echo "  make helm-lint       - Lint Helm charts"
	@echo "  make format          - Auto-format code"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests in Docker (unit + contract + integration)"
	@echo "  make test-unit       - Run unit tests only (no Docker required)"
	@echo "  make test-contract   - Run contract tests only (no Docker required)"
	@echo "  make test-integration - Run integration tests only in Docker"
	@echo "  make test-helm       - Run Helm chart validation tests"
	@echo ""
	@echo "Docker Services:"
	@echo "  make docker-up       - Start test infrastructure"
	@echo "  make docker-down     - Stop test infrastructure"
	@echo "  make docker-logs     - View service logs"
	@echo ""
	@echo "Kubernetes Deployment (Docker Desktop - Two-Tier Architecture):"
	@echo "  make deploy-local-infra   - Deploy infra with platform.yaml ConfigMap"
	@echo "  make deploy-local-dagster - Deploy Dagster (mounts platform ConfigMap)"
	@echo "  make deploy-local-cube    - Deploy Cube semantic layer"
	@echo "  make deploy-local-full    - Deploy complete stack (infra + dagster + cube)"
	@echo "  make undeploy-local       - Remove all local Kubernetes deployments"
	@echo ""
	@echo "  Two-Tier: Platform config drives K8s deployment via:"
	@echo "    PLATFORM_FILE=platform/local/platform.yaml (configurable)"
	@echo ""
	@echo "Demo Operations:"
	@echo "  make demo-quickstart      - 🚀 One-command: clean, build, deploy, validate"
	@echo "  make demo-full-e2e        - 🔬 Deploy + materialize + E2E validation (full pipeline)"
	@echo "  make demo-materialize     - Trigger Dagster jobs (bronze + full pipeline)"
	@echo "  make demo-e2e             - E2E validation: data + observability + cube"
	@echo "  make demo-clean           - Clean deployment (keep images)"
	@echo "  make demo-validate        - Validate deployment health (pods + endpoints)"
	@echo "  make show-urls            - Show service URLs (NodePort - resilient access)"
	@echo "  make port-forward-all     - Start all port-forwards (admin UIs)"
	@echo "  make port-forward-stop    - Stop all port-forwards"
	@echo "  make demo-status          - Show status of all deployed services"
	@echo "  make demo-logs            - Show logs from floe-demo user deployment"
	@echo "  make demo-logs-all        - Show logs from all Dagster components"
	@echo "  make demo-image-build     - Build demo Docker image"
	@echo "  make demo-image-push      - Build and push demo image to ghcr.io"
	@echo ""
	@echo "Cleanup & Maintenance:"
	@echo "  make dev-clean            - Daily cleanup (completed pods, Docker volumes)"
	@echo "  make dev-clean-weekly     - Weekly maintenance (+ old containers/ConfigMaps)"
	@echo "  make dev-clean-monthly    - Monthly deep clean (+ unused images)"
	@echo "  make dev-clean-dry-run    - Preview daily cleanup actions"
	@echo "  make dev-reset            - Nuclear reset (destroys entire environment)"
	@echo "  make demo-cleanup         - Alias for dev-clean (backward compatibility)"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install dependencies"
	@echo "  make hooks           - Install git hooks"
	@echo ""

# Full CI check - mirrors .github/workflows/ci.yml exactly
check: lint typecheck security helm-lint test
	@echo "✅ All checks passed!"

# Lint checks - mirrors CI lint job exactly
# Note: ruff check includes I001 import sorting via [tool.ruff.lint] select = ["I"]
# This replaces the need for a separate isort check
lint:
	@echo "📋 Running lint checks..."
	uv run ruff check .
	uv run ruff format --check .

# Type checking - mirrors CI typecheck job
typecheck:
	@echo "🔬 Running type check..."
	uv run mypy --strict packages/*/src/

# Security scanning - mirrors CI security job
security:
	@echo "🔒 Running security scan..."
	uv run bandit -r packages/*/src/ -ll -q

# Tests - ALL tests run in Docker for consistent hostname resolution
test:
	@echo "🧪 Running all tests in Docker..."
	@./testing/docker/scripts/run-all-tests.sh

# Auto-format code (ruff handles both formatting and import sorting)
format:
	@echo "🎨 Formatting code..."
	uv run ruff check --fix .
	uv run ruff format .

# Install dependencies
install:
	uv sync --all-packages

# Install git hooks
hooks:
	git config core.hooksPath .githooks
	@echo "✅ Git hooks installed from .githooks/"

# ==============================================================================
# Docker Test Infrastructure
# ==============================================================================

# Run unit tests (no Docker required)
test-unit:
	@echo "🧪 Running unit tests..."
	uv run pytest packages/*/tests/unit/ -v --tb=short

# Run contract tests (no Docker required)
test-contract:
	@echo "🧪 Running contract tests..."
	uv run pytest tests/contract/ packages/*/tests/contract/ -v --tb=short

# Run integration tests inside Docker network (zero-config)
test-integration:
	@echo "🐳 Running integration tests in Docker..."
	@./testing/docker/scripts/run-integration-tests.sh

# Start Docker services (storage profile)
docker-up:
	@echo "🚀 Starting Docker services..."
	cd testing/docker && docker compose --profile storage up -d --wait
	@echo "✅ Services ready!"
	@echo "   Polaris:    http://localhost:8181"
	@echo "   LocalStack: http://localhost:4566"

# Stop Docker services
docker-down:
	@echo "🛑 Stopping Docker services..."
	cd testing/docker && docker compose --profile storage --profile test down
	@echo "✅ Services stopped"

# View Docker service logs
docker-logs:
	cd testing/docker && docker compose --profile storage logs -f

# ==============================================================================
# Helm Chart Validation
# ==============================================================================

# Lint Helm charts
helm-lint:
	@echo "⎈ Linting Helm charts..."
	@helm lint $(DEMO_CHARTS_DIR)/floe-infrastructure/
	@helm lint $(DEMO_CHARTS_DIR)/floe-dagster/
	@helm lint $(DEMO_CHARTS_DIR)/floe-cube/

# Run Helm chart validation tests
test-helm:
	@echo "⎈ Running Helm chart tests..."
	uv run pytest testing/tests/test_helm_charts.py testing/tests/test_dockerfiles.py -v --tb=short

# ==============================================================================
# Kubernetes Local Deployment (Docker Desktop)
# ==============================================================================
# Deploy the complete floe-runtime stack to Docker Desktop Kubernetes.
# Uses emptyDir storage (no PVCs) for compatibility with Docker Desktop.
#
# Architecture:
#   Infrastructure (floe-infra): PostgreSQL, MinIO, Polaris, Jaeger, Marquez
#   Orchestration (floe-dagster): Dagster webserver, daemon, workers with DuckDB
#   Semantic Layer (floe-cube): Cube API, refresh worker, Cube Store
#
# Access services via port-forward:
#   kubectl port-forward svc/floe-dagster-webserver 3000:80 -n floe
#   kubectl port-forward svc/floe-cube 4000:4000 -n floe
#   kubectl port-forward svc/floe-infra-jaeger 16686:16686 -n floe
# ==============================================================================

FLOE_NAMESPACE := floe
# Three-Tier Architecture: Platform config file for K8s deployment
# Uses K8s service names (floe-infra-minio, floe-infra-polaris, etc.)
PLATFORM_FILE := demo/platform-config/platform/local/platform.yaml
DEMO_CHARTS_DIR := demo/platform-config/charts

# Deploy infrastructure layer (MinIO, Polaris, PostgreSQL, Jaeger, Marquez)
# Three-Tier Architecture: Injects platform.yaml as ConfigMap for apps to consume
deploy-local-infra:
	@echo "⎈ Deploying floe-infrastructure to Kubernetes (Three-Tier Architecture)..."
	@echo "   Platform config: $(PLATFORM_FILE)"
	@helm dependency update $(DEMO_CHARTS_DIR)/floe-infrastructure/
	helm upgrade --install floe-infra $(DEMO_CHARTS_DIR)/floe-infrastructure/ \
		--namespace $(FLOE_NAMESPACE) --create-namespace \
		--values $(DEMO_CHARTS_DIR)/floe-infrastructure/values-local.yaml \
		--set platformConfig.enabled=true \
		--set-file platformConfig.content=$(PLATFORM_FILE) \
		--wait --timeout 5m
	@echo "✅ Infrastructure deployed!"
	@echo ""
	@echo "Platform ConfigMap created: floe-infra-platform-config"
	@echo ""
	@echo "Waiting for Polaris initialization..."
	@kubectl wait --for=condition=complete job/floe-infra-polaris-init \
		-n $(FLOE_NAMESPACE) --timeout=120s || true
	@echo "✅ Polaris initialized!"

# Deploy Dagster orchestration layer
# Three-Tier Architecture: Mounts platform ConfigMap from infrastructure chart
deploy-local-dagster:
	@echo "⎈ Deploying floe-dagster to Kubernetes (Three-Tier Architecture)..."
	helm upgrade --install floe-dagster $(DEMO_CHARTS_DIR)/floe-dagster/ \
		--namespace $(FLOE_NAMESPACE) \
		--values $(DEMO_CHARTS_DIR)/floe-dagster/values-local.yaml \
		--skip-schema-validation \
		--wait --timeout 5m
	@echo "✅ Dagster deployed!"
	@echo ""
	@echo "Platform config mounted at: /etc/floe/platform.yaml"
	@echo ""
	@echo "Access Dagster UI:"
	@echo "  kubectl port-forward svc/floe-dagster-webserver 3000:80 -n $(FLOE_NAMESPACE)"
	@echo "  Open: http://localhost:3000"

# Deploy Cube semantic layer
deploy-local-cube:
	@echo "⎈ Deploying floe-cube to Kubernetes..."
	helm upgrade --install floe-cube $(DEMO_CHARTS_DIR)/floe-cube/ \
		--namespace $(FLOE_NAMESPACE) \
		--values $(DEMO_CHARTS_DIR)/floe-cube/values-local.yaml \
		--wait --timeout 5m
	@echo "✅ Cube deployed!"
	@echo ""
	@echo "Access Cube APIs:"
	@echo "  kubectl port-forward svc/floe-cube 4000:4000 -n $(FLOE_NAMESPACE)"
	@echo "  REST API: http://localhost:4000/cubejs-api/v1/load"
	@echo "  GraphQL:  http://localhost:4000/cubejs-api/graphql"
	@echo "  SQL API:  kubectl port-forward svc/floe-cube 15432:15432 -n $(FLOE_NAMESPACE)"

# Deploy complete stack (infrastructure + dagster + cube)
deploy-local-full: deploy-local-infra
	@echo ""
	@echo "Infrastructure ready. Deploying application layers..."
	@$(MAKE) deploy-local-dagster
	@$(MAKE) deploy-local-cube
	@echo ""
	@echo "=============================================="
	@echo "✅ Full stack deployed to namespace: $(FLOE_NAMESPACE)"
	@echo "=============================================="
	@echo ""
	@echo "Services accessible via NodePort:"
	@echo "  Dagster UI:      http://localhost:30000"
	@echo "  Cube REST API:   http://localhost:30400"
	@echo "  Cube SQL API:    psql -h localhost -p 30432 -U cube -d cube"
	@echo "  Marquez UI:      http://localhost:30301"
	@echo "  Jaeger UI:       http://localhost:30686"
	@echo "  LocalStack S3:   http://localhost:30566"
	@echo "  Polaris API:     http://localhost:30181"
	@echo ""
	@echo "Quick test: curl http://localhost:30400/cubejs-api/v1/meta"
	@echo ""
	@echo "Run 'make demo-status' to check pod status"
	@echo "Run 'make demo-cleanup' to remove completed run pods"

# Remove all local Kubernetes deployments
undeploy-local:
	@echo "⎈ Removing floe deployments from Kubernetes..."
	-helm uninstall floe-cube -n $(FLOE_NAMESPACE) 2>/dev/null || true
	-helm uninstall floe-dagster -n $(FLOE_NAMESPACE) 2>/dev/null || true
	-helm uninstall floe-infra -n $(FLOE_NAMESPACE) 2>/dev/null || true
	@echo ""
	@echo "Delete namespace? (removes all resources)"
	@echo "  kubectl delete namespace $(FLOE_NAMESPACE)"
	@echo ""
	@echo "✅ Deployments removed!"

# Show all service URLs (NodePort access - resilient to pod restarts)
show-urls:
	@echo "=============================================="
	@echo "⎈ Floe Service URLs (NodePort Access)"
	@echo "=============================================="
	@echo ""
	@echo "These URLs are resilient - they survive pod restarts!"
	@echo "No manual port-forwarding required."
	@echo ""
	@echo "Application UIs:"
	@echo "  Dagster UI:      http://localhost:30000"
	@echo ""
	@echo "Infrastructure Services:"
	@echo "  Polaris API:     http://localhost:30181  (Iceberg catalog)"
	@echo "  MinIO Console:   http://localhost:30901  (S3 storage, user: minioadmin)"
	@echo ""
	@echo "Observability:"
	@echo "  Jaeger UI:       http://localhost:30686  (distributed tracing)"
	@echo "  Marquez Web:     http://localhost:30301  (data lineage UI)"
	@echo "  Marquez API:     http://localhost:30500  (lineage API)"
	@echo ""
	@echo "Verify services are running:"
	@echo "  kubectl get svc -n $(FLOE_NAMESPACE) | grep NodePort"
	@echo ""

# Start all port-forwards in background
# Run this after deploy-local-full to access all services
port-forward-all:
	@echo "⎈ Starting port-forwards for all services..."
	@echo ""
	@echo "Killing any existing port-forwards..."
	@-pkill -f 'kubectl port-forward' 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "Starting port-forwards in background (logs in /tmp/port-forward-*.log)..."
	@kubectl port-forward svc/floe-dagster-dagster-webserver 3000:80 -n $(FLOE_NAMESPACE) > /tmp/port-forward-dagster.log 2>&1 &
	@kubectl port-forward svc/floe-infra-jaeger-query 16686:16686 -n $(FLOE_NAMESPACE) > /tmp/port-forward-jaeger.log 2>&1 &
	@kubectl port-forward svc/floe-infra-marquez 5000:5000 -n $(FLOE_NAMESPACE) > /tmp/port-forward-marquez.log 2>&1 &
	@kubectl port-forward svc/floe-infra-marquez-web 3001:3001 -n $(FLOE_NAMESPACE) > /tmp/port-forward-marquez-web.log 2>&1 &
	@kubectl port-forward svc/floe-infra-minio-console 9001:9001 -n $(FLOE_NAMESPACE) > /tmp/port-forward-minio.log 2>&1 &
	@kubectl port-forward svc/floe-infra-polaris 8181:8181 -n $(FLOE_NAMESPACE) > /tmp/port-forward-polaris.log 2>&1 &
	@sleep 2
	@echo ""
	@echo "✅ Port-forwards started!"
	@echo ""
	@echo "Admin UIs available at:"
	@echo "  Dagster UI:      http://localhost:3000"
	@echo "  Jaeger UI:       http://localhost:16686  (tracing)"
	@echo "  Marquez Web UI:  http://localhost:3001   (lineage)"
	@echo "  Marquez API:     http://localhost:5000   (lineage API)"
	@echo "  MinIO Console:   http://localhost:9001   (storage - user: minioadmin)"
	@echo "  Polaris API:     http://localhost:8181   (catalog - API only, no UI)"
	@echo ""
	@echo "To stop all port-forwards:"
	@echo "  make port-forward-stop"

# Stop all port-forwards
port-forward-stop:
	@echo "⎈ Stopping all port-forwards..."
	@-pkill -f 'kubectl port-forward' 2>/dev/null || true
	@echo "✅ Port-forwards stopped!"

# Show status of all deployed services
demo-status:
	@echo "⎈ Floe Demo Status"
	@echo "=================="
	@echo ""
	@echo "Pods:"
	@kubectl get pods -n $(FLOE_NAMESPACE) 2>/dev/null || echo "  Namespace $(FLOE_NAMESPACE) not found"
	@echo ""
	@echo "Services:"
	@kubectl get svc -n $(FLOE_NAMESPACE) 2>/dev/null || true
	@echo ""
	@echo "Jobs:"
	@kubectl get jobs -n $(FLOE_NAMESPACE) 2>/dev/null || true

# Clean up completed Dagster run pods (can accumulate over time) - DEPRECATED
# Use 'make dev-clean' instead

# ============================================================================
# Development Cleanup and Maintenance
# ============================================================================
# Comprehensive cleanup strategies for local Kubernetes development.
# Uses the claude-cleanup.sh script for safe, graduated cleanup options.

# Daily cleanup - safe for active development (preserves running services)
dev-clean:
	@./scripts/claude-cleanup.sh daily

# Weekly maintenance - includes old containers and ConfigMaps
dev-clean-weekly:
	@./scripts/claude-cleanup.sh weekly

# Monthly deep clean - includes unused Docker images
dev-clean-monthly:
	@./scripts/claude-cleanup.sh monthly

# Preview cleanup actions without making changes
dev-clean-dry-run:
	@./scripts/claude-cleanup.sh daily --dry-run

# Show what weekly cleanup would do
dev-clean-weekly-dry-run:
	@./scripts/claude-cleanup.sh weekly --dry-run

# Show what monthly cleanup would do
dev-clean-monthly-dry-run:
	@./scripts/claude-cleanup.sh monthly --dry-run

# Legacy cleanup for backward compatibility (maps to daily)
demo-cleanup:
	@./scripts/claude-cleanup.sh daily

# Nuclear option: complete environment reset (requires confirmation)
dev-reset:
	@./scripts/claude-cleanup.sh nuclear

# Show logs from demo user deployment (tail)
demo-logs:
	@echo "⎈ Floe Demo Logs (floe-demo user deployment)"
	@echo "============================================="
	@kubectl logs -l deployment=floe-demo -n $(FLOE_NAMESPACE) --tail=50 2>/dev/null || echo "No floe-demo pods found"

# Show logs from all dagster components
demo-logs-all:
	@echo "⎈ All Dagster Logs"
	@echo "=================="
	@echo ""
	@echo "--- Webserver ---"
	@kubectl logs -l component=dagster-webserver -n $(FLOE_NAMESPACE) --tail=20 2>/dev/null || true
	@echo ""
	@echo "--- Daemon ---"
	@kubectl logs -l component=dagster-daemon -n $(FLOE_NAMESPACE) --tail=20 2>/dev/null || true
	@echo ""
	@echo "--- User Deployment (floe-demo) ---"
	@kubectl logs -l deployment=floe-demo -n $(FLOE_NAMESPACE) --tail=20 2>/dev/null || true

# Build demo Docker image
demo-image-build:
	@echo "🐳 Building demo Docker image..."
	docker build -t ghcr.io/obsidian-owl/floe-demo:latest -f docker/Dockerfile.demo .
	@echo "✅ Demo image built: ghcr.io/obsidian-owl/floe-demo:latest"

# Build and push demo image to GitHub Container Registry
demo-image-push: demo-image-build
	@echo "🚀 Pushing demo image to ghcr.io..."
	docker push ghcr.io/obsidian-owl/floe-demo:latest
	@echo "✅ Demo image pushed: ghcr.io/obsidian-owl/floe-demo:latest"
	@echo ""
	@echo "To deploy updated image:"
	@echo "  kubectl rollout restart deployment/floe-dagster-dagster-user-deployments-floe-demo -n $(FLOE_NAMESPACE)"

# Clean demo environment (complete reset)
demo-clean:
	@./scripts/clean-demo.sh

# Clean demo environment including Docker images
demo-clean-all:
	@./scripts/clean-demo.sh --all

# Validate demo deployment health
demo-validate:
	@./scripts/validate-demo.sh

# Materialize demo data (automated Dagster job execution)
# Use DEBUG=1 to enable GraphQL response debugging
demo-materialize:
	@DEBUG=$(DEBUG) ./scripts/materialize-demo.sh --all

# E2E validation: data + observability + semantic layer
demo-e2e:
	@./scripts/validate-e2e.sh

# Full E2E pipeline: deploy → materialize → validate → evidence
# Fully automated demo with comprehensive evidence collection
demo-full-e2e: deploy-local-full
	@echo ""
	@echo "=============================================="
	@echo "⏳ Waiting for all pods to stabilize..."
	@echo "=============================================="
	@sleep 30
	@kubectl wait --for=condition=ready pod --field-selector=status.phase!=Succeeded -n $(FLOE_NAMESPACE) --timeout=300s 2>&1 | grep -v "condition met" | grep -v "no matching resources" || true
	@echo ""
	@echo "=============================================="
	@echo "🚀 Materializing Data Pipeline"
	@echo "=============================================="
	@DEBUG=1 ./scripts/materialize-demo.sh --all
	@echo ""
	@echo "=============================================="
	@echo "🔍 Running E2E Validation"
	@echo "=============================================="
	@$(MAKE) demo-e2e
	@echo ""
	@echo "=============================================="
	@echo "📊 Evidence Report"
	@echo "=============================================="
	@cat ./evidence/latest/SUMMARY.md || echo "⚠️  No evidence generated"
	@echo ""

# Quickstart: clean + build + deploy + validate (interactive)
demo-quickstart:
	@./scripts/quickstart.sh

# Automated quickstart: clean + build + deploy + materialize + validate (no prompts)
# For CI/CD pipelines - runs E2E validation automatically
demo-quickstart-auto:
	@./scripts/quickstart.sh --auto
