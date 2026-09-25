---
title: SageMakerSpace — Shared Collaborative Space
description: "The `SageMakerSpace` resource represents a shared collaborative space within a SageMaker Studio domain — a shared compute, storage, and configuration environment for multiple users."
doc_type: reference
---
# SageMakerSpace — Shared Collaborative Space

The `SageMakerSpace` resource represents a shared collaborative space within a SageMaker Studio domain — a shared compute, storage, and configuration environment for multiple users. Shared spaces enable team-based ML development with centralized resource management.

## Core Fields

### Space Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the space name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS space) or `"delete"` (deletes AWS space) |
| `domainId` | string | required | ID of the parent SageMaker domain |
| `spaceName` | string | required | The space's name within the domain |

### Space Type

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spaceType` | string | required | Type of space: `"JupyterLab"` or `"Code"` |

### Space Settings

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spaceSettings` | object | optional | Jupyter server, KernelGateway, and space-specific defaults |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the space's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective space name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `spaceArn` | string | The ARN of the space in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Shared spaces are named using a configurable template. The default template is `{namespace}-{name}`.

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
kind: SageMakerSpace
metadata:
  name: team-notebooks
  namespace: ml-team
spec:
  configRef: ml-production
  domainId: d-12345678abcd
  spaceName: team-notebooks
  spaceType: JupyterLab
  spaceSettings:
    jupyterServerAppSettings:
      defaultResourceSpec:
        instanceType: ml.t3.medium
        sageMakerImageArn: arn:aws:sagemaker:us-east-1:246618743249:image/sagemaker-data-science-310
  tags:
    Team: ml-platform
    Purpose: team-development
```

## Dependencies

- **Requires:** Parent `SageMakerDomain` (specified by `domainId`)
- **Governance:** `SageMakerConfig` for instance type enforcement and network isolation
