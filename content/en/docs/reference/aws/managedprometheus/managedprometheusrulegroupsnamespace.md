---
title: ManagedPrometheusRuleGroupsNamespace
description: "A `ManagedPrometheusRuleGroupsNamespace` creates a named collection of Prometheus recording and alerting rules within an AWS Managed Service for Prometheus workspace."
doc_type: reference
---
# ManagedPrometheusRuleGroupsNamespace

A `ManagedPrometheusRuleGroupsNamespace` creates a named collection of Prometheus recording and alerting rules within an AWS Managed Service for Prometheus workspace. Multiple rule groups namespaces can exist per workspace.

## Overview

`ManagedPrometheusRuleGroupsNamespace` is the **only** resource in the Managed Prometheus family that supports custom naming and cloud tags. It is an Atomic RGD with full governance support for naming templates, tags, and labels.

## Configuration Fields

```yaml
spec:
  configRef              string   default="general-policy"
                                  # Selects ManagedPrometheusConfig profile
  nameOverride           string   default=""
                                  # Custom name; bypasses naming template when set
  deletionPolicy         string   default="retain"
                                  # retain | delete
  tags                   map      default={}
                                  # Cloud tags, merged via governance tiers
  syncedLabels           map      default={}
                                  # K8s labels AND AWS tags (prefixed aws.kropath.run/)
  syncedAnnotations      map      default={}
                                  # K8s annotations (prefixed aws.kropath.run/)
  
  # RuleGroupsNamespace-specific
  configuration          string   required
                                  # Prometheus alerting and recording rules (YAML);
                                  # not governed via effectiveConfig
  workspaceRef           string   required
                                  # Reference to ManagedPrometheusWorkspace CR
                                  # (metadata.name in the same namespace)
```

### Governance Fields

| Field | Governance | Notes |
|---|---|---|
| `namingTemplate` | Mandatory → nameOverride → defaults | Generates cloud `name` field. Default: `{namespace}-{name}`. |
| `tags` | Merged: mandatory + instance + defaults | Standard tag governance |
| `syncedLabels` | Merged: mandatory + instance + defaults | K8s labels AND AWS tags |
| `syncedAnnotations` | Merged: mandatory + instance + defaults | K8s annotations |

### Status Fields

```yaml
status:
  resourceName           string   # Effective cloud name (derived from naming template)
  namingStatus           string   # "valid" | "invalid-unresolved-tokens"
  statusCode             string   # CREATING | ACTIVE | UPDATE_FAILED
  statusReason           string   # Failure reason (empty when healthy)
  conditions             array    # Standard Kubernetes conditions
```

## Naming

Resource names follow the naming convention. The effective cloud name is derived from the naming template.

- **Default `namingTemplate`:** `{namespace}-{name}`
- **Token vocabulary:** `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}`
- **Provider constraints:** `[0-9A-Za-z][-.0-9A-Z_a-z]*`
- **Immutability:** Once created, the cloud `name` cannot be changed. Renaming requires delete-and-recreate.

**Example:** Namespace `monitoring`, CR name `app-rules`, template `{namespace}-{name}` produces cloud name `monitoring-app-rules`.

## Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusRuleGroupsNamespace
metadata:
  name: app-rules
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  deletionPolicy: delete
  tags:
    application: my-app
    team: platform
  syncedLabels:
    application: my-app
  configuration: |
    groups:
      - name: app_metrics
        interval: 15s
        rules:
          - record: job:requests:rate5m
            expr: 'rate(http_requests_total{job="myapp"}[5m])'
          - alert: HighErrorRate
            expr: 'rate(http_errors_total{job="myapp"}[5m]) > 0.05'
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High error rate on {{ $labels.job }}"
```

## Common Patterns

### Recording Rules

Pre-compute expensive aggregations:

```yaml
configuration: |
  groups:
    - name: recording_rules
      interval: 1m
      rules:
        - record: job:request_duration:p95
          expr: 'histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))'
        - record: job:error_rate:5m
          expr: 'rate(errors_total[5m])'
```

### Alerting Rules

Define conditions that trigger alerts:

```yaml
configuration: |
  groups:
    - name: alerting_rules
      interval: 1m
      rules:
        - alert: CPUUsageHigh
          expr: 'node_cpu_seconds_total > 80'
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High CPU usage: {{ $value }}%"
        
        - alert: DiskSpaceLow
          expr: 'node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1'
          for: 10m
          labels:
            severity: critical
```

### With Custom Naming

Override the naming template:

```yaml
metadata:
  name: app-rules
  namespace: monitoring
spec:
  configRef: production-monitoring
  nameOverride: custom-app-rules  # Bypasses template
  workspaceRef: prod-metrics
```

### Environment-Specific Rules

Use config profile to enforce naming patterns:

```yaml
# Using "prod" profile with template "prod-{namespace}-{name}"
metadata:
  name: app-rules
  namespace: monitoring
spec:
  configRef: prod  # Enforces "prod-monitoring-app-rules" as cloud name
  workspaceRef: prod-metrics
```

## How to Deploy

1. Create the rule groups namespace:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusRuleGroupsNamespace
metadata:
  name: app-rules
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  configuration: |
    groups:
      - name: app_rules
        interval: 15s
        rules:
          - record: job:requests:rate5m
            expr: 'rate(http_requests_total[5m])'
EOF
```

2. Verify creation and naming:

```bash
kubectl get managedprometheusrulegroupsnamespace -n monitoring
kubectl get managedprometheusrulegroupsnamespace app-rules -n monitoring -o jsonpath='{.status.resourceName}'
# Output: monitoring-app-rules
```

3. Check naming status:

```bash
kubectl get managedprometheusrulegroupsnamespace app-rules -n monitoring -o jsonpath='{.status.namingStatus}'
# Output: valid
```

## Prerequisites

- **Workspace exists** — A `ManagedPrometheusWorkspace` CR matching `spec.workspaceRef` must exist
- **Valid rules** — The `configuration` field must contain valid Prometheus rules (validated by AWS)
- **Governance profile** — A `ManagedPrometheusConfig` CR matching `spec.configRef` must exist
- **Valid naming** — If `namingTemplate` uses tokens, all tokens must resolve to non-empty values

## Limitations

- **Immutable naming** — The cloud `name` cannot be changed after creation. Renaming requires delete-and-recreate.
- **Configuration is opaque** — Kropath does not validate Prometheus rule syntax. Invalid rules are rejected by AWS.
- **Multiple namespaces per workspace** — While multiple rule groups namespaces can exist per workspace, AWS may have limits on the total number of rules per workspace.

## Troubleshooting

### Invalid Naming Status

If `status.namingStatus` shows `"invalid-unresolved-tokens"`, the naming template references a token that couldn't resolve:

```bash
kubectl describe managedprometheusrulegroupsnamespace <name> -n <namespace>
```

Check that:
- All tokens in the template are valid: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}`
- If using `{tag.KEY}`, the tag `KEY` exists in either instance or governance tiers

## Related Resources

- [ManagedPrometheusWorkspace](./managedprometheusworkspace.md) — Workspace these rules attach to
- [ManagedPrometheusAlertManagerDefinition](./managedprometheusalertmanagerdefinition.md) — Alert routing for alerts from these rules
- [ManagedPrometheusConfig](./managedprometheusconfig.md) — Governance configuration (naming, tags)
