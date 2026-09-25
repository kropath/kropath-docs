---
title: LambdaEventSourceMapping — Event Triggers for Lambda Functions
description: "The `LambdaEventSourceMapping` resource connects a Lambda function to an event source for automatic, push-based invocation."
doc_type: reference
---
# LambdaEventSourceMapping — Event Triggers for Lambda Functions

The `LambdaEventSourceMapping` resource connects a Lambda function to an event source for automatic, push-based invocation. Supported event sources in this release are SQS queues, Kinesis streams, and DynamoDB Streams.

## Overview

Event source mappings enable serverless architectures where Lambda automatically processes events from queues and streams. The mapping handles batching, error recovery, and filtering. You define:

- **Which function** to invoke via `functionRef`
- **Which event source** via `eventSourceArn`
- **How to batch** (batch size, window)
- **How to handle errors** (retry, DLQ)
- **How to filter** (pattern-based filtering)

The mapping state is maintained in AWS; the Kubernetes resource tracks synchronization status.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS mapping) or `"delete"` (remove mapping) |

### Target Function

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionRef` | string | required | Local `LambdaFunction` CR name; resolved to function ARN via cross-resource reference |

**Note:** The function must exist before creating the event source mapping. Cross-resource resolution reads the function's `status.functionArn`.

### Event Source

| Field | Type | Default | Purpose |
|---|---|---|---|
| `eventSourceArn` | string | required | ARN of the event source (SQS queue, Kinesis stream, or DynamoDB stream) |

Examples:
- SQS: `arn:aws:sqs:us-east-1:123456789012:my-queue`
- Kinesis: `arn:aws:kinesis:us-east-1:123456789012:stream/my-stream`
- DynamoDB: `arn:aws:dynamodb:us-east-1:123456789012:table/my-table/stream/2024-01-01T00:00:00.000`

### Batching

| Field | Type | Default | Purpose |
|---|---|---|---|
| `batchSize` | integer | `0` | Max records per batch: `0` = AWS default (SQS: 10, Kinesis: 100, DDB: 100) |
| `maximumBatchingWindowInSeconds` | integer | `0` | Buffer time before invoking (0–300 seconds); `0` = immediate |

**Use case:** Combine `batchSize: 100` and `maximumBatchingWindowInSeconds: 5` to invoke every 5 seconds or when 100 records arrive, whichever comes first.

### Error Handling (Kinesis and DynamoDB Streams only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `bisectBatchOnFunctionError` | boolean | `false` | Split failed batch in half and retry each half independently |
| `maximumRetryAttempts` | integer | `-1` | Max retries on function error (0–2); `-1` = infinite |
| `maximumRecordAgeInSeconds` | integer | `-1` | Discard records older than this (in seconds); `-1` = no limit |
| `destinationConfig.onFailure.destination` | string | `""` | SQS queue or SNS topic ARN for permanently failed batches |

**Important:** Error handling fields only apply to Kinesis and DynamoDB Streams. SQS has its own retry logic and DLQ configuration.

### Event Filtering

| Field | Type | Default | Purpose |
|---|---|---|---|
| `filterCriteria.filters` | array | `[]` | Event filtering rules; each: `{pattern: "string"}` |

Pattern format (JSON-based):
```json
[
  {
    "pattern": "{\"eventType\": [\"order\"], \"amount\": [{\"numeric\": [\">=\", 100]}]}"
  }
]
```

### Control and State

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enabled` | boolean | `true` | `true` = active polling; `false` = paused (no events processed) |

### Stream-Specific Fields (Kinesis and DynamoDB Streams only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `startingPosition` | string | `""` | `TRIM_HORIZON` (all records), `LATEST` (new records only), or `AT_TIMESTAMP` |
| `startingPositionTimestamp` | string | `""` | ISO-8601 timestamp; required when `startingPosition: AT_TIMESTAMP` |

### Concurrency and Reporting

| Field | Type | Default | Purpose |
|---|---|---|---|
| `parallelizationFactor` | integer | `1` | (Kinesis/DDB) concurrent batches per shard (1–10); higher = faster but higher cost |
| `scalingConfig.maximumConcurrency` | integer | `0` | (SQS only) max concurrent Lambda invocations; `0` = AWS auto-scales |
| `functionResponseTypes` | array | `[]` | Set to `["ReportBatchItemFailures"]` to report per-record failures |
| `tumblingWindowInSeconds` | integer | `0` | (Kinesis/DDB) tumbling window aggregation (0–900 seconds); groups records by time |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `uuid` | string | AWS-assigned UUID for this event source mapping |
| `state` | string | Current state: `Creating`, `Enabling`, `Enabled`, `Disabling`, `Disabled`, `Updating`, `Deleting` |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

**Note:** Event source mappings do NOT have predictable names or ARNs like functions; they are identified by UUID.

## Naming Convention

**Event source mappings do not have user-defined names.** AWS assigns a UUID (`status.uuid`) that uniquely identifies each mapping. The Kubernetes resource name is purely for organization within Kubernetes.

## Complete Examples

### SQS Queue Trigger

Connect a Lambda function to an SQS queue for automatic message processing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaEventSourceMapping
metadata:
  name: order-queue-processor
  namespace: order-team
spec:
  configRef: general-policy
  functionRef: process-order  # References LambdaFunction in same namespace
  eventSourceArn: "arn:aws:sqs:us-east-1:123456789012:order-queue"
  batchSize: 10
  enabled: true
  deletionPolicy: retain
```

Result:
- Lambda automatically invoked when messages arrive in SQS queue
- Processes up to 10 messages per batch
- Visible SQS messages are deleted after successful invocation
- Failed messages returned to queue for retry

### Kinesis Stream Trigger with Error Handling

Process records from a Kinesis stream with custom error handling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaEventSourceMapping
metadata:
  name: stream-processor
  namespace: streaming-team
spec:
  configRef: general-policy
  functionRef: kinesis-handler
  eventSourceArn: "arn:aws:kinesis:us-east-1:123456789012:stream/events"
  batchSize: 100
  maximumBatchingWindowInSeconds: 5
  startingPosition: TRIM_HORIZON
  parallelizationFactor: 4
  bisectBatchOnFunctionError: true
  maximumRetryAttempts: 2
  maximumRecordAgeInSeconds: 3600
  destinationConfig:
    onFailure:
      destination: "arn:aws:sqs:us-east-1:123456789012:stream-dlq"
  functionResponseTypes:
    - "ReportBatchItemFailures"
  deletionPolicy: delete
```

Result:
- Processes 100 records per batch or every 5 seconds
- Up to 4 concurrent batches per shard (parallelization)
- Failed batches split in half and retried (up to 2 times)
- Records older than 1 hour discarded
- Permanently failed batches sent to SQS DLQ
- Mapping deleted when Kubernetes resource is deleted

### DynamoDB Stream Trigger with Filtering

Process changes from a DynamoDB table with pattern-based event filtering:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaEventSourceMapping
metadata:
  name: dynamodb-sync
  namespace: database-team
spec:
  configRef: general-policy
  functionRef: db-sync-handler
  eventSourceArn: "arn:aws:dynamodb:us-east-1:123456789012:table/users/stream/2024-01-01T12:00:00.000"
  batchSize: 100
  startingPosition: LATEST
  filterCriteria:
    filters:
      - pattern: |
          {
            "eventName": ["MODIFY", "REMOVE"],
            "dynamodb": {
              "Keys": {
                "userId": {
                  "S": [{"prefix": "user#"}]
                }
              }
            }
          }
  parallelizationFactor: 2
  functionResponseTypes:
    - "ReportBatchItemFailures"
```

Result:
- Only MODIFY and REMOVE events processed (INSERT events filtered)
- Only records for users with ID prefix `user#`
- Up to 2 concurrent batches per shard
- New records only (LATEST starting position)

### SQS Queue with Scaling Configuration

Auto-scale concurrent Lambda invocations based on queue depth:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaEventSourceMapping
metadata:
  name: payment-queue-processor
  namespace: payments
spec:
  configRef: general-policy
  functionRef: payment-handler
  eventSourceArn: "arn:aws:sqs:us-east-1:123456789012:payment-queue"
  batchSize: 5
  maximumBatchingWindowInSeconds: 2
  scalingConfig:
    maximumConcurrency: 100  # Max 100 concurrent Lambda invocations
  enabled: true
```

Result:
- Lambda auto-scales from 0 to 100 concurrent invocations
- Processes up to 5 messages per batch
- Invokes every 2 seconds if fewer than 5 messages

### Paused Mapping for Maintenance

Create a mapping but keep it paused (disabled) initially:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaEventSourceMapping
metadata:
  name: scheduled-processor
  namespace: batch-team
spec:
  configRef: general-policy
  functionRef: batch-handler
  eventSourceArn: "arn:aws:sqs:us-east-1:123456789012:scheduled-queue"
  batchSize: 50
  enabled: false  # Paused; no events will be processed
  deletionPolicy: retain
```

Result:
- Mapping created but inactive
- Enable by updating `spec.enabled: true`
- No Lambda invocations until enabled

## Governance

Event source mappings inherit tags, syncedLabels, and syncedAnnotations from the `LambdaConfig` governance profile via `configRef`. Resource-specific governance (runtime, memory, encryption) applies at the function level, not the mapping.

The effective configuration for tags is:

```
LambdaConfig.mandatory.tags
  + LambdaConfig.defaults.tags
  + spec.tags
```

## Key Behaviors

### Function Resolution

The `functionRef` field resolves to a function ARN by reading the `LambdaFunction` CR's `status.functionArn`. The function must exist before the mapping can be created.

### Event Source Ownership

AWS allows only one mapping per event source per function. Creating a second mapping for the same source and function fails.

### Batching Behavior

- **SQS:** Messages are deleted only after successful Lambda invocation
- **Kinesis:** Records are processed sequentially; shard iterator advances only after successful batch
- **DynamoDB:** Same as Kinesis

### State Transitions

State changes are asynchronous:
- Creating → Enabling → Enabled (minutes for large streams)
- Disabling → Disabled (quick)
- Updating (when you modify the mapping config)

Check `status.state` to monitor transitions.

### Filtering

Filtering happens at the event source level before Lambda is invoked. This reduces Lambda invocation costs for high-volume sources.

## Troubleshooting

### Mapping Stuck in "Creating" State

Check AWS CloudTrail for permission errors. Ensure the Lambda function's execution role has permission to read from the event source.

### Function Not Being Invoked

- Verify `status.state` is `Enabled`
- Check `spec.enabled: true`
- Verify `functionRef` resolves correctly (function must exist)
- Check function logs for invocation errors

### Events Arriving Out of Order

This is expected behavior for SQS (no ordering guarantee). For Kinesis/DynamoDB, ordering is guaranteed within a shard but not across shards (unless `parallelizationFactor: 1`).

### DLQ Messages Pile Up

Check function logs for errors. Increase `maximumRetryAttempts` if retryable errors occur, or fix the underlying issue in the function code.

### Filter Criteria Not Working

Verify filter pattern JSON is valid. Use AWS Lambda console to test the filter pattern against sample events.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for event source mapping design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html
