# CloudWatchMetricStream — Metric Streaming to Firehose

The `CloudWatchMetricStream` resource creates and manages AWS CloudWatch metric streams in Kubernetes. Metric streams continuously export CloudWatch metrics to a Kinesis Data Firehose, enabling near-real-time delivery to external observability platforms (Datadog, Splunk, New Relic, custom S3/OpenTelemetry pipelines).

## Overview

CloudWatch metric streams push metrics from AWS CloudWatch to external destinations via Kinesis Data Firehose. A `CloudWatchMetricStream` wraps the AWS CloudWatch MetricStream API and coordinates with governance policy defined in `CloudWatchConfig`.

Metric streams support:
- **Output format selection** — JSON, OpenTelemetry 1.0, or OpenTelemetry 0.7
- **Namespace filtering** — Include or exclude specific metric namespaces
- **Metric-level filtering** — Fine-grained control of which metrics are exported
- **Additional statistics** — Extend exported metrics with percentile or custom statistics
- **Cross-account metrics** — Include metrics from linked monitoring accounts

## Spec Fields

### Delivery and Identity

| Field | Type | Default | Required | Description |
|---|---|---|---|---|
| `firehoseArn` | string | `` | ✓ | ARN of the Kinesis Data Firehose delivery stream (must exist in same account) |
| `roleArn` | string | `` | ✓ | IAM role ARN with `firehose:PutRecord` and `firehose:PutRecordBatch` permissions |

### Configuration and Output

| Field | Type | Default | Description |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects governance profile from `CloudWatchConfig` |
| `nameOverride` | string | `` | Bypasses naming template; sets cloud stream name directly |
| `deletionPolicy` | string | `retain` | Deletion behavior: `retain` (keep) or `delete` (remove cloud resource) |
| `outputFormat` | string | `` | Output format: `json`, `opentelemetry1.0`, `opentelemetry0.7`. Empty = fall through to governance. Default: `json` |

### Metric Filtering

| Field | Type | Default | Description |
|---|---|---|---|
| `includeFilters` | []object | `[]` | Namespaces (and optionally metric names) to include. Mutually exclusive with `excludeFilters`. |
| `excludeFilters` | []object | `[]` | Namespaces (and optionally metric names) to exclude. Mutually exclusive with `includeFilters`. |

Each filter has:
- `namespace` (string) — AWS metric namespace (e.g. `AWS/EC2`)
- `metricNames` ([]string, optional) — Specific metric names within the namespace; omit to include/exclude all

### Advanced Options

| Field | Type | Default | Description |
|---|---|---|---|
| `includeLinkedAccountsMetrics` | boolean | false | Include metrics from linked monitoring-account sources |
| `statisticsConfigurations` | []object | `[]` | Additional statistics beyond MAX/MIN/SUM/SAMPLECOUNT |
| `tags` | map | `{}` | Cloud tags applied to stream. Governance-mandated tags cannot be removed. |
| `syncedLabels` | map | `{}` | Synced to Kubernetes labels and cloud tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Synced to Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Metric Stream Name and ARN

- **Stream name:** Derived from `spec.nameOverride` (if set) or naming template from governance
- **Default template:** `{namespace}-{name}` (e.g. `observability-prod-ec2-stream`)
- **Naming tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}`
- **ARN format:** `arn:aws:cloudwatch:<region>:<accountId>:metric-stream/<effectiveName>`

## Important Constraints

**Tag mutation:** Tags set on a metric stream at creation time are not updated by subsequent patches. Governance-mandated tags must be correct at creation time.

**Include/exclude mutual exclusivity:** You cannot set both `includeFilters` and `excludeFilters` simultaneously. The AWS API enforces this and returns `InvalidParameterInput` error if both are populated.

**Firehose and role requirements:** Both `firehoseArn` and `roleArn` are semantically required by the AWS API, even though the ACK CRD may not explicitly mark them as required. Omitting either causes reconciliation failure.

**Statistics configurations:** Additional statistics (e.g. percentiles) are only supported on specific metrics and statistics. Consult the AWS CloudWatch Metric Streams documentation for supported combinations.

## Governance Cascade

`CloudWatchConfig` governance profiles set:
- **Mandatory `outputFormat`** — Overrides instance setting; streams must use policy-mandated format
- **Mandatory `namingTemplate`** — Cloud stream name must match template (instance `nameOverride` only escape hatch)

Note: `actionsEnabled` and `treatMissingData` do not apply to Metric Streams (no alarm actions or missing data concepts).

## Example: Simple Metric Stream (Include All EC2)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchMetricStream
metadata:
  name: ec2-stream
  namespace: observability-prod
spec:
  configRef: general-policy
  firehoseArn: arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-to-datadog
  roleArn: arn:aws:iam::123456789012:role/CloudWatchMetricStreamRole
  outputFormat: json
  includeFilters:
    - namespace: AWS/EC2
  tags:
    destination: datadog
    environment: production
  syncedLabels:
    team: platform
```

## Example: Filtered Metric Stream (Exclude System Metrics)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchMetricStream
metadata:
  name: app-metrics
  namespace: observability-prod
spec:
  configRef: general-policy
  firehoseArn: arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-to-splunk
  roleArn: arn:aws:iam::123456789012:role/CloudWatchMetricStreamRole
  outputFormat: opentelemetry1.0
  excludeFilters:
    - namespace: AWS/EC2
    - namespace: AWS/Lambda
    - namespace: AWS/RDS
  tags:
    destination: splunk
    environment: production
  syncedLabels:
    team: platform
```

## Example: Multi-Namespace Stream with Statistics

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchMetricStream
metadata:
  name: comprehensive-metrics
  namespace: observability-prod
spec:
  configRef: general-policy
  firehoseArn: arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-to-newrelic
  roleArn: arn:aws:iam::123456789012:role/CloudWatchMetricStreamRole
  outputFormat: json
  includeFilters:
    - namespace: AWS/ApplicationELB
      metricNames:
        - TargetResponseTime
        - RequestCount
        - HTTPCode_Target_5XX_Count
    - namespace: AWS/RDS
      metricNames:
        - DatabaseConnections
        - CPUUtilization
        - ReadLatency
        - WriteLatency
  statisticsConfigurations:
    - includeMetrics:
        - namespace: AWS/ApplicationELB
          metricName: TargetResponseTime
      additionalStatistics:
        - p50
        - p90
        - p99
    - includeMetrics:
        - namespace: AWS/RDS
          metricName: ReadLatency
      additionalStatistics:
        - p99.9
  tags:
    destination: newrelic
    environment: production
```

## Example: Cross-Account Metrics

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchMetricStream
metadata:
  name: org-metrics
  namespace: observability-prod
spec:
  configRef: general-policy
  firehoseArn: arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-org-stream
  roleArn: arn:aws:iam::123456789012:role/CloudWatchMetricStreamRole
  outputFormat: json
  includeLinkedAccountsMetrics: true
  includeFilters:
    - namespace: AWS/EC2
  tags:
    scope: organization
    environment: production
```

## Cluster Setup

CloudWatch metric streams require:
1. CloudWatchConfig profiles deployed in `kro-system`
2. A Kinesis Data Firehose delivery stream already created in the same AWS account
3. An IAM role with `firehose:PutRecord` and `firehose:PutRecordBatch` permissions
4. (Optional) External destination configured on the Firehose (e.g. Datadog, Splunk) to consume the exported metrics

## Common Destination Setups

**Datadog:** Configure Firehose with an HTTPS endpoint to `https://awsmetrics-intake.<DATADOG-SITE>.datadoghq.com/v1/input/<API_KEY>`. Use JSON output format.

**Splunk:** Configure Firehose with an HTTPS endpoint to your Splunk HEC (HTTP Event Collector) endpoint.

**New Relic:** Configure Firehose with an HTTPS endpoint to the New Relic metrics API.

**Custom S3 / OpenTelemetry:** Configure Firehose to write to S3 or process via Lambda for custom ingestion pipelines.

## Related Resources

- [CloudWatchConfig](./cloudwatchconfig.md) — Governance profiles for metric stream policies
- [CloudWatchAlarm](./cloudwatchalarm.md) — Metric alarms to trigger on threshold breaches
- [CloudWatchDashboard](./cloudwatchdashboard.md) — Visual dashboards to display metrics
