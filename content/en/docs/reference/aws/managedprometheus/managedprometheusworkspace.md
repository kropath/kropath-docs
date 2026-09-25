---
title: ManagedPrometheusWorkspace
description: "A `ManagedPrometheusWorkspace` creates an AWS Managed Service for Prometheus (AMP) workspace — the root resource in the Managed Prometheus family."
doc_type: reference
---
# ManagedPrometheusWorkspace

A `ManagedPrometheusWorkspace` creates an AWS Managed Service for Prometheus (AMP) workspace — the root resource in the Managed Prometheus family. A workspace provides remote write and query endpoints for Prometheus-compatible agents and tools.

## Overview

`ManagedPrometheusWorkspace` is the dependency root. All other Managed Prometheus resources (`AlertManagerDefinition`, `RuleGroupsNamespace`, `LoggingConfiguration`) attach to a workspace via `spec.workspaceRef`.

## Configuration Fields

```yaml
spec:
  configRef              string   default="general-policy"
                                  # Selects ManagedPrometheusConfig profile via
                                  # labelSelector (aws.kropath.run/resource-name)
  deletionPolicy         string   default="retain"
                                  # retain | delete — what happens to the cloud workspace
                                  # when the CR is deleted
  tags                   map      default={}
                                  # Cloud tags, merged via governance tiers
  syncedLabels           map      default={}
                                  # K8s labels AND AWS tags (prefixed aws.kropath.run/)
  syncedAnnotations      map      default={}
                                  # K8s annotations (prefixed aws.kropath.run/)
  
  # Workspace-specific
  alias                  string   default=""
                                  # Human-readable workspace alias;
                                  # governance cascade applies (mandatory → instance → defaults)
```

### Governance Fields

The following fields are governed by `ManagedPrometheusConfig`:

| Field | Governance | Notes |
|---|---|---|
| `alias` | Mandatory → instance → defaults | Empty string (`""`) = no alias (valid; workspace identified by workspaceID) |
| `tags` | Merged: mandatory + instance + defaults | Standard tag governance |
| `syncedLabels` | Merged: mandatory + instance + defaults | Appear in K8s labels AND cloud tags |
| `syncedAnnotations` | Merged: mandatory + instance + defaults | Mirrored to K8s annotations |

### Status Fields

```yaml
status:
  workspaceID            string   # AWS-assigned workspace identifier (e.g. ws-12345678-...)
  workspaceStatus        string   # CREATING | ACTIVE | UPDATING | DELETING
  conditions             array    # Standard Kubernetes conditions
```

## Naming

**Naming exemption (KRO-236).** This resource has no provider `name` field. AWS Managed Prometheus workspaces are identified by a system-assigned `workspaceID` (e.g. `ws-12345678-1234-1234-1234-123456789012`). The naming convention does not apply.

Omitted from this resource:
- `spec.nameOverride`
- `status.resourceName`, `status.predictedArn`, `status.namingStatus`

## Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: prod-metrics
  namespace: monitoring
spec:
  configRef: general-policy
  alias: "Production Metrics"
  tags:
    environment: production
    team: platform
    cost-center: "1234"
  syncedLabels:
    environment: production
  syncedAnnotations:
    owner: platform-team
  deletionPolicy: retain
```

## Common Patterns

### Development Workspace

Minimal configuration for development:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: dev-metrics
  namespace: observability-dev
spec:
  configRef: dev  # Uses development profile
  alias: "Dev Metrics"
  deletionPolicy: delete  # Safe to delete in dev
```

### Production Workspace with Governance

Strict configuration for production with mandatory compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: prod-amp
  namespace: observability-prod
spec:
  configRef: production-monitoring
  alias: "Production AMP"
  tags:
    environment: production
    compliance: required
  syncedLabels:
    environment: production
  deletionPolicy: retain  # Safer in production
```

### Multi-Team Workspace

Shared workspace with team tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: shared-metrics
  namespace: observability
spec:
  configRef: general-policy
  alias: "Shared Metrics Workspace"
  tags:
    team: shared-platform
    purpose: cross-team-monitoring
  syncedLabels:
    team: platform
```

## How to Deploy

1. Create the workspace:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: app-metrics
  namespace: monitoring
spec:
  configRef: general-policy
  alias: "App Metrics"
  deletionPolicy: retain
EOF
```

2. Verify the workspace is created:

```bash
kubectl get managedprometheusworkspace -n monitoring
kubectl describe managedprometheusworkspace app-metrics -n monitoring
```

3. Check the workspace status:

```bash
kubectl get managedprometheusworkspace app-metrics -n monitoring -o jsonpath='{.status.workspaceID}'
# Output: ws-12345678-1234-1234-1234-123456789012
```

## Deletion Behavior

- **`deletionPolicy: retain`** (default) — The AWS AMP workspace persists when the CR is deleted. Useful for production workspaces where you want to preserve metrics data.
- **`deletionPolicy: delete`** — The AWS AMP workspace is deleted when the CR is deleted. Use with caution in production.

## Prerequisites

- **AWS credentials** — Cluster must have IAM permissions to create AMP workspaces
- **Governance profile** — A `ManagedPrometheusConfig` CR matching `spec.configRef` must exist
- **Unique workspace name** — Each workspace in a cluster must have a unique `metadata.name`

## Limitations

- **Workspace identity** — Workspaces are identified by system-assigned `workspaceID`, not by name. The `metadata.name` is for Kubernetes organization only.
- **Immutable alias** — Once created, workspace configuration cannot be changed via Kubernetes. To change alias or tags, use the AWS console or API.
- **One workspace per CR** — Each `ManagedPrometheusWorkspace` CR creates exactly one AWS workspace.

## Next Steps

After creating a workspace, attach other resources:

1. **Configure alerting** — Create a [ManagedPrometheusAlertManagerDefinition](./managedprometheusalertmanagerdefinition.md)
2. **Add recording/alerting rules** — Create [ManagedPrometheusRuleGroupsNamespace](./managedprometheusrulegroupsnamespace.md) resources
3. **Enable logging** — Create a [ManagedPrometheusLoggingConfiguration](./managedprometheusloggingconfiguration.md)

## Related Resources

- [ManagedPrometheusConfig](./managedprometheusconfig.md) — Governance configuration that this workspace references
- [ManagedPrometheusAlertManagerDefinition](./managedprometheusalertmanagerdefinition.md) — Alerting rules attached to this workspace
- [ManagedPrometheusRuleGroupsNamespace](./managedprometheusrulegroupsnamespace.md) — Rule groups attached to this workspace
- [ManagedPrometheusLoggingConfiguration](./managedprometheusloggingconfiguration.md) — Logging destination for this workspace
