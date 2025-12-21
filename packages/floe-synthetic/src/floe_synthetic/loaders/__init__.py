"""Data loaders for synthetic data.

This module provides loaders for persisting generated data:
- IcebergLoader: Load data into Iceberg tables via PyIceberg
"""

from __future__ import annotations

from floe_synthetic.loaders.iceberg import IcebergLoader

__all__ = ["IcebergLoader"]
