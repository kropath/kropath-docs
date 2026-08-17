# CloudWatchLogsLogGroup — Creating and Managing Log Groups

The `CloudWatchLogsLogGroup` resource represents a single log group in AWS CloudWatch Logs. This guide covers all configuration fields, governance cascade, subscription filters for log routing, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudWatchLogsConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the log group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the log group is deleted: `"retain"` (safe, keeps logs) or `"delete"` (removes logs from AWS) |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyId` | string | `""` | Full AWS KMS key ARN for encryption at rest. CloudWatch Logs requires the complete ARN. Empty = governed by profile, or no KMS encryption if profile default is empty. |

### Retention

| Field | Type | Default | Purpose |
|---|---|---|---|
| `retentionDays` | integer | `0` | Log retention period. Must be one of the allowed values. `0` = governed by profile, or indefinite if profile default is `0`. |

### Subscription Filters

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subscriptionFilters` | array | `[]` | Up to 2 subscription filters for routing log events to destinations (Kinesis, Lambda, Firehose) |
| `subscriptionFilters[].filterName` | string | required | Unique name for this subscription filter |
| `subscriptionFilters[].filterPattern` | string | required | CloudWatch Logs filter pattern; empty string `""` matches all log events |
| `subscriptionFilters[].destinationArn` | string | required | ARN of the destination (Kinesis stream, Lambda function, or Firehose delivery stream) |
| `subscriptionFilters[].roleArn` | string | `""` | IAM role ARN that CloudWatch Logs assumes to deliver log events. Required for Kinesis and Firehose; leave empty for Lambda destinations. |
| `subscriptionFilters[].distribution` | string | `"ByLogStream"` | Distribution method for log stream events: `"ByLogStream"` or `"Random"` |

**AWS limit:** A maximum of 2 subscription filters per log group.

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the log group's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective log group name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the log group name is ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `predictedArn` | string | Expected ARN in AWS format: `arn:aws:logs:region:account:log-group:resourceName` |
| `logGroupArn` | string | Actual ARN after creation from AWS |

## Naming Convention

Log groups are named using a configurable template. The default template is `{namespace}-{name}`, which produces log group names like `app-team-app-logs` (where `app-team` is the Kubernetes namespace and `app-logs` is the resource name).

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from the merged tags (e.g. `{tag.environment}`)

Example: A profile with `namingTemplate: "/aws/lambda/{name}"` would produce hierarchical names like `/aws/lambda/my-function` for Lambda application log groups.

**AWS constraints on log group names:**
- 1–512 characters
- Allowed characters: `A-Z a-z 0-9 _ - / . #`
- The `/` character is commonly used for hierarchical naming (e.g. `/aws/lambda/`, `/aws/ecs/`)

**Important:** Log group names are immutable in CloudWatch Logs. Changing `spec.nameOverride` or the governance naming template on an existing log group does not rename it — it remains under its original name.

## Complete Examples

### Basic Log Group

Create a simple log group with default governance settings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: app-logs
  namespace: app-team
spec:
  configRef: general-policy
  deletionPolicy: retain
```

Result:
- Log group created with name `app-team-app-logs`
- No KMS encryption (uses CloudWatch Logs default encryption)
- 90-day retention (from `general-policy` defaults)
- Deletion of the Kubernetes resource keeps logs in CloudWatch Logs

### Log Group with Custom Encryption

Create a log group with a customer-managed KMS key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: sensitive-logs
  namespace: security
spec:
  configRef: general-policy
  kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/mrk-sensitive"
  deletionPolicy: retain
```

Result:
- Log group encrypted with the specified KMS key
- CloudWatch Logs enforces encryption via the key's access policies
- Only users with KMS key permissions can decrypt logs

### Log Group with Custom Retention

Override the governance default retention period:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: short-lived-logs
  namespace: app-team
spec:
  configRef: general-policy
  retentionDays: 7  # Override default 90 days
  deletionPolicy: retain
```

Result:
- Logs retained for 7 days
- After 7 days, CloudWatch Logs automatically deletes entries
- Useful for high-volume debug logs or temporary troubleshooting

### Log Group with Subscription Filter (Kinesis)

Route log events to Kinesis for centralized processing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: event-logs
  namespace: app-team
spec:
  configRef: general-policy
  subscriptionFilters:
    - filterName: "to-kinesis"
      filterPattern: ""  # Match all log events
      destinationArn: "arn:aws:kinesis:us-east-1:123456789012:stream/event-stream"
      roleArn: "arn:aws:iam::123456789012:role/cwl-to-kinesis"
      distribution: "ByLogStream"
  deletionPolicy: retain
```

Result:
- All log events sent to the Kinesis stream
- CloudWatch Logs assumes the specified role to deliver events
- Events distributed by log stream for order preservation

### Log Group with Subscription Filter (Lambda)

Route ERROR-level log events to a Lambda function for alerting:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: alert-logs
  namespace: app-team
spec:
  configRef: general-policy
  subscriptionFilters:
    - filterName: "error-alerts"
      filterPattern: "[timestamp, level=\"ERROR\", ...]"  # Match ERROR-level events
      destinationArn: "arn:aws:lambda:us-east-1:123456789012:function:alert-processor"
      roleArn: ""  # Not required for Lambda
      distribution: "Random"
  deletionPolicy: retain
```

Result:
- Only ERROR-level log events sent to the Lambda function
- Lambda function invoked asynchronously for each matching batch
- No IAM role needed for Lambda destinations

### Multiple Subscription Filters

Route different log patterns to different destinations:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: multi-route-logs
  namespace: app-team
spec:
  configRef: general-policy
  subscriptionFilters:
    - filterName: "to-kinesis"
      filterPattern: ""  # All events to Kinesis
      destinationArn: "arn:aws:kinesis:us-east-1:123456789012:stream/all-events"
      roleArn: "arn:aws:iam::123456789012:role/cwl-to-kinesis"
      distribution: "ByLogStream"
    - filterName: "errors-to-lambda"
      filterPattern: "[timestamp, level=\"ERROR\", ...]"  # Errors to Lambda
      destinationArn: "arn:aws:lambda:us-east-1:123456789012:function:error-handler"
      roleArn: ""
      distribution: "Random"
  deletionPolicy: retain
```

Result:
- All events routed to Kinesis for audit/analytics
- Error events also routed to Lambda for immediate alerting
- Two independent subscription filters working in parallel

### Hierarchical Log Group Name

Create a log group with a hierarchical name (common for application logs):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: my-function
  namespace: app-team
spec:
  configRef: general-policy
  nameOverride: "/aws/lambda/my-function"  # Explicit hierarchical name
  retentionDays: 30
  deletionPolicy: retain
```

Result:
- Log group created with name `/aws/lambda/my-function`
- Naming template is bypassed
- Follows AWS convention for Lambda function logs

### PCI Compliance Profile

Use a compliance profile with mandatory encryption and retention:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: payment-logs
  namespace: payments
spec:
  configRef: pci  # Uses PCI compliance profile
  tags:
    business-unit: payments
    data-sensitivity: high
  syncedLabels:
    compliance-scope: pci
  deletionPolicy: retain
```

Result:
- Profile's mandatory encryption key enforced (cannot be overridden)
- Profile's mandatory 1-year retention enforced
- PCI compliance tags applied automatically
- Labels synced to both Kubernetes and AWS tags
- Custom tags merged with governance tags

## Governance Cascade

The effective configuration for each log group is determined by a three-tier cascade:

1. **Governance mandatory tier** (highest priority) — Platform enforcement that overrides everything
2. **Log group spec** (middle) — Developer choices
3. **Governance defaults tier** (lowest priority) — Fallback values

For example:
- If the PCI profile has `mandatory.kmsKeyId` set, that key is always used, even if the log group specifies a different key.
- If mandatory is empty but the log group doesn't specify retention, the profile's default retention applies.
- If both mandatory and default are empty, the log group can use indefinite retention (not recommended).

Platform teams use the mandatory tier for critical controls (compliance, encryption, retention); they also use the defaults tier to provide reasonable baselines that developers can override when needed.

## Key Behaviors

### Immutable Log Group Name After Creation

Once created in CloudWatch Logs, a log group's name cannot be changed. The naming template or `nameOverride` field determines the name at creation time only.

### Subscription Filter Limits

CloudWatch Logs enforces a **maximum of 2 subscription filters per log group**. If you need to route logs to more than 2 destinations, use intermediate services (e.g., Kinesis → Lambda function that forks to multiple targets).

### Field Name Differences from AWS API

The kropath schema normalizes field names to camelCase while AWS CloudWatch Logs API uses different casing:
- `destinationArn` in kropath → `destinationARN` in AWS (uppercase ARN)
- `roleArn` in kropath → `roleARN` in AWS (uppercase ARN)

This conversion is handled automatically during reconciliation.

### Tag Format

Tags in kropath are specified as a map (e.g. `key: value`). AWS CloudWatch Logs stores tags internally as a map. The conversion is handled automatically during reconciliation.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the log group and its logs safe in CloudWatch Logs
- `delete` — Deleting the Kubernetes resource also deletes the log group and all its logs from AWS (use with caution)

## Troubleshooting

### Log Group Not Creating

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template has a token that cannot be resolved (e.g., a tag key that doesn't exist). Fix the template or ensure required tags are present.
- If `valid` but log group not created, check `status.conditions` for errors from AWS (e.g., permission issues, duplicate name).

### Can't Override Encryption or Retention

If governance has a mandatory tier set for `kmsKeyId` or `retentionDays`, those values cannot be overridden at the log group level. Only the defaults tier can be overridden by the developer. Contact your platform team if you need different encryption or retention settings.

### Subscription Filter Not Delivering Events

Verify:
- The destination ARN is correct (Kinesis stream, Lambda function, or Firehose delivery stream must exist in the same region)
- The `roleArn` is correct (for Kinesis and Firehose; not needed for Lambda)
- The IAM role has permissions to access the destination resource
- The filter pattern syntax is valid (test with `aws logs test-metric-filter --filter-pattern "..."`)

### Too Many Subscription Filters

CloudWatch Logs limits you to 2 filters per log group. If you need more routing logic, fan out through a Kinesis stream or Lambda function that distributes to multiple targets.
