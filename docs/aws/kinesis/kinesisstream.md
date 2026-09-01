# AWS Kinesis Data Stream Usage Guide

The `KinesisStream` resource enables teams to create and manage AWS Kinesis Data Streams on any Kubernetes cluster. Each `KinesisStream` CR is composed into an ACK (AWS Controller for Kubernetes) `Stream` resource, giving platform teams full control over capacity modes, shard counts, naming, tagging, and deletion policies through a Kubernetes-native interface.

## Capacity Modes and Shard Configuration

Kinesis Data Streams support two distinct capacity models, each with different scaling and cost characteristics.

### ON_DEMAND Capacity Mode

Best for workloads with unpredictable traffic or spiky patterns. ON_DEMAND mode automatically scales throughput up and down based on actual traffic, with billing based on data ingested and retrieved (no fixed shard cost).

**Characteristics:**

- Auto-scaling: No manual shard management required
- Billing: Based on PUT records and scanned records (pay-as-you-go)
- Throughput: Up to 4 MB/s input and 2 MB/s output per stream by default; request higher limits if needed
- No `shardCount` parameter — Kinesis manages shards automatically

### PROVISIONED Capacity Mode

Best for workloads with predictable, sustained traffic. PROVISIONED mode requires explicit shard count configuration, with billing based on the number of shards and retention hours.

**Characteristics:**

- Fixed shards: You specify the number of shards; throughput scales linearly with shard count (1 MB/s input + 2 MB/s output per shard)
- Billing: Based on shard-hours (predictable cost model)
- Manual scaling: Increase or decrease shard count as traffic patterns change
- Requires `shardCount` parameter when `streamMode: "provisioned"`

### Default Behavior

If neither `KinesisConfig` nor the instance specifies a capacity mode, kropath defaults to `"on_demand"` — the most cost-effective choice for most new workloads. Existing provisioned streams continue to operate at their configured shard count.

## Basic Stream Creation

### Minimal Example: Using Defaults

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: my-events
  namespace: default
spec:
  configRef: general-policy    # Use general-policy profile (defaults to ON_DEMAND)
```

This creates a Kinesis stream named `default-my-events` (from the default naming template `{namespace}-{name}`) with:

- **Capacity mode:** ON_DEMAND (from `general-policy` defaults)
- **Stream name:** `default-my-events`
- **Deletion policy:** `retain` (default — the stream survives CR deletion)
- **Tags:** Inherited from `general-policy` profile

### ON_DEMAND Stream

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: user-activity
  namespace: analytics
spec:
  configRef: general-policy
  streamMode: "on_demand"      # Explicit ON_DEMAND (overrides defaults if present)
  tags:
    service: user-tracking
    cost-center: analytics
```

Stream name: `analytics-user-activity`

### PROVISIONED Stream

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: high-volume-events
  namespace: streaming-prod
spec:
  configRef: high-throughput   # Uses high-throughput profile
  streamMode: "provisioned"
  shardCount: 8                # 8 MB/s input, 16 MB/s output capacity
  tags:
    service: event-aggregator
    sla: critical
```

Stream name: `streaming-prod-high-volume-events` (from `high-throughput` profile's naming template)

## Profile-Based Configuration

### Selecting a Configuration Profile

The `configRef` field allows resource instances to select from multiple `KinesisConfig` profiles defined by your platform team. This decouples instance configuration from governance policies.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: analytics-batch
  namespace: data-processing
spec:
  configRef: analytics-pipeline    # References custom "analytics-pipeline" KinesisConfig
```

If a profile doesn't exist or `configRef` is left empty, it falls back to `general-policy`.

### Profile Cascade Behavior

When a stream is created, kropath resolves configuration in this order (highest priority first):

1. **Mandatory tier (org-wide):** `KropathConfig.spec.mandatory.kinesis.*`
2. **Mandatory tier (profile):** `KinesisConfig.spec.mandatory.*` (from the selected profile)
3. **Instance spec:** `streamMode`, `shardCount`, `tags` on the CR itself
4. **Defaults tier (profile):** `KinesisConfig.spec.defaults.*`
5. **Defaults tier (org-wide):** `KropathConfig.spec.defaults.kinesis.*`
6. **Built-in defaults:** ON_DEMAND mode; shard count = 1 for provisioned streams

**Example:** If `KinesisConfig/general-policy` has `defaults.streamMode: "on_demand"` and your CR specifies `streamMode: "provisioned"`, the instance wins — the stream is provisioned. But if the profile has `mandatory.streamMode: "on_demand"`, the profile wins and the instance cannot override it.

## Naming and Resource Discovery

### Automatic Name Resolution

Stream names are derived from the naming template selected by the governance cascade. The default template is `{namespace}-{name}`.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: click-stream
  namespace: web-analytics
spec:
  configRef: general-policy
status:
  resourceName: "web-analytics-click-stream"     # Effective stream name
  namingStatus: "valid"                           # Naming template resolved successfully
  predictedArn: "arn:aws:kinesis:us-east-1:123456789012:stream/web-analytics-click-stream"
```

### Custom Naming Override

For streams that need custom names (e.g., migrating existing streams or external integrations):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: internal-k8s-name
  namespace: default
spec:
  nameOverride: "legacy-kinesis-stream"   # Use this exact cloud name instead of template
```

The stream will be named exactly `legacy-kinesis-stream` in AWS, regardless of the naming template.

### Dynamic Names with Tags

Naming templates can reference tag values for hierarchical naming:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: events
  namespace: analytics
spec:
  tags:
    env: prod
    service: etl
  # Assuming KinesisConfig has namingTemplate: "{tag.env}-{tag.service}-{name}"
status:
  resourceName: "prod-etl-events"
  namingStatus: "valid"
```

If a referenced tag is missing, it resolves to an empty string:

```yaml
spec:
  # KinesisConfig has namingTemplate: "{tag.missing}-events"
  # tag "missing" does not exist
status:
  resourceName: "-events"              # Missing token → empty string
  namingStatus: "valid"                # Still valid (missing tokens are allowed)
```

Unrecognized tokens (e.g., `{env}` instead of `{tag.env}`) are kept verbatim and cause naming errors:

```yaml
spec:
  # KinesisConfig has namingTemplate: "{env}-events" (missing "tag." prefix)
status:
  resourceName: "{env}-events"         # Unresolved token kept verbatim
  namingStatus: "invalid-unresolved-tokens"
```

## Capacity Mode Switching

Kinesis supports changing a stream's capacity mode without data loss. This transition may take several minutes, during which the stream status shows `UPDATING`.

### Switching from ON_DEMAND to PROVISIONED

```yaml
# Original: ON_DEMAND stream
spec:
  streamMode: "on_demand"

# Updated: Provisioned with 4 shards
spec:
  streamMode: "provisioned"
  shardCount: 4

# During transition:
status:
  streamStatus: "UPDATING"

# After transition completes:
status:
  streamStatus: "ACTIVE"
  openShardCount: 4
```

### Switching from PROVISIONED to ON_DEMAND

```yaml
# Original: Provisioned stream with 8 shards
spec:
  streamMode: "provisioned"
  shardCount: 8

# Updated: Switch to auto-scaling
spec:
  streamMode: "on_demand"
  # shardCount is omitted or ignored in ON_DEMAND mode

# During transition:
status:
  streamStatus: "UPDATING"

# After transition:
status:
  streamStatus: "ACTIVE"
```

## Metadata: Tags, Labels, and Annotations

### Tag Management

Tags are merged from three sources in cascade order:

1. **Mandatory tags (org-wide):** `KropathConfig.spec.mandatory.tags`
2. **Mandatory tags (profile):** `KinesisConfig.spec.mandatory.tags`
3. **Instance tags:** `KinesisStream.spec.tags`
4. **Default tags (profile):** `KinesisConfig.spec.defaults.tags`
5. **Default tags (org-wide):** `KropathConfig.spec.defaults.tags`

Mandatory tags cannot be removed by the instance (they always appear on the AWS resource). Default tags can be extended but not overridden.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: user-events
  namespace: default
spec:
  configRef: general-policy
  tags:
    service: user-service
    version: v2
  # KinesisConfig/general-policy has:
  #   mandatory.tags: { environment: production }
  #   defaults.tags: { managed-by: kropath, owner-team: platform }
status:
  # Final tags on the AWS stream:
  # - environment: production        (mandatory, cannot be removed)
  # - managed-by: kropath            (default, can be extended)
  # - owner-team: platform           (default, can be extended)
  # - service: user-service          (instance-level)
  # - version: v2                    (instance-level)
```

### Synced Labels and Annotations

Kubernetes labels and annotations can be mirrored to both the CR and AWS resource tags using `syncedLabels` and `syncedAnnotations`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: events
  namespace: analytics
spec:
  syncedLabels:
    workload-type: streaming
    sla-tier: critical
  syncedAnnotations:
    team: data-platform
    runbook-url: "https://wiki.internal/kinesis-runbook"
  # KinesisConfig/general-policy has:
  #   mandatory.syncedLabels: { data-class: public }

# Results in:
# 1. Kubernetes labels on the CR:
#    - aws.kropath.run/data-class: public              (mandatory)
#    - aws.kropath.run/workload-type: streaming        (instance)
#    - aws.kropath.run/sla-tier: critical              (instance)
#    - aws.kropath.run/team: data-platform             (annotation → label)
#    - app.kubernetes.io/managed-by: kro
#    - app.kubernetes.io/instance: events

# 2. AWS resource tags (for CloudWatch correlation):
#    - aws.kropath.run/data-class: public
#    - aws.kropath.run/workload-type: streaming
#    - aws.kropath.run/sla-tier: critical
#    - aws.kropath.run/team: data-platform
```

## Deletion Policy

The `deletionPolicy` field controls whether the AWS stream is deleted when the Kubernetes CR is deleted.

### Retain Policy (Default)

```yaml
spec:
  deletionPolicy: "retain"    # Default; stream survives CR deletion
```

When the CR is deleted, the AWS stream continues to exist and retain all records. Use this for production streams to prevent accidental data loss.

### Delete Policy

```yaml
spec:
  deletionPolicy: "delete"    # Stream is deleted when CR is deleted
```

When the CR is deleted, the AWS stream is deleted immediately. Use with caution for development or ephemeral workloads only.

## Status Fields and Observability

### Key Status Fields

| Field | Type | Description |
|---|---|---|
| `resourceName` | string | The effective AWS stream name (computed from naming template) |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` (indicates naming errors) |
| `predictedArn` | string | The expected AWS ARN for the stream (useful for cross-service references) |
| `streamStatus` | string | `CREATING` \| `ACTIVE` \| `UPDATING` \| `DELETING` |
| `openShardCount` | integer | Current number of active shards (from AWS) |
| `retentionPeriodHours` | integer | Data retention duration in hours (default 24) |
| `encryptionType` | string | `"NONE"` or `"KMS"` (encryption method) |
| `keyID` | string | KMS key identifier if `encryptionType: "KMS"` |
| `conditions` | array | Standard Kubernetes condition objects (Ready, etc.) |

### Complete Example with Status

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: customer-events
  namespace: streaming-prod
spec:
  configRef: high-throughput
  streamMode: "provisioned"
  shardCount: 4
  tags:
    service: customer-tracking
    cost-center: platform
status:
  resourceName: "streaming-prod-customer-events"
  namingStatus: "valid"
  predictedArn: "arn:aws:kinesis:us-east-1:123456789012:stream/streaming-prod-customer-events"
  streamStatus: "ACTIVE"
  openShardCount: 4
  retentionPeriodHours: 24
  encryptionType: "NONE"
  keyID: ""
  conditions:
    - type: Ready
      status: "True"
      reason: "StreamReady"
      message: "Stream is active and ready for use"
```

## Cross-Service Integration

### Lambda Event Source Mapping

Configure a Lambda function to process stream records:

```yaml
# Kubernetes-side: Create the KinesisStream
apiVersion: aws.kropath.run/v1alpha1
kind: KinesisStream
metadata:
  name: user-events
  namespace: lambda-tasks
spec:
  streamMode: "on_demand"

---
# AWS-side: Create a Lambda event source mapping
# (Use AWS Lambda console, SDK, or CloudFormation)
# EventSourceArn: <KinesisStream.status.predictedArn>
# FunctionName: my-processor-function
# BatchSize: 100
# StartingPosition: TRIM_HORIZON
```

### CloudWatch Metrics and Alarms

Monitor stream health and throughput:

```yaml
# Set up a CloudWatch alarm for iterator age
apiVersion: cloudwatch.aws.amazon.com/v1beta1
kind: Alarm
metadata:
  name: kinesis-stream-lag-alarm
spec:
  StreamName: <KinesisStream.status.resourceName>
  MetricName: "GetRecords.IteratorAgeMilliseconds"
  Threshold: 60000  # 1 minute lag
  ComparisonOperator: "GreaterThanThreshold"
  AlarmActions:
    - Arn: "arn:aws:sns:us-east-1:123456789012:alerts"
```

## Troubleshooting

### Naming Errors: `invalid-unresolved-tokens`

If `status.namingStatus` shows `"invalid-unresolved-tokens"`, the naming template contains unrecognized tokens. Check:

- `{tag.X}` tokens: Ensure the tag key `X` exists in the merged tag sources
- Unrecognized tokens: Verify tokens follow the format `{name}`, `{namespace}`, `{account_id}`, `{region}`, or `{tag.<key>}`

```yaml
# Wrong: {env} (missing "tag." prefix)
status:
  namingStatus: "invalid-unresolved-tokens"
  resourceName: "{env}-events"

# Right: {tag.env} (correct prefix)
status:
  namingStatus: "valid"
  resourceName: "prod-events"
```

### Shard Count Enforcement

If you try to set `shardCount` on an ON_DEMAND stream, it is silently ignored:

```yaml
spec:
  streamMode: "on_demand"
  shardCount: 5    # Ignored; ON_DEMAND auto-scales
```

For PROVISIONED streams, `shardCount` is required:

```yaml
spec:
  streamMode: "provisioned"
  # Missing shardCount: defaults to 1 shard (minimum viable)
```

### Cascade Conflicts

If both a mandatory tier and instance spec set different values, mandatory always wins:

```yaml
# KinesisConfig/general-policy has:
#   mandatory.streamMode: "on_demand"

# Instance tries to override:
spec:
  streamMode: "provisioned"   # Ignored; mandatory tier wins

status:
  # Stream is ON_DEMAND despite instance request
```

## See Also

- [KinesisConfig Governance Reference](kinesisconfig.md) — Manage profiles and org-wide policies
- [AWS Kinesis Data Streams Documentation](https://docs.aws.amazon.com/kinesis/latest/dev/) — AWS native documentation
- [ADR-015](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — Governance cascade design
