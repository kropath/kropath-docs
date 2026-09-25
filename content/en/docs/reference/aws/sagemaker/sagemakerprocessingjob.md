---
title: SageMakerProcessingJob — Data Processing Execution
description: "The `SageMakerProcessingJob` resource runs data processing, feature engineering, or model evaluation on managed ML compute with full configuration for containers, input/output data, and framework support."
doc_type: reference
---
# SageMakerProcessingJob — Data Processing Execution

The `SageMakerProcessingJob` resource runs data processing, feature engineering, or model evaluation on managed ML compute with full configuration for containers, input/output data, and framework support.

## Core Fields

### Job Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the job name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Processing Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `roleArn` | string | required | IAM role ARN for processing job execution |
| `processingInputs` | array | required | Input data channels |
| `processingInputs[].inputName` | string | required | Channel name for input |
| `processingInputs[].s3Input.s3Uri` | string | required | S3 path to input data |
| `processingOutputConfig.outputs` | array | required | Output data locations |
| `processingOutputConfig.outputs[].outputName` | string | required | Channel name for output |
| `processingOutputConfig.outputs[].s3Output.s3Uri` | string | required | S3 path for output |

### Compute Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `processingResources.clusterConfig.instanceCount` | integer | `1` | Number of processing instances |
| `processingResources.clusterConfig.instanceType` | string | required | Instance type. Governable by `SageMakerConfig`. |
| `processingResources.clusterConfig.volumeSizeInGB` | integer | `30` | EBS volume size |

### Container Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `appSpecification.imageUri` | string | required | Docker image for processing |
| `appSpecification.containerArguments` | array | optional | Arguments to pass to the container |
| `appSpecification.containerEntrypoint` | array | optional | Entrypoint command |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the job's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective job name in AWS |
| `processingJobArn` | string | The ARN of the processing job in AWS |
| `processingJobStatus` | string | Current status (`"InProgress"`, `"Completed"`, `"Failed"`, etc.) |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerProcessingJob
metadata:
  name: data-preprocessing
  namespace: ml-team
spec:
  configRef: ml-production
  roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  processingInputs:
    - inputName: input-data
      s3Input:
        s3Uri: s3://my-bucket/raw-data
  processingOutputConfig:
    outputs:
      - outputName: processed-data
        s3Output:
          s3Uri: s3://my-bucket/processed
  processingResources:
    clusterConfig:
      instanceCount: 2
      instanceType: ml.m5.xlarge
      volumeSizeInGB: 50
  appSpecification:
    imageUri: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1
    containerArguments:
      - "--drop-duplicates"
      - "--normalize"
  tags:
    Stage: preprocessing
```

## Dependencies

- **Requires:** IAM execution role, S3 buckets for input/output
- **Governance:** `SageMakerConfig` for instance type enforcement
