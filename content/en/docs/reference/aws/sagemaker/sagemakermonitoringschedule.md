---
title: SageMakerMonitoringSchedule — Recurring Monitoring Job
description: "The `SageMakerMonitoringSchedule` resource runs recurring monitoring jobs against an endpoint to detect drift and anomalies."
doc_type: reference
---
# SageMakerMonitoringSchedule — Recurring Monitoring Job

The `SageMakerMonitoringSchedule` resource runs recurring monitoring jobs against an endpoint to detect drift and anomalies.

## Core Fields

### Schedule Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SageMakerConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the schedule name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted |

### Monitoring Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `endpointName` | string | required | Endpoint to monitor |
| `baselineConfig.baseliningJobName` | string | optional | Baseline job for drift comparison |
| `monitoringScheduleConfig.scheduleExpression` | string | required | Cron expression for monitoring schedule |
| `monitoringScheduleConfig.monitoringJobDefinitionName` | string | required | Job definition to use (one of the job definition types) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |

## Status Outputs

After reconciliation, the schedule's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective schedule name in AWS |
| `monitoringScheduleArn` | string | The ARN of the monitoring schedule in AWS |
| `monitoringScheduleStatus` | string | `"Pending"`, `"Scheduled"`, `"Stopped"`, etc. |
| `conditions` | array | Status conditions (ready, error, etc.) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SageMakerMonitoringSchedule
metadata:
  name: endpoint-monitoring
  namespace: ml-team
spec:
  configRef: ml-production
  endpointName: ml-inference
  monitoringScheduleConfig:
    scheduleExpression: "cron(0 */1 * * ? *)"
    monitoringJobDefinitionName: data-quality-job
  tags:
    Endpoint: ml-inference
```

## Dependencies

- **Requires:** Endpoint to monitor, job definition resource
- **Governance:** `SageMakerConfig` for governance tagging
