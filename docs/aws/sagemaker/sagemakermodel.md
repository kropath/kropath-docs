# SageMakerModel — ML Model Definition

The `SageMakerModel` resource defines the container image(s) and model artifact location(s) that serve inference requests. A model is the foundation for endpoint deployment and can reference one or more containers with different algorithms or frameworks.

## Core Fields

### Model Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the model name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS model) or `"delete"` (deletes AWS model) |

### Container Definition

| Field | Type | Default | Purpose |
|---|---|---|---|
| `primaryContainer` | object | required | Primary container image and model artifact location |
| `primaryContainer.image` | string | required | Docker image URI for inference (e.g., SageMaker algorithm image) |
| `primaryContainer.modelDataUrl` | string | optional | S3 path to model artifacts |
| `containers` | array | optional | Additional containers for multi-model or custom inference |

### Execution Role

| Field | Type | Default | Purpose |
|---|---|---|---|
| `executionRoleArn` | string | required | IAM role ARN for model execution and artifact access |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the model's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective model name in AWS |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `modelArn` | string | The ARN of the model in AWS |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Models are named using a configurable template. The default template is `{namespace}-{name}`.

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerModel
metadata:
  name: xgboost-model
  namespace: ml-team
spec:
  configRef: ml-production
  executionRoleArn: arn:aws:iam::123456789012:role/SageMakerExecutionRole
  primaryContainer:
    image: 246618743249.dkr.ecr.us-east-1.amazonaws.com/sagemaker-xgboost:1.5-1
    modelDataUrl: s3://my-bucket/models/xgboost-model.tar.gz
  tags:
    Framework: xgboost
    Version: "1.5"
```

## Dependencies

- **Referenced by:** `SageMakerEndpointConfig`
- **Requires:** IAM execution role, S3 bucket for model artifacts
- **Governance:** `SageMakerConfig` for governance tagging
