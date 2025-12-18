"""Maintenance operations for Iceberg tables.

This module provides:
- expire_snapshots: Remove old snapshots
- Retention policy support (retain_last parameter)

TODO: Implement maintenance operations per contracts/floe-iceberg-api.md
"""

from __future__ import annotations
