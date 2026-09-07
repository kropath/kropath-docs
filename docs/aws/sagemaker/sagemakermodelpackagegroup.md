# SageMakerModelPackageGroup — Model Registry Container

The `SageMakerModelPackageGroup` resource is a logical container for organizing versioned model packages in the model registry.

## Core Fields

### Group Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Group Settings

| Field | Type | Default | Purpose |
|---|---|---|---|
| `modelPackageGroupDescription` | string | optional | Description of the model package group |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the group's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective group name in AWS |
| `modelPackageGroupArn` | string | The ARN of the model package group in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerModelPackageGroup
metadata:
  name: xgboost-models
  namespace: ml-team
spec:
  configRef: ml-production
  modelPackageGroupDescription: XGBoost model versions for production
  tags:
    ModelType: xgboost
    Department: ml-platform
```

## Dependencies

- **Referenced by:** `SageMakerModelPackage`
- **Governance:** `SageMakerConfig` for governance tagging
