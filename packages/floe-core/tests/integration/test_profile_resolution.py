"""Integration tests for profile resolution.

T042: [US2] Integration test: same floe.yaml + different platform.yaml
Tests that the same floe.yaml works correctly with different platform.yaml
configurations, demonstrating environment portability.

This validates the Two-Tier Configuration Architecture where:
- Data engineers write ONE floe.yaml with profile references
- Platform engineers configure different platform.yaml per environment
- Same pipeline deploys correctly across dev/staging/prod
"""

from __future__ import annotations

from pathlib import Path

import pytest

from floe_core.compiler.compiler import Compiler
from floe_core.compiler.platform_resolver import PlatformResolver
from floe_core.compiler.profile_resolver import ProfileResolver
from floe_core.schemas.platform_spec import PlatformSpec


class TestMultiEnvironmentProfileResolution:
    """Test same floe.yaml resolves correctly with different platform.yaml files."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear resolver cache before each test."""
        PlatformResolver.clear_cache()

    @pytest.fixture
    def shared_floe_yaml(self) -> str:
        """Same floe.yaml used across all environments.

        This represents a data engineer's pipeline config that should
        work identically in local, dev, and prod environments.
        """
        return """
# Same floe.yaml for all environments (Two-Tier Architecture)
name: data-pipeline
version: "1.0.0"

# Profile references - resolved from platform.yaml at runtime
storage: default
catalog: default
compute: default

transforms:
  - type: dbt
    path: ./dbt

governance:
  classification_source: dbt_meta

observability:
  traces: true
  metrics: true
  lineage: true
"""

    @pytest.fixture
    def local_platform_yaml(self) -> str:
        """Local development platform.yaml with MinIO and local Polaris."""
        return """
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    region: us-east-1
    bucket: local-iceberg-data
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials

catalogs:
  default:
    type: polaris
    uri: "http://polaris:8181/api/catalog"
    warehouse: local-warehouse
    namespace: development
    credentials:
      mode: oauth2
      client_id: local-client
      client_secret:
        secret_ref: polaris-local-secret
      scope: "PRINCIPAL_ROLE:ALL"

compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"
      threads: 4
    credentials:
      mode: static

observability:
  traces: true
  otlp_endpoint: "http://jaeger:4317"
"""

    @pytest.fixture
    def prod_platform_yaml(self) -> str:
        """Production platform.yaml with AWS S3 and managed Polaris."""
        return """
version: "1.0.0"

storage:
  default:
    type: s3
    region: us-east-1
    bucket: prod-data-lake
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/FloeStorageRole"

catalogs:
  default:
    type: polaris
    uri: "https://polaris.prod.internal/api/catalog"
    warehouse: production-warehouse
    namespace: production
    credentials:
      mode: oauth2
      client_id: prod-service-account
      client_secret:
        secret_ref: polaris-prod-secret
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: snowflake
    properties:
      account: acme.us-east-1
      warehouse: PRODUCTION_WH
    credentials:
      mode: static
      secret_ref: snowflake-credentials

observability:
  traces: true
  metrics: true
  otlp_endpoint: "https://otel.prod.internal:4317"
"""

    def test_same_floe_yaml_local_environment(
        self,
        tmp_path: Path,
        shared_floe_yaml: str,
        local_platform_yaml: str,
    ) -> None:
        """Same floe.yaml compiles correctly with local platform.yaml."""
        # Setup: Create project directory with floe.yaml
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        floe_file = project_dir / "floe.yaml"
        floe_file.write_text(shared_floe_yaml)

        # Setup: Create platform/local/platform.yaml
        platform_dir = project_dir / "platform" / "local"
        platform_dir.mkdir(parents=True)
        (platform_dir / "platform.yaml").write_text(local_platform_yaml)

        # Act: Compile with local environment
        compiler = Compiler(platform_env="local")
        artifacts = compiler.compile(floe_file)

        # Assert: Resolved profiles match local configuration
        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.storage.bucket == "local-iceberg-data"
        assert artifacts.resolved_profiles.storage.endpoint == "http://minio:9000"
        assert artifacts.resolved_profiles.catalog.warehouse == "local-warehouse"
        assert artifacts.resolved_profiles.catalog.namespace == "development"
        assert str(artifacts.resolved_profiles.compute.type.value) == "duckdb"
        assert artifacts.resolved_profiles.platform_env == "local"

    def test_same_floe_yaml_prod_environment(
        self,
        tmp_path: Path,
        shared_floe_yaml: str,
        prod_platform_yaml: str,
    ) -> None:
        """Same floe.yaml compiles correctly with production platform.yaml."""
        # Setup: Create project directory with floe.yaml
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        floe_file = project_dir / "floe.yaml"
        floe_file.write_text(shared_floe_yaml)

        # Setup: Create platform/prod/platform.yaml
        platform_dir = project_dir / "platform" / "prod"
        platform_dir.mkdir(parents=True)
        (platform_dir / "platform.yaml").write_text(prod_platform_yaml)

        # Act: Compile with prod environment
        compiler = Compiler(platform_env="prod")
        artifacts = compiler.compile(floe_file)

        # Assert: Resolved profiles match production configuration
        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.storage.bucket == "prod-data-lake"
        assert artifacts.resolved_profiles.storage.endpoint == ""  # AWS S3 (empty string)
        assert artifacts.resolved_profiles.catalog.warehouse == "production-warehouse"
        assert artifacts.resolved_profiles.catalog.namespace == "production"
        assert str(artifacts.resolved_profiles.compute.type.value) == "snowflake"
        assert artifacts.resolved_profiles.platform_env == "prod"

    def test_same_floe_yaml_both_environments_side_by_side(
        self,
        tmp_path: Path,
        shared_floe_yaml: str,
        local_platform_yaml: str,
        prod_platform_yaml: str,
    ) -> None:
        """Same floe.yaml produces different artifacts based on environment.

        This is the key test demonstrating environment portability:
        ONE floe.yaml → DIFFERENT CompiledArtifacts based on FLOE_PLATFORM_ENV
        """
        # Setup: Create project with both platform configurations
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        floe_file = project_dir / "floe.yaml"
        floe_file.write_text(shared_floe_yaml)

        local_dir = project_dir / "platform" / "local"
        local_dir.mkdir(parents=True)
        (local_dir / "platform.yaml").write_text(local_platform_yaml)

        prod_dir = project_dir / "platform" / "prod"
        prod_dir.mkdir(parents=True)
        (prod_dir / "platform.yaml").write_text(prod_platform_yaml)

        # Act: Compile with each environment
        local_compiler = Compiler(platform_env="local")
        local_artifacts = local_compiler.compile(floe_file)

        PlatformResolver.clear_cache()  # Clear cache between environments

        prod_compiler = Compiler(platform_env="prod")
        prod_artifacts = prod_compiler.compile(floe_file)

        # Assert: Same floe.yaml, different resolved profiles
        assert local_artifacts.resolved_profiles is not None
        assert prod_artifacts.resolved_profiles is not None

        # Storage differs
        assert local_artifacts.resolved_profiles.storage.bucket == "local-iceberg-data"
        assert prod_artifacts.resolved_profiles.storage.bucket == "prod-data-lake"

        # Catalog differs
        assert local_artifacts.resolved_profiles.catalog.warehouse == "local-warehouse"
        assert prod_artifacts.resolved_profiles.catalog.warehouse == "production-warehouse"

        # Compute differs
        assert str(local_artifacts.resolved_profiles.compute.type.value) == "duckdb"
        assert str(prod_artifacts.resolved_profiles.compute.type.value) == "snowflake"

        # Environment tag differs
        assert local_artifacts.resolved_profiles.platform_env == "local"
        assert prod_artifacts.resolved_profiles.platform_env == "prod"

        # But core metadata is the same (same floe.yaml)
        assert local_artifacts.metadata.source_hash == prod_artifacts.metadata.source_hash


class TestProfileResolverIntegration:
    """Integration tests for ProfileResolver with real platform.yaml."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear resolver cache before each test."""
        PlatformResolver.clear_cache()

    def test_resolve_all_profiles(self, tmp_path: Path) -> None:
        """ProfileResolver resolves all profile types from platform.yaml."""
        platform_yaml = """
version: "1.0.0"

storage:
  default:
    bucket: test-bucket
  backup:
    bucket: backup-bucket
    region: us-west-2

catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: primary
  analytics:
    uri: http://analytics:8181/api/catalog
    warehouse: analytics-wh

compute:
  default:
    type: duckdb
  production:
    type: snowflake
    properties:
      account: test.us-east-1
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(platform_yaml)

        platform = PlatformSpec.from_yaml(yaml_file)
        resolver = ProfileResolver(platform)

        # Resolve default profiles
        profiles = resolver.resolve_all()
        assert profiles.storage.bucket == "test-bucket"
        assert profiles.catalog.warehouse == "primary"
        assert str(profiles.compute.type.value) == "duckdb"

        # Resolve named profiles
        named_profiles = resolver.resolve_all(
            storage="backup",
            catalog="analytics",
            compute="production",
        )
        assert named_profiles.storage.bucket == "backup-bucket"
        assert named_profiles.catalog.warehouse == "analytics-wh"
        assert str(named_profiles.compute.type.value) == "snowflake"


class TestCredentialModeResolution:
    """Integration tests for credential mode handling in profile resolution."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear resolver cache before each test."""
        PlatformResolver.clear_cache()

    def test_static_credential_mode(self, tmp_path: Path) -> None:
        """Static mode credentials are correctly preserved."""
        platform_yaml = """
version: "1.0.0"

storage:
  default:
    bucket: test-bucket
    credentials:
      mode: static
      secret_ref: storage-credentials

catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo

compute:
  default:
    type: duckdb
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(platform_yaml)

        platform = PlatformSpec.from_yaml(yaml_file)
        resolver = ProfileResolver(platform)
        profiles = resolver.resolve_all()

        assert profiles.storage.credentials is not None
        assert str(profiles.storage.credentials.mode.value) == "static"
        assert profiles.storage.credentials.secret_ref == "storage-credentials"

    def test_oauth2_credential_mode(self, tmp_path: Path) -> None:
        """OAuth2 mode credentials are correctly preserved."""
        platform_yaml = """
version: "1.0.0"

storage:
  default:
    bucket: test-bucket

catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo
    credentials:
      mode: oauth2
      client_id: test-client
      client_secret:
        secret_ref: oauth-secret
      scope: "PRINCIPAL_ROLE:ALL"

compute:
  default:
    type: duckdb
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(platform_yaml)

        platform = PlatformSpec.from_yaml(yaml_file)
        resolver = ProfileResolver(platform)
        profiles = resolver.resolve_all()

        assert profiles.catalog.credentials is not None
        assert str(profiles.catalog.credentials.mode.value) == "oauth2"
        assert profiles.catalog.credentials.client_id == "test-client"
        assert profiles.catalog.credentials.scope == "PRINCIPAL_ROLE:ALL"

    def test_iam_role_credential_mode(self, tmp_path: Path) -> None:
        """IAM role mode credentials are correctly preserved."""
        platform_yaml = """
version: "1.0.0"

storage:
  default:
    bucket: test-bucket
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::123456789012:role/TestRole"

catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo

compute:
  default:
    type: duckdb
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(platform_yaml)

        platform = PlatformSpec.from_yaml(yaml_file)
        resolver = ProfileResolver(platform)
        profiles = resolver.resolve_all()

        assert profiles.storage.credentials is not None
        assert str(profiles.storage.credentials.mode.value) == "iam_role"
        assert profiles.storage.credentials.role_arn == "arn:aws:iam::123456789012:role/TestRole"
