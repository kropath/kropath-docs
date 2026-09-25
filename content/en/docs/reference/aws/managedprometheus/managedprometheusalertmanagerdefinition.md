---
title: ManagedPrometheusAlertManagerDefinition
description: "A `ManagedPrometheusAlertManagerDefinition` defines Prometheus Alertmanager configuration (routing, receivers, inhibition rules) for an AWS Managed Service for Prometheus workspace."
doc_type: reference
---
# ManagedPrometheusAlertManagerDefinition

A `ManagedPrometheusAlertManagerDefinition` defines Prometheus Alertmanager configuration (routing, receivers, inhibition rules) for an AWS Managed Service for Prometheus workspace. Exactly one alert manager definition is allowed per workspace.

## Overview

`ManagedPrometheusAlertManagerDefinition` is a singleton per workspace. It holds the complete Alertmanager configuration in YAML or JSON format, specifying how alerts are routed to receivers and processed.

## Configuration Fields

```yaml
spec:
  configRef              string   default="general-policy"
                                  # Selects ManagedPrometheusConfig profile
  deletionPolicy         string   default="retain"
                                  # retain | delete
  syncedLabels           map      default={}
                                  # K8s labels AND AWS tags (prefixed aws.kropath.run/)
  syncedAnnotations      map      default={}
                                  # K8s annotations (prefixed aws.kropath.run/)
  
  # AlertManagerDefinition-specific
  configuration          string   required
                                  # Alertmanager config (YAML or JSON format);
                                  # not governed via effectiveConfig
  workspaceRef           string   required
                                  # Reference to ManagedPrometheusWorkspace CR
                                  # (metadata.name in the same namespace)
```

### Governance Fields

| Field | Governance | Notes |
|---|---|---|
| `syncedLabels` | Merged: mandatory + instance + defaults | K8s labels on the alert manager resource |
| `syncedAnnotations` | Merged: mandatory + instance + defaults | K8s annotations on the alert manager resource |

**Note on `configuration`:** The alert manager configuration content is **not** governed by `ManagedPrometheusConfig`. It is an opaque YAML/JSON blob specific to each workspace's alerting needs. Platform teams should enforce alerting standards through organizational policy (OPA/Kyverno) if needed.

### Status Fields

```yaml
status:
  statusCode             string   # CREATING | ACTIVE | UPDATE_FAILED
  statusReason           string   # Failure reason (empty when healthy)
  conditions             array    # Standard Kubernetes conditions
```

## Naming

**Naming exemption (KRO-236).** This resource has no provider `name` field and is a singleton per workspace. Omitted: `spec.nameOverride`, `status.resourceName`, `status.predictedArn`, `status.namingStatus`.

## Tag Governance

**Tag exemption:** This resource has no `spec.tags` field in the upstream AWS API. Cloud tags do not apply. Only `syncedLabels` and `syncedAnnotations` are available for governance.

## Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusAlertManagerDefinition
metadata:
  name: alerts
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  deletionPolicy: retain
  syncedLabels:
    alerting: enabled
  syncedAnnotations:
    managed-by: platform-team
  configuration: |
    global:
      resolve_timeout: 5m
    route:
      receiver: 'default'
      group_by: ['alertname', 'cluster', 'service']
      routes:
        - match:
            severity: critical
          receiver: 'critical'
          continue: true
        - match:
            severity: warning
          receiver: 'warnings'
    receivers:
      - name: 'default'
        # Receivers send to SNS, PagerDuty, Slack, etc.
      - name: 'critical'
      - name: 'warnings'
```

## Common Patterns

### Basic Alert Routing

Route critical alerts to a dedicated receiver:

```yaml
configuration: |
  global:
    resolve_timeout: 5m
  route:
    receiver: default
    routes:
      - match:
          severity: critical
        receiver: critical
  receivers:
    - name: default
    - name: critical
```

### Multi-Team Routing

Route alerts based on team labels:

```yaml
configuration: |
  global:
    resolve_timeout: 5m
  route:
    receiver: default
    routes:
      - match:
          team: platform
        receiver: platform-team
      - match:
          team: applications
        receiver: app-team
  receivers:
    - name: default
    - name: platform-team
    - name: app-team
```

### Inhibition Rules

Suppress warnings when critical alerts are firing:

```yaml
configuration: |
  global:
    resolve_timeout: 5m
  route:
    receiver: default
  inhibit_rules:
    - source_match:
        severity: critical
      target_match:
        severity: warning
      equal: ['alertname', 'namespace', 'pod']
  receivers:
    - name: default
```

## How to Deploy

1. Create the alert manager definition:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusAlertManagerDefinition
metadata:
  name: alerts
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  configuration: |
    global:
      resolve_timeout: 5m
    route:
      receiver: default
    receivers:
      - name: default
EOF
```

2. Verify creation:

```bash
kubectl get managedprometheusalertmanagerdefinition -n monitoring
kubectl describe managedprometheusalertmanagerdefinition alerts -n monitoring
```

## Prerequisites

- **Workspace exists** — A `ManagedPrometheusWorkspace` CR matching `spec.workspaceRef` must exist in the same namespace
- **Valid Alertmanager config** — The `configuration` field must be valid YAML or JSON; validation is performed by AWS
- **Governance profile** — A `ManagedPrometheusConfig` CR matching `spec.configRef` must exist
- **Singleton constraint** — Only one alert manager definition per workspace

## Limitations

- **Singleton per workspace** — A second creation attempt on the same workspace will fail
- **Configuration is opaque** — Kropath does not validate Alertmanager YAML. Invalid configurations are rejected by AWS.
- **No automatic receiver creation** — Alertmanager receivers reference external systems (SNS, email, etc.) that must be pre-created

## Related Resources

- [ManagedPrometheusWorkspace](./managedprometheusworkspace.md) — Workspace this alert manager attaches to
- [ManagedPrometheusRuleGroupsNamespace](./managedprometheusrulegroupsnamespace.md) — Alerting rules that trigger these alerts
- [ManagedPrometheusConfig](./managedprometheusconfig.md) — Governance configuration
