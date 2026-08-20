# ECRRepository — Creating and Managing Container Repositories

The `ECRRepository` resource creates and manages private AWS Elastic Container Registry repositories. Use it to store, manage, and deploy container images with encryption, tag mutability controls, and lifecycle management.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the repository resource is deleted: `"retain"` (safe) or `"delete"` |

### Repository Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `nameOverride` | string | `""` | Bypasses the naming template; sets the repository name directly |
| `registryID` | string | `""` | AWS account ID; defaults to the cluster's AWS account |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionType` | string | `""` | `AES256` (AWS-managed) or `KMS` (customer-managed); falls through to governance |
| `kmsKeyRef` | string | `""` | Reference to a kropath `KMSKey` resource (mutually exclusive with `kmsKeyArn`) |
| `kmsKeyArn` | string | `""` | Direct KMS key ARN (mutually exclusive with `kmsKeyRef`) |

### Image Tag Mutability

| Field | Type | Default | Purpose |
|---|---|---|---|
| `imageTagMutability` | string | `""` | `MUTABLE` (default, tags can be overwritten) or `IMMUTABLE` (supply chain security) |
| `imageTagMutabilityExclusionFilters` | array | `[]` | Exempt specific tags from mutability setting (e.g., exclude `latest` from IMMUTABLE) |

### Lifecycle and Access

| Field | Type | Default | Purpose |
|---|---|---|---|
| `lifecyclePolicy` | string | `""` | JSON policy to auto-expire images (e.g., untagged after 30 days) |
| `policy` | string | `""` | JSON repository access policy (cross-account access, role permissions) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels also synced to cloud tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Deprecated Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scanOnPush` | boolean | `false` | **Deprecated** — AWS recommends registry-level scanning instead; kept for backward compatibility |

## Status Fields

After the repository is created, you can read these output fields:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective repository name (after naming template substitution) |
| `namingStatus` | string | `valid` or `invalid-unresolved-tokens` (indicates if all naming tokens resolved) |
| `predictedArn` | string | Full ARN of the repository (e.g., `arn:aws:ecr:us-east-1:123456789012:repository/team/my-app`) |
| `repositoryURI` | string | **The primary runtime output** — use this in image pull secrets and deployments (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/team/my-app`) |

## Basic Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-app
  namespace: default
spec:
  configRef: general-policy
  deletionPolicy: retain
  tags:
    team: backend
    environment: production
```

After reconciliation:

```bash
$ kubectl get ecrrepository my-app -o jsonpath='{.status.repositoryURI}'
123456789012.dkr.ecr.us-east-1.amazonaws.com/default/my-app
```

Use this URI in your deployments:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/default/my-app:latest
```

## Encryption Examples

### AWS-Managed Encryption (Default)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: basic-app
  namespace: default
spec:
  configRef: general-policy
  # No encryption fields — falls back to AES256
```

- Encryption type: AES256 (AWS-managed)
- AWS manages key rotation automatically
- No additional cost

### Customer-Managed KMS Encryption

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: secure-app
  namespace: default
spec:
  configRef: general-policy
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

- Encryption type: KMS (customer-managed key)
- You control key access via IAM policies
- Required for compliance (PCI, HIPAA, SOC 2)
- **Important:** Cannot be changed after repository creation

### KMS Encryption via Reference

Use a kropath `KMSKey` resource instead of a direct ARN:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KMSKey
metadata:
  name: my-key
  namespace: default
spec:
  keySpec: SYMMETRIC_DEFAULT

---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: secure-app
  namespace: default
spec:
  configRef: general-policy
  encryptionType: KMS
  kmsKeyRef: my-key  # References the KMSKey resource above
```

## Image Tag Mutability

### Mutable Tags (Default)

```yaml
spec:
  imageTagMutability: MUTABLE
```

- Tags can be overwritten (typical for `latest`)
- Flexible for CI/CD pipelines
- May mask supply chain issues

### Immutable Tags (Supply Chain Security)

```yaml
spec:
  imageTagMutability: IMMUTABLE
```

- Tags are permanent once pushed
- Ensures reproducibility and traceability
- Recommended for production workloads
- Prevents accidental overwrite of released versions

### Immutable with Exclusions

Allow specific tags to be mutable while others remain immutable:

```yaml
spec:
  imageTagMutability: IMMUTABLE
  imageTagMutabilityExclusionFilters:
  - filter: "latest"
    filterType: WILDCARD
  - filter: "dev-*"
    filterType: WILDCARD
```

- Released versions (`v1.0`, `v1.1`) are immutable
- Development tags (`latest`, `dev-*`) can be overwritten
- Useful for gradual compliance enforcement

## Lifecycle Policies

Automatically expire old images to reduce storage costs:

```yaml
spec:
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
          "description": "Keep only last 10 builds",
          "selection": {
            "tagStatus": "tagged",
            "tagPrefixList": ["build-"],
            "countType": "imageCountMoreThan",
            "countNumber": 10
          },
          "action": {
            "type": "expire"
          }
        }
      ]
    }
```

**Common patterns:**

**Expire old untagged images:**
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

**Keep only latest release images:**
```json
{
  "rules": [{
    "rulePriority": 1,
    "description": "Keep last 5 releases",
    "selection": {
      "tagStatus": "tagged",
      "tagPrefixList": ["release-"],
      "countType": "imageCountMoreThan",
      "countNumber": 5
    },
    "action": { "type": "expire" }
  }]
}
```

## Repository Access Control

Grant other AWS accounts or roles permission to pull images:

```yaml
spec:
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

This allows the account `999888777666` to pull images from your repository.

## Governance Examples

### Development Repository (Permissive)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: dev-api
  namespace: team-backend
spec:
  configRef: development  # References the development ECRConfig profile
  tags:
    team: backend
```

**Profile enforcement:**
- Mutable tags (can overwrite `latest`)
- AES256 encryption
- No lifecycle policy
- Naming: `team-backend/dev-api`

### Production Repository (Strict)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: prod-api
  namespace: team-backend
spec:
  configRef: production  # References the production ECRConfig profile
  tags:
    team: backend
```

**Profile enforcement (from production ECRConfig):**
- Immutable tags (supply chain security)
- KMS encryption (compliance requirement)
- Automatic lifecycle policy (clean up old images)
- Naming: `team-backend/production/prod-api`

### Custom Naming

Override the default naming template:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-service
  namespace: default
spec:
  nameOverride: "legacy-service-v1"  # Direct repository name
  tags:
    team: platform
```

Repository name: `legacy-service-v1` (naming template ignored)

## Complete Production Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: payment-processor
  namespace: payments
spec:
  configRef: production
  deletionPolicy: retain
  encryptionType: KMS
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/cmk-payments"
  imageTagMutability: IMMUTABLE
  imageTagMutabilityExclusionFilters:
  - filter: "latest"
    filterType: WILDCARD
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
        },
        {
          "rulePriority": 2,
          "description": "Keep last 10 release images",
          "selection": {
            "tagStatus": "tagged",
            "tagPrefixList": ["v"],
            "countType": "imageCountMoreThan",
            "countNumber": 10
          },
          "action": { "type": "expire" }
        }
      ]
    }
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AllowPaymentTeamPull",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::123456789012:role/payment-team"
          },
          "Action": [
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage"
          ]
        }
      ]
    }
  tags:
    team: payments
    compliance: pci-dss
    criticality: high
  syncedLabels:
    data-sensitivity: financial
```

**Result:**
- Repository: `payments/production/payment-processor`
- KMS encryption with customer-managed key
- Immutable release tags, mutable `latest` tag
- Auto-expires untagged images after 7 days
- Keeps last 10 release images
- Only the payments team can pull
- Tags and labels synced to AWS

## Troubleshooting

### Repository URI Not Available

If `status.repositoryURI` is empty:

1. Check that the resource has reconciled successfully
2. View the conditions: `kubectl describe ecrrepository <name>`
3. Ensure the underlying ACK Repository resource was created: `kubectl get repository -n <namespace>`

### Naming Validation Failed

If `status.namingStatus` is `invalid-unresolved-tokens`:

1. Check the naming template for unresolved tokens (e.g., `{tag.missing-key}`)
2. Ensure all referenced tags exist in `spec.tags`
3. Fix the naming template or add missing tags

### Encryption Configuration Cannot Be Changed

If you try to change encryption on an existing repository:

Encryption configuration (type and key) is **immutable** after creation. To change encryption:

1. Create a new ECRRepository resource
2. Migrate images to the new repository
3. Delete the old repository

This is an AWS API limitation, not a kropath limitation.

## Using Repository URIs in Deployments

The `repositoryURI` is the full DNS name for pushing and pulling images:

```bash
# Push an image
docker tag my-image:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/team/my-app:v1.0
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/team/my-app:v1.0

# Pull from Kubernetes (requires image pull secret)
kubectl create secret docker-registry ecr-secret \
  --docker-server=123456789012.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1)
```

Deployment example:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      imagePullSecrets:
      - name: ecr-secret
      containers:
      - name: app
        image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/team/my-app:v1.0
```
