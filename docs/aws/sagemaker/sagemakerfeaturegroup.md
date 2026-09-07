# SageMakerFeatureGroup — ML Feature Store

The `SageMakerFeatureGroup` resource represents a collection of features for ML models, with online and/or offline storage backing for feature engineering and retrieval.

## Core Fields

### Group Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |
| `recordIdentifierFeatureName` | string | required | Feature name serving as the record identifier |

### Feature Definition

| Field | Type | Default | Purpose |
|---|---|---|---|
| `featureDefinitions` | array | required | List of feature definitions with names and types |
| `featureGroupStatus` | string | `"InProgress"` | Group status during creation |

### Feature Store Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `onlineStoreConfig.enableOnlineStore` | boolean | `false` | Enable online feature store |
| `offlineStoreConfig.s3StorageConfig.s3Uri` | string | optional | S3 path for offline feature store |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the group's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective group name in AWS |
| `featureGroupArn` | string | The ARN of the feature group in AWS |
| `featureGroupStatus` | string | `"Created"` or `"Failed"` |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerFeatureGroup
metadata:
  name: user-features
  namespace: ml-team
spec:
  configRef: ml-production
  recordIdentifierFeatureName: user_id
  featureDefinitions:
    - featureName: user_id
      featureType: String
    - featureName: age
      featureType: Integral
    - featureName: revenue
      featureType: Fractional
  onlineStoreConfig:
    enableOnlineStore: true
  offlineStoreConfig:
    s3StorageConfig:
      s3Uri: s3://my-bucket/features
  tags:
    Domain: user-analytics
```

## Dependencies

- **Requires:** S3 bucket for offline storage (optional online store)
- **Governance:** `SageMakerConfig` for governance tagging
