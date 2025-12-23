"""Storage profile models for floe-runtime.

T004: [Setup] Create schema module storage_profile.py
T023-T026: [Phase 2] Will implement StorageProfile and related models

This module defines storage backend configuration including:
- StorageProfile: S3-compatible storage configuration
- StorageType: Enum for supported storage types (s3, gcs, adls)
- Path style access, region, endpoint configuration
- Credential references for storage access
"""

from __future__ import annotations

# Supported storage types
STORAGE_TYPES = frozenset({"s3", "gcs", "adls"})

# Default S3 region
DEFAULT_REGION = "us-east-1"

# Pattern for S3 bucket names
S3_BUCKET_PATTERN = r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"

# TODO(T023): Implement StorageType enum
# TODO(T024): Implement StorageProfile model
# TODO(T025): Implement storage endpoint validation
# TODO(T026): Implement path_style_access logic for MinIO vs AWS
