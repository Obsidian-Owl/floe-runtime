"""DbtExecutor: Invoke dbt CLI with proper configuration.

This module provides the DbtExecutor class for running dbt commands
with the correct project and profile directories.

Per component-ownership.md:
- dbt owns ALL SQL and SQL dialect translation
- floe-dbt only invokes dbt, never parses SQL

TODO: Implement per docs/04-building-blocks.md section 5.3
"""

from __future__ import annotations
