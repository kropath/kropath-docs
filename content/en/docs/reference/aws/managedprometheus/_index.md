---
title: Managed Prometheus Family
description: AWS Managed Service for Prometheus (AMP) provides a fully managed Prometheus-compatible monitoring service for collecting, storing, and querying metrics.
doc_type: reference
weight: 320
---
# Managed Prometheus Family

AWS Managed Service for Prometheus (AMP) provides a fully managed Prometheus-compatible monitoring service for collecting, storing, and querying metrics. The Managed Prometheus family lets you provision and manage AMP workspaces, define alert manager configurations, create rule groups for recording and alerting rules, and configure logging destinations — all through Kubernetes with centralized governance policies.

## Resources

### Governance

- **[ManagedPrometheusConfig](./managedprometheusconfig.md)** — Define governance profiles (mandatory and default policies) for workspace aliases, logging destinations, naming conventions, tags, and metadata. Platform teams create named profiles; developers select a profile for their workspaces and rules.

### Workspace & Monitoring

- **[ManagedPrometheusWorkspace](./managedprometheusworkspace.md)** — Create an AMP workspace for Prometheus metrics ingestion and querying. Workspaces are the root resource; all other resources attach to a workspace.

- **[ManagedPrometheusAlertManagerDefinition](./managedprometheusalertmanagerdefinition.md)** — Define alert manager configuration (routing, receivers, inhibition rules) for a workspace. Exactly one alert manager definition per workspace.

- **[ManagedPrometheusRuleGroupsNamespace](./managedprometheusrulegroupsnamespace.md)** — Create named collections of Prometheus recording and alerting rules within a workspace. The only resource in this family that supports custom naming and cloud tags.

### Logging

- **[ManagedPrometheusLoggingConfiguration](./managedprometheusloggingconfiguration.md)** — Route workspace vended logs to CloudWatch Logs. Exactly one logging configuration per workspace.

## Quick Start

1. **Deploy a governance profile** — Create a `ManagedPrometheusConfig` CR in the `kro-system` namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    alias: ""
    logGroupARN: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

2. **Create a workspace** — Developers provision an AMP workspace:

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
  deletionPolicy: retain
```

3. **Define alert manager rules** — Configure alerting for the workspace:

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
  configuration: |
    global:
      resolve_timeout: 5m
    route:
      receiver: 'default'
      group_by: ['alertname']
      routes:
        - match:
            severity: critical
          receiver: 'critical'
    receivers:
      - name: 'default'
      - name: 'critical'
```

4. **Create rule groups** — Add recording and alerting rules:

```yaml
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
          - alert: HighErrorRate
            expr: 'rate(http_errors_total[5m]) > 0.05'
            for: 5m
            labels:
              severity: warning
  deletionPolicy: delete
```

5. **Set up logging** — Route workspace logs to CloudWatch:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusLoggingConfiguration
metadata:
  name: logs
  namespace: monitoring
spec:
  configRef: general-policy
  workspaceRef: prod-metrics
  logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/prod:*"
  deletionPolicy: retain
```

## Governance and Policy

All Managed Prometheus resources respect a **two-tier governance cascade**:

1. **Mandatory tier** — Platform-enforced controls (e.g., all workspaces must use a specific alias pattern, all rule groups must use a naming template, all resources must include compliance tags)
2. **Defaults tier** — Baseline values developers can override (e.g., default naming pattern, default tags, default aliases)

**Organization-wide governance** flows through `KropathConfig` (in `kro-system`), which sets org-level mandatory and default policies. **Resource-specific governance** flows through `ManagedPrometheusConfig` profiles, which can be more restrictive than org-wide settings.

### Governance Cascade

The cascade applies to fields managed by `ManagedPrometheusConfig`:

| Field | Applies To | Cascade Order |
|---|---|---|
| `alias` | Workspace only | Mandatory → instance → defaults → `""` (no alias) |
| `logGroupARN` | LoggingConfiguration only | Mandatory → instance → defaults (required if no tier sets it) |
| `namingTemplate` | RuleGroupsNamespace only | Mandatory → nameOverride → defaults → `{namespace}-{name}` |
| `tags` | Workspace, RuleGroupsNamespace | Merged: mandatory + instance + defaults |
| `syncedLabels` | All resources | Merged: mandatory + instance + defaults |
| `syncedAnnotations` | All resources | Merged: mandatory + instance + defaults |

See [ManagedPrometheusConfig](./managedprometheusconfig.md) for complete cascade semantics.

## Common Patterns

### Multi-Profile Setup

Create separate `ManagedPrometheusConfig` profiles for development and production:

```yaml
---
# Development: permissive
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}
  defaults:
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development

---
# Production: strict
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: prod
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod
spec:
  mandatory:
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      compliance: required
  defaults: {}
```

Developers select the appropriate profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: metrics
  namespace: myapp
spec:
  configRef: prod  # ← Select the prod profile
  deletionPolicy: retain
```

### Centralized Logging

Enforce all workspaces to log to a central CloudWatch log group:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: logging-enabled
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: logging-enabled
spec:
  mandatory:
    logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/central:*"
  defaults: {}
```

All `ManagedPrometheusLoggingConfiguration` resources using this profile must route to the enforced log group.

### Compliance Tagging

Create a profile with mandatory compliance tags for regulated workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    tags:
      compliance: hipaa
      data-classification: phi
      audit-required: "true"
    syncedLabels:
      compliance: hipaa
  defaults: {}
```

Developers using this profile get mandatory compliance tags on all resources.

## Prerequisites

- **AWS credentials** — Cluster must have IAM permissions to create/update AMP resources in the target AWS account
- **Governance profiles** — At least one `ManagedPrometheusConfig` CR (e.g. `general-policy`) must exist in `kro-system` before creating resources
- **CloudWatch Logs integration** — For `ManagedPrometheusLoggingConfiguration`, target CloudWatch Logs log groups must be pre-created
- **Workspace must exist** — All other resources (`AlertManagerDefinition`, `RuleGroupsNamespace`, `LoggingConfiguration`) require an existing `ManagedPrometheusWorkspace`

## Limitations

- **AlertManagerDefinition and LoggingConfiguration are singletons** — Exactly one per workspace. A second creation attempt will fail.
- **RuleGroupsNamespace naming is immutable** — The `spec.name` field on the underlying AWS resource is immutable. Renaming requires delete-and-recreate.
- **Configuration fields are opaque** — The `configuration` field in AlertManagerDefinition and RuleGroupsNamespace (Prometheus YAML) is not validated or governed by kropath. Platform teams should enforce alerting and rule standards through organizational policy (OPA/Kyverno).
- **LoggingConfiguration requires valid ARN** — The `logGroupARN` must be a valid CloudWatch Logs log group ARN. The target log group must already exist.

## Related Families

- [CloudWatch](../cloudwatch/index.md) — Alarms and dashboards for monitoring metrics
- [CloudWatch Logs](../cloudwatchlogs/index.md) — Log group management
