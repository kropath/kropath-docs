# AWS Elastic Container Registry (ECR)

Manage container image repositories, pull-through caching, and repository templates with kropath ECR resources.

## Resources

- **[ECRConfig](ecrconfig.md)** — Governance configuration for ECR repositories
- **[ECRRepository](ecrrepository.md)** — Create and manage private container image repositories
- **[ECRPullThroughCacheRule](ecrpullthroughcacherule.md)** — Configure pull-through cache rules
- **[ECRRepositoryCreationTemplate](ecrrepositorycreationtemplate.md)** — Define templates for auto-created repositories

## Quick Start

### 1. Set Up Governance

Define an ECR governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    imageTagMutability: "MUTABLE"
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{name}"
```

### 2. Create a Repository

Create a private container image repository:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-app
  namespace: app-team
spec:
  configRef: general-policy
  deletionPolicy: retain
  tags:
    team: platform
    environment: production
```

After reconciliation, the repository URI is available in `status.repositoryURI`:

```
123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app
```

### 3. Pull from Public Registries (Optional)

Set up a pull-through cache to proxy images from Docker Hub:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub-cache
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io
  deletionPolicy: retain
```

Users can now pull images as `ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/docker-hub/nginx:latest`.

## Key Concepts

### Repository Naming

ECR repository names use the forward-slash (`/`) separator to create hierarchical namespaces. The default naming pattern is `{namespace}/{name}`, creating repositories like `app-team/my-app`.

### Encryption

ECR supports two encryption modes:

- **AES256** (AWS-managed) — Default, no key management overhead
- **KMS** (Customer-managed) — Required for compliance, specify a KMS key

### Image Tag Mutability

Control whether image tags can be overwritten:

- **MUTABLE** (default) — Tags can be overwritten (typical for `latest`)
- **IMMUTABLE** — Tags are permanent (enforces supply chain security)

Use `imageTagMutabilityExclusionFilters` to exempt specific tags from the mutability setting.

### Governance Cascade

ECRConfig profiles define mandatory and default settings:

- **Mandatory** — Platform team enforcement (e.g., immutable tags for production)
- **Defaults** — Applied only if the developer doesn't specify a value

Developers can override defaults in their resource spec, but mandatory settings always apply.

## Common Use Cases

### Production-Grade Repository

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  defaults:
    lifecyclePolicy: |
      {
        "rules": [
          {
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
              "tagStatus": "tagged",
              "tagPrefixList": ["v"],
              "countType": "imageCountMoreThan",
              "countNumber": 10
            },
            "action": {
              "type": "expire"
            }
          }
        ]
      }
    namingTemplate: "{namespace}/{configRef}/{name}"
```

This profile enforces:
- Immutable tags (prevents overwriting released versions)
- KMS encryption (compliance requirement)
- Automatic cleanup of old images
- Hierarchical naming: `team/prod/service-name`

### Cross-Account Image Pull

Grant another AWS account permission to pull images:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: shared-library
  namespace: platform
spec:
  configRef: general-policy
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AllowCrossAccountPull",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::999888777666:root"
          },
          "Action": [
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "ecr:DescribeImages"
          ]
        }
      ]
    }
```

## Next Steps

- [Set up ECRConfig governance profiles](ecrconfig.md)
- [Create your first ECRRepository](ecrrepository.md)
- [Configure pull-through caching](ecrpullthroughcacherule.md)
- [Define repository creation templates](ecrrepositorycreationtemplate.md)
