---
title: CloudWatch Logs Resources
description: The CloudWatch Logs family in kropath provides Kubernetes-native management of AWS CloudWatch Logs resources.
doc_type: reference
weight: 110
---
# CloudWatch Logs Resources

The CloudWatch Logs family in kropath provides Kubernetes-native management of AWS CloudWatch Logs resources. Platform teams define governance profiles, and developers create log groups that reference those profiles.

## Resources

| Resource | Purpose |
|---|---|
| [CloudWatchLogsConfig](./cloudwatchlogsconfig.md) | Governance configuration CRD — defines profiles controlling encryption, retention, and naming |
| [CloudWatchLogsLogGroup](./cloudwatchlogsloggroup.md) | Log group resource — represents an AWS CloudWatch Logs log group with subscription filters |

## Quick Start

1. **Create a governance profile** in the `kro-system` namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    retentionDays: 90
    namingTemplate: "{namespace}-{name}"
```

2. **Create a log group** in your application namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: my-app-logs
  namespace: my-app
spec:
  configRef: general-policy
```

## Key Concepts

- **Governance cascade:** Platform teams enforce mandatory controls (encryption, retention) while developers override defaults
- **Subscription filters:** Route log events to Kinesis, Lambda, or Firehose for centralized processing
- **Naming templates:** Use dynamic tokens (`{namespace}`, `{name}`, `{tag.KEY}`) to auto-generate log group names
- **Encryption:** All log groups support KMS encryption with customer-managed keys (ARN required, not key IDs or aliases)
- **Retention:** Logs are automatically deleted after the configured retention period (allowed values: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653 days)

## Common Tasks

- [Define a governance profile](./cloudwatchlogsconfig.md#example-profiles)
- [Create a log group](./cloudwatchlogsloggroup.md#basic-log-group)
- [Add subscription filters for log routing](./cloudwatchlogsloggroup.md#log-group-with-subscription-filter-kinesis)
- [Use hierarchical log group names](./cloudwatchlogsloggroup.md#hierarchical-log-group-name)
- [Enforce compliance with mandatory profiles](./cloudwatchlogsloggroup.md#pci-compliance-profile)
