"""Unit tests for enterprise configuration models (v1.1.0).

This module tests:
- InfrastructureConfig: Network, DNS, cloud configuration
- SecurityConfig: Authentication, authorization, secrets
- EnterpriseGovernanceConfig: Classification, retention, compliance
- Extended ObservabilityConfig: Tracing, metrics, logging

Covers: 009-US2 (Enterprise Platform Configuration)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

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
from floe_core.schemas.platform_spec import (
    PLATFORM_SPEC_VERSION,
    PlatformSpec,
)
from floe_core.schemas.security_config import (
    AtRestEncryption,
    AuditBackend,
    AuditConfig,
    AuditEventsConfig,
    AuthenticationConfig,
    AuthMethod,
    AuthorizationConfig,
    AuthorizationMode,
    EncryptionConfig,
    EncryptionProvider,
    InTransitEncryption,
    OidcConfig,
    RoleDefinition,
    SecretBackendsConfig,
    SecretBackendType,
    SecurityConfig,
    VaultAuthMethod,
    VaultSecretBackend,
)


class TestPlatformSpecVersion:
    """Tests for platform spec version."""

    def test_platform_spec_version_is_1_1_0(self) -> None:
        """Platform spec version is 1.1.0 for enterprise features."""
        assert PLATFORM_SPEC_VERSION == "1.1.0"


# =============================================================================
# Infrastructure Configuration Tests
# =============================================================================


class TestDnsConfig:
    """Tests for DNS configuration."""

    def test_default_dns_config(self) -> None:
        """Default DNS config uses Kubernetes strategy."""
        dns = DnsConfig()
        assert dns.strategy == DnsStrategy.KUBERNETES
        assert dns.internal_domain is None
        assert dns.external_domain is None

    def test_dns_with_domains(self) -> None:
        """DNS config accepts domain names."""
        dns = DnsConfig(
            internal_domain="floe.internal",
            external_domain="data.company.com",
            strategy=DnsStrategy.ROUTE53,
        )
        assert dns.internal_domain == "floe.internal"
        assert dns.external_domain == "data.company.com"
        assert dns.strategy == DnsStrategy.ROUTE53

    def test_dns_invalid_domain_rejected(self) -> None:
        """Invalid domain names are rejected."""
        with pytest.raises(ValidationError):
            DnsConfig(internal_domain="-invalid-domain")


class TestNetworkPoliciesConfig:
    """Tests for network policies configuration."""

    def test_default_network_policies(self) -> None:
        """Default network policies are disabled."""
        policies = NetworkPoliciesConfig()
        assert policies.enabled is False
        assert policies.default_rule == NetworkPolicyRule.ALLOW_ALL

    def test_network_policies_with_zones(self) -> None:
        """Network policies accept zone definitions."""
        policies = NetworkPoliciesConfig(
            enabled=True,
            default_rule=NetworkPolicyRule.DENY_ALL,
            zones={
                "data_plane": NetworkZone(
                    description="Data plane components",
                    allowed_egress=["s3_endpoints"],
                ),
            },
        )
        assert policies.enabled is True
        assert policies.default_rule == NetworkPolicyRule.DENY_ALL
        assert "data_plane" in policies.zones


class TestIngressConfig:
    """Tests for ingress configuration."""

    def test_default_ingress_config(self) -> None:
        """Default ingress config is disabled."""
        ingress = IngressConfig()
        assert ingress.enabled is False
        assert ingress.ingress_class == IngressClass.NGINX

    def test_ingress_with_routes(self) -> None:
        """Ingress config accepts routes."""
        ingress = IngressConfig(
            enabled=True,
            ingress_class=IngressClass.ALB,
            tls=TlsConfig(enabled=True, provider=TlsProvider.ACM),
            routes={
                "dagster": IngressRoute(
                    host="dagster.data.company.com",
                    service="dagster-webserver",
                    port=3000,
                ),
            },
        )
        assert ingress.enabled is True
        assert ingress.ingress_class == IngressClass.ALB
        assert "dagster" in ingress.routes


class TestLocalAccessConfig:
    """Tests for local access configuration."""

    def test_default_local_access(self) -> None:
        """Default local access is disabled."""
        local = LocalAccessConfig()
        assert local.enabled is False
        assert local.access_type == LocalAccessType.NODEPORT

    def test_local_access_with_custom_ports(self) -> None:
        """Local access accepts custom port mappings."""
        local = LocalAccessConfig(
            enabled=True,
            access_type=LocalAccessType.NODEPORT,
            ports=LocalAccessPorts(
                dagster=30000,
                polaris=30181,
                jaeger=30686,
            ),
        )
        assert local.enabled is True
        assert local.ports.dagster == 30000
        assert local.ports.polaris == 30181

    def test_local_access_port_range_validation(self) -> None:
        """Port numbers must be in NodePort range (30000-32767)."""
        with pytest.raises(ValidationError):
            LocalAccessPorts(dagster=8080)  # Below range

        with pytest.raises(ValidationError):
            LocalAccessPorts(dagster=40000)  # Above range


class TestCloudConfig:
    """Tests for cloud configuration."""

    def test_default_cloud_config(self) -> None:
        """Default cloud config is local provider."""
        cloud = CloudConfig()
        assert cloud.provider == CloudProvider.LOCAL

    def test_aws_cloud_config(self) -> None:
        """AWS cloud config requires region."""
        cloud = CloudConfig(
            provider=CloudProvider.AWS,
            region="us-east-1",
            aws=AwsConfig(account_id="123456789012"),
        )
        assert cloud.provider == CloudProvider.AWS
        assert cloud.region == "us-east-1"
        assert cloud.aws.account_id == "123456789012"

    def test_aws_without_region_fails(self) -> None:
        """AWS provider without region fails validation."""
        with pytest.raises(ValidationError):
            CloudConfig(
                provider=CloudProvider.AWS,
                # Missing region
            )

    def test_localstack_config(self) -> None:
        """LocalStack configuration."""
        cloud = CloudConfig(
            provider=CloudProvider.LOCAL,
            localstack=LocalStackConfig(
                enabled=True,
                endpoint="http://localstack:4566",
                services=["s3", "sts", "iam"],
            ),
        )
        assert cloud.localstack.enabled is True
        assert cloud.localstack.endpoint == "http://localstack:4566"


class TestInfrastructureConfig:
    """Tests for infrastructure configuration root."""

    def test_default_infrastructure_config(self) -> None:
        """Default infrastructure config."""
        infra = InfrastructureConfig()
        assert infra.network is not None
        assert infra.cloud is not None

    def test_complete_infrastructure_config(self) -> None:
        """Complete infrastructure configuration."""
        infra = InfrastructureConfig(
            network=NetworkConfig(
                enabled=True,
                dns=DnsConfig(internal_domain="floe.local"),
                local_access=LocalAccessConfig(enabled=True),
            ),
            cloud=CloudConfig(
                provider=CloudProvider.LOCAL,
                localstack=LocalStackConfig(enabled=True),
            ),
        )
        assert infra.network.enabled is True
        assert infra.network.local_access.enabled is True
        assert infra.cloud.provider == CloudProvider.LOCAL


# =============================================================================
# Security Configuration Tests
# =============================================================================


class TestAuthenticationConfig:
    """Tests for authentication configuration."""

    def test_default_authentication(self) -> None:
        """Default authentication is disabled."""
        auth = AuthenticationConfig()
        assert auth.enabled is False
        assert auth.method == AuthMethod.STATIC

    def test_oidc_authentication(self) -> None:
        """OIDC authentication configuration."""
        auth = AuthenticationConfig(
            enabled=True,
            method=AuthMethod.OIDC,
            oidc=OidcConfig(
                provider_url="https://auth.company.com",
                client_id="floe-platform",
                scopes=["openid", "profile", "email", "groups"],
            ),
        )
        assert auth.enabled is True
        assert auth.method == AuthMethod.OIDC
        assert auth.oidc is not None
        assert auth.oidc.provider_url == "https://auth.company.com"

    def test_oidc_without_config_fails(self) -> None:
        """OIDC method without config fails validation."""
        with pytest.raises(ValidationError):
            AuthenticationConfig(
                enabled=True,
                method=AuthMethod.OIDC,
                # Missing oidc config
            )


class TestAuthorizationConfig:
    """Tests for authorization configuration."""

    def test_default_authorization(self) -> None:
        """Default authorization is disabled."""
        authz = AuthorizationConfig()
        assert authz.enabled is False
        assert authz.mode == AuthorizationMode.RBAC

    def test_rbac_authorization(self) -> None:
        """RBAC authorization with roles."""
        authz = AuthorizationConfig(
            enabled=True,
            mode=AuthorizationMode.RBAC,
            roles={
                "platform_admin": RoleDefinition(
                    description="Full platform access",
                    permissions=["platform:*", "security:*"],
                ),
                "data_engineer": RoleDefinition(
                    description="Data engineering operations",
                    permissions=["pipelines:read,write,execute"],
                ),
            },
            group_mappings={
                "platform-admins@company.com": "platform_admin",
                "data-engineering@company.com": "data_engineer",
            },
        )
        assert authz.enabled is True
        assert "platform_admin" in authz.roles
        assert "data_engineer" in authz.roles
        assert len(authz.group_mappings) == 2


class TestSecretBackendsConfig:
    """Tests for secret backends configuration."""

    def test_default_secret_backends(self) -> None:
        """Default secret backend is Kubernetes."""
        secrets = SecretBackendsConfig()
        assert secrets.primary == SecretBackendType.KUBERNETES
        assert secrets.kubernetes.enabled is True

    def test_vault_secret_backend(self) -> None:
        """Vault secret backend configuration."""
        secrets = SecretBackendsConfig(
            primary=SecretBackendType.VAULT,
            vault=VaultSecretBackend(
                enabled=True,
                server_url="https://vault.internal:8200",
                auth_method=VaultAuthMethod.KUBERNETES,
                kubernetes_role="floe-runtime",
            ),
        )
        assert secrets.primary == SecretBackendType.VAULT
        assert secrets.vault.enabled is True
        assert secrets.vault.server_url == "https://vault.internal:8200"

    def test_vault_without_server_url_fails(self) -> None:
        """Vault enabled without server_url fails validation."""
        with pytest.raises(ValidationError):
            VaultSecretBackend(
                enabled=True,
                # Missing server_url
            )

    def test_vault_kubernetes_auth_without_role_fails(self) -> None:
        """Vault Kubernetes auth without role fails validation."""
        with pytest.raises(ValidationError):
            VaultSecretBackend(
                enabled=True,
                server_url="https://vault.internal:8200",
                auth_method=VaultAuthMethod.KUBERNETES,
                # Missing kubernetes_role
            )


class TestEncryptionConfig:
    """Tests for encryption configuration."""

    def test_default_encryption(self) -> None:
        """Default encryption has in-transit enabled."""
        encryption = EncryptionConfig()
        assert encryption.in_transit.enabled is True
        assert encryption.at_rest.enabled is False

    def test_full_encryption(self) -> None:
        """Full encryption configuration."""
        encryption = EncryptionConfig(
            in_transit=InTransitEncryption(
                enabled=True,
                min_tls_version="1.3",
            ),
            at_rest=AtRestEncryption(
                enabled=True,
                provider=EncryptionProvider.AWS_KMS,
            ),
        )
        assert encryption.in_transit.min_tls_version == "1.3"
        assert encryption.at_rest.provider == EncryptionProvider.AWS_KMS


class TestAuditConfig:
    """Tests for audit configuration."""

    def test_default_audit(self) -> None:
        """Default audit is disabled."""
        audit = AuditConfig()
        assert audit.enabled is False

    def test_full_audit(self) -> None:
        """Full audit configuration."""
        audit = AuditConfig(
            enabled=True,
            events=AuditEventsConfig(
                authentication=True,
                authorization=True,
                data_access=True,
                configuration_changes=True,
            ),
            backend=AuditBackend.CLOUDWATCH,
            retention_days=90,
        )
        assert audit.enabled is True
        assert audit.events.authentication is True
        assert audit.backend == AuditBackend.CLOUDWATCH


class TestSecurityConfig:
    """Tests for security configuration root."""

    def test_default_security_config(self) -> None:
        """Default security config."""
        security = SecurityConfig()
        assert security.authentication is not None
        assert security.authorization is not None
        assert security.secret_backends is not None

    def test_complete_security_config(self) -> None:
        """Complete security configuration."""
        security = SecurityConfig(
            authentication=AuthenticationConfig(enabled=True, method=AuthMethod.STATIC),
            authorization=AuthorizationConfig(enabled=True),
            secret_backends=SecretBackendsConfig(),
            encryption=EncryptionConfig(),
            audit=AuditConfig(enabled=True),
        )
        assert security.authentication.enabled is True
        assert security.authorization.enabled is True
        assert security.audit.enabled is True


# =============================================================================
# Governance Configuration Tests
# =============================================================================


class TestClassificationsConfig:
    """Tests for classifications configuration."""

    def test_default_classifications(self) -> None:
        """Default classifications is disabled."""
        classifications = ClassificationsConfig()
        assert classifications.enabled is False
        assert classifications.classes == {}

    def test_classifications_with_classes(self) -> None:
        """Classifications with custom classes."""
        classifications = ClassificationsConfig(
            enabled=True,
            classes={
                "pii": ClassificationClass(
                    sensitivity=SensitivityLevel.CRITICAL,
                    encryption_required=True,
                    masking_required=True,
                    compliance_required=[
                        ComplianceFramework.GDPR,
                        ComplianceFramework.CCPA,
                    ],
                ),
            },
        )
        assert classifications.enabled is True
        assert "pii" in classifications.classes
        pii = classifications.classes["pii"]
        assert pii.sensitivity == SensitivityLevel.CRITICAL
        assert pii.masking_required is True

    def test_with_defaults_factory(self) -> None:
        """ClassificationsConfig.with_defaults() creates standard classes."""
        classifications = ClassificationsConfig.with_defaults()
        assert classifications.enabled is True
        assert "public" in classifications.classes
        assert "internal" in classifications.classes
        assert "confidential" in classifications.classes
        assert "pii" in classifications.classes


class TestRetentionConfig:
    """Tests for retention configuration."""

    def test_default_retention(self) -> None:
        """Default retention is disabled."""
        retention = RetentionConfig()
        assert retention.enabled is False
        assert retention.default_policy.retention_days == 730

    def test_retention_with_policies(self) -> None:
        """Retention with custom policies."""
        retention = RetentionConfig(
            enabled=True,
            default_policy=RetentionPolicy(
                retention_days=365,
                archive_after_days=90,
            ),
            policies={
                "short_term": RetentionPolicy(retention_days=30),
            },
        )
        assert retention.enabled is True
        assert retention.default_policy.retention_days == 365
        assert "short_term" in retention.policies


class TestComplianceConfig:
    """Tests for compliance configuration."""

    def test_default_compliance(self) -> None:
        """Default compliance is disabled."""
        compliance = ComplianceConfig()
        assert compliance.enabled is False

    def test_compliance_with_frameworks(self) -> None:
        """Compliance with frameworks."""
        compliance = ComplianceConfig(
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
        )
        assert compliance.enabled is True
        assert compliance.frameworks["gdpr"].enabled is True
        assert compliance.frameworks["gdpr"].enforcement == ComplianceEnforcement.STRICT


class TestDataQualityConfig:
    """Tests for data quality configuration."""

    def test_default_data_quality(self) -> None:
        """Default data quality is disabled."""
        quality = DataQualityConfig()
        assert quality.enabled is False
        assert DataQualityCheck.SCHEMA_VALIDATION in quality.default_checks

    def test_data_quality_enabled(self) -> None:
        """Data quality enabled with fail on error."""
        quality = DataQualityConfig(
            enabled=True,
            fail_on_error=True,
            default_checks=[
                DataQualityCheck.SCHEMA_VALIDATION,
                DataQualityCheck.NULL_PERCENTAGE,
                DataQualityCheck.UNIQUE_CONSTRAINTS,
            ],
        )
        assert quality.enabled is True
        assert quality.fail_on_error is True
        assert len(quality.default_checks) == 3


class TestEnterpriseGovernanceConfig:
    """Tests for enterprise governance configuration root."""

    def test_default_governance_config(self) -> None:
        """Default governance config."""
        governance = EnterpriseGovernanceConfig()
        assert governance.classifications is not None
        assert governance.retention is not None
        assert governance.compliance is not None
        assert governance.data_quality is not None

    def test_for_local_dev_factory(self) -> None:
        """for_local_dev() creates minimal config."""
        governance = EnterpriseGovernanceConfig.for_local_dev()
        assert governance.classifications.enabled is False
        assert governance.retention.enabled is False
        assert governance.compliance.enabled is False
        assert governance.data_quality.enabled is False

    def test_for_production_factory(self) -> None:
        """for_production() creates full enterprise config."""
        governance = EnterpriseGovernanceConfig.for_production()
        assert governance.classifications.enabled is True
        assert governance.retention.enabled is True
        assert governance.compliance.enabled is True
        assert governance.data_quality.enabled is True


# =============================================================================
# Extended Observability Tests
# =============================================================================


class TestTracingConfig:
    """Tests for extended tracing configuration."""

    def test_default_tracing(self) -> None:
        """Default tracing samples all traces."""
        tracing = TracingConfig()
        assert tracing.sampling.sampling_type == SamplingType.ALWAYS_ON
        assert tracing.sampling.probability == 1.0

    def test_probabilistic_sampling(self) -> None:
        """Probabilistic sampling configuration."""
        tracing = TracingConfig(
            sampling=TraceSamplingConfig(
                sampling_type=SamplingType.PROBABILISTIC,
                probability=0.1,
            ),
            exporters=TraceExportersConfig(
                jaeger=True,
                xray=True,
            ),
        )
        assert tracing.sampling.sampling_type == SamplingType.PROBABILISTIC
        assert tracing.sampling.probability == 0.1
        assert tracing.exporters.xray is True


class TestMetricsConfig:
    """Tests for extended metrics configuration."""

    def test_default_metrics(self) -> None:
        """Default metrics configuration."""
        metrics = MetricsConfig()
        assert metrics.scrape_interval == "15s"
        assert metrics.exporters.prometheus is True

    def test_metrics_with_alerting(self) -> None:
        """Metrics with alerting configuration."""
        metrics = MetricsConfig(
            scrape_interval="30s",
            retention_days=30,
            exporters=MetricsExportersConfig(
                prometheus=True,
                cloudwatch=True,
            ),
            alerting=MetricsAlertingConfig(
                enabled=True,
                rules={
                    "pipeline_failure": AlertRule(
                        severity=AlertSeverity.CRITICAL,
                        notify=["slack", "pagerduty"],
                    ),
                },
            ),
        )
        assert metrics.scrape_interval == "30s"
        assert metrics.alerting.enabled is True
        assert "pipeline_failure" in metrics.alerting.rules


class TestLoggingConfig:
    """Tests for extended logging configuration."""

    def test_default_logging(self) -> None:
        """Default logging configuration."""
        logging_config = LoggingConfig()
        assert logging_config.level == LogLevel.INFO
        assert logging_config.log_format == LogFormat.JSON

    def test_logging_with_backends(self) -> None:
        """Logging with multiple backends."""
        logging_config = LoggingConfig(
            level=LogLevel.DEBUG,
            log_format=LogFormat.JSON,
            backends=LoggingBackendsConfig(
                loki=True,
                cloudwatch=True,
            ),
        )
        assert logging_config.level == LogLevel.DEBUG
        assert logging_config.backends.loki is True
        assert logging_config.backends.cloudwatch is True


class TestExtendedObservabilityConfig:
    """Tests for extended observability configuration."""

    def test_backward_compatible(self) -> None:
        """v1.0.0 observability config still works."""
        obs = ObservabilityConfig(
            traces=True,
            metrics=True,
            lineage=True,
            otlp_endpoint="http://jaeger:4317",
            lineage_endpoint="http://marquez:5000",
        )
        assert obs.traces is True
        assert obs.otlp_endpoint == "http://jaeger:4317"

    def test_extended_config(self) -> None:
        """v1.1.0 extended observability config."""
        obs = ObservabilityConfig(
            traces=True,
            otlp_endpoint="http://jaeger:4317",
            tracing=TracingConfig(
                sampling=TraceSamplingConfig(probability=0.1),
            ),
            metrics_config=MetricsConfig(
                exporters=MetricsExportersConfig(prometheus=True),
            ),
            logging=LoggingConfig(
                level=LogLevel.INFO,
            ),
        )
        assert obs.tracing is not None
        assert obs.tracing.sampling.probability == 0.1
        assert obs.metrics_config is not None
        assert obs.logging is not None


# =============================================================================
# PlatformSpec v1.1.0 Integration Tests
# =============================================================================


class TestPlatformSpecV110:
    """Tests for PlatformSpec v1.1.0 with enterprise features."""

    def test_platform_spec_with_infrastructure(self) -> None:
        """PlatformSpec accepts infrastructure config."""
        spec = PlatformSpec(
            version="1.1.0",
            infrastructure=InfrastructureConfig(
                network=NetworkConfig(
                    local_access=LocalAccessConfig(enabled=True),
                ),
            ),
        )
        assert spec.infrastructure is not None
        assert spec.infrastructure.network.local_access.enabled is True

    def test_platform_spec_with_security(self) -> None:
        """PlatformSpec accepts security config."""
        spec = PlatformSpec(
            version="1.1.0",
            security=SecurityConfig(
                authentication=AuthenticationConfig(enabled=False),
                secret_backends=SecretBackendsConfig(
                    primary=SecretBackendType.KUBERNETES,
                ),
            ),
        )
        assert spec.security is not None
        assert spec.security.secret_backends.primary == SecretBackendType.KUBERNETES

    def test_platform_spec_with_governance(self) -> None:
        """PlatformSpec accepts governance config."""
        spec = PlatformSpec(
            version="1.1.0",
            governance=EnterpriseGovernanceConfig.for_local_dev(),
        )
        assert spec.governance is not None
        assert spec.governance.classifications.enabled is False

    def test_platform_spec_backward_compatible(self) -> None:
        """v1.0.0 configs still work (enterprise sections optional)."""
        spec = PlatformSpec(
            version="1.0.0",
            # No infrastructure, security, or governance
        )
        assert spec.infrastructure is None
        assert spec.security is None
        assert spec.governance is None

    def test_complete_v110_from_yaml(self) -> None:
        """Complete v1.1.0 config loads from YAML."""
        yaml_content = """
version: "1.1.0"

infrastructure:
  network:
    enabled: true
    local_access:
      enabled: true
      access_type: nodeport
      ports:
        dagster: 30000
        polaris: 30181
  cloud:
    provider: local

security:
  authentication:
    enabled: false
    method: static
  secret_backends:
    primary: kubernetes

governance:
  classifications:
    enabled: false
  compliance:
    enabled: false

storage:
  default:
    type: s3
    bucket: iceberg-data

catalogs:
  default:
    type: polaris
    uri: http://polaris:8181/api/catalog
    warehouse: demo

observability:
  traces: true
  otlp_endpoint: http://jaeger:4317
  tracing:
    sampling:
      sampling_type: always_on
      probability: 1.0
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            spec = PlatformSpec.from_yaml(Path(f.name))

        assert spec.version == "1.1.0"
        assert spec.infrastructure is not None
        assert spec.infrastructure.network.local_access.enabled is True
        assert spec.infrastructure.network.local_access.ports.dagster == 30000
        assert spec.security is not None
        assert spec.security.authentication.method == AuthMethod.STATIC
        assert spec.governance is not None
        assert spec.observability is not None
        assert spec.observability.tracing is not None
        assert spec.observability.tracing.sampling.sampling_type == SamplingType.ALWAYS_ON
