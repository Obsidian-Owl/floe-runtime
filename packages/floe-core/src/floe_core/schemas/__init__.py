"""Schema definitions for floe-runtime.

This module exports the core Pydantic models:

Root Models:
- FloeSpec: Root schema for floe.yaml (Data Engineer configuration)
- PlatformSpec: Root schema for platform.yaml (Platform Engineer configuration)

Profile Models (Two-Tier Configuration):
- StorageProfile: S3-compatible storage configuration
- CatalogProfile: Iceberg catalog configuration
- ComputeProfile: Compute engine configuration
- CredentialConfig: Credential management (OAuth2, IAM, static)
- SecretReference: Reference to external secrets

Enterprise Configuration (v1.1.0):
- InfrastructureConfig: Network, DNS, cloud provider configuration
- SecurityConfig: Authentication, authorization, secret backends
- EnterpriseGovernanceConfig: Classification, retention, compliance

Legacy Models:
- ComputeTarget: Enum for compute targets
- ComputeConfig: Compute target configuration
- TransformConfig: Transformation step configuration
- ConsumptionConfig: Cube semantic layer configuration
- GovernanceConfig: Data governance configuration
- ObservabilityConfig: Observability configuration
- CatalogConfig: Iceberg catalog configuration
"""

from __future__ import annotations

from floe_core.schemas.asset_config import AssetConfig
from floe_core.schemas.backfill_definition import BackfillDefinition
from floe_core.schemas.catalog import CatalogConfig
from floe_core.schemas.catalog_profile import (
    AccessDelegation,
    CatalogProfile,
    CatalogType,
)
from floe_core.schemas.compute import ComputeConfig, ComputeTarget
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.consumption import (
    ConsumptionConfig,
    CubeSecurityConfig,
    CubeStoreConfig,
    ExportBucketConfig,
    PreAggregationConfig,
)
from floe_core.schemas.credential_config import (
    CredentialConfig,
    CredentialMode,
    SecretNotFoundError,
    SecretReference,
)
from floe_core.schemas.floe_spec import (
    DEFAULT_PROFILE_NAME,
    FloeSpec,
)
from floe_core.schemas.floe_spec import (
    PROFILE_NAME_PATTERN as FLOE_PROFILE_NAME_PATTERN,
)
from floe_core.schemas.governance import ColumnClassification, GovernanceConfig
from floe_core.schemas.governance_config import (
    ClassificationClass,
    ClassificationsConfig,
    ComplianceConfig,
    ComplianceEnforcement,
    ComplianceFramework,
    DataQualityCheck,
    DataQualityConfig,
    EnterpriseGovernanceConfig,
    FrameworkConfig,
    RetentionConfig,
    RetentionPolicy,
    SensitivityLevel,
)
from floe_core.schemas.infrastructure_config import (
    AwsConfig,
    AwsIamConfig,
    AwsKmsConfig,
    AwsServiceAccountConfig,
    AwsVpcConfig,
    CloudConfig,
    CloudProvider,
    DnsConfig,
    DnsStrategy,
    InfrastructureConfig,
    IngressClass,
    IngressConfig,
    IngressRoute,
    LocalAccessConfig,
    LocalAccessPorts,
    LocalAccessType,
    LocalStackConfig,
    NetworkConfig,
    NetworkPoliciesConfig,
    NetworkPolicyRule,
    NetworkZone,
    TlsConfig,
    TlsProvider,
)
from floe_core.schemas.job_definition import BatchJob, JobDefinition, OpsJob
from floe_core.schemas.observability import (
    AlertRule,
    AlertSeverity,
    LogFormat,
    LoggingBackendsConfig,
    LoggingConfig,
    LogLevel,
    MetricsAlertingConfig,
    MetricsConfig,
    MetricsExportersConfig,
    ObservabilityConfig,
    SamplingType,
    TraceExportersConfig,
    TraceSamplingConfig,
    TracingConfig,
)
from floe_core.schemas.orchestration_config import (
    DbtConfig,
    ObservabilityLevel,
    OrchestrationConfig,
)
from floe_core.schemas.partition_definition import (
    DynamicPartition,
    MultiPartition,
    PartitionDefinition,
    StaticPartition,
    TimeWindowPartition,
)
from floe_core.schemas.platform_spec import (
    ENVIRONMENT_TYPES,
    PLATFORM_SPEC_VERSION,
    PROFILE_NAME_PATTERN,
    PlatformSpec,
)
from floe_core.schemas.schedule_definition import ScheduleDefinition
from floe_core.schemas.security_config import (
    AtRestEncryption,
    AuditBackend,
    AuditConfig,
    AuditEventsConfig,
    AuthenticationConfig,
    AuthMethod,
    AuthorizationConfig,
    AuthorizationMode,
    AwsSecretsManagerBackend,
    EncryptionConfig,
    EncryptionProvider,
    InTransitEncryption,
    KubernetesSecretBackend,
    OidcClaimsMapping,
    OidcConfig,
    RoleDefinition,
    SameSitePolicy,
    SecretBackendsConfig,
    SecretBackendType,
    SecurityConfig,
    SessionConfig,
    VaultAuthMethod,
    VaultSecretBackend,
)
from floe_core.schemas.sensor_definition import (
    AssetSensor,
    CustomSensor,
    FileWatcherSensor,
    RunStatusSensor,
    SensorDefinition,
)
from floe_core.schemas.storage_profile import StorageProfile, StorageType
from floe_core.schemas.transforms import TransformConfig

__all__: list[str] = [
    # Root models
    "FloeSpec",
    "PlatformSpec",
    # Platform configuration constants
    "ENVIRONMENT_TYPES",
    "PLATFORM_SPEC_VERSION",
    "PROFILE_NAME_PATTERN",
    # FloeSpec configuration constants
    "DEFAULT_PROFILE_NAME",
    "FLOE_PROFILE_NAME_PATTERN",
    # Credential management
    "CredentialConfig",
    "CredentialMode",
    "SecretReference",
    "SecretNotFoundError",
    # Storage profiles
    "StorageProfile",
    "StorageType",
    # Catalog profiles
    "CatalogProfile",
    "CatalogType",
    "AccessDelegation",
    # Compute profiles
    "ComputeProfile",
    # Infrastructure (v1.1.0)
    "InfrastructureConfig",
    "NetworkConfig",
    "DnsConfig",
    "DnsStrategy",
    "NetworkPoliciesConfig",
    "NetworkPolicyRule",
    "NetworkZone",
    "IngressConfig",
    "IngressClass",
    "IngressRoute",
    "TlsConfig",
    "TlsProvider",
    "LocalAccessConfig",
    "LocalAccessType",
    "LocalAccessPorts",
    "CloudConfig",
    "CloudProvider",
    "AwsConfig",
    "AwsVpcConfig",
    "AwsIamConfig",
    "AwsServiceAccountConfig",
    "AwsKmsConfig",
    "LocalStackConfig",
    # Security (v1.1.0)
    "SecurityConfig",
    "AuthenticationConfig",
    "AuthMethod",
    "OidcConfig",
    "OidcClaimsMapping",
    "SessionConfig",
    "SameSitePolicy",
    "AuthorizationConfig",
    "AuthorizationMode",
    "RoleDefinition",
    "SecretBackendsConfig",
    "SecretBackendType",
    "KubernetesSecretBackend",
    "VaultSecretBackend",
    "VaultAuthMethod",
    "AwsSecretsManagerBackend",
    "EncryptionConfig",
    "InTransitEncryption",
    "AtRestEncryption",
    "EncryptionProvider",
    "AuditConfig",
    "AuditEventsConfig",
    "AuditBackend",
    # Enterprise Governance (v1.1.0)
    "EnterpriseGovernanceConfig",
    "ClassificationsConfig",
    "ClassificationClass",
    "SensitivityLevel",
    "RetentionConfig",
    "RetentionPolicy",
    "ComplianceConfig",
    "FrameworkConfig",
    "ComplianceFramework",
    "ComplianceEnforcement",
    "DataQualityConfig",
    "DataQualityCheck",
    # Compute (legacy)
    "ComputeTarget",
    "ComputeConfig",
    # Transforms
    "TransformConfig",
    # Consumption
    "CubeStoreConfig",
    "ExportBucketConfig",
    "PreAggregationConfig",
    "CubeSecurityConfig",
    "ConsumptionConfig",
    # Governance (legacy)
    "ColumnClassification",
    "GovernanceConfig",
    # Observability (extended in v1.1.0)
    "ObservabilityConfig",
    "TracingConfig",
    "TraceSamplingConfig",
    "SamplingType",
    "TraceExportersConfig",
    "MetricsConfig",
    "MetricsExportersConfig",
    "MetricsAlertingConfig",
    "AlertRule",
    "AlertSeverity",
    "LoggingConfig",
    "LoggingBackendsConfig",
    "LogLevel",
    "LogFormat",
    # Catalog (legacy)
    "CatalogConfig",
    # Orchestration (Feature 010)
    "OrchestrationConfig",
    "DbtConfig",
    "ObservabilityLevel",
    "PartitionDefinition",
    "TimeWindowPartition",
    "StaticPartition",
    "MultiPartition",
    "DynamicPartition",
    "JobDefinition",
    "BatchJob",
    "OpsJob",
    "ScheduleDefinition",
    "SensorDefinition",
    "FileWatcherSensor",
    "AssetSensor",
    "RunStatusSensor",
    "CustomSensor",
    "AssetConfig",
    "BackfillDefinition",
]
