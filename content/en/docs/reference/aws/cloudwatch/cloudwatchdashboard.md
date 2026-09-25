---
title: CloudWatchDashboard — CloudWatch Dashboards
description: "The `CloudWatchDashboard` resource creates and manages AWS CloudWatch dashboards in Kubernetes."
doc_type: reference
---
# CloudWatchDashboard — CloudWatch Dashboards

The `CloudWatchDashboard` resource creates and manages AWS CloudWatch dashboards in Kubernetes. Dashboards provide visual displays of CloudWatch metrics with customizable widgets, graphs, and layouts.

## Overview

CloudWatch dashboards are global AWS resources (no region scoping) that display metrics, alarms, and logs via customizable widgets. A `CloudWatchDashboard` wraps the AWS CloudWatch Dashboard API and coordinates with governance policy defined in `CloudWatchConfig`.

## Spec Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects governance profile from `CloudWatchConfig` |
| `nameOverride` | string | `` | Bypasses naming template; sets cloud dashboard name directly |
| `deletionPolicy` | string | `retain` | Deletion behavior: `retain` (keep) or `delete` (remove cloud resource) |
| `dashboardBody` | string | `` | **Required.** Dashboard layout as JSON string defining widgets, metrics, and layout |
| `tags` | map | `{}` | *Not applied to cloud resource.* Dashboards do not support cloud tags (platform limitation). This field is accepted for cross-resource consistency. |
| `syncedLabels` | map | `{}` | Synced to Kubernetes labels only (not to cloud tags due to Dashboard tag limitation). Prefixed `aws.kropath.run/` |
| `syncedAnnotations` | map | `{}` | Synced to Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Dashboard Name and ARN

- **Dashboard name:** Derived from `spec.nameOverride` (if set) or naming template from governance
- **Default template:** `{namespace}-{name}` (e.g. `observability-prod-ops-dashboard`)
- **Naming tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}` (tags resolve from governance only, not instance tags)
- **ARN format:** `arn:aws:cloudwatch::<accountId>:dashboard/<effectiveName>` (global: no region segment)

## Important Constraints

**Cloud tags not supported:** The AWS CloudWatch Dashboard API does not support tags at creation time. Governance-mandated tags from `CloudWatchConfig` cannot be applied to Dashboard cloud resources. This is a current platform limitation.

**Synced labels:** `syncedLabels` are mirrored to Kubernetes metadata only, not to cloud tags.

**Idempotent by name:** If a dashboard with the same name already exists, the `PutDashboard` API replaces its contents without requiring a separate delete-then-create operation.

**Naming tag tokens:** Naming template tokens like `{tag.env}` resolve from governance tags (`CloudWatchConfig.mandatory.tags + CloudWatchConfig.defaults.tags`) only. Instance `spec.tags` do not contribute to naming tokens because Dashboards have no cloud tag field.

## Dashboard Body

The `dashboardBody` field contains the complete dashboard definition as a JSON string. CloudWatch validates the body structure at creation time and returns validation messages via `status.dashboardValidationMessages`.

The dashboard body defines:
- **Widgets** — Individual visualizations (e.g. line graphs, numbers, logs)
- **Layout** — Widget placement and sizing on the dashboard
- **Metrics and queries** — Data sources for each widget

For detailed dashboard body schema, see the [AWS CloudWatch Dashboard Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_DashboardBody.html).

## Governance Cascade

`CloudWatchConfig` governance profiles set:
- **Mandatory `namingTemplate`** — Cloud dashboard name must match template (instance `nameOverride` only escape hatch)
- **Mandatory `syncedLabels` / `syncedAnnotations`** — Applied to Kubernetes metadata (no cloud tag dual-write because Dashboards have no cloud tags)

Note: `actionsEnabled` and `treatMissingData` do not apply to Dashboards (no alarm actions or missing data concepts).

## Example: Simple Dashboard

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchDashboard
metadata:
  name: app-metrics
  namespace: observability-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  dashboardBody: |
    {
      "widgets": [
        {
          "type": "metric",
          "properties": {
            "metrics": [
              [ "AWS/ApplicationELB", "TargetResponseTime", { "stat": "Average" } ],
              [ ".", "RequestCount", { "stat": "Sum" } ]
            ],
            "period": 300,
            "stat": "Average",
            "region": "us-east-1",
            "title": "Load Balancer Performance"
          }
        },
        {
          "type": "metric",
          "properties": {
            "metrics": [
              [ "AWS/EC2", "CPUUtilization" ]
            ],
            "period": 300,
            "stat": "Average",
            "region": "us-east-1",
            "title": "EC2 CPU Usage"
          }
        }
      ]
    }
  syncedLabels:
    environment: production
    team: platform
  syncedAnnotations:
    docs: https://wiki.example.com/dashboards/app-metrics
```

## Example: Multi-Metric Dashboard with Alarms

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchDashboard
metadata:
  name: platform-health
  namespace: observability-prod
spec:
  configRef: general-policy
  dashboardBody: |
    {
      "widgets": [
        {
          "type": "metric",
          "properties": {
            "metrics": [
              [ "AWS/ApplicationELB", "HealthyHostCount" ],
              [ ".", "UnHealthyHostCount" ]
            ],
            "period": 60,
            "stat": "Average",
            "region": "us-east-1",
            "title": "Target Health",
            "yAxis": { "left": { "min": 0 } }
          }
        },
        {
          "type": "metric",
          "properties": {
            "metrics": [
              [ "AWS/RDS", "DatabaseConnections" ],
              [ ".", "CPUUtilization" ]
            ],
            "period": 300,
            "stat": "Average",
            "region": "us-east-1",
            "title": "Database Performance"
          }
        }
      ]
    }
  tags:
    application: platform
    environment: production
  syncedLabels:
    team: platform
```

## Cluster Setup

CloudWatch dashboards require:
1. CloudWatchConfig profiles deployed in `kro-system`
2. Valid `dashboardBody` JSON that conforms to CloudWatch dashboard schema

Dashboards are global AWS resources; no regional configuration needed beyond normal AWS authentication.

## Related Resources

- [CloudWatchConfig](./cloudwatchconfig.md) — Governance profiles for dashboard policies
- [CloudWatchAlarm](./cloudwatchalarm.md) — Metric alarms to trigger on threshold breaches
- [CloudWatchMetricStream](./cloudwatchmetricstream.md) — Export metrics to external observability tools
