"""Compiler: Transform FloeSpec → CompiledArtifacts.

This module implements the Compiler class that parses floe.yaml,
validates the configuration, and produces CompiledArtifacts for
downstream consumers (floe-dagster, floe-dbt, etc.).

TODO: Implement per docs/04-building-blocks.md section 2.3
"""

from __future__ import annotations
