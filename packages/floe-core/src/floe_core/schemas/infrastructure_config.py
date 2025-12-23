"""Infrastructure configuration models for floe-runtime.

This module defines infrastructure configuration including:
- Network: DNS, network policies, ingress, local access
- Cloud: Provider configuration (AWS, GCP, Azure, Local)
- LocalStack: Local development emulation

Covers: 009-US2 (Enterprise Infrastructure Layer)
"""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Pattern for valid DNS domain names
DNS_DOMAIN_PATTERN = (
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$"
)

# Pattern for AWS ARN
AWS_ARN_PATTERN = r"^arn:aws:[a-zA-Z0-9-]+:[a-z0-9-]*:\d{12}:[a-zA-Z0-9-/]+$"

# Pattern for AWS IAM role ARN
AWS_IAM_ROLE_PATTERN = r"^arn:aws:iam::\d{12}:role/[\w+=,.@-]+$"

# Pattern for AWS KMS key ARN
AWS_KMS_KEY_PATTERN = r"^arn:aws:kms:[a-z0-9-]+:\d{12}:key/[a-f0-9-]+$"


class DnsStrategy(str, Enum):
    """DNS and service discovery strategy.

    Values:
        KUBERNETES: Use Kubernetes CoreDNS (default for K8s).
        CONSUL: Use HashiCorp Consul for service mesh.
        ROUTE53: Use AWS Route 53 for DNS.
    """

    KUBERNETES = "kubernetes"
    CONSUL = "consul"
    ROUTE53 = "route53"


class IngressClass(str, Enum):
    """Kubernetes ingress controller class.

    Values:
        NGINX: NGINX Ingress Controller.
        TRAEFIK: Traefik Ingress Controller.
        ALB: AWS Application Load Balancer.
        GCE: Google Cloud Load Balancer.
    """

    NGINX = "nginx"
    TRAEFIK = "traefik"
    ALB = "alb"
    GCE = "gce"


class TlsProvider(str, Enum):
    """TLS certificate provider.

    Values:
        CERT_MANAGER: cert-manager for K8s (Let's Encrypt, etc.).
        ACM: AWS Certificate Manager.
        MANUAL: Manual certificate management.
    """

    CERT_MANAGER = "cert-manager"
    ACM = "acm"
    MANUAL = "manual"


class NetworkPolicyRule(str, Enum):
    """Default network policy rule.

    Values:
        DENY_ALL: Deny all traffic by default (zero-trust).
        ALLOW_ALL: Allow all traffic by default.
    """

    DENY_ALL = "deny-all"
    ALLOW_ALL = "allow-all"


class LocalAccessType(str, Enum):
    """External access type for local development.

    Values:
        NODEPORT: K8s NodePort services (resilient to pod restarts).
        PORT_FORWARD: kubectl port-forward (ephemeral).
        LOADBALANCER: LoadBalancer services (requires cloud/MetalLB).
    """

    NODEPORT = "nodeport"
    PORT_FORWARD = "port-forward"
    LOADBALANCER = "loadbalancer"


class CloudProvider(str, Enum):
    """Cloud provider type.

    Values:
        AWS: Amazon Web Services.
        GCP: Google Cloud Platform.
        AZURE: Microsoft Azure.
        LOCAL: Local development (LocalStack, MinIO).
    """

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LOCAL = "local"


# =============================================================================
# DNS Configuration
# =============================================================================


class DnsConfig(BaseModel):
    """DNS and service discovery configuration.

    Attributes:
        internal_domain: Internal cluster DNS domain.
        external_domain: Public/external DNS domain.
        strategy: DNS resolution strategy.

    Example:
        >>> dns = DnsConfig(
        ...     internal_domain="floe.internal",
        ...     external_domain="data.company.com",
        ...     strategy=DnsStrategy.KUBERNETES,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    internal_domain: str | None = Field(
        default=None,
        pattern=DNS_DOMAIN_PATTERN,
        description="Internal cluster DNS domain (e.g., 'floe.internal')",
    )
    external_domain: str | None = Field(
        default=None,
        pattern=DNS_DOMAIN_PATTERN,
        description="External/public DNS domain (e.g., 'data.company.com')",
    )
    strategy: DnsStrategy = Field(
        default=DnsStrategy.KUBERNETES,
        description="DNS resolution strategy",
    )


# =============================================================================
# Network Policies
# =============================================================================


class NetworkZone(BaseModel):
    """Network zone definition for policy enforcement.

    Attributes:
        description: Human-readable zone description.
        allowed_egress: List of zones/endpoints this zone can reach.
        allowed_ingress: List of zones/endpoints that can reach this zone.

    Example:
        >>> zone = NetworkZone(
        ...     description="Data plane components",
        ...     allowed_egress=["s3_endpoints", "catalog_endpoints"],
        ...     allowed_ingress=[],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str = Field(
        default="",
        max_length=500,
        description="Human-readable zone description",
    )
    allowed_egress: list[str] = Field(
        default_factory=list,
        description="Zones/endpoints this zone can reach",
    )
    allowed_ingress: list[str] = Field(
        default_factory=list,
        description="Zones/endpoints that can reach this zone",
    )


class NetworkPoliciesConfig(BaseModel):
    """Network policies configuration.

    Attributes:
        enabled: Enable network policy enforcement.
        default_rule: Default policy (deny-all for zero-trust).
        zones: Named network zones with egress/ingress rules.

    Example:
        >>> policies = NetworkPoliciesConfig(
        ...     enabled=True,
        ...     default_rule=NetworkPolicyRule.DENY_ALL,
        ...     zones={
        ...         "data_plane": NetworkZone(description="Storage & compute"),
        ...         "control_plane": NetworkZone(description="Orchestration"),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable network policy enforcement",
    )
    default_rule: NetworkPolicyRule = Field(
        default=NetworkPolicyRule.ALLOW_ALL,
        description="Default network policy rule",
    )
    zones: dict[str, NetworkZone] = Field(
        default_factory=dict,
        description="Named network zones with traffic rules",
    )


# =============================================================================
# TLS Configuration
# =============================================================================


class TlsConfig(BaseModel):
    """TLS/SSL configuration for ingress.

    Attributes:
        enabled: Enable TLS termination.
        provider: Certificate provider.
        issuer: cert-manager issuer name (for cert-manager provider).
        min_version: Minimum TLS version.

    Example:
        >>> tls = TlsConfig(
        ...     enabled=True,
        ...     provider=TlsProvider.CERT_MANAGER,
        ...     issuer="letsencrypt-prod",
        ...     min_version="1.3",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable TLS termination",
    )
    provider: TlsProvider = Field(
        default=TlsProvider.CERT_MANAGER,
        description="TLS certificate provider",
    )
    issuer: str | None = Field(
        default=None,
        description="cert-manager issuer name",
    )
    min_version: str = Field(
        default="1.2",
        pattern=r"^1\.[0-3]$",
        description="Minimum TLS version (1.2 or 1.3)",
    )


# =============================================================================
# Ingress Routes
# =============================================================================


class IngressRoute(BaseModel):
    """Ingress route configuration for a service.

    Attributes:
        host: External hostname for the route.
        service: Kubernetes service name.
        port: Service port.
        auth: Authentication method (e.g., 'oauth2-proxy').

    Example:
        >>> route = IngressRoute(
        ...     host="dagster.data.company.com",
        ...     service="dagster-webserver",
        ...     port=3000,
        ...     auth="oauth2-proxy",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = Field(
        ...,
        pattern=DNS_DOMAIN_PATTERN,
        description="External hostname for the route",
    )
    service: str = Field(
        ...,
        min_length=1,
        description="Kubernetes service name",
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Service port",
    )
    auth: str | None = Field(
        default=None,
        description="Authentication method (e.g., 'oauth2-proxy')",
    )


class IngressConfig(BaseModel):
    """Kubernetes ingress configuration.

    Attributes:
        enabled: Enable ingress controller.
        ingress_class: Ingress controller class.
        tls: TLS configuration.
        routes: Named service routes.

    Example:
        >>> ingress = IngressConfig(
        ...     enabled=True,
        ...     ingress_class=IngressClass.NGINX,
        ...     tls=TlsConfig(enabled=True),
        ...     routes={
        ...         "dagster": IngressRoute(
        ...             host="dagster.data.company.com",
        ...             service="dagster-webserver",
        ...             port=3000,
        ...         ),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable ingress controller",
    )
    ingress_class: IngressClass = Field(
        default=IngressClass.NGINX,
        description="Ingress controller class",
    )
    tls: TlsConfig = Field(
        default_factory=TlsConfig,
        description="TLS configuration",
    )
    routes: dict[str, IngressRoute] = Field(
        default_factory=dict,
        description="Named service routes",
    )


# =============================================================================
# Local Access Configuration
# =============================================================================


class LocalAccessPorts(BaseModel):
    """NodePort/LoadBalancer port mappings for local development.

    Attributes:
        dagster: Dagster UI port (default: 30000).
        polaris: Polaris API port (default: 30181).
        minio_console: MinIO Console port (default: 30901).
        jaeger: Jaeger UI port (default: 30686).
        marquez_web: Marquez Web UI port (default: 30301).
        marquez_api: Marquez API port (default: 30500).

    Example:
        >>> ports = LocalAccessPorts(dagster=30000, polaris=30181)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dagster: int = Field(
        default=30000,
        ge=30000,
        le=32767,
        description="Dagster UI NodePort",
    )
    polaris: int = Field(
        default=30181,
        ge=30000,
        le=32767,
        description="Polaris API NodePort",
    )
    minio_console: int = Field(
        default=30901,
        ge=30000,
        le=32767,
        description="MinIO Console NodePort",
    )
    jaeger: int = Field(
        default=30686,
        ge=30000,
        le=32767,
        description="Jaeger UI NodePort",
    )
    marquez_web: int = Field(
        default=30301,
        ge=30000,
        le=32767,
        description="Marquez Web UI NodePort",
    )
    marquez_api: int = Field(
        default=30500,
        ge=30000,
        le=32767,
        description="Marquez API NodePort",
    )


class LocalAccessConfig(BaseModel):
    """Local development external access configuration.

    Provides resilient external access for local Kubernetes (Docker Desktop).
    NodePort services survive pod restarts without manual port-forwarding.

    Attributes:
        enabled: Enable local access configuration.
        access_type: Type of external access (nodeport, port-forward, loadbalancer).
        ports: Port mappings for services.

    Example:
        >>> local = LocalAccessConfig(
        ...     enabled=True,
        ...     access_type=LocalAccessType.NODEPORT,
        ...     ports=LocalAccessPorts(dagster=30000),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable local access configuration",
    )
    access_type: LocalAccessType = Field(
        default=LocalAccessType.NODEPORT,
        description="External access type",
    )
    ports: LocalAccessPorts = Field(
        default_factory=LocalAccessPorts,
        description="Port mappings for services",
    )


# =============================================================================
# Network Configuration (Root)
# =============================================================================


class NetworkConfig(BaseModel):
    """Network configuration for the platform.

    Combines DNS, network policies, ingress, and local access configuration.

    Attributes:
        enabled: Enable network configuration.
        dns: DNS and service discovery configuration.
        network_policies: Network policy enforcement.
        ingress: Ingress controller configuration.
        local_access: Local development access configuration.

    Example:
        >>> network = NetworkConfig(
        ...     enabled=True,
        ...     dns=DnsConfig(external_domain="data.company.com"),
        ...     local_access=LocalAccessConfig(enabled=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable network configuration",
    )
    dns: DnsConfig = Field(
        default_factory=DnsConfig,
        description="DNS configuration",
    )
    network_policies: NetworkPoliciesConfig = Field(
        default_factory=NetworkPoliciesConfig,
        description="Network policies configuration",
    )
    ingress: IngressConfig = Field(
        default_factory=IngressConfig,
        description="Ingress configuration",
    )
    local_access: LocalAccessConfig = Field(
        default_factory=LocalAccessConfig,
        description="Local development access",
    )


# =============================================================================
# AWS Configuration
# =============================================================================


class AwsVpcConfig(BaseModel):
    """AWS VPC configuration (reference, not provisioning).

    Attributes:
        id: VPC ID.
        subnets: Subnet configuration.

    Example:
        >>> vpc = AwsVpcConfig(
        ...     id="vpc-abc123",
        ...     subnets={"private": ["subnet-1a", "subnet-1b"]},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str | None = Field(
        default=None,
        pattern=r"^vpc-[a-f0-9]+$",
        description="VPC ID",
    )
    subnets: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Subnet configuration (private, public)",
    )


class AwsServiceAccountConfig(BaseModel):
    """AWS IAM service account configuration (IRSA).

    Attributes:
        role_arn: IAM role ARN for the service account.

    Example:
        >>> sa = AwsServiceAccountConfig(
        ...     role_arn="arn:aws:iam::123456789012:role/DagsterRole",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    role_arn: str = Field(
        ...,
        pattern=AWS_IAM_ROLE_PATTERN,
        description="IAM role ARN",
    )


class AwsIamConfig(BaseModel):
    """AWS IAM configuration.

    Attributes:
        service_accounts: Service account to IAM role mappings (IRSA).

    Example:
        >>> iam = AwsIamConfig(
        ...     service_accounts={
        ...         "dagster": AwsServiceAccountConfig(
        ...             role_arn="arn:aws:iam::123456789012:role/DagsterRole"
        ...         ),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    service_accounts: dict[str, AwsServiceAccountConfig] = Field(
        default_factory=dict,
        description="Service account to IAM role mappings",
    )


class AwsKmsConfig(BaseModel):
    """AWS KMS configuration.

    Attributes:
        key_arn: KMS key ARN for encryption.

    Example:
        >>> kms = AwsKmsConfig(
        ...     key_arn="arn:aws:kms:us-east-1:123456789012:key/abc-123",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key_arn: str | None = Field(
        default=None,
        pattern=AWS_KMS_KEY_PATTERN,
        description="KMS key ARN",
    )


class AwsCloudWatchConfig(BaseModel):
    """AWS CloudWatch integration configuration.

    Attributes:
        enabled: Enable CloudWatch integration.
        log_group: CloudWatch log group name.
        metrics_namespace: CloudWatch metrics namespace.

    Example:
        >>> cw = AwsCloudWatchConfig(
        ...     enabled=True,
        ...     log_group="/floe/runtime",
        ...     metrics_namespace="Floe/Runtime",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable CloudWatch integration",
    )
    log_group: str | None = Field(
        default=None,
        description="CloudWatch log group name",
    )
    metrics_namespace: str | None = Field(
        default=None,
        description="CloudWatch metrics namespace",
    )


class AwsConfig(BaseModel):
    """AWS-specific configuration.

    Attributes:
        account_id: AWS account ID.
        vpc: VPC configuration.
        iam: IAM configuration (IRSA).
        kms: KMS encryption configuration.
        cloudwatch: CloudWatch integration.

    Example:
        >>> aws = AwsConfig(
        ...     account_id="123456789012",
        ...     iam=AwsIamConfig(service_accounts={}),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str | None = Field(
        default=None,
        pattern=r"^\d{12}$",
        description="AWS account ID (12 digits)",
    )
    vpc: AwsVpcConfig = Field(
        default_factory=AwsVpcConfig,
        description="VPC configuration",
    )
    iam: AwsIamConfig = Field(
        default_factory=AwsIamConfig,
        description="IAM configuration",
    )
    kms: AwsKmsConfig = Field(
        default_factory=AwsKmsConfig,
        description="KMS configuration",
    )
    cloudwatch: AwsCloudWatchConfig = Field(
        default_factory=AwsCloudWatchConfig,
        description="CloudWatch integration",
    )


# =============================================================================
# LocalStack Configuration
# =============================================================================


class LocalStackConfig(BaseModel):
    """LocalStack configuration for local AWS emulation.

    Attributes:
        enabled: Enable LocalStack integration.
        endpoint: LocalStack endpoint URL.
        services: AWS services to emulate.

    Example:
        >>> ls = LocalStackConfig(
        ...     enabled=True,
        ...     endpoint="http://localstack:4566",
        ...     services=["s3", "sts", "iam"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable LocalStack integration",
    )
    endpoint: str | None = Field(
        default=None,
        description="LocalStack endpoint URL",
    )
    services: list[str] = Field(
        default_factory=lambda: ["s3", "sts"],
        description="AWS services to emulate",
    )


# =============================================================================
# Cloud Configuration (Root)
# =============================================================================


class CloudConfig(BaseModel):
    """Cloud provider configuration.

    Supports AWS-first design with cloud-agnostic abstractions.
    LocalStack provides AWS emulation for local development.

    Attributes:
        provider: Cloud provider type.
        region: Cloud region.
        aws: AWS-specific configuration.
        localstack: LocalStack configuration for local dev.

    Example:
        >>> cloud = CloudConfig(
        ...     provider=CloudProvider.AWS,
        ...     region="us-east-1",
        ...     aws=AwsConfig(account_id="123456789012"),
        ... )

        >>> local = CloudConfig(
        ...     provider=CloudProvider.LOCAL,
        ...     localstack=LocalStackConfig(enabled=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: CloudProvider = Field(
        default=CloudProvider.LOCAL,
        description="Cloud provider",
    )
    region: str | None = Field(
        default=None,
        description="Cloud region",
    )
    aws: AwsConfig = Field(
        default_factory=AwsConfig,
        description="AWS configuration",
    )
    localstack: LocalStackConfig = Field(
        default_factory=LocalStackConfig,
        description="LocalStack configuration",
    )

    @model_validator(mode="after")
    def validate_provider_config(self) -> Self:
        """Validate provider-specific configuration.

        Raises:
            ValueError: If AWS provider without region or LocalStack misconfigured.
        """
        if self.provider == CloudProvider.AWS and not self.region:
            raise ValueError("AWS provider requires region to be set")
        # Note: LocalStack is optional even for local provider
        return self


# =============================================================================
# Infrastructure Configuration (Root)
# =============================================================================


class InfrastructureConfig(BaseModel):
    """Infrastructure configuration for the platform.

    Combines network and cloud configuration for enterprise deployment.
    Supports AWS-first design with LocalStack for local development.

    Attributes:
        network: Network configuration (DNS, policies, ingress).
        cloud: Cloud provider configuration (AWS, LocalStack).

    Example:
        >>> infra = InfrastructureConfig(
        ...     network=NetworkConfig(
        ...         local_access=LocalAccessConfig(enabled=True),
        ...     ),
        ...     cloud=CloudConfig(
        ...         provider=CloudProvider.LOCAL,
        ...         localstack=LocalStackConfig(enabled=True),
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    network: NetworkConfig = Field(
        default_factory=NetworkConfig,
        description="Network configuration",
    )
    cloud: CloudConfig = Field(
        default_factory=CloudConfig,
        description="Cloud provider configuration",
    )
