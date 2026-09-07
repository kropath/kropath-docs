# SageMakerDataQualityJobDefinition — Data Drift Monitoring

The `SageMakerDataQualityJobDefinition` resource specifies the analysis algorithm and configuration for detecting data drift in endpoint inputs.

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

### Data Quality Monitoring

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dataQualityAppSpecification.imageUri` | string | required | Container image for data quality analysis |
| `dataQualityBaselineConfig.baseliningJobName` | string | optional | Baseline job reference for drift comparison |

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
kind: SageMakerDataQualityJobDefinition
metadata:
  name: data-quality-monitoring
  namespace: ml-team
spec:
  configRef: ml-production
  roleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  jobResources:
    clusterConfig:
      instanceCount: 1
      instanceType: ml.m5.xlarge
  dataQualityAppSpecification:
    imageUri: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-model-monitor-container
  tags:
    MonitoringType: data-quality
```

## Dependencies

- **Requires:** IAM execution role, optional baseline job
- **Referenced by:** `SageMakerMonitoringSchedule`
- **Governance:** `SageMakerConfig` for instance type enforcement
