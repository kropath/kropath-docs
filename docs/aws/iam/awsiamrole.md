# IAMRole — Workload Identity Principals

The `IAMRole` resource creates IAM roles for your workloads. A role is a principal identity that your applications, services, and infrastructure assume to make AWS API calls.

## Overview

Use `IAMRole` to create roles for:

- **EC2 instances** — Attach to instances via instance profile
- **Lambda functions** — Specify as the execution role
- **ECS tasks** — Attach to task definitions
- **EKS pods** — Bind to service accounts via OIDC or Pod Identity
- **AWS services** — Services like RDS, DynamoDB, or Lambda

Each role has:
- A **trust policy** — Specifies who can assume the role (auto-generated based on `spec.type`)
- **Attached policies** — AWS managed or custom policies granting permissions
- **Governance controls** — Permissions boundary, max session duration, and org constraints

## Role Types

Choose the role type that matches your workload:

| Type | For | Trust Principal |
|---|---|---|
| `ec2` | EC2 instances | `ec2.amazonaws.com` |
| `ecs-task` | ECS tasks | `ecs-tasks.amazonaws.com` |
| `lambda` | Lambda functions | `lambda.amazonaws.com` |
| `eks-irsa` | EKS pods (OIDC federation) | Your OIDC provider (external) |
| `eks-pod-identity` | EKS pods (Pod Identity) | `pods.eks.amazonaws.com` |
| `aws-service` | AWS services (RDS, DynamoDB, etc.) | Specified service principal |
| `generic` | Custom trust relationships | Your custom policy |

## Creating a Role

### Simple EC2 Role

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: web-server
  namespace: default
spec:
  configRef: general-policy
  type: ec2
  description: "Role for web server EC2 instances"
```

This role:
- Automatically trusts `ec2.amazonaws.com`
- Automatically attaches `AmazonSSMManagedInstanceCore` for AWS Systems Manager
- Creates an instance profile (needed when attaching to instances)

### Lambda Role with Permissions

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: data-processor
  namespace: default
spec:
  configRef: general-policy
  type: lambda
  description: "Role for Lambda data processing"
  policies:
    - arn: "arn:aws:iam::aws:policy/service-role/AWSLambdaS3ExecutionRole"
  inlinePolicies:
    - name: dynamodb-access
      documentJSON: |
        {
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem", "dynamodb:GetItem"],
            "Resource": "arn:aws:dynamodb:*:123456789012:table/data-table"
          }]
        }
```

### EKS IRSA Role (OIDC Federation)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMIdentityProvider
metadata:
  name: eks-oidc
  namespace: kro-system
spec:
  configRef: general-policy
  type: oidc
  oidc:
    url: "https://oidc.eks.us-east-1.amazonaws.com/id/1234567890ABCDEF"
    thumbprints:
      - "9e99a48a9960b14926bb7f3b02e22da2b0ab7280"
---
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: app-role
  namespace: default
spec:
  configRef: general-policy
  type: eks-irsa
  oidcProviderArn: "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/1234567890ABCDEF"
  serviceAccountNamespace: "app-namespace"
  serviceAccountName: "app-sa"
  policies:
    - arn: "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
```

### Service Role

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: IAMRole
metadata:
  name: rds-monitoring
  namespace: default
spec:
  configRef: general-policy
  type: aws-service
  servicePrincipal: "monitoring.rds.amazonaws.com"
  policies:
    - arn: "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
```

## Attaching Policies

### AWS Managed Policies

Reference pre-built policies by ARN:

```yaml
policies:
  - arn: "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
```

### Reusable Managed Policies

Create an `IAMPolicy` and reference it:

```yaml
policies:
  - ref: database-access  # References IAMPolicy/database-access
```

### Inline Policies

Define policies directly on the role:

```yaml
inlinePolicies:
  - name: s3-logs
    documentJSON: |
      {
        "Version": "2012-10-17",
        "Statement": [{
          "Effect": "Allow",
          "Action": "s3:PutObject",
          "Resource": "arn:aws:s3:::my-logs/*"
        }]
      }
```

## Governance Controls

### Permissions Boundary

Configure via `IAMConfig`:

```yaml
spec:
  mandatory:
    permissionsBoundaryArn: "arn:aws:iam::123456789012:policy/Boundary"
```

Roles cannot grant permissions beyond the boundary.

### Session Duration

```yaml
spec:
  maxSessionDuration: 1800  # 30 minutes
```

Value must not exceed mandatory limit from the config profile.

## Monitoring

Check role status:

```bash
kubectl describe awsiamrole my-role -n default
```

Look for `status.resourceName`, `status.predictedArn`, and `status.conditions`.

## Deletion

By default, roles are retained. To delete the underlying AWS resource:

```yaml
spec:
  deletionPolicy: delete
```
