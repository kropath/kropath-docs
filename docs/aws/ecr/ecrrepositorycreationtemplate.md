# ECRRepositoryCreationTemplate — Governing Auto-Created Repositories

The `ECRRepositoryCreationTemplate` resource governs how repositories are automatically created by ECR when triggered by pull-through cache rules or cross-region replication. When ECR auto-creates a repository, it matches the image path against your templates and applies the matching template's encryption, tag mutability, lifecycle policy, and tags to the new repository.

## Use Cases

- **Compliance enforcement:** Ensure all auto-created repositories have KMS encryption and immutable tags
- **Cost governance:** Apply lifecycle policies to auto-created repositories for automatic cleanup
- **Tagging automation:** Add required AWS tags to repositories created by pull-through cache
- **Cross-region replication:** Control how repositories are configured when replicated to other regions

## Core Fields

### Template Identity

| Field | Type | Required | Immutable | Purpose |
|---|---|---|---|---|
| `prefix` | string | Yes | Yes | Namespace prefix for auto-created repositories (e.g. `"prod/"`, `"staging/"`, `"ROOT"` for catch-all). Immutable after creation. |
| `appliedFor` | array | Yes | No | When the template applies: `["PULL_THROUGH_CACHE"]`, `["REPLICATION"]`, or both |
| `description` | string | No | No | Human-readable description of when and why this template is used |

**Prefix matching:** Repositories created with names matching the prefix use this template's configuration.

### Repository Configuration

These fields are applied to auto-created repositories (not subject to `ECRConfig` governance):

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `encryptionType` | string | `""` | Force auto-created repos to use `"AES256"` or `"KMS"` encryption. Empty uses AWS default. |
| `kmsKeyRef` | string | `""` | Reference to a local `KMSKey` CR for encryption. Mutually exclusive with `kmsKeyArn`. |
| `kmsKeyArn` | string | `""` | Direct KMS key ARN for encryption. Mutually exclusive with `kmsKeyRef`. |
| `imageTagMutability` | string | `""` | Force auto-created repos to use `"IMMUTABLE"` or `"MUTABLE"` tags. Empty uses AWS default. |
| `imageTagMutabilityExclusionFilters` | array | `[]` | Exemptions to tag mutability (e.g., allow `latest` to be mutable) |
| `lifecyclePolicy` | string | `""` | JSON lifecycle policy for automatic image cleanup |
| `repositoryPolicy` | string | `""` | JSON resource-based policy for access control |
| `resourceTags` | array | `[]` | Cloud resource tags (`{key, value}` pairs) applied to auto-created repos |
| `customRoleArn` | string | `""` | IAM role ARN for template-driven creation |

### Governance and Deletion

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` profile for K8s-level tagging (not for repository configuration) |
| `deletionPolicy` | string | `"retain"` | When the template resource is deleted: `"retain"` or `"delete"` |
| `tags` | map | `{}` | Kubernetes labels on this template resource (K8s metadata only) |
| `syncedLabels` | map | `{}` | Kubernetes labels synced to the template (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Examples

### Production Template with KMS and Immutable Tags

Ensure all production repositories are encrypted with KMS and have immutable tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: prod-template
  namespace: kro-system
spec:
  prefix: "prod/"
  appliedFor:
    - "PULL_THROUGH_CACHE"
    - "REPLICATION"
  description: "Production repositories: KMS encryption, immutable tags, strict lifecycle"
  encryptionType: "KMS"
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-production"
  imageTagMutability: "IMMUTABLE"
  lifecyclePolicy: |
    {
      "rules": [
        {
          "rulePriority": 1,
          "description": "Expire untagged images after 30 days",
          "selection": {
            "tagStatus": "untagged",
            "countType": "sinceImagePushed",
            "countUnit": "days",
            "countNumber": 30
          },
          "action": {
            "type": "expire"
          }
        }
      ]
    }
  resourceTags:
    - key: environment
      value: production
    - key: compliance
      value: required
  deletionPolicy: retain
```

Result:
- Repositories with names starting with `prod/` are created with:
  - KMS encryption using the specified production key
  - Immutable tags (cannot reassign tags)
  - Lifecycle policy that removes untagged images after 30 days
  - AWS tags `environment=production` and `compliance=required`

### Staging Template with Default Encryption

Staging repositories use AWS-managed encryption and mutable tags for faster iteration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: staging-template
  namespace: kro-system
spec:
  prefix: "staging/"
  appliedFor:
    - "PULL_THROUGH_CACHE"
  description: "Staging repositories: AWS-managed encryption, mutable tags"
  encryptionType: "AES256"
  imageTagMutability: "MUTABLE"
  resourceTags:
    - key: environment
      value: staging
  deletionPolicy: retain
```

Result:
- Repositories with names starting with `staging/` are created with:
  - AWS-managed AES256 encryption
  - Mutable tags for rapid iteration
  - Staging environment tag

### Exclude Latest Tag from Immutability

Keep `latest` mutable for rapid pushes while other tags are immutable:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: ci-cd-template
  namespace: kro-system
spec:
  prefix: "ci-cd/"
  appliedFor:
    - "PULL_THROUGH_CACHE"
  description: "CI/CD repositories: immutable version tags, mutable latest"
  imageTagMutability: "IMMUTABLE"
  imageTagMutabilityExclusionFilters:
    - filter: "latest"
      filterType: "WILDCARD"
    - filter: "dev-*"
      filterType: "WILDCARD"
  resourceTags:
    - key: purpose
      value: cicd-builds
  deletionPolicy: retain
```

Result:
- Repositories with names starting with `ci-cd/` are created with:
  - Immutable tags for production versions
  - Exception: `latest` and `dev-*` tags can be reassigned
  - CI/CD purpose tag

### Cross-Region Replication Template

Configure repositories created by cross-region replication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: replication-template
  namespace: kro-system
spec:
  prefix: "replicated/"
  appliedFor:
    - "REPLICATION"
  description: "Repositories created by cross-region replication"
  encryptionType: "KMS"
  kmsKeyArn: "arn:aws:kms:us-west-2:123456789012:key/mrk-dr"
  imageTagMutability: "IMMUTABLE"
  resourceTags:
    - key: purpose
      value: disaster-recovery
  deletionPolicy: retain
```

Result:
- Repositories created during cross-region replication with names starting with `replicated/` are configured with:
  - Regional KMS encryption (using the DR region's key)
  - Immutable tags
  - Disaster-recovery purpose tag

### Permissive Catch-All Template

A catch-all template (ROOT prefix) applied when no more specific template matches:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepositoryCreationTemplate
metadata:
  name: default-template
  namespace: kro-system
spec:
  prefix: "ROOT"
  appliedFor:
    - "PULL_THROUGH_CACHE"
    - "REPLICATION"
  description: "Default template for all other repositories"
  encryptionType: "AES256"
  imageTagMutability: "MUTABLE"
  resourceTags:
    - key: managed-by
      value: kropath
  deletionPolicy: retain
```

Result:
- Any repository not matching a more specific prefix uses this default template
- AWS-managed encryption, mutable tags

## How Templates are Matched

When ECR creates a repository, it searches for matching templates based on the repository name (prefix):

1. **Exact match:** If a template has `prefix: "prod/nginx/"` and the repo is `prod/nginx/api`, use that template
2. **Longest prefix:** If multiple templates match, the one with the longest matching prefix is used
3. **ROOT fallback:** If no prefix matches, the template with `prefix: "ROOT"` is used

**Example matching:**
- Repository name: `prod/web/frontend`
- Available templates:
  - `prefix: "prod/"` (matches)
  - `prefix: "prod/web/"` (matches, longer)
  - `prefix: "staging/"` (no match)
  - `prefix: "ROOT"` (fallback)
- **Result:** Template with `prefix: "prod/web/"` is used

## Key Behaviors

### Immutable Prefix

Once created, the `prefix` cannot be changed. To change the prefix, delete the template and create a new one.

### Not Governed by ECRConfig

Unlike `ECRRepository` resources, the template's encryption, tag mutability, and lifecycle policy settings are **NOT** subject to `ECRConfig` governance. The template itself IS the governance mechanism for auto-created repositories.

This is intentional: templates are platform infrastructure that control auto-creation, while `ECRConfig` controls manual repository creation.

### Fields vs Template Configuration

The `tags` field (Kubernetes metadata) is different from `resourceTags`:
- **`tags`** — Kubernetes labels on the template resource itself
- **`resourceTags`** — AWS tags applied to the auto-created repositories

### No Direct Management of Auto-Created Repositories

Auto-created repositories are created directly by AWS ECR, not through kropath. You cannot update an auto-created repository through Kubernetes (it has no Kubernetes resource). To change an auto-created repository's configuration, update the template and recreate the repository in AWS (delete and re-pull the image).

## Troubleshooting

### Template Not Applied

Check:
1. The repository name matches the template's `prefix`
2. The template's `appliedFor` includes the scenario (PULL_THROUGH_CACHE or REPLICATION)
3. The template is in the `kro-system` namespace

### Can't Change Immutable Fields

Once created, these cannot be changed without recreating:
- `prefix`

To change the prefix, delete the template and create a new one. **Note:** This does not affect already auto-created repositories.

### Auto-Created Repository Has Wrong Configuration

If an auto-created repository doesn't have the expected encryption or tags:

1. Check that a matching template exists and is applied for the scenario
2. Verify the repository was created **after** the template was deployed
3. If created before the template existed, it won't use the template's configuration — you must delete and recreate it (pull the image again)

### Multiple Templates Match, Wrong One Applied

If multiple templates have prefixes that match the repository name, the one with the **longest prefix** is used. Ensure your template organization has non-overlapping or hierarchical prefixes:
- `prod/` (matches all prod repositories)
- `prod/web/` (matches prod web repos specifically)

Use hierarchical prefixes to avoid ambiguity.
