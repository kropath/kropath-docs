# SQSQueue — Message Queues

The `SQSQueue` resource creates AWS SQS message queues for asynchronous communication between services. A queue receives messages from producers and holds them until consumers retrieve them.

## Overview

Use `SQSQueue` to create:

- **Standard queues** — Best-effort ordering, unlimited throughput, at-least-once delivery
- **FIFO queues** — Strict ordering, exactly-once processing, per-message-group throughput
- **Dead-letter queues** — Capture messages that fail processing
- **Encrypted queues** — SQS-managed or KMS encryption

Each queue has:
- **Message behavior settings** — Visibility timeout, retention, delay, max message size
- **Governance controls** — Applied via `SQSConfig` profiles
- **Encryption** — Org-wide, profile, or instance-level
- **Dead-letter routing** — Optional redrive policy for failed messages
- **Access policy** — Optional queue policy for fine-grained access control

## Queue Types

Choose the queue type that matches your use case:

| Type | Ordering | Deduplication | Throughput | For |
|---|---|---|---|---|
| **Standard** (`fifo: false`) | Best-effort | None | Unlimited | Generic async work, load shedding, microservices |
| **FIFO** (`fifo: true`) | Strict per-group | Content-based or ID-based | Capped | Order processing, event sourcing, transactions |

## Creating a Queue

### Simple Standard Queue

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: notifications
  namespace: app-prod
spec:
  configRef: general-policy
```

This queue:
- Uses the `general-policy` governance profile
- Inherits encryption, visibility timeout, and retention from the profile defaults
- Is named `app-prod-notifications` (from the naming template)
- Retains messages for 4 days (default)
- Has 30-second visibility timeout (default)

### FIFO Queue with Exactly-Once Processing

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
  fifo: true
  contentBasedDeduplication: true
  deduplicationScope: "queue"
  fifoThroughputLimit: "perQueue"
```

This queue:
- Delivers messages in strict order within message groups
- Deduplicates messages based on content hash
- Stores the deduplication ID for 5 minutes (default)
- Supports standard FIFO throughput (300 msg/sec per queue)
- Queue name: `payments-prod-order-events.fifo`

### FIFO Queue with High Throughput

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: events
  namespace: analytics
spec:
  configRef: general-policy
  fifo: true
  fifoThroughputLimit: "perMessageGroupId"
  deduplicationScope: "messageGroup"
  contentBasedDeduplication: false
```

This queue:
- Supports high throughput: 300 msg/sec per message group (not per queue)
- Useful when you have many logical message groups
- Still maintains ordering within each group

### Queue with Custom Settings

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: batch-jobs
  namespace: jobs-prod
spec:
  configRef: general-policy
  visibilityTimeout: 300         # 5 minutes for long-running jobs
  messageRetentionPeriod: 1209600 # 14 days
  delaySeconds: 60               # 1 minute initial delay
  maximumMessageSize: 131072     # 128 KB
```

### Queue with Encryption

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: sensitive-data
  namespace: compliance-prod
spec:
  configRef: pci
  encryptionType: "kms"
  kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
  kmsDataKeyReusePeriodSeconds: 300
```

If your governance profile mandates KMS encryption, specifying `encryptionType: "kms"` is required even if you can choose which key.

## Queue Behavior

### Visibility Timeout

Controls how long a message is hidden after a consumer receives it:

```yaml
spec:
  visibilityTimeout: 30  # 30 seconds (default)
```

If the consumer processes the message and deletes it within 30 seconds, it's gone. If the consumer crashes, the message reappears after 30 seconds and another consumer can retry.

**Set this based on processing time:**
- Fast operations (< 30 sec): Use default 30 seconds
- Longer operations: Increase proportionally
- Mandatory limits: Cannot exceed `SQSConfig` mandatory ceiling

### Message Retention

Controls how long messages stay in the queue before expiring:

```yaml
spec:
  messageRetentionPeriod: 345600  # 4 days (default)
```

Expired messages are automatically deleted. Useful for durability — if all consumers crash, you have a time window to recover.

### Delivery Delay

Delays when a newly-sent message becomes visible to consumers:

```yaml
spec:
  delaySeconds: 60  # 60 seconds
```

Useful for scheduled publishing — messages sent now won't be visible for 1 minute.

### Long Polling

Reduces empty queue checks by having consumers wait for messages:

```yaml
spec:
  receiveMessageWaitTimeSeconds: 20  # 20 seconds max wait
```

When a consumer checks for messages and the queue is empty, it waits up to 20 seconds. If a message arrives during that window, it's delivered immediately.

## Encryption

### SQS-Managed Encryption (Default)

```yaml
spec:
  encryptionType: "sqs-managed"
```

AWS handles encryption keys; minimal configuration needed.

### KMS Encryption

```yaml
spec:
  encryptionType: "kms"
  kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
  kmsDataKeyReusePeriodSeconds: 300
```

Encrypt messages with a specific KMS key. The data key reuse period controls how often a new key is generated.

### No Encryption

```yaml
spec:
  encryptionType: "none"
```

Messages are stored unencrypted (usually forbidden by governance policies).

## Dead-Letter Queues

Configure a dead-letter queue to capture messages that fail processing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events-dlq
  namespace: payments-prod
spec:
  configRef: general-policy
---
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
  redrivePolicy:
    deadLetterTargetRef: "order-events-dlq"
    maxReceiveCount: 3
```

When a message is received 3 times and not deleted, it's moved to the dead-letter queue for inspection.

### DLQ with Source Restrictions

If the DLQ itself needs to know which queues can send to it, use `redriveAllowPolicy`:

| Value | Behavior |
|---|---|
| `allowAll` | Any queue can send messages to this DLQ (default) |
| `denyAll` | No queue can send messages to this DLQ (restrictive) |
| `byQueue` | Only queues listed in `sourceQueueArns` can send to this DLQ |

Example with `byQueue`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events-dlq
  namespace: payments-prod
spec:
  configRef: general-policy
  redriveAllowPolicy:
    redrivePermission: "byQueue"
    sourceQueueArns:
      - "arn:aws:sqs:us-east-1:123456789012:payments-prod-order-events"
      - "arn:aws:sqs:us-east-1:123456789012:payments-prod-order-events.fifo"
```

## Queue Policy

Attach a resource-based access policy to control who can send and receive messages:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AWSPolicyDocument
metadata:
  name: order-queue-policy
  namespace: payments-prod
spec:
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": ["sqs:SendMessage"],
        "Resource": "arn:aws:sqs:*:*:order-events*"
      }]
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
  queuePolicyRef: "order-queue-policy"
```

## Tags and Labels

Add organization and application metadata:

```yaml
spec:
  tags:
    team: payments
    cost-center: "1234"
    environment: production
  syncedLabels:
    application: order-processor
    data-class: internal
  syncedAnnotations:
    slack-channel: "#payments-alerts"
```

Tags appear on both the AWS queue and Kubernetes labels/annotations. Synced labels and annotations are propagated to Kubernetes.

## Naming

Queue names are auto-generated from a template. The default template is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-events`
- **Queue name:** `payments-prod-order-events`

Override the template in `SQSConfig`, or override per-queue:

```yaml
spec:
  nameOverride: "my-custom-queue"
```

With `nameOverride`, the queue is named exactly `my-custom-queue` (no template applied).

**FIFO suffix:** FIFO queues automatically get `.fifo` appended:
- Standard: `payments-prod-order-events`
- FIFO: `payments-prod-order-events.fifo`

## Monitoring

Check queue status:

```bash
kubectl describe sqsqueue order-events -n payments-prod
```

Look for:
- `status.resourceName` — The actual queue name in AWS
- `status.predictedArn` — The full ARN
- `status.queueUrl` — The queue URL for SDK calls
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (indicates naming errors)
- `status.conditions` — Ready, error, or warning states

## Deletion

By default, queues are retained when the CR is deleted (the AWS queue stays):

```yaml
spec:
  deletionPolicy: "retain"  # default
```

To delete the underlying AWS queue when the CR is deleted:

```yaml
spec:
  deletionPolicy: "delete"
```
