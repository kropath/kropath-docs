# AWSIAMConfig — Governance Configuration

The `AWSIAMConfig` resource defines governance profiles that control IAM behavior across your organization and namespaces. Platform teams create named profiles; developers and operators select the profile they need via `spec.configRef` on each IAM resource.

## Overview

`AWSIAMConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., permissions boundary that all roles must use)
- **Defaults tier** — Baseline values developers can override (e.g., default session duration if not specified on the role)

This two-tier approach lets platform teams enforce critical compliance controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `permissionsBoundaryArn` | string | ARN of a permissions boundary all roles must respect |
| `blockIamUserAccessKeys` | boolean | If `true`, blocks creation of access keys on all users |
| `maxSessionDurationSeconds` | integer | Maximum session duration (seconds). Clamps any longer duration |
| `namingTemplate` | string | Template for resource names |
| `tags` | map | Tags applied to all resources (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Purpose |
|---|---|---|
| `permissionsBoundaryArn` | string | Default permissions boundary (can be overridden per role) |
| `blockIamUserAccessKeys` | boolean | Default access key blocking behavior |
| `maxSessionDurationSeconds` | integer | Default session duration |
| `namingTemplate` | string | Default naming template |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers.

## Example Profiles

### Conservative Baseline (general-policy)

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    maxSessionDurationSeconds: 3600  # 1 hour
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

### Hardened (pci)

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    permissionsBoundaryArn: "arn:aws:iam::123456789012:policy/PCI-Boundary"
    blockIamUserAccessKeys: true
    maxSessionDurationSeconds: 900  # 15 minutes
    syncedLabels:
      compliance: pci
  defaults:
    namingTemplate: "{namespace}-pci-{name}"
```

## Using Profiles

Select a profile on any IAM resource:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSIAMRole
metadata:
  name: my-lambda-role
  namespace: my-namespace
spec:
  configRef: general-policy  # Select the profile
  type: lambda
```

If a named profile does not exist, resources fall back to `general-policy`.

## Organization-Wide Defaults

Set org-wide controls using the cloud provider's root configuration:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    iam:
      permissionsBoundaryArn: "arn:aws:iam::123456789012:policy/OrgBoundary"
      blockIamUserAccessKeys: true
  defaults:
    iam:
      maxSessionDurationSeconds: 3600
```

These values act as the ultimate fallback when namespace profiles do not set them.

## Monitoring

Verify a profile and its settings:

```bash
kubectl get awsiamconfig general-policy -n kro-system -o yaml
kubectl describe awsiamconfig pci -n kro-system
```

Check what profile a resource is using:

```bash
kubectl describe awsiamrole my-role -n my-namespace | grep configRef
```
