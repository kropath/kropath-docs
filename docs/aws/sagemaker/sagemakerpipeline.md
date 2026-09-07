# SageMakerPipeline — ML Workflow Definition

The `SageMakerPipeline` resource defines an ML workflow as a JSON pipeline definition with steps for training, processing, evaluation, and model registration.

## Core Fields

### Pipeline Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the pipeline name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Pipeline Definition

| Field | Type | Default | Purpose |
|---|---|---|---|
| `pipelineDefinition` | string | required | JSON-serialized pipeline definition |
| `roleArn` | string | required | IAM role ARN for pipeline execution |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the pipeline's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective pipeline name in AWS |
| `pipelineArn` | string | The ARN of the pipeline in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerPipeline
metadata:
  name: ml-workflow
  namespace: ml-team
spec:
  configRef: ml-production
  roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  pipelineDefinition: |
    {
      "PipelineDefinitionBody": {
        "Version": "2020-12-01",
        "Steps": [
          {
            "Name": "TrainingStep",
            "Type": "Training",
            "Properties": {
              "TrainingJobName": "ml-training",
              "RoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
            }
          },
          {
            "Name": "EvaluationStep",
            "Type": "Processing",
            "DependsOn": ["TrainingStep"]
          }
        ]
      }
    }
  tags:
    Workflow: training-pipeline
```

## Dependencies

- **Requires:** IAM execution role
- **Governance:** `SageMakerConfig` for governance tagging
