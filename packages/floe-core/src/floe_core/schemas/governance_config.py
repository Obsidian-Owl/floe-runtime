"""Enterprise governance configuration models for floe-runtime.

This module defines enterprise governance configuration including:
- Data classification: Classes with sensitivity levels and requirements
- Retention policies: Time-based data lifecycle management
- Compliance frameworks: GDPR, SOC2, HIPAA enforcement
- Data quality: Default quality checks and thresholds

Note: This extends the existing governance.py (column-level classification)
with enterprise-level policies.

Covers: 009-US2 (Enterprise Governance Layer)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SensitivityLevel(str, Enum):
    """Data sensitivity levels.

    Values:
        LOW: Public or non-sensitive data.
        MEDIUM: Internal use only.
        HIGH: Confidential data.
        CRITICAL: Highly sensitive (PII, financial).
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceEnforcement(str, Enum):
    """Compliance enforcement level.

    Values:
        STRICT: Block operations that violate compliance.
        MODERATE: Warn but allow operations.
        PERMISSIVE: Log violations only.
    """

    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks.

    Values:
        GDPR: EU General Data Protection Regulation.
        CCPA: California Consumer Privacy Act.
        SOC2: Service Organization Control 2.
        HIPAA: Health Insurance Portability and Accountability Act.
        PCI_DSS: Payment Card Industry Data Security Standard.
    """

    GDPR = "gdpr"
    CCPA = "ccpa"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"


class DataQualityCheck(str, Enum):
    """Built-in data quality check types.

    Values:
        SCHEMA_VALIDATION: Validate data against schema.
        NULL_PERCENTAGE: Check null percentage thresholds.
        UNIQUE_CONSTRAINTS: Validate uniqueness constraints.
        REFERENTIAL_INTEGRITY: Check foreign key relationships.
        VALUE_RANGES: Validate value ranges.
        FRESHNESS: Check data freshness/staleness.
    """

    SCHEMA_VALIDATION = "schema_validation"
    NULL_PERCENTAGE = "null_percentage"
    UNIQUE_CONSTRAINTS = "unique_constraints"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    VALUE_RANGES = "value_ranges"
    FRESHNESS = "freshness"


# =============================================================================
# Data Classification
# =============================================================================


class ClassificationClass(BaseModel):
    """Data classification class definition.

    Defines requirements and constraints for a classification level.

    Attributes:
        sensitivity: Sensitivity level.
        encryption_required: Require encryption for this class.
        retention_days: Default retention period in days.
        require_approval: Require approval for access.
        compliance_required: Compliance frameworks that apply.
        masking_required: Require data masking for display.

    Example:
        >>> pii_class = ClassificationClass(
        ...     sensitivity=SensitivityLevel.CRITICAL,
        ...     encryption_required=True,
        ...     retention_days=365,
        ...     compliance_required=[ComplianceFramework.GDPR, ComplianceFramework.CCPA],
        ...     masking_required=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sensitivity: SensitivityLevel = Field(
        default=SensitivityLevel.MEDIUM,
        description="Data sensitivity level",
    )
    encryption_required: bool = Field(
        default=False,
        description="Require encryption for this class",
    )
    retention_days: int | None = Field(
        default=None,
        ge=1,
        le=36500,
        description="Default retention period in days",
    )
    require_approval: bool = Field(
        default=False,
        description="Require approval for access",
    )
    compliance_required: list[ComplianceFramework] = Field(
        default_factory=list,
        description="Compliance frameworks that apply",
    )
    masking_required: bool = Field(
        default=False,
        description="Require data masking for display",
    )


class ClassificationsConfig(BaseModel):
    """Data classification configuration.

    Attributes:
        enabled: Enable classification enforcement.
        classes: Named classification classes.

    Example:
        >>> classifications = ClassificationsConfig(
        ...     enabled=True,
        ...     classes={
        ...         "public": ClassificationClass(
        ...             sensitivity=SensitivityLevel.LOW,
        ...         ),
        ...         "pii": ClassificationClass(
        ...             sensitivity=SensitivityLevel.CRITICAL,
        ...             encryption_required=True,
        ...             masking_required=True,
        ...         ),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable classification enforcement",
    )
    classes: dict[str, ClassificationClass] = Field(
        default_factory=dict,
        description="Named classification classes",
    )

    @classmethod
    def with_defaults(cls) -> ClassificationsConfig:
        """Create ClassificationsConfig with default enterprise classes.

        Returns:
            ClassificationsConfig with public, internal, confidential, and pii classes.
        """
        return cls(
            enabled=True,
            classes={
                "public": ClassificationClass(
                    sensitivity=SensitivityLevel.LOW,
                    encryption_required=False,
                    retention_days=365,
                ),
                "internal": ClassificationClass(
                    sensitivity=SensitivityLevel.MEDIUM,
                    encryption_required=True,
                    retention_days=730,
                ),
                "confidential": ClassificationClass(
                    sensitivity=SensitivityLevel.HIGH,
                    encryption_required=True,
                    require_approval=True,
                    retention_days=365,
                ),
                "pii": ClassificationClass(
                    sensitivity=SensitivityLevel.CRITICAL,
                    encryption_required=True,
                    retention_days=365,
                    compliance_required=[ComplianceFramework.GDPR, ComplianceFramework.CCPA],
                    masking_required=True,
                ),
            },
        )


# =============================================================================
# Retention Policies
# =============================================================================


class RetentionPolicy(BaseModel):
    """Data retention policy configuration.

    Attributes:
        retention_days: Days to retain data before deletion.
        archive_after_days: Days before archiving to cold storage.

    Example:
        >>> policy = RetentionPolicy(
        ...     retention_days=730,
        ...     archive_after_days=365,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    retention_days: int = Field(
        default=730,
        ge=1,
        le=36500,
        description="Days to retain data",
    )
    archive_after_days: int | None = Field(
        default=None,
        ge=1,
        le=36500,
        description="Days before archiving to cold storage",
    )


class RetentionConfig(BaseModel):
    """Retention policies configuration.

    Attributes:
        enabled: Enable retention policy enforcement.
        default_policy: Default retention policy.
        policies: Named retention policies (override defaults).

    Example:
        >>> retention = RetentionConfig(
        ...     enabled=True,
        ...     default_policy=RetentionPolicy(retention_days=730),
        ...     policies={
        ...         "short_term": RetentionPolicy(retention_days=90),
        ...         "long_term": RetentionPolicy(retention_days=2555),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable retention policy enforcement",
    )
    default_policy: RetentionPolicy = Field(
        default_factory=RetentionPolicy,
        description="Default retention policy",
    )
    policies: dict[str, RetentionPolicy] = Field(
        default_factory=dict,
        description="Named retention policies",
    )


# =============================================================================
# Compliance Frameworks
# =============================================================================


class FrameworkConfig(BaseModel):
    """Individual compliance framework configuration.

    Attributes:
        enabled: Enable this compliance framework.
        enforcement: Enforcement level.

    Example:
        >>> gdpr = FrameworkConfig(
        ...     enabled=True,
        ...     enforcement=ComplianceEnforcement.STRICT,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable this compliance framework",
    )
    enforcement: ComplianceEnforcement = Field(
        default=ComplianceEnforcement.MODERATE,
        description="Enforcement level",
    )


class ComplianceConfig(BaseModel):
    """Compliance frameworks configuration.

    Attributes:
        enabled: Enable compliance enforcement.
        frameworks: Individual framework configurations.

    Example:
        >>> compliance = ComplianceConfig(
        ...     enabled=True,
        ...     frameworks={
        ...         "gdpr": FrameworkConfig(enabled=True, enforcement=ComplianceEnforcement.STRICT),
        ...         "soc2": FrameworkConfig(enabled=True),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable compliance enforcement",
    )
    frameworks: dict[str, FrameworkConfig] = Field(
        default_factory=dict,
        description="Framework configurations",
    )


# =============================================================================
# Data Quality
# =============================================================================


class DataQualityConfig(BaseModel):
    """Data quality configuration.

    Attributes:
        enabled: Enable data quality checks.
        default_checks: Default quality checks to run.
        fail_on_error: Fail pipeline on quality check failure.

    Example:
        >>> quality = DataQualityConfig(
        ...     enabled=True,
        ...     default_checks=[
        ...         DataQualityCheck.SCHEMA_VALIDATION,
        ...         DataQualityCheck.NULL_PERCENTAGE,
        ...     ],
        ...     fail_on_error=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable data quality checks",
    )
    default_checks: list[DataQualityCheck] = Field(
        default_factory=lambda: [
            DataQualityCheck.SCHEMA_VALIDATION,
            DataQualityCheck.NULL_PERCENTAGE,
        ],
        description="Default quality checks to run",
    )
    fail_on_error: bool = Field(
        default=False,
        description="Fail pipeline on quality check failure",
    )


# =============================================================================
# Enterprise Governance Configuration (Root)
# =============================================================================


class EnterpriseGovernanceConfig(BaseModel):
    """Enterprise governance configuration.

    Combines data classification, retention policies, compliance frameworks,
    and data quality for enterprise data governance.

    Attributes:
        classifications: Data classification configuration.
        retention: Retention policy configuration.
        compliance: Compliance framework configuration.
        data_quality: Data quality configuration.

    Example:
        >>> governance = EnterpriseGovernanceConfig(
        ...     classifications=ClassificationsConfig(enabled=True),
        ...     retention=RetentionConfig(enabled=True),
        ...     compliance=ComplianceConfig(
        ...         enabled=True,
        ...         frameworks={
        ...             "gdpr": FrameworkConfig(enabled=True),
        ...         },
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    classifications: ClassificationsConfig = Field(
        default_factory=ClassificationsConfig,
        description="Data classification configuration",
    )
    retention: RetentionConfig = Field(
        default_factory=RetentionConfig,
        description="Retention policy configuration",
    )
    compliance: ComplianceConfig = Field(
        default_factory=ComplianceConfig,
        description="Compliance framework configuration",
    )
    data_quality: DataQualityConfig = Field(
        default_factory=DataQualityConfig,
        description="Data quality configuration",
    )

    @classmethod
    def for_local_dev(cls) -> EnterpriseGovernanceConfig:
        """Create minimal governance config for local development.

        Returns:
            EnterpriseGovernanceConfig with minimal/disabled settings.
        """
        return cls(
            classifications=ClassificationsConfig(enabled=False),
            retention=RetentionConfig(enabled=False),
            compliance=ComplianceConfig(enabled=False),
            data_quality=DataQualityConfig(enabled=False),
        )

    @classmethod
    def for_production(cls) -> EnterpriseGovernanceConfig:
        """Create full governance config for production.

        Returns:
            EnterpriseGovernanceConfig with enterprise defaults.
        """
        return cls(
            classifications=ClassificationsConfig.with_defaults(),
            retention=RetentionConfig(
                enabled=True,
                default_policy=RetentionPolicy(retention_days=730, archive_after_days=365),
            ),
            compliance=ComplianceConfig(
                enabled=True,
                frameworks={
                    "gdpr": FrameworkConfig(
                        enabled=True,
                        enforcement=ComplianceEnforcement.STRICT,
                    ),
                    "soc2": FrameworkConfig(
                        enabled=True,
                        enforcement=ComplianceEnforcement.MODERATE,
                    ),
                },
            ),
            data_quality=DataQualityConfig(
                enabled=True,
                fail_on_error=True,
            ),
        )
