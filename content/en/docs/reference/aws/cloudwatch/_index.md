---
title: CloudWatch Family
description: The CloudWatch family of resources provides comprehensive monitoring and observability for AWS workloads.
doc_type: reference
weight: 100
---
# CloudWatch Family

The CloudWatch family of resources provides comprehensive monitoring and observability for AWS workloads. You can create and manage CloudWatch alarms, dashboards, and metric streams entirely through Kubernetes, with centralized governance policies for compliance and operational control.

## Resources

### Governance

- **[CloudWatchConfig](./cloudwatchconfig.md)** — Define governance profiles (mandatory and default policies) for alarm actions, missing data handling, output formats, naming conventions, and metadata. Platform teams create named profiles; developers select the profile they need.

### Monitoring

- **[CloudWatchAlarm](./cloudwatchalarm.md)** — Create metric alarms with static thresholds, metric math expressions, anomaly detection, or PromQL queries. Connect alarms to SNS topics, Lambda functions, EC2 actions, or Systems Manager for automated remediation.

### Dashboarding

- **[CloudWatchDashboard](./cloudwatchdashboard.md)** — Build custom visual dashboards to display metrics, logs, and alarms. Dashboards are global AWS resources with widget-based layouts defined as JSON.

### Streaming

- **[CloudWatchMetricStream](./cloudwatchmetricstream.md)** — Stream CloudWatch metrics to external observability platforms (Datadog, Splunk, New Relic) or custom pipelines via Kinesis Data Firehose. Supports format selection (JSON, OpenTelemetry) and metric filtering.

## Quick Start

1. **Deploy governance profiles** — Create `CloudWatchConfig` CRs in the `kro-system` namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    treatMissingData: "missing"
    outputFormat: "json"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

2. **Create an alarm** — Developers create alarms in their namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: cpu-high
  namespace: app-team
spec:
  configRef: general-policy
  metricName: CPUUtilization
  namespace: AWS/EC2
  statistic: Average
  period: 300
  evaluationPeriods: 1
  threshold: 80
  comparisonOperator: GreaterThanThreshold
  alarmActions:
    - arn:aws:sns:us-east-1:123456789012:alerts
```

3. **Create a dashboard** — Visualize metrics:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchDashboard
metadata:
  name: app-metrics
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
              [ "AWS/EC2", "CPUUtilization" ]
            ],
            "period": 300,
            "stat": "Average",
            "region": "us-east-1",
            "title": "EC2 CPU"
          }
        }
      ]
    }
```

## Governance and Policy

All CloudWatch resources respect a **two-tier governance cascade**:

1. **Mandatory tier** — Platform-enforced controls (e.g., all alarms must have actions enabled, all metric streams must use OpenTelemetry format, all resources must use the compliance naming pattern)
2. **Defaults tier** — Baseline values developers can override (e.g., default missing data treatment is `"missing"`, default metric stream format is `"json"`)

**Organization-wide governance** flows through `KropathConfig` (in `kro-system`), which sets org-level mandatory and default policies. **Resource-specific governance** flows through `CloudWatchConfig` profiles, which can be more restrictive than org-wide settings.

See [CloudWatchConfig](./cloudwatchconfig.md) for complete cascade semantics.

## Common Patterns

### Multi-Environment Profiles

Create separate `CloudWatchConfig` profiles for different environments:

```yaml
---
# Development: permissive
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}
  defaults:
    treatMissingData: "notBreaching"
    outputFormat: "json"
    namingTemplate: "dev-{namespace}-{name}"

---
# Production: strict
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: prod
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod
spec:
  mandatory:
    actionsEnabled: true
    treatMissingData: "breaching"
    outputFormat: "json"
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
  defaults: {}
```

Developers select the appropriate profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: cpu-high
  namespace: my-app
spec:
  configRef: prod  # ← Select the prod profile
  # ... alarm spec
```

### Metric Export Pipeline

Stream CloudWatch metrics to an external platform for enhanced analytics:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchMetricStream
metadata:
  name: datadog-stream
  namespace: observability-prod
spec:
  configRef: general-policy
  firehoseArn: arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-to-datadog
  roleArn: arn:aws:iam::123456789012:role/CloudWatchMetricStreamRole
  outputFormat: json
  includeFilters:
    - namespace: AWS/ApplicationELB
    - namespace: AWS/RDS
  tags:
    destination: datadog
```

### Compliance Enforcement

Create a strict profile for regulated workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    actionsEnabled: true
    treatMissingData: "breaching"
    namingTemplate: "hipaa-{namespace}-{name}"
    tags:
      compliance: hipaa
      data-classification: phi
    syncedLabels:
      compliance: hipaa
      audit-required: "true"
  defaults: {}
```

Developers creating regulated resources reference this profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: data-pipeline-alert
  namespace: healthcare-app
spec:
  configRef: hipaa  # ← Enforces HIPAA compliance controls
  metricName: DataPipelineLatency
  # ... rest of spec
```

## Limitations

**Dashboard cloud tags:** CloudWatchDashboard does not support AWS cloud tags due to a current platform limitation. Governance-mandated tags cannot be applied to Dashboard cloud resources. Governance-mandated `syncedLabels` are mirrored to Kubernetes metadata only.

**Metric stream format:** `outputFormat` is not governed by `KropathConfig` org-wide settings; it is a `CloudWatchConfig`-only field.

## Prerequisites

- **AWS credentials** — Cluster must have IAM permissions to create/update CloudWatch resources in the target AWS account
- **Governance profiles** — At least one `CloudWatchConfig` CR (e.g. `general-policy`) must exist in `kro-system` before creating resources
- **External integrations** — For metric streams, a Kinesis Data Firehose delivery stream must exist and be configured with appropriate destination
- **Alarm targets** — SNS topics, Lambda functions, or other alarm actions must be pre-created in AWS

## Related Families

- [CloudWatch Logs](../cloudwatchlogs/index.md) — Log group management and log filtering
