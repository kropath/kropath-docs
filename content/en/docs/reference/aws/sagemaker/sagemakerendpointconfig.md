---
title: SageMakerEndpointConfig — Endpoint Hosting Configuration
description: "The `SageMakerEndpointConfig` resource specifies which models to host on an endpoint, with production variant weights, instance types, data capture settings, and optional async inference configuration."
doc_type: reference
---
# SageMakerEndpointConfig — Endpoint Hosting Configuration

The `SageMakerEndpointConfig` resource specifies which models to host on an endpoint, with production variant weights, instance types, data capture settings, and optional async inference configuration. It decouples model definition from endpoint deployment.

## Core Fields

### Config Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the config name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS config) or `"delete"` (deletes AWS config) |

### Production Variants

| Field | Type | Default | Purpose |
|---|---|---|---|
| `productionVariants` | array | required | List of model variants to host on this endpoint |
| `productionVariants[].modelName` | string | required | Name of the `SageMakerModel` to deploy |
| `productionVariants[].variantName` | string | required | Name of this variant (e.g., `"primary"`, `"canary"`) |
| `productionVariants[].instanceType` | string | required | Instance type for this variant. Governable by `SageMakerConfig`. |
| `productionVariants[].initialInstanceCount` | integer | `1` | Initial number of instances for this variant |
| `productionVariants[].initialVariantWeight` | float | `1.0` | Traffic weight for this variant (0.0–1.0) |

### Data Capture & Monitoring

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dataCapture` | object | optional | Enable input/output data capture to S3 for monitoring |
| `dataCapture.enableCapture` | boolean | `false` | Enable data capture |
| `dataCapture.initialSamplingPercentage` | integer | `100` | Percentage of data to capture |
| `dataCapture.destinationS3Uri` | string | required (if enabled) | S3 URI for captured data |

### Async Inference (Optional)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `asyncInferenceConfig` | object | optional | Enable asynchronous inference |
| `asyncInferenceConfig.outputLocation` | string | required (if enabled) | S3 path for async prediction results |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the config's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective config name in AWS |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `endpointConfigArn` | string | The ARN of the endpoint config in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Endpoint configs are named using a configurable template. The default template is `{namespace}-{name}`.

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerEndpointConfig
metadata:
  name: ml-endpoint-config
  namespace: ml-team
spec:
  configRef: ml-production
  productionVariants:
    - modelName: xgboost-model
      variantName: primary
      instanceType: ml.m5.xlarge
      initialInstanceCount: 2
      initialVariantWeight: 1.0
  dataCapture:
    enableCapture: true
    initialSamplingPercentage: 100
    destinationS3Uri: s3://my-bucket/data-capture
  tags:
    Environment: production
    MonitoringEnabled: "true"
```

## Dependencies

- **Requires:** `SageMakerModel` resources (referenced by `productionVariants[].modelName`)
- **Referenced by:** `SageMakerEndpoint`
- **Governance:** `SageMakerConfig` for instance type enforcement
