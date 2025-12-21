"""Unit tests for Dagster resources.

Tests for ConfigurableResource implementations that wrap generators and loaders.
These are thin wrappers - we test instantiation and method returns.
"""

from __future__ import annotations

from floe_synthetic.dagster.resources import (
    EcommerceGeneratorResource,
    IcebergLoaderResource,
    SaaSGeneratorResource,
)
from floe_synthetic.generators.ecommerce import EcommerceGenerator
from floe_synthetic.generators.saas import SaaSGenerator


class TestEcommerceGeneratorResource:
    """Tests for EcommerceGeneratorResource."""

    def test_default_seed(self) -> None:
        """Resource has default seed of 42."""
        resource = EcommerceGeneratorResource()
        assert resource.seed == 42

    def test_custom_seed(self) -> None:
        """Resource accepts custom seed."""
        resource = EcommerceGeneratorResource(seed=123)
        assert resource.seed == 123

    def test_get_generator_returns_ecommerce_generator(self) -> None:
        """get_generator returns EcommerceGenerator instance."""
        resource = EcommerceGeneratorResource(seed=42)
        generator = resource.get_generator()
        assert isinstance(generator, EcommerceGenerator)
        assert generator.seed == 42

    def test_get_generator_uses_configured_seed(self) -> None:
        """Generator uses the resource's configured seed."""
        resource = EcommerceGeneratorResource(seed=999)
        generator = resource.get_generator()
        assert generator.seed == 999


class TestSaaSGeneratorResource:
    """Tests for SaaSGeneratorResource."""

    def test_default_seed(self) -> None:
        """Resource has default seed of 42."""
        resource = SaaSGeneratorResource()
        assert resource.seed == 42

    def test_custom_seed(self) -> None:
        """Resource accepts custom seed."""
        resource = SaaSGeneratorResource(seed=456)
        assert resource.seed == 456

    def test_get_generator_returns_saas_generator(self) -> None:
        """get_generator returns SaaSGenerator instance."""
        resource = SaaSGeneratorResource(seed=42)
        generator = resource.get_generator()
        assert isinstance(generator, SaaSGenerator)
        assert generator.seed == 42

    def test_get_generator_uses_configured_seed(self) -> None:
        """Generator uses the resource's configured seed."""
        resource = SaaSGeneratorResource(seed=888)
        generator = resource.get_generator()
        assert generator.seed == 888


class TestIcebergLoaderResource:
    """Tests for IcebergLoaderResource configuration.

    Note: get_loader() is not tested here as it requires catalog connection.
    That path is covered by integration tests.
    """

    def test_default_values(self) -> None:
        """Resource has sensible defaults."""
        resource = IcebergLoaderResource()
        assert resource.catalog_uri == "http://localhost:8181/api/catalog"
        assert resource.catalog_name == "polaris"
        assert resource.warehouse == "warehouse"
        assert resource.credential is None
        assert resource.s3_endpoint is None
        assert resource.s3_region == "us-east-1"

    def test_custom_configuration(self) -> None:
        """Resource accepts custom configuration."""
        resource = IcebergLoaderResource(
            catalog_uri="http://polaris:8181/api/catalog",
            catalog_name="my_catalog",
            warehouse="my_warehouse",
            credential="client:secret",
            s3_endpoint="http://localstack:4566",
            s3_region="us-west-2",
        )
        assert resource.catalog_uri == "http://polaris:8181/api/catalog"
        assert resource.catalog_name == "my_catalog"
        assert resource.warehouse == "my_warehouse"
        assert resource.credential == "client:secret"
        assert resource.s3_endpoint == "http://localstack:4566"
        assert resource.s3_region == "us-west-2"
