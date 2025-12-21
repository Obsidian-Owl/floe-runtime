"""Unit tests for ConsumptionConfig and related models.

T013: [US1] Unit tests for ConsumptionConfig defaults
Tests ConsumptionConfig, PreAggregationConfig, and CubeSecurityConfig defaults.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCubeStoreConfig:
    """Tests for CubeStoreConfig model."""

    def test_cube_store_config_default_values(self) -> None:
        """CubeStoreConfig should have correct defaults."""
        from floe_core.schemas import CubeStoreConfig

        config = CubeStoreConfig()
        assert config.enabled is False
        assert config.s3_bucket is None
        assert config.s3_region is None
        assert config.s3_endpoint is None
        assert config.s3_access_key_ref is None
        assert config.s3_secret_key_ref is None

    def test_cube_store_config_enabled_with_s3(self) -> None:
        """CubeStoreConfig should accept S3 configuration."""
        from floe_core.schemas import CubeStoreConfig

        config = CubeStoreConfig(
            enabled=True,
            s3_bucket="my-cube-preaggs",
            s3_region="us-east-1",
        )
        assert config.enabled is True
        assert config.s3_bucket == "my-cube-preaggs"
        assert config.s3_region == "us-east-1"

    def test_cube_store_config_custom_endpoint(self) -> None:
        """CubeStoreConfig should accept custom S3 endpoint (MinIO/LocalStack)."""
        from floe_core.schemas import CubeStoreConfig

        config = CubeStoreConfig(
            enabled=True,
            s3_bucket="test-bucket",
            s3_endpoint="http://localhost:4566",
        )
        assert config.s3_endpoint == "http://localhost:4566"

    def test_cube_store_config_k8s_secret_refs(self) -> None:
        """CubeStoreConfig should accept K8s secret references."""
        from floe_core.schemas import CubeStoreConfig

        config = CubeStoreConfig(
            enabled=True,
            s3_bucket="my-bucket",
            s3_access_key_ref="cube-s3-credentials",
            s3_secret_key_ref="cube-s3-credentials",
        )
        assert config.s3_access_key_ref == "cube-s3-credentials"
        assert config.s3_secret_key_ref == "cube-s3-credentials"

    def test_cube_store_config_invalid_secret_ref(self) -> None:
        """CubeStoreConfig should reject invalid K8s secret names."""
        from floe_core.schemas import CubeStoreConfig

        with pytest.raises(ValidationError) as exc_info:
            CubeStoreConfig(
                enabled=True,
                s3_access_key_ref="-invalid-start",
            )
        assert "s3_access_key_ref" in str(exc_info.value)

    def test_cube_store_config_is_frozen(self) -> None:
        """CubeStoreConfig should be immutable."""
        from floe_core.schemas import CubeStoreConfig

        config = CubeStoreConfig()
        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]


class TestExportBucketConfig:
    """Tests for ExportBucketConfig model."""

    def test_export_bucket_config_default_values(self) -> None:
        """ExportBucketConfig should have correct defaults."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig()
        assert config.enabled is False
        assert config.bucket_type is None
        assert config.name is None
        assert config.region is None
        assert config.access_key_ref is None
        assert config.secret_key_ref is None
        assert config.integration is None

    def test_export_bucket_config_s3_bucket(self) -> None:
        """ExportBucketConfig should accept S3 configuration."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig(
            enabled=True,
            bucket_type="s3",
            name="my-export-bucket",
            region="us-west-2",
        )
        assert config.enabled is True
        assert config.bucket_type == "s3"
        assert config.name == "my-export-bucket"
        assert config.region == "us-west-2"

    def test_export_bucket_config_gcs_bucket(self) -> None:
        """ExportBucketConfig should accept GCS configuration."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig(
            enabled=True,
            bucket_type="gcs",
            name="my-gcs-export-bucket",
        )
        assert config.bucket_type == "gcs"

    def test_export_bucket_config_snowflake_integration(self) -> None:
        """ExportBucketConfig should accept Snowflake storage integration."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig(
            enabled=True,
            bucket_type="s3",
            name="my-bucket",
            integration="my_storage_integration",
        )
        assert config.integration == "my_storage_integration"

    def test_export_bucket_config_k8s_secret_refs(self) -> None:
        """ExportBucketConfig should accept K8s secret references."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig(
            enabled=True,
            bucket_type="s3",
            name="my-bucket",
            access_key_ref="export-bucket-creds",
            secret_key_ref="export-bucket-creds",
        )
        assert config.access_key_ref == "export-bucket-creds"
        assert config.secret_key_ref == "export-bucket-creds"

    def test_export_bucket_config_invalid_secret_ref(self) -> None:
        """ExportBucketConfig should reject invalid K8s secret names."""
        from floe_core.schemas import ExportBucketConfig

        with pytest.raises(ValidationError) as exc_info:
            ExportBucketConfig(
                enabled=True,
                access_key_ref="-invalid-start",
            )
        assert "access_key_ref" in str(exc_info.value)

    def test_export_bucket_config_is_frozen(self) -> None:
        """ExportBucketConfig should be immutable."""
        from floe_core.schemas import ExportBucketConfig

        config = ExportBucketConfig()
        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]


class TestPreAggregationConfig:
    """Tests for PreAggregationConfig model."""

    def test_pre_aggregation_config_default_values(self) -> None:
        """PreAggregationConfig should have correct defaults."""
        from floe_core.schemas import (
            CubeStoreConfig,
            ExportBucketConfig,
            PreAggregationConfig,
        )

        config = PreAggregationConfig()
        assert config.refresh_schedule == "*/30 * * * *"
        assert config.timezone == "UTC"
        assert config.external is True  # Default to Cube Store (production)
        assert isinstance(config.cube_store, CubeStoreConfig)
        assert isinstance(config.export_bucket, ExportBucketConfig)

    def test_pre_aggregation_config_custom_values(self) -> None:
        """PreAggregationConfig should accept custom values."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig(
            refresh_schedule="0 * * * *",
            timezone="America/New_York",
        )
        assert config.refresh_schedule == "0 * * * *"
        assert config.timezone == "America/New_York"

    def test_pre_aggregation_config_external_false_for_testing(self) -> None:
        """PreAggregationConfig should accept external=False for testing."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig(external=False)
        assert config.external is False

    def test_pre_aggregation_config_with_cube_store(self) -> None:
        """PreAggregationConfig should accept custom cube_store config."""
        from floe_core.schemas import CubeStoreConfig, PreAggregationConfig

        config = PreAggregationConfig(
            external=True,
            cube_store=CubeStoreConfig(
                enabled=True,
                s3_bucket="my-cube-preaggs",
                s3_region="us-east-1",
            ),
        )
        assert config.cube_store.enabled is True
        assert config.cube_store.s3_bucket == "my-cube-preaggs"

    def test_pre_aggregation_config_with_export_bucket(self) -> None:
        """PreAggregationConfig should accept custom export_bucket config."""
        from floe_core.schemas import ExportBucketConfig, PreAggregationConfig

        config = PreAggregationConfig(
            external=True,
            export_bucket=ExportBucketConfig(
                enabled=True,
                bucket_type="s3",
                name="my-export-bucket",
                region="us-west-2",
            ),
        )
        assert config.export_bucket.enabled is True
        assert config.export_bucket.bucket_type == "s3"
        assert config.export_bucket.name == "my-export-bucket"

    def test_pre_aggregation_config_is_frozen(self) -> None:
        """PreAggregationConfig should be immutable."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig()

        with pytest.raises(ValidationError):
            config.timezone = "Europe/London"  # type: ignore[misc]

    def test_pre_aggregation_config_nested_isolation(self) -> None:
        """PreAggregationConfig nested configs should be isolated."""
        from floe_core.schemas import PreAggregationConfig

        config1 = PreAggregationConfig()
        config2 = PreAggregationConfig()

        assert config1.cube_store is not config2.cube_store
        assert config1.export_bucket is not config2.export_bucket


class TestCubeSecurityConfig:
    """Tests for CubeSecurityConfig model."""

    def test_cube_security_config_default_values(self) -> None:
        """CubeSecurityConfig should have correct defaults."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig()
        assert config.row_level is True
        assert config.filter_column == "organization_id"

    def test_cube_security_config_custom_values(self) -> None:
        """CubeSecurityConfig should accept custom values."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig(
            row_level=False,
            filter_column="department_id",
        )
        assert config.row_level is False
        assert config.filter_column == "department_id"

    def test_cube_security_config_is_frozen(self) -> None:
        """CubeSecurityConfig should be immutable."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig()

        with pytest.raises(ValidationError):
            config.row_level = False  # type: ignore[misc]


class TestConsumptionConfig:
    """Tests for ConsumptionConfig model."""

    def test_consumption_config_default_values(self) -> None:
        """ConsumptionConfig should have correct defaults."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig()
        assert config.enabled is False
        assert config.port == 4000
        assert config.api_secret_ref is None
        assert config.database_type is None
        assert config.dev_mode is False

    def test_consumption_config_pre_aggregations_default(self) -> None:
        """ConsumptionConfig should have default PreAggregationConfig."""
        from floe_core.schemas import ConsumptionConfig, PreAggregationConfig

        config = ConsumptionConfig()
        assert isinstance(config.pre_aggregations, PreAggregationConfig)
        assert config.pre_aggregations.refresh_schedule == "*/30 * * * *"

    def test_consumption_config_security_default(self) -> None:
        """ConsumptionConfig should have default CubeSecurityConfig."""
        from floe_core.schemas import ConsumptionConfig, CubeSecurityConfig

        config = ConsumptionConfig()
        assert isinstance(config.security, CubeSecurityConfig)
        assert config.security.row_level is True

    def test_consumption_config_enabled(self) -> None:
        """ConsumptionConfig should accept enabled=True."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(enabled=True)
        assert config.enabled is True

    def test_consumption_config_custom_port(self) -> None:
        """ConsumptionConfig should accept custom port."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(port=8080)
        assert config.port == 8080

    def test_consumption_config_database_type(self) -> None:
        """ConsumptionConfig should accept database_type."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            database_type="snowflake",
        )
        assert config.database_type == "snowflake"

    def test_consumption_config_api_secret_ref(self) -> None:
        """ConsumptionConfig should accept api_secret_ref."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            api_secret_ref="cube-api-secret",
        )
        assert config.api_secret_ref == "cube-api-secret"

    def test_consumption_config_invalid_api_secret_ref(self) -> None:
        """ConsumptionConfig should reject invalid api_secret_ref."""
        from floe_core.schemas import ConsumptionConfig

        with pytest.raises(ValidationError) as exc_info:
            ConsumptionConfig(
                enabled=True,
                api_secret_ref="-invalid-start",
            )

        assert "api_secret_ref" in str(exc_info.value)

    def test_consumption_config_dev_mode(self) -> None:
        """ConsumptionConfig should accept dev_mode."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            dev_mode=True,
        )
        assert config.dev_mode is True

    def test_consumption_config_custom_pre_aggregations(self) -> None:
        """ConsumptionConfig should accept custom pre_aggregations."""
        from floe_core.schemas import ConsumptionConfig, PreAggregationConfig

        config = ConsumptionConfig(
            enabled=True,
            pre_aggregations=PreAggregationConfig(
                refresh_schedule="0 */2 * * *",
                timezone="Europe/London",
            ),
        )
        assert config.pre_aggregations.refresh_schedule == "0 */2 * * *"
        assert config.pre_aggregations.timezone == "Europe/London"

    def test_consumption_config_custom_security(self) -> None:
        """ConsumptionConfig should accept custom security."""
        from floe_core.schemas import ConsumptionConfig, CubeSecurityConfig

        config = ConsumptionConfig(
            enabled=True,
            security=CubeSecurityConfig(
                row_level=False,
                filter_column="department_id",
            ),
        )
        assert config.security.row_level is False
        assert config.security.filter_column == "department_id"

    def test_consumption_config_is_frozen(self) -> None:
        """ConsumptionConfig should be immutable."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig()

        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]

    def test_consumption_config_rejects_extra_fields(self) -> None:
        """ConsumptionConfig should reject unknown fields."""
        from floe_core.schemas import ConsumptionConfig

        with pytest.raises(ValidationError) as exc_info:
            ConsumptionConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "extra" in str(exc_info.value).lower()

    def test_consumption_config_default_factory_isolation(self) -> None:
        """ConsumptionConfig defaults should be isolated (no shared state)."""
        from floe_core.schemas import ConsumptionConfig

        config1 = ConsumptionConfig()
        config2 = ConsumptionConfig()

        # Verify they are independent objects
        assert config1 is not config2
        assert config1.pre_aggregations is not config2.pre_aggregations
        assert config1.security is not config2.security
