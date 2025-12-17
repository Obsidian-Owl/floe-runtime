"""Time travel and snapshot management for Iceberg tables.

This module provides:
- list_snapshots: List all snapshots for a table
- get_current_snapshot: Get the current snapshot
- Time travel scan support via snapshot_id parameter

TODO: Implement snapshot operations per contracts/floe-iceberg-api.md
"""

from __future__ import annotations
