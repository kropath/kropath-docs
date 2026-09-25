---
title: ECRConfig — ECR Governance and Policy
description: "The `ECRConfig` resource defines governance policies for ECR repositories in your cluster."
doc_type: reference
---
# ECRConfig — ECR Governance and Policy

The `ECRConfig` resource defines governance policies for ECR repositories in your cluster. Platform teams use ECRConfig profiles to enforce compliance requirements, encryption standards, and naming conventions across all repositories.

## When to Use ECRConfig

ECRConfig is for **platform teams** managing cluster-wide policies. Developers interact with it indirectly via `ECRRepository.spec.configRef`.

- Define mandatory encryption, tag immutability, and lifecycle policies
- Create named profiles (e.g., `production`, `pci`, `development`)
- Set organization-wide defaults
- Enforce naming conventions

## Core Concepts

### Governance Tiers

ECRConfig has two tiers:

| Tier | Purpose | Behavior |
|---|---|---|
| **Mandatory** | Platform enforcement | Always applied; developers cannot override |
| **Defaults** | Sensible defaults | Applied only if the developer doesn't specify a value |

For example, if the `production` profile mandates `imageTagMutability: IMMUTABLE`, all repositories using that profile must have immutable tags, even if they specify `imageTagMutability: MUTABLE`.

## Configuration Fields

### Governance Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `imageTagMutability` | string | `"MUTABLE"` (defaults tier) | Force IMMUTABLE or MUTABLE tags across repositories |
| `encryptionType` | string | `"AES256"` (defaults tier) | Force KMS or AES256 encryption |
| `kmsKeyID` | string | `""` | ARN of a specific KMS key to enforce (requires `encryptionType: KMS`) |
| `lifecyclePolicy` | string | `""` | JSON lifecycle policy applied to all repositories |
| `namingTemplate` | string | `"{namespace}/{name}"` | Enforce a specific naming pattern (e.g., `"{namespace}/{configRef}/{name}"`) |

### Tagging Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | Cloud tags merged with repository tags |
| `syncedLabels` | map | `{}` | Kubernetes labels also synced to cloud tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations on the repository |

## Profile Examples

### Default Profile (Development)

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

**Applies to:** Repositories that don't specify a different `configRef` or when the specified profile doesn't exist.

**Behavior:** Development-friendly defaults with AWS-managed encryption.

### Production Profile (PCI Compliance)

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
    tags:
      compliance: pci-dss
      managed-by: platform
  defaults:
    namingTemplate: "{namespace}/{configRef}/{name}"
    lifecyclePolicy: |
      {
        "rules": [
          {
            "rulePriority": 1,
            "description": "Expire images older than 90 days",
            "selection": {
              "tagStatus": "untagged",
              "countType": "sinceImagePushed",
              "countUnit": "days",
              "countNumber": 90
            },
            "action": {
              "type": "expire"
            }
          },
          {
            "rulePriority": 2,
            "description": "Keep tagged images for 1 year",
            "selection": {
              "tagStatus": "tagged",
              "countType": "sinceImagePushed",
              "countUnit": "days",
              "countNumber": 365
            },
            "action": {
              "type": "expire"
            }
          }
        ]
      }
```

**Applies to:** Production workloads requiring compliance.

**Behavior:**
- All repositories must have immutable tags
- All repositories must use KMS encryption with the specified key
- Automatic cleanup: untagged images after 90 days, tagged images after 1 year
- Hierarchical naming: `namespace/prod/service-name`

### Immutable-Only Profile (Supply Chain Security)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: immutable-only
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: immutable-only
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
  defaults:
    encryptionType: "AES256"
```

**Applies to:** Teams needing supply chain security without KMS overhead.

**Behavior:** Enforce immutable tags; use default encryption.

## Using ECRConfig Profiles

Developers select a profile via `ECRRepository.spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-service
  namespace: app-team
spec:
  configRef: production  # Uses the 'production' ECRConfig profile
  tags:
    team: backend
```

If the specified profile doesn't exist, the system falls back to `general-policy`.

## Encryption Configuration

### AES256 (AWS-Managed)

```yaml
spec:
  mandatory: {}
  defaults:
    encryptionType: "AES256"
```

- No key management overhead
- Suitable for non-regulated workloads
- AWS manages key rotation

### KMS (Customer-Managed)

```yaml
spec:
  mandatory:
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

- Fine-grained access control via IAM policies
- Required for compliance (PCI, HIPAA, SOC 2)
- You manage key rotation
- Cannot be changed after repository creation

**Important:** Setting both `encryptionType: KMS` AND `kmsKeyID` in the **same tier** (both in `mandatory` or both in `defaults`) is the correct PCI pattern. Never combine `encryptionType: AES256` with `kmsKeyID`—the controller rejects this because AES256 does not use a customer-managed key.

## Lifecycle Policies

Lifecycle policies automatically expire old images. Define them as JSON:

```yaml
spec:
  defaults:
    lifecyclePolicy: |
      {
        "rules": [
          {
            "rulePriority": 1,
            "description": "Expire untagged images after 7 days",
            "selection": {
              "tagStatus": "untagged",
              "countType": "sinceImagePushed",
              "countUnit": "days",
              "countNumber": 7
            },
            "action": {
              "type": "expire"
            }
          },
          {
            "rulePriority": 2,
            "description": "Keep only the last 5 builds",
            "selection": {
              "tagStatus": "tagged",
              "tagPrefixList": ["build-"],
              "countType": "imageCountMoreThan",
              "countNumber": 5
            },
            "action": {
              "type": "expire"
            }
          }
        ]
      }
```

### Common Patterns

**Clean up untagged images:**
```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Expire untagged after 30 days",
    "selection": {
      "tagStatus": "untagged",
      "countType": "sinceImagePushed",
      "countUnit": "days",
      "countNumber": 30
    },
    "action": { "type": "expire" }
  }]
}
```

**Keep last N tagged images:**
```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 10 release images",
    "selection": {
      "tagStatus": "tagged",
      "tagPrefixList": ["v"],
      "countType": "imageCountMoreThan",
      "countNumber": 10
    },
    "action": { "type": "expire" }
  }]
}
```

## Naming Conventions

ECRConfig can enforce naming patterns via `namingTemplate`:

| Template | Example Result |
|---|---|
| `{namespace}/{name}` | `app-team/my-app` |
| `{namespace}/{configRef}/{name}` | `app-team/prod/my-app` |
| `prod/{namespace}/{name}` | `prod/app-team/my-app` |

Tokens in templates:

| Token | Resolves to |
|---|---|
| `{name}` | Resource `metadata.name` |
| `{namespace}` | Resource `metadata.namespace` |
| `{configRef}` | The ECRConfig profile name (e.g., `prod`) |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{tag.KEY}` | Value of cloud tag with key `KEY` |

## Setting Up Profiles

1. Create ECRConfig resources in the `kro-system` namespace:

   ```bash
   kubectl apply -f ecrconfig-profiles.yaml
   ```

2. Label each profile so repositories can find it:

   ```yaml
   metadata:
     labels:
       aws.kropath.run/resource-name: general-policy  # REQUIRED
   ```

3. Developers reference profiles via `ECRRepository.spec.configRef`:

   ```yaml
   spec:
     configRef: production
   ```

## Validation Rules

ECRConfig has built-in validation:

- **Cannot set the same field in both tiers** — If `spec.mandatory.imageTagMutability` is set, `spec.defaults.imageTagMutability` must be empty (and vice versa).
- **Encryption configuration must be valid** — If `encryptionType: AES256` is set, `kmsKeyID` must be empty (AES256 doesn't use a customer-managed key).

Example of invalid ECRConfig (will be rejected):

```yaml
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
  defaults:
    imageTagMutability: "MUTABLE"  # ERROR: Cannot set in both tiers
```

## Status and Feedback

After you apply an ECRConfig, the cluster validates it and computes `status.effectiveConfig` — the merged configuration that repositories read.

```bash
kubectl get ecrconfig production -o yaml
```

If the configuration is invalid, `status.conditions` will show an error.

## Complete Example: Multi-Profile Setup

```yaml
---
# Development profile (permissive)
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}
  defaults:
    imageTagMutability: "MUTABLE"
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{name}"

---
# Staging profile (moderate)
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: staging
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: staging
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
  defaults:
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{configRef}/{name}"

---
# Production profile (strict)
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
    namingTemplate: "{namespace}/{configRef}/{name}"
    tags:
      managed-by: kropath
      environment: production
```

Developers then choose the profile that matches their environment:

```yaml
# Development deployment
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: api
  namespace: team-a
spec:
  configRef: development

---
# Production deployment
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: api
  namespace: team-a
spec:
  configRef: production
```
