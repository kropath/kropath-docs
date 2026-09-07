# SageMakerEndpoint — Managed Inference Hosting

The `SageMakerEndpoint` resource represents a managed compute resource that hosts one or more models for real-time predictions. It references an endpoint configuration and manages autoscaling, traffic routing, and operational health.

## Core Fields

### Endpoint Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the endpoint name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS endpoint) or `"delete"` (deletes AWS endpoint) |

### Endpoint Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `endpointConfigName` | string | required | Name of the `SageMakerEndpointConfig` to deploy |
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the endpoint's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective endpoint name in AWS |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `endpointArn` | string | The ARN of the endpoint in AWS |
| `endpointStatus` | string | Current status (`"Creating"`, `"InService"`, `"Updating"`, `"Deleting"`, `"Failed"`) |
| `creationTime` | timestamp | When the endpoint was created |
| `lastModifiedTime` | timestamp | When the endpoint was last modified |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Naming Convention

Endpoints are named using a configurable template. The default template is `{namespace}-{name}`.

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name

**AWS constraints:**
- Max 63 characters
- Alphanumeric and hyphens only
- No leading/trailing hyphens

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerEndpoint
metadata:
  name: ml-inference
  namespace: ml-team
spec:
  configRef: ml-production
  endpointConfigName: ml-endpoint-config
  tags:
    Environment: production
    Service: inference
```

## Dependencies

- **Requires:** `SageMakerEndpointConfig` (specified by `endpointConfigName`)
- **Provides:** Inference endpoint accessible via AWS SDK
- **Governance:** `SageMakerConfig` for operational governance
