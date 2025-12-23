"""Storage profile models for floe-runtime.

This module defines storage backend configuration including:
- StorageType: Enum for supported storage types (s3, gcs, azure, local)
- StorageProfile: S3-compatible storage configuration
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.credential_config import CredentialConfig, SecretReference

# Pattern for S3 bucket names (RFC compliant)
S3_BUCKET_PATTERN = r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$"

# Default S3 region
DEFAULT_REGION = "us-east-1"


class StorageType(str, Enum):
    """Supported storage backend types.

    Values:
        S3: Amazon S3 or S3-compatible storage (MinIO, LocalStack).
        GCS: Google Cloud Storage.
        AZURE: Azure Blob Storage.
        LOCAL: Local filesystem (development only).
    """

    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"
    LOCAL = "local"


class StorageProfile(BaseModel):
    """S3-compatible storage configuration.

    Defines connection parameters for object storage backends.
    Supports AWS S3, MinIO, LocalStack, and other S3-compatible services.

    Attributes:
        type: Storage backend type.
        endpoint: S3 endpoint URL (empty for AWS S3).
        region: AWS region.
        bucket: Default bucket name.
        path_style_access: Use path-style S3 access (required for MinIO).
        credentials: Credential configuration.

    Example:
        >>> profile = StorageProfile(
        ...     type=StorageType.S3,
        ...     endpoint="http://minio:9000",
        ...     bucket="iceberg-data",
        ...     path_style_access=True,
        ...     credentials=CredentialConfig(
        ...         mode=CredentialMode.STATIC,
        ...         secret_ref="minio-credentials",
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: StorageType = Field(
        default=StorageType.S3,
        description="Storage backend type",
    )
    endpoint: str | SecretReference = Field(
        default="",
        description="S3 endpoint URL (empty for AWS S3, set for MinIO/LocalStack)",
    )
    region: str = Field(
        default=DEFAULT_REGION,
        description="AWS region",
    )
    bucket: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Default bucket name",
    )
    path_style_access: bool = Field(
        default=False,
        description="Use path-style S3 access (required for MinIO)",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )

    def get_endpoint(self) -> str:
        """Get endpoint URL, resolving SecretReference if needed.

        Returns:
            Endpoint URL string.
        """
        if isinstance(self.endpoint, SecretReference):
            return self.endpoint.resolve().get_secret_value()
        return self.endpoint

    def is_aws_s3(self) -> bool:
        """Check if this is AWS S3 (not a custom endpoint).

        Returns:
            True if endpoint is empty (AWS S3), False otherwise.
        """
        endpoint = self.get_endpoint()
        return not endpoint or endpoint == ""
