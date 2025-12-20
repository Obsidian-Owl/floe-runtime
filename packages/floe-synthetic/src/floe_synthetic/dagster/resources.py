"""Dagster resources for synthetic data generation.

This module provides Dagster ConfigurableResource implementations
for the generators and loaders.
"""

from __future__ import annotations

from typing import Any

from dagster import ConfigurableResource
from pydantic import Field

from floe_synthetic.generators.ecommerce import EcommerceGenerator
from floe_synthetic.generators.saas import SaaSGenerator
from floe_synthetic.loaders.iceberg import IcebergLoader, IcebergLoaderConfig


class EcommerceGeneratorResource(ConfigurableResource):
    """Dagster resource for EcommerceGenerator.

    Example:
        >>> @asset
        >>> def orders(generator: EcommerceGeneratorResource):
        ...     return generator.get_generator().generate_orders(1000)
    """

    seed: int = Field(default=42, description="Random seed for reproducibility")

    def get_generator(self) -> EcommerceGenerator:
        """Create a configured EcommerceGenerator instance."""
        return EcommerceGenerator(seed=self.seed)


class SaaSGeneratorResource(ConfigurableResource):
    """Dagster resource for SaaSGenerator.

    Example:
        >>> @asset
        >>> def events(generator: SaaSGeneratorResource):
        ...     return generator.get_generator().generate_events(10000)
    """

    seed: int = Field(default=42, description="Random seed for reproducibility")

    def get_generator(self) -> SaaSGenerator:
        """Create a configured SaaSGenerator instance."""
        return SaaSGenerator(seed=self.seed)


class IcebergLoaderResource(ConfigurableResource):
    """Dagster resource for IcebergLoader.

    Example:
        >>> @asset
        >>> def load_orders(loader: IcebergLoaderResource, orders: pa.Table):
        ...     loader.get_loader().append("default.orders", orders)
    """

    catalog_uri: str = Field(
        default="http://localhost:8181/api/catalog",
        description="Polaris catalog URI",
    )
    catalog_name: str = Field(default="polaris", description="Catalog name")
    warehouse: str = Field(default="warehouse", description="Warehouse name")
    credential: str | None = Field(default=None, description="OAuth credential")
    s3_endpoint: str | None = Field(default=None, description="S3 endpoint override")
    s3_region: str = Field(default="us-east-1", description="S3 region")

    def get_loader(self) -> IcebergLoader:
        """Create a configured IcebergLoader instance."""
        config = IcebergLoaderConfig(
            catalog_name=self.catalog_name,
            catalog_uri=self.catalog_uri,
            warehouse=self.warehouse,
            credential=self.credential,
            s3_endpoint=self.s3_endpoint,
            s3_region=self.s3_region,
        )
        return IcebergLoader(config=config)
