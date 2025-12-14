"""Custom exception hierarchy for floe-core.

This module defines the exception classes used throughout floe-runtime:
- FloeError: Base exception for all floe-related errors
- ValidationError: Raised when configuration validation fails
- CompilationError: Raised when compilation fails

TODO: Implement per .claude/rules/security.md error handling section
"""

from __future__ import annotations
