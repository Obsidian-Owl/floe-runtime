# AWS Account Setup for Floe Deployment

This guide walks through setting up your AWS account for deploying Floe to EKS. Follow these steps after validating your local K8s deployment works correctly.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] AWS account with admin access
- [ ] AWS CLI configured (`aws sts get-caller-identity` works)
- [ ] kubectl installed
- [ ] Helm 3.x installed
- [ ] eksctl installed (recommended for EKS management)

```bash
# Verify prerequisites
aws sts get-caller-identity
kubectl version --client
helm version
eksctl version
```

---

## Step 1: VPC and Networking

### Option A: Use Existing VPC

If you already have a VPC with private subnets, skip to Step 2. Ensure your VPC has:
- At least 2 private subnets (for EKS worker nodes)
- NAT gateway for outbound internet access
- DNS hostnames enabled

### Option B: Create New VPC with eksctl

eksctl creates a VPC automatically when you create a cluster:

```bash
# This creates VPC, subnets, NAT gateways automatically
eksctl create cluster --name floe-demo \
  --region us-east-1 \
  --vpc-nat-mode HighlyAvailable \
  --nodes 3 \
  --node-type t3.large \
  --managed
```

---

## Step 2: EKS Cluster Setup

### Create Cluster (if not using existing)

```bash
eksctl create cluster --name floe-demo \
  --region us-east-1 \
  --nodes 3 \
  --node-type t3.large \
  --managed \
  --with-oidc  # Enables IRSA
```

### Enable OIDC Provider (for IRSA)

IRSA (IAM Roles for Service Accounts) is required for secure credential management:

```bash
# If you created cluster without --with-oidc, enable it now
eksctl utils associate-iam-oidc-provider \
  --cluster floe-demo \
  --region us-east-1 \
  --approve

# Verify OIDC provider exists
aws eks describe-cluster --name floe-demo \
  --query "cluster.identity.oidc.issuer" \
  --output text
```

### Install Required Controllers

#### AWS Load Balancer Controller (for ALB ingress)

```bash
# Create IAM policy
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json

# Create service account with IRSA
eksctl create iamserviceaccount \
  --cluster=floe-demo \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=floe-demo \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

---

## Step 3: IAM Roles

### Create Data Engineer Role (for Dagster workers)

This role grants S3 and Polaris access to Dagster pods:

```bash
# Get OIDC provider ID
OIDC_ID=$(aws eks describe-cluster --name floe-demo \
  --query "cluster.identity.oidc.issuer" \
  --output text | cut -d '/' -f 5)

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:floe:dagster-worker"
      }
    }
  }]
}
EOF

# Create role
aws iam create-role \
  --role-name FloeDataEngineer \
  --assume-role-policy-document file://trust-policy.json
```

### Attach S3 Policy

```bash
cat > s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ],
    "Resource": [
      "arn:aws:s3:::floe-iceberg-data",
      "arn:aws:s3:::floe-iceberg-data/*"
    ]
  }]
}
EOF

aws iam put-role-policy \
  --role-name FloeDataEngineer \
  --policy-name S3Access \
  --policy-document file://s3-policy.json
```

### Create Polaris Admin Role (for catalog management)

```bash
# Trust policy for Polaris pod
cat > polaris-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-east-1.amazonaws.com/id/${OIDC_ID}:sub": "system:serviceaccount:floe:polaris"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name FloePolarisAdmin \
  --assume-role-policy-document file://polaris-trust-policy.json

# Polaris needs full S3 access for credential vending
aws iam put-role-policy \
  --role-name FloePolarisAdmin \
  --policy-name S3FullAccess \
  --policy-document file://s3-policy.json

# Also needs STS for credential vending
cat > sts-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "sts:AssumeRole",
      "sts:GetFederationToken"
    ],
    "Resource": "*"
  }]
}
EOF

aws iam put-role-policy \
  --role-name FloePolarisAdmin \
  --policy-name STSAccess \
  --policy-document file://sts-policy.json
```

---

## Step 4: S3 Bucket

```bash
# Create bucket
aws s3 mb s3://floe-iceberg-data --region us-east-1

# Enable versioning (recommended for Iceberg)
aws s3api put-bucket-versioning \
  --bucket floe-iceberg-data \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket floe-iceberg-data \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

---

## Step 5: Secrets Manager (Optional)

Store sensitive credentials in AWS Secrets Manager:

```bash
# Store Polaris OAuth2 credentials
aws secretsmanager create-secret \
  --name "floe/polaris-client-id" \
  --secret-string "your-polaris-client-id"

aws secretsmanager create-secret \
  --name "floe/polaris-client-secret" \
  --secret-string "your-polaris-client-secret"

# Store database password
aws secretsmanager create-secret \
  --name "floe/postgres-password" \
  --secret-string "your-secure-password"
```

---

## Step 6: Create platform.yaml for AWS

Create `platform/aws-dev/platform.yaml`:

```yaml
version: "1.1.0"

infrastructure:
  cloud:
    provider: aws
    region: us-east-1
    aws:
      account_id: "YOUR_ACCOUNT_ID"
      iam:
        service_accounts:
          dagster:
            role_arn: "arn:aws:iam::YOUR_ACCOUNT_ID:role/FloeDataEngineer"
          polaris:
            role_arn: "arn:aws:iam::YOUR_ACCOUNT_ID:role/FloePolarisAdmin"
  network:
    enabled: true
    dns:
      internal_domain: floe.local
      strategy: kubernetes
    ingress:
      enabled: true
      class: alb
      tls:
        enabled: true
        provider: acm
    local_access:
      enabled: false  # Use ALB ingress in AWS

security:
  authentication:
    enabled: false  # Enable later with OIDC
    method: static
  secret_backends:
    primary: kubernetes  # Or aws_secrets_manager
    kubernetes:
      enabled: true
      namespace: floe
  encryption:
    in_transit:
      enabled: true
    at_rest:
      enabled: true

governance:
  classifications:
    enabled: false
  retention:
    enabled: false
  compliance:
    enabled: false

storage:
  default:
    type: s3
    bucket: floe-iceberg-data
    region: us-east-1
    credentials:
      mode: iam_role
      role_arn: "arn:aws:iam::YOUR_ACCOUNT_ID:role/FloeDataEngineer"

catalogs:
  default:
    type: polaris
    uri: "http://floe-infra-polaris:8181/api/catalog"
    warehouse: demo_catalog
    namespace: default
    credentials:
      mode: oauth2
      client_id:
        secret_ref: polaris-client-id
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:DATA_ENGINEER"
    access_delegation: vended_credentials

compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"
      threads: 4
    credentials:
      mode: static

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: "http://floe-infra-jaeger-collector:4317"
  lineage_endpoint: "http://floe-infra-marquez:5000"
  attributes:
    service.name: floe-aws-dev
    deployment.environment: aws-dev
```

Replace `YOUR_ACCOUNT_ID` with your actual AWS account ID.

---

## Step 7: Deploy Floe

```bash
# Create namespace
kubectl create namespace floe

# Deploy infrastructure
helm install floe-infra ./charts/floe-infrastructure \
  -n floe \
  -f ./charts/floe-infrastructure/values.yaml \
  --set-file platformConfig.content=./platform/aws-dev/platform.yaml \
  --set platformConfig.enabled=true \
  --set minio.enabled=false \
  --set localstack.enabled=false

# Wait for pods
kubectl get pods -n floe -w

# Deploy Dagster
helm install floe-dagster ./charts/floe-dagster \
  -n floe \
  -f ./charts/floe-dagster/values.yaml
```

---

## Step 8: Verification

### Check Pods

```bash
kubectl get pods -n floe
```

Expected output:
```
NAME                                    READY   STATUS    RESTARTS   AGE
floe-dagster-daemon-xxx                 1/1     Running   0          2m
floe-dagster-webserver-xxx              1/1     Running   0          2m
floe-infra-polaris-xxx                  1/1     Running   0          5m
floe-infra-postgresql-0                 1/1     Running   0          5m
floe-infra-jaeger-xxx                   1/1     Running   0          5m
floe-infra-marquez-xxx                  1/1     Running   0          5m
```

### Get ALB URL

```bash
kubectl get ingress -n floe
```

### Test S3 Access from Dagster Pod

```bash
kubectl exec -n floe deploy/floe-dagster-webserver -- \
  aws s3 ls s3://floe-iceberg-data/
```

---

## Cost Estimation

| Resource | Monthly Cost (estimate) |
|----------|------------------------|
| EKS cluster | ~$73 |
| t3.large nodes (3x) | ~$180 |
| S3 (100GB) | ~$2 |
| ALB | ~$20 |
| NAT Gateway | ~$45 |
| **Total** | **~$320/month** |

Note: Costs vary by region and usage. Enable AWS Cost Explorer for accurate tracking.

---

## Cleanup

```bash
# Remove Helm releases
helm uninstall floe-dagster -n floe
helm uninstall floe-infra -n floe

# Delete namespace
kubectl delete namespace floe

# Delete EKS cluster
eksctl delete cluster --name floe-demo --region us-east-1

# Delete S3 bucket
aws s3 rb s3://floe-iceberg-data --force

# Delete IAM roles
aws iam delete-role-policy --role-name FloeDataEngineer --policy-name S3Access
aws iam delete-role --role-name FloeDataEngineer
aws iam delete-role-policy --role-name FloePolarisAdmin --policy-name S3FullAccess
aws iam delete-role-policy --role-name FloePolarisAdmin --policy-name STSAccess
aws iam delete-role --role-name FloePolarisAdmin

# Delete Secrets Manager secrets
aws secretsmanager delete-secret --secret-id floe/polaris-client-id --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id floe/polaris-client-secret --force-delete-without-recovery
```

---

## Troubleshooting

### Pods Stuck in Pending

```bash
kubectl describe pod <pod-name> -n floe
```

Common issues:
- Insufficient node resources (increase node count or size)
- PVC not binding (check storage class)

### IRSA Not Working

```bash
# Verify service account annotation
kubectl get sa dagster-worker -n floe -o yaml

# Should show:
# annotations:
#   eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/FloeDataEngineer
```

### S3 Access Denied

1. Check IAM role trust policy
2. Verify OIDC provider ID matches
3. Check service account namespace/name in trust policy

### Polaris Not Starting

```bash
kubectl logs -n floe deploy/floe-infra-polaris --tail=50
```

Common issues:
- PostgreSQL not ready (check init container)
- S3 credentials not configured

---

## Next Steps

After successful deployment:

1. **Enable OIDC authentication** for production security
2. **Configure ALB with ACM certificate** for HTTPS
3. **Set up monitoring** with CloudWatch or Prometheus
4. **Configure backup** for PostgreSQL metadata
5. **Add more IAM roles** for different user personas
