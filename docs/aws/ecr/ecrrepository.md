# ECRRepository — Creating and Managing Container Image Repositories

The `ECRRepository` resource represents a private container image repository in AWS Elastic Container Registry. This guide covers all configuration fields, governance, naming, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ECRConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the repository name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keep in AWS) or `"delete"` (remove from AWS) |

### Image Tag Mutability

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `imageTagMutability` | string | `""` | Force tags to be `"IMMUTABLE"` or `"MUTABLE"`. Empty uses governance or AWS default (MUTABLE). Mandatory governance tier overrides this. |
| `imageTagMutabilityExclusionFilters` | array | `[]` | List of tag patterns to exempt from mutability enforcement. Useful to keep `latest` mutable while other tags are immutable. |

**Exclusion filter object:**
```yaml
imageTagMutabilityExclusionFilters:
  - filter: "latest"
    filterType: "WILDCARD"  # or EXACTMATCH
  - filter: "dev-*"
    filterType: "WILDCARD"
```

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `encryptionType` | string | `""` | Force encryption to `"AES256"` (AWS-managed) or `"KMS"` (customer-managed). Empty uses governance or AWS default. Mandatory governance tier overrides this. |
| `kmsKeyRef` | string | `""` | Reference to a local `KMSKey` CR. Mutually exclusive with `kmsKeyArn`. |
| `kmsKeyArn` | string | `""` | Direct AWS KMS key ARN, key ID, or alias. Mutually exclusive with `kmsKeyRef`. |

**Important:** `kmsKeyRef` and `kmsKeyArn` are mutually exclusive — set one or neither.

### Lifecycle Management

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `lifecyclePolicy` | string | `""` | JSON lifecycle policy document defining image retention rules. See AWS documentation for structure. |
| `policy` | string | `""` | JSON repository resource-based policy (for cross-account or cross-role access). |
| `deletionPolicy` | string | `"retain"` | When the Kubernetes resource is deleted, whether to `"retain"` or `"delete"` the AWS repository |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `tags` | map | `{}` | AWS tags applied to the repository; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Operational Fields

| Field | Type | Default | Purpose |
|---|---|---|---|---|
| `registryID` | string | `""` | AWS account ID. Empty uses the account where the controller runs. |
| `scanOnPush` | boolean | `false` | Enable image scanning on push (deprecated by AWS). |

## Status Outputs

After reconciliation, the repository's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective repository name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the resource name is ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `predictedArn` | string | ARN of the repository: `arn:aws:ecr:region:account:repository/resourceName` |
| `repositoryURI` | string | Full push/pull URI (e.g. `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-team/my-app`) — used by CI/CD pipelines and application deployments |
| `conditions[]` | array | Standard Kubernetes conditions (Ready, etc.) |

**`repositoryURI` is the operationally significant output.** Use this to configure image pull secrets, CI/CD pipeline push targets, and Pod `image` fields.

## Naming Convention

Repositories are named using a configurable template. The default template is `{namespace}/{name}`, which produces names like `app-team/my-app` (where `app-team` is the Kubernetes namespace and `my-app` is the resource name).

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Any tag key from the merged tags (e.g. `{tag.environment}`)

**Example template:** `{namespace}/{configRef}/{tag.environment}/{name}` produces `payments/pci/production/payment-processor` for a resource in the `payments` namespace with `configRef: pci` and `environment: production`.

**Important:** The repository name is immutable after creation in AWS. Changing `spec.nameOverride` or the governance naming template on an existing repository does not rename the AWS repository.

## Complete Examples

### Basic Repository

Create a simple repository with defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-app
  namespace: app-team
spec:
  configRef: general-policy
  deletionPolicy: retain
```

Result:
- Repository named `app-team/my-app` (using default naming template)
- AWS-managed encryption (`AES256`)
- Mutable image tags
- URI: `123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app`

### Repository with Immutable Tags and Custom Encryption

Enforce immutable tags and customer-managed encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: critical-service
  namespace: payments
spec:
  configRef: pci
  imageTagMutability: "IMMUTABLE"
  encryptionType: "KMS"
  kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/mrk-payments"
  tags:
    business-critical: "true"
    cost-center: "payments"
  deletionPolicy: retain
```

Result:
- Repository named `payments/pci/critical-service` (using PCI profile's naming template)
- Immutable image tags (cannot reassign tags)
- Encrypted with customer-managed KMS key
- Business-critical and cost-center tags applied

### Exclude Latest Tag from Mutability

Keep `latest` mutable for rapid iteration while other tags are immutable:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: web-app
  namespace: frontend
spec:
  configRef: general-policy
  imageTagMutability: "IMMUTABLE"
  imageTagMutabilityExclusionFilters:
    - filter: "latest"
      filterType: "WILDCARD"
    - filter: "dev-*"
      filterType: "WILDCARD"
  deletionPolicy: retain
```

Result:
- Tags like `v1.0`, `v1.1`, `v1.2` are immutable
- Tags like `latest`, `dev-`, `dev-branch-1` can be reassigned
- Developers can rapidly iterate with `latest` while production uses immutable version tags

### Lifecycle Policy for Image Retention

Define retention rules for automatic cleanup:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: build-artifacts
  namespace: ci-cd
spec:
  configRef: general-policy
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
          "description": "Keep only 10 most recent tagged images",
          "selection": {
            "tagStatus": "tagged",
            "tagPrefixList": ["release-"],
            "countType": "imageCountMoreThan",
            "countNumber": 10
          },
          "action": {
            "type": "expire"
          }
        }
      ]
    }
  deletionPolicy: retain
```

Result:
- Untagged images (build artifacts with no version tag) expire after 7 days
- Only the 10 most recent `release-*` tagged images are kept
- Older images are automatically removed, reducing storage costs

### Cross-Account Repository Access

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
            "AWS": "arn:aws:iam::111111111111:root"
          },
          "Action": [
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage"
          ]
        }
      ]
    }
  deletionPolicy: retain
```

Result:
- AWS account `111111111111` can pull images from this repository
- They cannot push or delete images
- Repository remains in your account; only read access is granted

## Governance Cascade

The effective configuration for each repository is determined by a three-tier cascade:

1. **Governance mandatory tier** (highest priority) — Platform enforcement that overrides everything
2. **Repository spec** (middle) — Developer choices
3. **Governance defaults tier** (lowest priority) — Fallback values

**Example:**
- PCI profile has `mandatory.imageTagMutability: "IMMUTABLE"`
- Repository specifies `imageTagMutability: "MUTABLE"`
- **Result:** Repository uses `IMMUTABLE` (mandatory overrides repository spec)

Platform teams use the mandatory tier for critical controls; they use the defaults tier to provide reasonable baselines that developers can override when needed.

## URI and Pull Secrets

The `status.repositoryURI` output is what you use to configure container deployments. Example URI: `123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app`

### In Kubernetes Pod Specs

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: app-team
spec:
  containers:
    - name: my-app
      image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app:latest
      imagePullPolicy: IfNotPresent
  imagePullSecrets:
    - name: ecr-pull-secret
```

### In CI/CD Pipelines

Use the URI as your image push target:

```bash
# Build image
docker build -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app:v1.0 .

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/app-team/my-app:v1.0
```

## Key Behaviors

### Immutable Repository Name After Creation

Once created in AWS ECR, a repository's name cannot be changed. The naming template or `nameOverride` field determines the name at creation time only.

### Encryption Configuration is Immutable

AWS ECR does not allow changing the encryption configuration after repository creation. You cannot convert from AES256 to KMS or vice versa without deleting and recreating the repository.

### Tag Format Conversion

Tags in kropath are specified as a map (e.g. `environment: production`). AWS ECR stores tags as a list of key-value pairs. The conversion is handled automatically.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the repository and all images safe in AWS ECR
- `delete` — Deleting the Kubernetes resource also deletes the ECR repository and all images (use with caution)

## Troubleshooting

### Repository Not Creating

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template has a token that cannot be resolved (e.g. a tag key that doesn't exist). Fix the template or ensure required tags are present.
- If `valid` but repository not created, check `status.conditions` for errors from AWS (e.g., permission issues, duplicate name).

### Can't Override Encryption or Tag Mutability

If governance has a mandatory tier set, those values cannot be overridden at the repository level. Only the defaults tier can be overridden by the developer. Contact your platform team if you need different settings.

### Repository Won't Delete When `deletionPolicy: delete`

Ensure the Kubernetes service account running kropath has AWS IAM permissions for `ecr:DeleteRepository`. The repository must also be empty (no images) before deletion, or the AWS API will reject the delete operation.

### URI Shows But Image Push Fails

Check:
1. Your CI/CD pipeline has AWS credentials with `ecr:PutImage` permission
2. You've authenticated Docker to ECR (run `aws ecr get-login-password | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com`)
3. The image name matches the repository name exactly
