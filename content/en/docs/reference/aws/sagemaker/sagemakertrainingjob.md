---
title: SageMakerTrainingJob — Model Training Execution
description: "The `SageMakerTrainingJob` resource runs model training on managed ML compute with full configuration for algorithms, hyperparameters, input/output data, debugging, and profiling."
doc_type: reference
---
# SageMakerTrainingJob — Model Training Execution

The `SageMakerTrainingJob` resource runs model training on managed ML compute with full configuration for algorithms, hyperparameters, input/output data, debugging, and profiling.

## Core Fields

### Job Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the job name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS job) or `"delete"` (deletes AWS job) |

### Compute Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `roleArn` | string | required | IAM role ARN for training job execution |
| `algorithmSpecification` | object | required | Training algorithm and image |
| `algorithmSpecification.trainingImage` | string | optional | Docker image for training (e.g., SageMaker built-in algorithm) |
| `instanceCount` | integer | `1` | Number of training instances. Governable by `SageMakerConfig`. |
| `instanceType` | string | required | Instance type for training. Governable by `SageMakerConfig`. |
| `volumeSizeInGB` | integer | `30` | EBS volume size. Governable by `SageMakerConfig`. |

### Data Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `inputDataConfig` | array | required | Training data input channels |
| `inputDataConfig[].channelName` | string | required | Channel name (e.g., `"training"`, `"validation"`) |
| `inputDataConfig[].dataSource.s3DataSource.s3Uri` | string | required | S3 path to training data |
| `outputDataConfig.s3OutputPath` | string | required | S3 path for training output artifacts |

### Hyperparameters

| Field | Type | Default | Purpose |
|---|---|---|---|
| `hyperParameters` | map | optional | Algorithm hyperparameters (e.g., `max_depth: "5"`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the job's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective job name in AWS |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `trainingJobArn` | string | The ARN of the training job in AWS |
| `trainingJobStatus` | string | Current status (`"InProgress"`, `"Completed"`, `"Failed"`, `"Stopping"`, `"Stopped"`) |
| `modelArtifacts.s3ModelArtifacts` | string | S3 path to output model artifacts |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Training jobs are named using a configurable template. The default template is `{namespace}-{name}`.

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only
- No leading/trailing hyphens

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerTrainingJob
metadata:
  name: xgboost-training
  namespace: ml-team
spec:
  configRef: ml-production
  roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  algorithmSpecification:
    trainingImage: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.5-1
  instanceCount: 2
  instanceType: ml.m5.xlarge
  volumeSizeInGB: 50
  inputDataConfig:
    - channelName: training
      dataSource:
        s3DataSource:
          s3Uri: s3://my-bucket/train
    - channelName: validation
      dataSource:
        s3DataSource:
          s3Uri: s3://my-bucket/validation
  outputDataConfig:
    s3OutputPath: s3://my-bucket/output
  hyperParameters:
    max_depth: "5"
    eta: "0.2"
    objective: "binary:logistic"
  tags:
    Algorithm: xgboost
    Dataset: v1
```

## Dependencies

- **Requires:** IAM execution role, S3 buckets for input/output
- **Governance:** `SageMakerConfig` for instance type and volume size enforcement
