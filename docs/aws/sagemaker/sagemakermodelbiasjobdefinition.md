# SageMakerModelBiasJobDefinition — Model Bias Monitoring

The `SageMakerModelBiasJobDefinition` resource specifies configuration for detecting bias in model predictions.

## Core Fields

### Job Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the job name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Job Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `jobResources.clusterConfig.instanceCount` | integer | `1` | Number of monitoring instances |
| `jobResources.clusterConfig.instanceType` | string | required | Instance type. Governable by `SageMakerConfig`. |
| `roleArn` | string | required | IAM role for job execution |

### Model Bias Monitoring

| Field | Type | Default | Purpose |
|---|---|---|---|
| `modelBiasAppSpecification.imageUri` | string | required | Container image for model bias analysis |
| `modelBiasBaselineConfig.baseliningJobName` | string | optional | Baseline job reference for drift comparison |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the definition's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective job definition name in AWS |
| `jobDefinitionArn` | string | The ARN of the job definition in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerModelBiasJobDefinition
metadata:
  name: model-bias-monitoring
  namespace: ml-team
spec:
  configRef: ml-production
  roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  jobResources:
    clusterConfig:
      instanceCount: 1
      instanceType: ml.m5.xlarge
  modelBiasAppSpecification:
    imageUri: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-container
  tags:
    MonitoringType: model-bias
```

## Dependencies

- **Requires:** IAM execution role, optional baseline job
- **Referenced by:** `SageMakerMonitoringSchedule`
- **Governance:** `SageMakerConfig` for instance type enforcement
