"""Integration tests for platform.yaml loading.

T029: [US1] Integration test for platform.yaml loading
End-to-end tests for loading real platform.yaml configurations.

Tests loading of platform.yaml files created in T030-T032 and verifies
all profiles are correctly parsed and validated.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from floe_core.compiler.platform_resolver import (
    PLATFORM_ENV_VAR,
    PlatformNotFoundError,
    PlatformResolver,
)
from floe_core.schemas.catalog_profile import AccessDelegation, CatalogType
from floe_core.schemas.credential_config import CredentialMode
from floe_core.schemas.platform_spec import PlatformSpec
from floe_core.schemas.storage_profile import StorageType


class TestPlatformYamlIntegration:
    """Integration tests for platform.yaml loading."""

    @pytest.fixture(autouse=True)
    def clear_resolver_cache(self) -> None:
        """Clear cache before each test."""
        PlatformResolver.clear_cache()

    def test_load_minimal_platform_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load minimal platform.yaml."""
        yaml_content = """
# Minimal platform.yaml
version: "1.0.0"
storage:
  default:
    bucket: test-bucket
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        spec = PlatformSpec.from_yaml(yaml_file)

        assert spec.version == "1.0.0"
        assert "default" in spec.storage
        assert spec.storage["default"].bucket == "test-bucket"
        assert "default" in spec.catalogs
        assert spec.catalogs["default"].warehouse == "demo"

    def test_load_local_development_config(self, tmp_path: Path) -> None:
        """Integration test: Load local development platform.yaml."""
        yaml_content = """
# Local Development Platform Configuration
version: "1.0.0"

storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    region: us-east-1
    bucket: iceberg-data
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials

catalogs:
  default:
    type: polaris
    uri: http://polaris:8181/api/catalog
    warehouse: demo
    namespace: default
    credentials:
      mode: oauth2
      client_id: root
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:ALL"
    access_delegation: vended-credentials
    token_refresh_enabled: true

compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"
      threads: 4

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: http://jaeger:4317
  lineage_endpoint: http://marquez:5000
  attributes:
    service.name: floe-local
    deployment.environment: local
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        spec = PlatformSpec.from_yaml(yaml_file)

        # Verify storage profile
        storage = spec.storage["default"]
        assert storage.type == StorageType.S3
        assert storage.bucket == "iceberg-data"
        assert storage.path_style_access is True
        assert storage.credentials.mode == CredentialMode.STATIC

        # Verify catalog profile
        catalog = spec.catalogs["default"]
        assert catalog.type == CatalogType.POLARIS
        assert catalog.warehouse == "demo"
        assert catalog.credentials.mode == CredentialMode.OAUTH2
        assert catalog.credentials.scope == "PRINCIPAL_ROLE:ALL"
        assert catalog.access_delegation == AccessDelegation.VENDED_CREDENTIALS

        # Verify compute profile
        compute = spec.compute["default"]
        assert compute.properties["path"] == ":memory:"
        assert compute.properties["threads"] == 4

        # Verify observability
        assert spec.observability is not None
        assert spec.observability.traces is True
        assert spec.observability.otlp_endpoint == "http://jaeger:4317"
        assert spec.observability.attributes["service.name"] == "floe-local"

    def test_load_production_config_with_multiple_profiles(self, tmp_path: Path) -> None:
        """Integration test: Load production platform.yaml with multiple profiles."""
        yaml_content = """
# Production Platform Configuration
version: "1.0.0"

storage:
  default:
    type: s3
    region: us-east-1
    bucket: floe-prod-data-lake
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::987654321098:role/FloeProdDataLakeRole"

  archive:
    type: s3
    region: us-east-1
    bucket: floe-prod-archive
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::987654321098:role/FloeProdArchiveRole"

catalogs:
  default:
    type: polaris
    uri: https://polaris.prod.example.com/api/catalog
    warehouse: prod_catalog
    namespace: production
    credentials:
      mode: oauth2
      client_id: floe-prod-service
      client_secret:
        secret_ref: polaris-oauth-prod
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended-credentials

  analytics:
    type: polaris
    uri: https://polaris.prod.example.com/api/catalog
    warehouse: analytics_catalog
    namespace: analytics
    credentials:
      mode: oauth2
      client_id: floe-analytics-service
      client_secret:
        secret_ref: polaris-analytics-oauth-prod
      scope: "PRINCIPAL_ROLE:DATA_ANALYST"
    access_delegation: vended-credentials

compute:
  default:
    type: snowflake
    properties:
      account: "acme-prod.us-east-1"
      warehouse: PROD_WH
      database: PROD_DB
      schema: ANALYTICS
      role: DATA_ENGINEER
    credentials:
      mode: static
      secret_ref: snowflake-prod

  reporting:
    type: snowflake
    properties:
      account: "acme-prod.us-east-1"
      warehouse: REPORTING_WH
    credentials:
      mode: static
      secret_ref: snowflake-reporting-prod

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: "https://otel-collector.prod.example.com:4317"
  lineage_endpoint: "https://marquez.prod.example.com:5000"
  attributes:
    service.name: floe-production
    deployment.environment: production
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        spec = PlatformSpec.from_yaml(yaml_file)

        # Verify multiple storage profiles
        assert len(spec.storage) == 2
        assert "default" in spec.storage
        assert "archive" in spec.storage
        assert spec.storage["default"].bucket == "floe-prod-data-lake"
        assert spec.storage["archive"].bucket == "floe-prod-archive"
        assert spec.storage["default"].credentials.mode == CredentialMode.IAM_ROLE

        # Verify multiple catalog profiles
        assert len(spec.catalogs) == 2
        assert "default" in spec.catalogs
        assert "analytics" in spec.catalogs
        assert spec.catalogs["default"].warehouse == "prod_catalog"
        assert spec.catalogs["analytics"].warehouse == "analytics_catalog"
        assert spec.catalogs["default"].credentials.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"
        assert spec.catalogs["analytics"].credentials.scope == "PRINCIPAL_ROLE:DATA_ANALYST"

        # Verify multiple compute profiles
        assert len(spec.compute) == 2
        assert "default" in spec.compute
        assert "reporting" in spec.compute
        assert spec.compute["default"].properties["warehouse"] == "PROD_WH"
        assert spec.compute["reporting"].properties["warehouse"] == "REPORTING_WH"

    def test_platform_resolver_env_specific(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integration test: PlatformResolver loads env-specific config."""
        # Create environment-specific directory structure
        local_dir = tmp_path / "platform" / "local"
        local_dir.mkdir(parents=True)
        local_file = local_dir / "platform.yaml"
        local_file.write_text("""
version: "1.0.0"
storage:
  default:
    bucket: local-bucket
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: local-demo
""")

        prod_dir = tmp_path / "platform" / "prod"
        prod_dir.mkdir(parents=True)
        prod_file = prod_dir / "platform.yaml"
        prod_file.write_text("""
version: "1.0.0"
storage:
  default:
    bucket: prod-bucket
catalogs:
  default:
    uri: https://polaris.prod.com/api/catalog
    warehouse: prod-catalog
""")

        # Load local environment
        resolver = PlatformResolver(
            env="local",
            search_paths=(tmp_path / "platform",),
        )
        local_spec = resolver.load()

        assert local_spec.storage["default"].bucket == "local-bucket"
        assert local_spec.catalogs["default"].warehouse == "local-demo"

        # Load production environment
        PlatformResolver.clear_cache()
        resolver = PlatformResolver(
            env="prod",
            search_paths=(tmp_path / "platform",),
        )
        prod_spec = resolver.load()

        assert prod_spec.storage["default"].bucket == "prod-bucket"
        assert prod_spec.catalogs["default"].warehouse == "prod-catalog"

    def test_platform_resolver_env_var_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Integration test: PlatformResolver uses FLOE_PLATFORM_ENV."""
        dev_dir = tmp_path / "platform" / "dev"
        dev_dir.mkdir(parents=True)
        dev_file = dev_dir / "platform.yaml"
        dev_file.write_text("""
version: "1.0.0"
storage:
  default:
    bucket: dev-bucket
catalogs:
  default:
    uri: http://polaris-dev:8181/api/catalog
    warehouse: dev-catalog
""")

        monkeypatch.setenv(PLATFORM_ENV_VAR, "dev")

        resolver = PlatformResolver(search_paths=(tmp_path / "platform",))
        spec = resolver.load()

        assert spec.storage["default"].bucket == "dev-bucket"
        assert spec.catalogs["default"].warehouse == "dev-catalog"

    def test_getter_methods_integration(self, tmp_path: Path) -> None:
        """Integration test: Verify profile getter methods work."""
        yaml_content = """
version: "1.0.0"

storage:
  default:
    bucket: default-data
  staging:
    bucket: staging-data

catalogs:
  default:
    uri: http://polaris:8181/api/catalog
    warehouse: default-warehouse
  analytics:
    uri: http://polaris:8181/api/catalog
    warehouse: analytics-warehouse

compute:
  default:
    type: duckdb
  snowflake:
    type: snowflake
    properties:
      account: acme.us-east-1
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        spec = PlatformSpec.from_yaml(yaml_file)

        # Test storage getters
        assert spec.get_storage_profile().bucket == "default-data"
        assert spec.get_storage_profile("staging").bucket == "staging-data"

        with pytest.raises(KeyError) as exc_info:
            spec.get_storage_profile("nonexistent")
        assert "nonexistent" in str(exc_info.value)

        # Test catalog getters
        assert spec.get_catalog_profile().warehouse == "default-warehouse"
        assert spec.get_catalog_profile("analytics").warehouse == "analytics-warehouse"

        # Test compute getters
        assert spec.get_compute_profile().type.value == "duckdb"
        assert spec.get_compute_profile("snowflake").properties["account"] == "acme.us-east-1"


class TestPlatformYamlErrorHandling:
    """Integration tests for error handling during platform.yaml loading."""

    @pytest.fixture(autouse=True)
    def clear_resolver_cache(self) -> None:
        """Clear cache before each test."""
        PlatformResolver.clear_cache()

    def test_error_on_invalid_version(self, tmp_path: Path) -> None:
        """Error on invalid version format."""
        yaml_content = """
version: "invalid-version"
storage:
  default:
    bucket: test-bucket
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec.from_yaml(yaml_file)
        assert "version" in str(exc_info.value)

    def test_error_on_invalid_profile_name(self, tmp_path: Path) -> None:
        """Error on invalid profile name (starts with number)."""
        yaml_content = """
version: "1.0.0"
storage:
  123-invalid:
    bucket: test-bucket
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec.from_yaml(yaml_file)
        assert "123-invalid" in str(exc_info.value)

    def test_error_on_missing_required_catalog_fields(self, tmp_path: Path) -> None:
        """Error when catalog profile missing required fields."""
        yaml_content = """
version: "1.0.0"
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    # warehouse is missing
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec.from_yaml(yaml_file)
        assert "warehouse" in str(exc_info.value)

    def test_error_on_invalid_credential_mode(self, tmp_path: Path) -> None:
        """Error when credential mode is invalid."""
        yaml_content = """
version: "1.0.0"
storage:
  default:
    bucket: test-bucket
    credentials:
      mode: invalid_mode
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec.from_yaml(yaml_file)
        # Error should mention the invalid mode value
        error_msg = str(exc_info.value)
        assert "mode" in error_msg or "invalid_mode" in error_msg

    def test_error_on_oauth2_missing_client_id(self, tmp_path: Path) -> None:
        """Error when OAuth2 mode is missing required fields."""
        yaml_content = """
version: "1.0.0"
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo
    credentials:
      mode: oauth2
      client_secret:
        secret_ref: my-secret
      # client_id is missing
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec.from_yaml(yaml_file)
        assert "client_id" in str(exc_info.value)

    def test_platform_not_found_error(self, tmp_path: Path) -> None:
        """PlatformNotFoundError when no platform.yaml found."""
        resolver = PlatformResolver(
            env="nonexistent",
            search_paths=(tmp_path / "nonexistent",),
        )

        with pytest.raises(PlatformNotFoundError) as exc_info:
            resolver.load()
        assert "nonexistent" in str(exc_info.value)


class TestPlatformYamlRoundTrip:
    """Integration tests for platform.yaml serialization roundtrip."""

    def test_roundtrip_model_dump_and_validate(self, tmp_path: Path) -> None:
        """Roundtrip: load → dump → validate."""
        yaml_content = """
version: "1.0.0"
storage:
  default:
    bucket: roundtrip-bucket
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo
compute:
  default:
    type: duckdb
observability:
  traces: true
  lineage: true
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        # Load from YAML
        spec = PlatformSpec.from_yaml(yaml_file)

        # Serialize to dict
        data = spec.model_dump()

        # Recreate from dict
        spec2 = PlatformSpec.model_validate(data)

        # Compare
        assert spec.version == spec2.version
        assert spec.storage["default"].bucket == spec2.storage["default"].bucket
        assert spec.catalogs["default"].warehouse == spec2.catalogs["default"].warehouse
        assert spec.compute["default"].type == spec2.compute["default"].type

    def test_roundtrip_json_serialization(self, tmp_path: Path) -> None:
        """Roundtrip: load → JSON → validate."""
        import json

        yaml_content = """
version: "1.0.0"
storage:
  default:
    bucket: json-test-bucket
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: json-demo
"""
        yaml_file = tmp_path / "platform.yaml"
        yaml_file.write_text(yaml_content)

        # Load from YAML
        spec = PlatformSpec.from_yaml(yaml_file)

        # Serialize to JSON
        json_str = spec.model_dump_json()

        # Parse JSON and recreate
        data = json.loads(json_str)
        spec2 = PlatformSpec.model_validate(data)

        # Compare
        assert spec.version == spec2.version
        assert spec.storage["default"].bucket == spec2.storage["default"].bucket
