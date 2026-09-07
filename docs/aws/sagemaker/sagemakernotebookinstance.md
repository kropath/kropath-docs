# SageMakerNotebookInstance — Managed Jupyter Environment

The `SageMakerNotebookInstance` resource represents an EC2-backed managed Jupyter notebook environment for interactive ML development. It supports lifecycle configuration scripts for automated setup, VPC networking, and KMS encryption.

## Core Fields

### Instance Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the instance name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS instance) or `"delete"` (deletes AWS instance) |

### Compute Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `instanceType` | string | required | EC2 instance type (e.g., `ml.t3.medium`, `ml.p3.2xlarge`). Governable by `SageMakerConfig`. |
| `volumeSizeInGB` | integer | `5` | Root EBS volume size in GB. Governable by `SageMakerConfig`. |

### Networking & Security

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subnetId` | string | optional | Subnet ID for VPC placement |
| `securityGroupIds` | array | optional | Security group IDs for network access |
| `rootAccess` | string | `"Enabled"` | `"Enabled"` or `"Disabled"` — root user access. Governable by `SageMakerConfig`. |
| `directInternetAccess` | string | `"Enabled"` | `"Enabled"` (outbound internet) or `"Disabled"` (VPC-only). Governable by `SageMakerConfig`. |

### Encryption & Lifecycle

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyId` | string | `""` | KMS key for EBS encryption. Governable by `SageMakerConfig`. |
| `lifecycleConfigName` | string | `""` | Name of a lifecycle configuration for setup scripts |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the instance's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective instance name in AWS |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `notebookInstanceArn` | string | The ARN of the instance in AWS |
| `notebookInstanceUrl` | string | The URL to access the Jupyter notebook |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Notebook instances are named using a configurable template. The default template is `{namespace}-{name}`.

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only
- No leading/trailing hyphens

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerNotebookInstance
metadata:
  name: dev-notebook
  namespace: ml-team
spec:
  configRef: ml-production
  instanceType: ml.t3.large
  volumeSizeInGB: 20
  subnetId: subnet-11111111
  securityGroupIds:
    - sg-12345678
  rootAccess: Enabled
  directInternetAccess: Disabled
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
  lifecycleConfigName: ml-setup-config
  tags:
    Environment: development
    Team: ml-platform
```

## Dependencies

- **Requires:** VPC networking (EC2 family), IAM roles, optional KMS keys
- **Governance:** `SageMakerConfig` for instance type, root access, and network isolation
