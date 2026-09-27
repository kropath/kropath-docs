---
title: SageMakerModelPackage — Versioned Model Artifact
description: "The `SageMakerModelPackage` resource represents a versioned model artifact with inference specifications, metrics, and approval status within a model package group."
doc_type: reference
---
# SageMakerModelPackage — Versioned Model Artifact

The `SageMakerModelPackage` resource represents a versioned model artifact with inference specifications, metrics, and approval status within a model package group.

## Core Fields

### Package Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |
| `modelPackageGroupName` | string | required | Parent `SageMakerModelPackageGroup` name |

### Package Content

| Field | Type | Default | Purpose |
|---|---|---|---|
| `inferenceSpecification` | object | required | Container specifications for inference |
| `modelMetrics` | object | optional | Model performance metrics |
| `modelApprovalStatus` | string | `"PendingManualApproval"` | `"PendingManualApproval"`, `"Approved"`, or `"Rejected"` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the package's status contains:

| Field | Type | Purpose |
|---|---|---|
| `modelPackageArn` | string | The ARN of the model package in AWS |
| `modelPackageStatus` | string | Current status |
| `conditions` | array | Status conditions (ready, error, etc.) |


## Naming Convention

Resource names are generated from a template using:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{tag.<key>}` | Tag value |

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** 1–63 characters, alphanumeric and hyphens only
- **Predicted ARN:** computed from the resource name

Naming templates support dynamic tag field substitution — use `{tag.fieldName}` to embed tag values directly into resource names. For details on tag resolution, provider constraints, and examples, see [Dynamic Tag Fields in Naming Templates](../../../concepts/configuration/naming-templates.md).


## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerModelPackage
metadata:
  name: xgboost-v1
  namespace: ml-team
spec:
  configRef: ml-production
  modelPackageGroupName: xgboost-models
  inferenceSpecification:
    containers:
      - image: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.5-1
        modelDataUrl: s3://my-bucket/models/xgboost-v1.tar.gz
  modelMetrics:
    modelQuality:
      statistics:
        contentType: application/json
        s3Uri: s3://my-bucket/metrics/quality.json
  modelApprovalStatus: PendingManualApproval
  tags:
    Version: "1.0"
```

## Dependencies

- **Requires:** Parent `SageMakerModelPackageGroup`
- **Governance:** `SageMakerConfig` for governance tagging
