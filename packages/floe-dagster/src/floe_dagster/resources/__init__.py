"""Dagster resources for floe-runtime.

T095: [US6] Create resources module with catalog abstraction

This package provides Dagster ConfigurableResource implementations that
load configuration from CompiledArtifacts and resolve secrets at runtime.

Key Components:
    - CatalogResource: Abstract base for catalog resources (catalog-agnostic)
    - CatalogProtocol: Protocol defining the catalog interface
    - PolarisCatalogResource: Polaris implementation
    - (Future) GlueCatalogResource: AWS Glue implementation

Design Philosophy:
    Data engineers write code against the abstract `CatalogResource` type.
    Platform engineers configure the concrete implementation (Polaris, Glue, etc.)
    in platform.yaml. The same asset code works across all catalog types.

Example (Data Engineer - uses abstract type):
    >>> from floe_dagster.resources import CatalogResource
    >>>
    >>> @floe_asset(outputs=["demo.bronze_customers"])
    ... def bronze_customers(context, catalog: CatalogResource):
    ...     # Works with Polaris, Glue, Unity, etc.
    ...     table = catalog.load_table("demo.bronze_customers")
    ...     ...

Example (Platform Engineer - configures concrete type):
    >>> # platform.yaml
    >>> catalogs:
    >>>   default:
    >>>     type: polaris  # or "glue", "unity"
    >>>     uri: http://polaris:8181/api/catalog
"""

from __future__ import annotations

from floe_dagster.resources.catalog import (
    Catalog,
    CatalogProtocol,
    CatalogResource,
    PolarisCatalogResource,
)
from floe_dagster.resources.dbt import create_dbt_cli_resource, get_dbt_cli_config

__all__ = [
    # Abstract types (for data engineers)
    "CatalogResource",
    "CatalogProtocol",
    "Catalog",  # Type alias for CatalogResource
    # Concrete implementations (for platform engineers)
    "PolarisCatalogResource",
    # dbt resources
    "create_dbt_cli_resource",
    "get_dbt_cli_config",
]
