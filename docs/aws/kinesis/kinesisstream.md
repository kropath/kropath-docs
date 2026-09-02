# AWS Kinesis Stream Resource Guide

The `KinesisStream` resource creates and manages AWS Kinesis Data Streams with support for both ON_DEMAND (auto-scaling) and PROVISIONED (manual shard count) capacity modes. Platform governance policies defined in `KinesisConfig` profiles ensure that all streams comply with organizational standards for capacity, naming, and tagging.

## Quick Start

Create a Kinesis stream using the default configuration profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: analytics-events
  namespace: analytics
spec:
  # (all fields below are optional and shown with their defaults)
  configRef: general-policy           # Reference to KinesisConfig profile
  streamMode: ""                      # Empty = use config profile defaults
  shardCount: 0                       # Not used in ON_DEMAND mode
  nameOverride: ""                    # Empty = use naming template from profile
  deletionPolicy: retain              # retain | delete
  tags: {}
  syncedLabels: {}
  syncedAnnotations: {}
```

The `general-policy` profile applies:
- Capacity mode: ON_DEMAND (auto-scaling)
- Naming template: `{namespace}-{name}` → `analytics-analytics-events`
- No mandatory tags

## Core Concepts

### Capacity Modes

#### ON_DEMAND Mode

Streams automatically scale to match demand. AWS charges per GB of data written. Use this mode when traffic patterns are unpredictable or bursty.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: click-stream
  namespace: analytics
spec:
  streamMode: "on_demand"
  # shardCount is ignored in ON_DEMAND mode
```

#### PROVISIONED Mode

Streams have a fixed number of shards that you control. Each shard provides 1 MB/sec write and 2 MB/sec read throughput. Use this mode for predictable, steady-state traffic.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: analytics-events
  namespace: analytics
spec:
  streamMode: "provisioned"
  shardCount: 4  # 4 MB/sec write, 8 MB/sec read capacity
```

### Capacity Mode Switching

You can switch a stream between ON_DEMAND and PROVISIONED modes by updating the resource. During the transition, the stream enters an UPDATING state and returns to ACTIVE once complete.

**Switching from ON_DEMAND to PROVISIONED:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: click-stream
spec:
  streamMode: "provisioned"  # Changed from "on_demand"
  shardCount: 2
  # status.streamStatus transitions: UPDATING → ACTIVE
```

**Switching from PROVISIONED to ON_DEMAND:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: analytics-events
spec:
  streamMode: "on_demand"  # Changed from "provisioned"
  # shardCount is ignored; no need to update it
  # status.streamStatus transitions: UPDATING → ACTIVE
```

### Stream Naming

Stream names are derived from a naming template in the governance configuration. By default, the template is `{namespace}-{name}`, producing names like:

*   Namespace: `analytics`, Resource name: `click-events` → Stream name: `analytics-click-events`
*   Namespace: `payments`, Resource name: `transactions` → Stream name: `payments-transactions`

AWS Kinesis stream names must:
- Use characters `a-zA-Z0-9_.-` only
- Be 1–128 characters long
- Be unique within your AWS account + region

If you need a custom name, use `nameOverride`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: events
  namespace: analytics
spec:
  nameOverride: "my-custom-stream-name"  # Bypasses naming template
```

The resource status field `resourceName` shows the final stream name:

```bash
$ kubectl get kinesisstream analytics-events -n analytics -o jsonpath='{.status.resourceName}'
analytics-analytics-events
```

## Configuration Profiles

Use `configRef` to select a platform-defined governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: high-volume-events
  namespace: analytics
spec:
  configRef: high-throughput  # Use high-throughput profile instead of default
```

The `high-throughput` profile might enforce:
- Capacity mode: PROVISIONED
- Minimum shard count: 8
- Mandatory tags for cost tracking

See the `KinesisConfig` documentation for available profiles and how platform teams define new ones.

## Tagging and Metadata

All streams receive tags for cost allocation, team attribution, and automation. Tags can come from three sources, which are merged in this order (earlier always wins on key conflicts):

1. **Governance mandatory tags** — Platform-enforced tags that always override any conflicting keys from other sources
2. **Stream-level tags** — Tags you specify on the resource (overrides defaults but not mandatory)
3. **Governance defaults** — Fallback tags from the profile if not already set by mandatory or stream-level

### Synced Labels and Annotations

Kubernetes labels and annotations can be mirrored to both Kubernetes metadata and AWS resource tags using `syncedLabels` and `syncedAnnotations`. `syncedLabels` appear as both Kubernetes `metadata.labels` (with `aws.kropath.run/` prefix) and cloud tags. `syncedAnnotations` appear as both Kubernetes `metadata.annotations` (with `aws.kropath.run/` prefix) and cloud tags.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: order-events
  namespace: ecommerce
  labels:
    app.kubernetes.io/team: fulfillment
spec:
  tags:
    cost-center: fulfillment
  syncedLabels:
    environment: production
    tier: critical
  # Both tags and syncedLabels appear as AWS tags:
  # - cost-center: fulfillment
  # - aws.kropath.run/environment: production
  # - aws.kropath.run/tier: critical
```

## Deletion Policy

Control what happens to the AWS stream when you delete the Kubernetes resource:

*   `retain` (default) — Stream persists in AWS; only the Kubernetes resource is deleted
*   `delete` — Stream is deleted from AWS when the Kubernetes resource is deleted

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: test-stream
  namespace: dev
spec:
  deletionPolicy: delete  # Delete the AWS stream on resource deletion
```

## Status Fields

The stream resource exposes several read-only status fields:

| Field | Description |
|---|---|
| `resourceName` | The actual stream name in AWS (after template and override resolution) |
| `namingStatus` | `"valid"` if the stream name is valid; `"invalid-unresolved-tokens"` if the naming template contains unresolved tokens |
| `predictedArn` | The expected ARN in the format `arn:aws:kinesis:<region>:<account>:stream/<resourceName>` |
| `streamStatus` | AWS stream status: CREATING, ACTIVE, UPDATING, or DELETING |
| `openShardCount` | Number of currently open shards in the stream |
| `retentionPeriodHours` | Data retention period in hours (read-only; configured via AWS) |
| `encryptionType` | Encryption type: NONE or KMS (read-only; configured via AWS) |
| `conditions` | Standard Kubernetes conditions for tracking reconciliation state |

View the full status:

```bash
$ kubectl describe kinesisstream analytics-events -n analytics
```

## Governance Cascade Example

This example shows how governance policies from `KinesisConfig` and `KropathConfig` combine with your stream configuration:

**Step 1: Platform setup**

A platform team creates a `high-throughput` profile:

```yaml
# KinesisConfig in kro-system namespace
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: high-throughput
  namespace: kro-system
spec:
  mandatory:
    streamMode: "provisioned"  # Force provisioned mode
    shardCount: 8               # Minimum 8 shards
    tags:
      workload-tier: high-throughput
  defaults:
    namingTemplate: "{namespace}-{name}"
```

**Step 2: Platform org policy**

Organization-wide policy enforced via `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    tags:
      cost-center: platform
    kinesis:
      # org-wide policy: all streams must be provisioned (overrides KinesisConfig if different)
      streamMode: "provisioned"
  defaults:
    kinesis:
      streamMode: "on_demand"  # Org default for other profiles
```

**Step 3: Developer creates a stream**

A developer references the `high-throughput` profile and adds custom tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: order-events
  namespace: payments
spec:
  configRef: high-throughput
  streamMode: ""  # Empty: let config profiles decide
  shardCount: 0   # Empty: let config profiles decide
  tags:
    product-team: payments
```

**Step 4: Final effective configuration (as computed by controller)**

The controller merges governance layers:

```
Mandatory tier wins:
  - streamMode: "provisioned" (from both KropathConfig and KinesisConfig)
  - shardCount: 8 (from KinesisConfig.mandatory)
  - tags: cost-center=platform + workload-tier=high-throughput + product-team=payments

Instance overrides: (none — all fields empty or 0)

Defaults tier (fallback):
  - namingTemplate: "{namespace}-{name}"

Final stream:
  - Capacity mode: PROVISIONED
  - Shard count: 8 shards
  - Stream name: payments-order-events
  - Tags: cost-center, workload-tier, product-team
```

## Cross-Family References

Kinesis streams can be referenced by other AWS services through their ARN. The `predictedArn` field contains the stream's ARN, enabling integration with:

### Lambda Event Source Mapping

Create an event source mapping to invoke a Lambda function when records arrive in the stream:

```bash
aws lambda create-event-source-mapping \
  --event-source-arn $(kubectl get kinesisstream order-events -n payments -o jsonpath='{.status.predictedArn}') \
  --function-name ProcessStreamRecords \
  --batch-size 100 \
  --starting-position LATEST
```

### CloudWatch Alarm Dimensions

Set up alarms monitoring stream metrics:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name high-latency-alert \
  --dimensions Name=StreamName,Value=$(kubectl get kinesisstream analytics-events -n analytics -o jsonpath='{.status.resourceName}') \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --threshold 5000 \
  --comparison-operator GreaterThanThreshold
```

## Complete Example: Multi-Environment Setup

Here's a complete setup showing development and production configurations:

```yaml
---
# 1. Development profile: cost-optimized with ON_DEMAND
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: dev-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev-policy
spec:
  mandatory: {}
  defaults:
    streamMode: "on_demand"
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: dev
    syncedLabels:
      tier: dev

---
# 2. Production profile: performance-optimized with PROVISIONED
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisConfig
metadata:
  name: prod-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod-policy
spec:
  mandatory:
    streamMode: "provisioned"
    shardCount: 4
    tags:
      environment: prod
      compliance-tier: prod
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
    syncedLabels:
      tier: prod

---
# 3. Development stream
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: user-events
  namespace: dev
spec:
  configRef: dev-policy
  tags:
    app: user-service

---
# 4. Production stream with higher capacity
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: user-events
  namespace: prod
spec:
  configRef: prod-policy
  shardCount: 16  # Override profile default for high traffic
  tags:
    app: user-service
    sla: critical
```

## Troubleshooting

### Stream stuck in UPDATING state

The stream may be held in UPDATING state while AWS processes the mode switch. This is normal and typically completes within a few minutes. Check the stream status in the AWS console for details.

### Naming validation error

If `status.namingStatus` shows `"invalid-unresolved-tokens"`, the naming template contains unrecognized tokens. Common causes:

*   Using `{env}` instead of `{tag.env}` for tag-based tokens
*   Referencing a tag key that doesn't exist in any governance tier or the stream specification

Verify the tag exists in the governance profile or add it to your stream's `tags`.

### ConfigRef profile not found

If your stream references a non-existent `configRef`, it will fail to reconcile. Verify the profile name exists:

```bash
kubectl get kinesisconfig -n kro-system
```

## Out of Scope

The following Kinesis features are managed outside of kropath:

*   Encryption at rest (KMS key configuration)
*   Data retention period (hours)
*   Enhanced monitoring (shard-level metrics)
*   Consumer management and enhanced fan-out
*   Kinesis Data Firehose, Analytics, and Video Streams (separate AWS services)
