---
title: CloudWatchAlarm — CloudWatch Metric Alarms
description: "The `CloudWatchAlarm` resource creates and manages AWS CloudWatch alarms in Kubernetes."
doc_type: reference
---
# CloudWatchAlarm — CloudWatch Metric Alarms

The `CloudWatchAlarm` resource creates and manages AWS CloudWatch alarms in Kubernetes. It supports three mutually exclusive alarm types: simple metric alarms (static thresholds), metric math alarms (including anomaly detection), and PromQL alarms (managed Prometheus queries).

## Overview

CloudWatch alarms monitor metrics and trigger actions when thresholds are crossed. A `CloudWatchAlarm` wraps AWS CloudWatch MetricAlarm and coordinates with governance policy defined in `CloudWatchConfig`.

Alarms support:
- **Simple metric alarms** — static threshold on a single metric
- **Metric math alarms** — computed expressions over multiple metrics (e.g. ratios, percentiles)
- **Anomaly detection alarms** — automatic anomaly bands via metric math
- **PromQL alarms** — native PromQL queries against managed Prometheus

## Spec Fields

### Common Fields (All Alarm Types)

| Field | Type | Default | Description |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects governance profile from `CloudWatchConfig` |
| `nameOverride` | string | `` | Bypasses naming template; sets cloud alarm name directly |
| `deletionPolicy` | string | `retain` | Deletion behavior: `retain` (keep) or `delete` (remove cloud resource) |
| `alarmDescription` | string | `` | Human-readable alarm description |
| `actionsEnabled` | boolean | nil | Enable/disable alarm actions. Nil = fall through to governance policy. |
| `alarmActions` | []string | `[]` | SNS/Lambda/EC2/SSM ARNs invoked on ALARM state (max 5) |
| `okActions` | []string | `[]` | ARNs invoked on OK state (max 5) |
| `insufficientDataActions` | []string | `[]` | ARNs invoked on INSUFFICIENT_DATA state (max 5) |
| `tags` | map | `{}` | Cloud tags applied to alarm. Governance-mandated tags cannot be removed. |
| `syncedLabels` | map | `{}` | Synced to Kubernetes labels and cloud tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Synced to Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Evaluation Configuration (Non-PromQL Alarms)

| Field | Type | Default | Description |
|---|---|---|---|
| `comparisonOperator` | string | `` | Required for metric alarms. `GreaterThanThreshold`, `GreaterThanOrEqualToThreshold`, `LessThanThreshold`, `LessThanOrEqualToThreshold`, `LessThanLowerOrGreaterThanUpperThreshold` (anomaly only) |
| `evaluationPeriods` | integer | 0 | Number of periods to evaluate (required for non-PromQL) |
| `datapointsToAlarm` | integer | 0 | M-out-of-N: trigger ALARM after M breaches in N periods. 0 = same as `evaluationPeriods` |
| `treatMissingData` | string | `` | How to treat missing data points: `breaching`, `notBreaching`, `ignore`, `missing` (AWS default). Empty = fall through to governance. |
| `evaluationWindow` | object | `` | Evaluation window config (sliding or wall-clock time) |

### Simple Metric Alarm Fields

Use for static-threshold alarms on a single metric:

| Field | Type | Default | Description |
|---|---|---|---|
| `metricName` | string | `` | CloudWatch metric name (e.g. `CPUUtilization`) |
| `namespace` | string | `` | Metric namespace (e.g. `AWS/EC2`); required with `metricName` |
| `statistic` | string | `` | `Average`, `Sum`, `Minimum`, `Maximum`, `SampleCount`. Mutually exclusive with `extendedStatistic`. |
| `extendedStatistic` | string | `` | Percentile statistic (e.g. `p99`, `p99.9`). Mutually exclusive with `statistic`. |
| `dimensions` | []object | `[]` | Metric dimensions (e.g. `[{name: "InstanceId", value: "i-123"}]`) |
| `period` | integer | 0 | Evaluation period in seconds |
| `unit` | string | `` | Metric unit of measure |
| `threshold` | float | 0 | Threshold value; use `0` explicitly for zero-threshold alarms |
| `evaluateLowSampleCountPercentile` | string | `` | `evaluate` or `ignore` for percentile metrics with low sample counts |

### Metric Math Alarm Fields

Use for computed expressions over multiple metrics:

| Field | Type | Default | Description |
|---|---|---|---|
| `metrics` | []object | `[]` | Array of MetricDataQuery objects (up to 20); each has `id`, `expression`, `metricStat`, `label`, `returnData` |
| `thresholdMetricID` | string | `` | ID of the metric to use as threshold (for anomaly detection: `ANOMALY_DETECTION_BAND` metric) |

### PromQL Alarm Fields

Use for managed Prometheus queries:

| Field | Type | Default | Description |
|---|---|---|---|
| `evaluationCriteria.promQLCriteria.query` | string | `` | PromQL query (must return single time series) |
| `evaluationCriteria.promQLCriteria.pendingPeriod` | integer | 0 | Seconds before ALARM after first breach |
| `evaluationCriteria.promQLCriteria.recoveryPeriod` | integer | 0 | Seconds of recovery before returning to OK |
| `evaluationInterval` | integer | 0 | Evaluation frequency in seconds (PromQL only) |

## Alarm Name and ARN

- **Alarm name:** Derived from `spec.nameOverride` (if set) or naming template from governance
- **Default template:** `{namespace}-{name}` (e.g. `app-team-cpu-high`)
- **Naming tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}`
- **ARN format:** `arn:aws:cloudwatch:<region>:<accountId>:alarm:<effectiveName>`

## Important Constraints

**Tag mutation:** Tags set on an alarm at creation time are not updated by subsequent patches. Governance-mandated tags must be correct at creation time.

**Missing data handling:** `treatMissingData` does not apply to PromQL alarms (which handle missing data natively).

**Alarm type mutual exclusivity:** `metricName`/`statistic`, `metrics`/`thresholdMetricID`, and `evaluationCriteria.promQLCriteria` are mutually exclusive. The AWS API enforces this.

## Governance Cascade

`CloudWatchConfig` governance profiles set:
- **Mandatory `actionsEnabled`** — Overrides instance setting; alarm actions cannot be disabled if policy enforces enabled
- **Mandatory `treatMissingData`** — Overrides instance setting; alarms must handle missing data as policy dictates
- **Mandatory `namingTemplate`** — Cloud alarm name must match template (instance `nameOverride` only escape hatch)

## Example: Simple Metric Alarm

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: cpu-high
  namespace: app-team
spec:
  configRef: general-policy
  alarmDescription: High CPU utilization alarm
  actionsEnabled: true
  metricName: CPUUtilization
  namespace: AWS/EC2
  statistic: Average
  period: 300
  evaluationPeriods: 2
  threshold: 80
  comparisonOperator: GreaterThanThreshold
  dimensions:
    - name: AutoScalingGroupName
      value: prod-asg
  alarmActions:
    - arn:aws:sns:us-east-1:123456789012:ops-alerts
  tags:
    app: production
```

## Example: Anomaly Detection Alarm

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: latency-anomaly
  namespace: app-team
spec:
  configRef: general-policy
  alarmDescription: Detects anomalous latency spikes
  comparisonOperator: LessThanLowerOrGreaterThanUpperThreshold
  evaluationPeriods: 2
  metrics:
    - id: m1
      returnData: false
      metricStat:
        metric:
          namespace: AWS/ApplicationELB
          metricName: TargetResponseTime
          dimensions:
            - name: LoadBalancer
              value: prod-lb
        period: 300
        stat: Average
    - id: ad1
      returnData: true
      expression: ANOMALY_DETECTION_BAND(m1, 2)
  thresholdMetricID: ad1
```

## Example: PromQL Alarm

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: request-rate-high
  namespace: app-team
spec:
  configRef: general-policy
  alarmDescription: Detects high request rates via PromQL
  evaluationCriteria:
    promQLCriteria:
      query: rate(http_requests_total[5m]) > 1000
      pendingPeriod: 300
      recoveryPeriod: 600
  evaluationInterval: 60
  alarmActions:
    - arn:aws:sns:us-east-1:123456789012:ops-alerts
```

## Cluster Setup

CloudWatch alarms require:
1. CloudWatchConfig profiles deployed in `kro-system`
2. SNS topics or other target resources for `alarmActions`, `okActions`, `insufficientDataActions`
3. Appropriate IAM permissions for the kropath controller to create/update alarms in AWS

## Related Resources

- [CloudWatchConfig](./cloudwatchconfig.md) — Governance profiles for alarm policies
- [CloudWatchDashboard](./cloudwatchdashboard.md) — Visual dashboards to display metrics
- [CloudWatchMetricStream](./cloudwatchmetricstream.md) — Export metrics to Firehose for external observability tools
