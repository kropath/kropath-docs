---
title: SageMakerTransformJob — Batch Inference Execution
description: "The `SageMakerTransformJob` resource runs offline batch inference against an existing model on a dataset."
doc_type: reference
---
# SageMakerTransformJob — Batch Inference Execution

The `SageMakerTransformJob` resource runs offline batch inference against an existing model on a dataset. It's ideal for processing large datasets without the overhead of a real-time endpoint.

## Core Fields

### Job Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the job name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Model & Data Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `modelName` | string | required | Name of the `SageMakerModel` to use for inference |
| `transformInput.dataSource.s3DataSource.s3Uri` | string | required | S3 path to input data |
| `transformOutput.s3OutputPath` | string | required | S3 path for output predictions |

### Compute Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `transformResources.instanceCount` | integer | `1` | Number of transform instances |
| `transformResources.instanceType` | string | required | Instance type. Governable by `SageMakerConfig`. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the job's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective job name in AWS |
| `transformJobArn` | string | The ARN of the transform job in AWS |
| `transformJobStatus` | string | Current status (`"InProgress"`, `"Completed"`, `"Failed"`, etc.) |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerTransformJob
metadata:
  name: batch-inference
  namespace: ml-team
spec:
  configRef: ml-production
  modelName: xgboost-model
  transformInput:
    dataSource:
      s3DataSource:
        s3Uri: s3://my-bucket/batch-data
  transformOutput:
    s3OutputPath: s3://my-bucket/predictions
  transformResources:
    instanceCount: 2
    instanceType: ml.m5.xlarge
  tags:
    Batch: "true"
```

## Dependencies

- **Requires:** `SageMakerModel`, S3 buckets for input/output
- **Governance:** `SageMakerConfig` for instance type enforcement
