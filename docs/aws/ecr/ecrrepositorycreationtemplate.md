# ECRRepositoryCreationTemplate — Configuring Auto-Created Repositories

The `ECRRepositoryCreationTemplate` resource defines configuration templates for repositories that are automatically created by pull-through cache rules or cross-region replication. When ECR auto-creates a repository, it applies the matching template to set encryption, tag mutability, lifecycle policies, and access control.

## When to Use Creation Templates

- **Enforce configuration on cached repositories** — Ensure auto-created repositories follow the same governance as manually-created ones
- **Standardize encryption and compliance** — Apply KMS encryption to all auto-created repositories automatically
- **Manage lifecycle across dynamic repositories** — Define expiration policies that apply to all generated repositories

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` governance profile to apply (for tags/labels) |
| `deletionPolicy` | string | `"retain"` | Behavior when the template is deleted: `"retain"` (safe) or `"delete"` |

### Template Identity (Immutable)

| Field | Type | Required | Purpose |
|---|---|---|---|
| `prefix` | string | Yes | Namespace prefix for matching auto-created repositories (e.g., `"docker-hub"`, `"prod/"`, `"ROOT"` for catch-all) |
| `appliedFor` | array | Yes | Scenarios where this template applies: `["PULL_THROUGH_CACHE"]` and/or `["REPLICATION"]` |
| `description` | string | No | Human-readable description of the template |

### Repository Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionType` | string | `""` | `AES256` (AWS-managed) or `KMS` (customer-managed) for auto-created repos |
| `kmsKeyRef` | string | `""` | Reference to a kropath `KMSKey` resource (mutually exclusive with `kmsKeyArn`) |
| `kmsKeyArn` | string | `""` | Direct KMS key ARN (mutually exclusive with `kmsKeyRef`) |
| `imageTagMutability` | string | `""` | `MUTABLE` or `IMMUTABLE` for auto-created repos |
| `imageTagMutabilityExclusionFilters` | array | `[]` | Exempt specific tags from mutability setting |
| `lifecyclePolicy` | string | `""` | JSON lifecycle policy for auto-created repos |
| `repositoryPolicy` | string | `""` | JSON resource-based access policy for auto-created repos |
| `resourceTags` | array | `[]` | Cloud tags applied to auto-created repos (as `{key, value}` pairs) |
| `customRoleArn` | string | `""` | IAM role ARN for template-driven repository creation |

### Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | Kubernetes tags on this template resource |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Basic Examples

### Default Configuration for Cached Repositories

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: default-template
  namespace: kro-system
spec:
  prefix: ROOT  # Matches all auto-created repositories
  appliedFor:
  - PULL_THROUGH_CACHE
  description: "Default configuration for pull-through cached repositories"
  deletionPolicy: retain
```

**Behavior:** Any repository auto-created by pull-through cache rules receives default settings (AES256 encryption, mutable tags, no lifecycle policy).

### KMS-Encrypted Repositories

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: kms-template
  namespace: kro-system
spec:
  prefix: docker-hub
  appliedFor:
  - PULL_THROUGH_CACHE
  description: "KMS-encrypted template for Docker Hub cached images"
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  imageTagMutability: IMMUTABLE
  deletionPolicy: retain
```

**Behavior:** When a Docker Hub image is pulled for the first time, ECR auto-creates the repository with:
- KMS encryption using the specified key
- Immutable tags (supply chain security)

### Production Template with Lifecycle Policy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: prod-template
  namespace: kro-system
spec:
  prefix: prod/
  appliedFor:
  - PULL_THROUGH_CACHE
  - REPLICATION
  description: "Production template: KMS encryption + lifecycle management"
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-prod"
  imageTagMutability: IMMUTABLE
  lifecyclePolicy: |
    {
      "rules": [
        {
          "rulePriority": 1,
          "description": "Expire untagged after 30 days",
          "selection": {
            "tagStatus": "untagged",
            "countType": "sinceImagePushed",
            "countUnit": "days",
            "countNumber": 30
          },
          "action": { "type": "expire" }
        }
      ]
    }
  resourceTags:
  - key: environment
    value: production
  - key: compliance
    value: pci-dss
  deletionPolicy: retain
```

**Behavior:** Any repository auto-created under the `prod/` prefix receives:
- KMS encryption with the production CMK
- Immutable tags
- Automatic cleanup of untagged images after 30 days
- Tags: `environment=production`, `compliance=pci-dss`

## Advanced Configuration

### Immutable Tags with Exclusions

Allow specific tags to be mutable while enforcing immutability for releases:

```yaml
spec:
  prefix: releases/
  appliedFor:
  - PULL_THROUGH_CACHE
  imageTagMutability: IMMUTABLE
  imageTagMutabilityExclusionFilters:
  - filter: "latest"
    filterType: WILDCARD
  - filter: "dev-*"
    filterType: WILDCARD
```

**Behavior:** Auto-created repositories allow `latest` and `dev-*` tags to be overwritten, but release tags (e.g., `v1.0`) are immutable.

### Multi-Scenario Template

Apply the same template to both pull-through cache and cross-region replication scenarios:

```yaml
spec:
  prefix: shared/
  appliedFor:
  - PULL_THROUGH_CACHE
  - REPLICATION
  description: "Template applies to both cached and replicated repositories"
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/..."
```

**Behavior:** Whether the repository is created by a pull-through cache rule or by cross-region replication, this template applies.

### Cross-Account Access

Grant another AWS account permission to pull from auto-created repositories:

```yaml
spec:
  prefix: shared/
  appliedFor:
  - PULL_THROUGH_CACHE
  repositoryPolicy: |
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
            "ecr:BatchGetImage"
          ]
        }
      ]
    }
```

## Immutable Fields

The `prefix` field **cannot be changed** after creation:

| Field | Mutable | Reason |
|---|---|---|
| `prefix` | No | Used by ECR to match repositories at creation time |
| `appliedFor` | Yes | Can be updated to apply to additional scenarios |
| Other fields | Yes | Can be updated for new repositories or via reapplication |

To change the `prefix`, delete the template and create a new one:

```bash
kubectl delete ecrrepositorycreationtemplate old-template
kubectl apply -f new-template.yaml
```

**Note:** Existing repositories created under the old prefix are not affected.

## Combining with Pull-Through Cache Rules

Templates and pull-through cache rules work together:

```yaml
---
# Cache rule
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: docker-hub
  upstreamRegistryURL: registry-1.docker.io

---
# Template for repositories created by the cache rule
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: docker-hub-template
  namespace: kro-system
spec:
  prefix: docker-hub
  appliedFor:
  - PULL_THROUGH_CACHE
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/..."
  imageTagMutability: IMMUTABLE
```

**Workflow:**

1. User pulls: `123456789012.dkr.ecr.us-east-1.amazonaws.com/docker-hub/nginx:latest`
2. ECR checks: Does this repository exist?
3. If not: Looks for a matching template (prefix `docker-hub`)
4. Finds the template and auto-creates the repository with KMS encryption + immutable tags
5. Fetches the image from Docker Hub and caches it

## Complete Example: Multi-Template Setup

```yaml
---
# Default template (development)
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: dev-template
  namespace: kro-system
spec:
  prefix: dev/
  appliedFor:
  - PULL_THROUGH_CACHE
  description: "Development caches: AES256 encryption, mutable tags"
  encryptionType: AES256
  imageTagMutability: MUTABLE
  deletionPolicy: retain

---
# Staging template (moderate controls)
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: staging-template
  namespace: kro-system
spec:
  prefix: staging/
  appliedFor:
  - PULL_THROUGH_CACHE
  - REPLICATION
  description: "Staging caches: KMS encryption, immutable tags"
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-staging"
  imageTagMutability: IMMUTABLE
  resourceTags:
  - key: environment
    value: staging
  deletionPolicy: retain

---
# Production template (strict controls)
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: prod-template
  namespace: kro-system
spec:
  prefix: prod/
  appliedFor:
  - PULL_THROUGH_CACHE
  - REPLICATION
  description: "Production caches: KMS encryption, immutable tags, lifecycle, compliance tags"
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-prod"
  imageTagMutability: IMMUTABLE
  lifecyclePolicy: |
    {
      "rules": [
        {
          "rulePriority": 1,
          "description": "Expire untagged after 7 days",
          "selection": {
            "tagStatus": "untagged",
            "countType": "sinceImagePushed",
            "countUnit": "days",
            "countNumber": 7
          },
          "action": { "type": "expire" }
        }
      ]
    }
  resourceTags:
  - key: environment
    value: production
  - key: compliance
    value: pci-dss
  - key: managed-by
    value: kropath
  deletionPolicy: retain

---
# Cache rules using these templates
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: dev-docker-hub
  namespace: kro-system
spec:
  ecrRepositoryPrefix: dev/docker-hub
  upstreamRegistryURL: registry-1.docker.io

---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRPullThroughCacheRule
metadata:
  name: prod-ghcr
  namespace: kro-system
spec:
  ecrRepositoryPrefix: prod/ghcr
  upstreamRegistryURL: ghcr.io
```

**Results:**
- Development caches: `dev/docker-hub/*` — AES256, mutable tags
- Staging caches: `staging/*` — KMS encryption, immutable tags
- Production caches: `prod/*` — Strict controls, lifecycle management, compliance tags

## Troubleshooting

### Template Not Applied

If auto-created repositories don't match the template configuration:

1. **Check prefix matching:**
   - Template prefix: `docker-hub`
   - Repository created: `docker-hub/nginx`
   - Match: ✓

2. **Verify `appliedFor`:**
   - If the repository was created via pull-through cache, check that `appliedFor` includes `PULL_THROUGH_CACHE`

3. **Check ECR templates:**
   ```bash
   aws ecr describe-repository-creation-templates --region us-east-1
   ```

### Cannot Change Prefix

If you need to change the prefix:

1. Delete the template: `kubectl delete ecrrepositorycreationtemplate <name>`
2. Create a new template with the desired prefix
3. Old repositories retain their original configuration
4. New repositories use the new template

## See Also

- [ECRPullThroughCacheRule](ecrpullthroughcacherule.md) — Configure pull-through caching
- [ECRRepository](ecrrepository.md) — Create manual repositories
- [ECRConfig](ecrconfig.md) — Set governance policies
