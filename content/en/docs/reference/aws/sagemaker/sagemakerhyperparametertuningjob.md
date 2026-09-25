---
title: SageMakerHyperParameterTuningJob — Automated Hyperparameter Optimization
description: "The `SageMakerHyperParameterTuningJob` resource runs automated hyperparameter optimization over one or more training job definitions to find the best model configuration."
doc_type: reference
---
# SageMakerHyperParameterTuningJob — Automated Hyperparameter Optimization

The `SageMakerHyperParameterTuningJob` resource runs automated hyperparameter optimization over one or more training job definitions to find the best model configuration.

## Core Fields

### Job Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the job name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Tuning Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `hyperParameterTuningJobConfig.strategy` | string | `"Bayesian"` | `"Bayesian"`, `"Random"`, or `"Grid"` |
| `hyperParameterTuningJobConfig.hyperParameterTuningJobObjective.type` | string | required | `"Maximize"` or `"Minimize"` |
| `hyperParameterTuningJobConfig.hyperParameterTuningJobObjective.metricName` | string | required | Metric to optimize (e.g., `"validation:accuracy"`) |

### Training Job Definition

| Field | Type | Default | Purpose |
|---|---|---|---|
| `trainingJobDefinition.roleArn` | string | required | IAM role for training jobs |
| `trainingJobDefinition.algorithmSpecification.trainingImage` | string | required | Docker image for training |
| `trainingJobDefinition.inputDataConfig` | array | required | Training data channels |
| `trainingJobDefinition.outputDataConfig.s3OutputPath` | string | required | S3 path for model artifacts |
| `trainingJobDefinition.resourceConfig.instanceType` | string | required | Instance type for training |
| `trainingJobDefinition.resourceConfig.instanceCount` | integer | `1` | Number of training instances |

### Hyperparameter Ranges

| Field | Type | Default | Purpose |
|---|---|---|---|
| `hyperParameterRanges.continuousParameterRanges` | array | optional | Ranges for continuous parameters |
| `hyperParameterRanges.integerParameterRanges` | array | optional | Ranges for integer parameters |
| `hyperParameterRanges.categoricalParameterRanges` | array | optional | Ranges for categorical parameters |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the job's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective job name in AWS |
| `hyperParameterTuningJobArn` | string | The ARN of the tuning job in AWS |
| `hyperParameterTuningJobStatus` | string | Current status (`"InProgress"`, `"Completed"`, `"Failed"`, etc.) |
| `bestTrainingJob` | object | Best training job found during tuning |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerHyperParameterTuningJob
metadata:
  name: xgboost-tuning
  namespace: ml-team
spec:
  configRef: ml-production
  hyperParameterTuningJobConfig:
    strategy: Bayesian
    hyperParameterTuningJobObjective:
      type: Maximize
      metricName: validation:accuracy
  trainingJobDefinition:
    roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
    algorithmSpecification:
      trainingImage: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.5-1
    inputDataConfig:
      - channelName: training
        dataSource:
          s3DataSource:
            s3Uri: s3://my-bucket/train
    outputDataConfig:
      s3OutputPath: s3://my-bucket/output
    resourceConfig:
      instanceType: ml.m5.xlarge
      instanceCount: 2
      volumeSizeInGB: 50
  hyperParameterRanges:
    continuousParameterRanges:
      - parameterName: eta
        minValue: "0.1"
        maxValue: "0.5"
    integerParameterRanges:
      - parameterName: max_depth
        minValue: "3"
        maxValue: "10"
  tags:
    Algorithm: xgboost
```

## Dependencies

- **Requires:** IAM execution role, training algorithm image, S3 buckets
- **Governance:** `SageMakerConfig` for instance type enforcement
