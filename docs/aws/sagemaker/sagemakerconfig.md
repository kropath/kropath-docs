# SageMakerConfig — Governance & Control Profile

The `SageMakerConfig` resource defines per-profile governance settings for SageMaker resources. Each `SageMakerConfig` instance includes `mandatory` and `defaults` sections for governance fields, enabling fine-grained control over compute, security, and compliance across the SageMaker family.

## Core Fields

### Config Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Profile name (e.g., `"general-policy"`, `"ml-production"`, `"ml-training"`) |
| `namespace` | string | required | Kubernetes namespace where the config is defined |

### Mandatory Fields (Enforced)

These fields enforce strict policies that cannot be overridden by resource instances:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mandatory.enableNetworkIsolation` | boolean | optional | Force network isolation on all resources using this profile |
| `mandatory.enableInterContainerTrafficEncryption` | boolean | optional | Force inter-container encryption on distributed training |
| `mandatory.directInternetAccess` | string | optional | Force direct internet access setting (`"Enabled"` or `"Disabled"`) |
| `mandatory.rootAccess` | string | optional | Force root access setting for notebook instances |
| `mandatory.kmsKeyId` | string | optional | Enforce KMS key for encryption |
| `mandatory.instanceType` | string | optional | Restrict to a specific instance type |
| `mandatory.tags` | map | optional | Tags that must be present on all resources |

### Defaults Section (Override-able)

These fields provide baseline configurations that resource instances can override:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaults.volumeSizeInGB` | integer | optional | Default EBS volume size |
| `defaults.rootAccess` | string | optional | Default root access setting |
| `defaults.instanceType` | string | optional | Default instance type |
| `defaults.kmsKeyId` | string | optional | Default KMS key for encryption |
| `defaults.namingTemplate` | string | `"{namespace}-{name}"` | Default naming template for resource names |
| `defaults.tags` | map | optional | Default tags applied to resources |
| `defaults.syncedLabels` | map | optional | Default Kubernetes labels to sync to AWS tags |
| `defaults.syncedAnnotations` | map | optional | Default Kubernetes annotations to sync to AWS tags |

## Tier Cascade

The SageMaker governance model uses a ten-level cascade to resolve effective configuration:

```
1. Resource-instance spec.<field>
2. SageMakerConfig.mandatory.<field>
3. SageMakerConfig.defaults.<field>
4. KropathConfig.mandatory.sagemaker.<field>
5. KropathConfig.defaults.sagemaker.<field>
6. Built-in defaults
```

Resources read `status.effectiveConfig` on the namespaced `SageMakerConfig` CR to determine the final, resolved settings.

## Complete Example: Production Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerConfig
metadata:
  name: ml-production
  namespace: ml-team
spec:
  mandatory:
    enableNetworkIsolation: true
    enableInterContainerTrafficEncryption: true
    directInternetAccess: "Disabled"
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
    tags:
      Environment: production
      Compliance: required
  defaults:
    instanceType: ml.m5.xlarge
    volumeSizeInGB: 50
    namingTemplate: "prod-{namespace}-{name}"
    rootAccess: "Disabled"
    tags:
      ManagedBy: kropath
      Service: sagemaker
```

## Complete Example: Training Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerConfig
metadata:
  name: ml-training
  namespace: ml-team
spec:
  defaults:
    instanceType: ml.p3.2xlarge
    volumeSizeInGB: 100
    namingTemplate: "train-{namespace}-{name}"
    rootAccess: "Enabled"
    tags:
      Purpose: training
      Preemptible: "true"
```

## When to Use

### Use `KropathConfig.sagemaker`

For blanket, organization-wide governance that applies across ALL SageMaker profiles:
- Enforce org-wide encryption keys across all teams
- Require network isolation globally
- Apply organization-wide compliance tagging

### Use `SageMakerConfig`

For per-profile governance with flexibility:
- Different policies for production vs. training vs. development
- Team-specific compliance postures
- Profile-specific defaults

## Dependencies

- **Referenced by:** All SageMaker RGDs (via `configRef` label selector)
- **Scope:** Namespace-scoped; resources can reference any `SageMakerConfig` in the same namespace
- **Governance:** Define organization-wide settings in `KropathConfig.sagemaker`; define profile-specific settings here
