"""E2E Tests for Deployment Automation.

This module contains end-to-end validation tests for the floe-runtime
deployment automation feature (007-deployment-automation).

Test Structure:
    - conftest.py: Fixtures for E2E tests (Docker services, Cube client)
    - test_demo_flow.py: E2E validation tests for demo data flow

Covers:
    - 007-FR-029: E2E validation tests
    - 007-FR-031: Medallion architecture demo
    - 007-FR-032: Cube pre-aggregation refresh

Usage:
    pytest testing/e2e/ -v --tb=short
"""

from __future__ import annotations
