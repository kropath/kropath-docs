---
title: SageMakerDomain — Studio Workspace Container
description: "The `SageMakerDomain` resource represents a SageMaker Studio domain — the top-level organizational container for user profiles, shared spaces, and collaborative applications."
doc_type: reference
---
# SageMakerDomain — Studio Workspace Container

The `SageMakerDomain` resource represents a SageMaker Studio domain — the top-level organizational container for user profiles, shared spaces, and collaborative applications. It controls authentication mode (IAM or SSO), VPC networking, default user settings, and EFS/EBS encryption.

## Core Fields

### Domain Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the domain name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS domain) or `"delete"` (deletes AWS domain) |
| `authMode` | string | required | `"IAM"` or `"SSO"` — authentication mode for domain access |

### Network Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `vpcId` | string | required | VPC ID for domain communication |
| `subnetIds` | array | required | Subnet IDs for domain communication |
| `appNetworkAccessType` | string | `"VpcOnly"` | `"VpcOnly"` (private access) or `"PublicInternetOnly"`. Governable by `SageMakerConfig`. |
| `appSecurityGroupManagement` | string | `""` | `"Service"` (AWS manages) or `"Customer"` (you manage). Governable by `SageMakerConfig`. |

### Security & Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyId` | string | `""` | KMS key ID for EFS/EBS encryption. Governable by `SageMakerConfig`. |
| `enableNetworkIsolation` | boolean | `false` | Enforce network isolation. Governable by `SageMakerConfig`. |

### Default Settings

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaultUserSettings` | object | required | Default execution role, security groups, and Jupyter/kernel settings for user profiles |
| `defaultSpaceSettings` | object | `{}` | Default settings inherited by shared spaces |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the domain's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective domain name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `domainId` | string | System-assigned domain ID (e.g., `d-xxxx`); exposed post-creation |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Domains are named using a configurable template. The default template is `{namespace}-{name}`, which produces names like `ml-team-studio`.

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from the merged tags

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only
- No leading/trailing hyphens

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerDomain
metadata:
  name: studio-domain
  namespace: ml-team
spec:
  configRef: ml-production
  authMode: IAM
  vpcId: vpc-12345678
  subnetIds:
    - subnet-11111111
    - subnet-22222222
  appNetworkAccessType: VpcOnly
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
  defaultUserSettings:
    executionRole: arn:aws:iam::123456789012:role/SageMakerExecutionRole
    sharingSettings:
      notebookOutputOption: AllowSharedNotebookAccess
  tags:
    Environment: production
    Team: ml-platform
```

## Dependencies

- **Requires:** VPC networking (EC2 family), IAM roles for execution
- **Referenced by:** `SageMakerUserProfile`, `SageMakerSpace` (via `domainId`)
- **Governance:** `SageMakerConfig` for network isolation, encryption, and network access policy
