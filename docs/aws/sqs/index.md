# SQS — Message Queues

The SQS family provides resources for creating and managing AWS Simple Queue Service (SQS) queues. Use SQS when you need reliable message delivery, decoupling between services, and managed scaling.

## Resources

- **[SQSQueue](./sqsqueue.md)** — Creates standard and FIFO message queues with encryption, dead-letter queue support, and governance controls
- **[SQSConfig](./sqsconfig.md)** — Governance profiles that enforce encryption, queue behavior limits, and naming conventions

## Quick Start

Define a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    encryptionType: "sqs-managed"
    visibilityTimeout: 30
    messageRetentionPeriod: 345600  # 4 days
```

Then create a queue:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events
  namespace: events-prod
spec:
  configRef: general-policy
```

## Common Patterns

### Standard Queue

```yaml
spec:
  fifo: false  # default
  visibilityTimeout: 30
  messageRetentionPeriod: 345600
```

### FIFO Queue (Exactly-Once Processing)

```yaml
spec:
  fifo: true
  contentBasedDeduplication: true
  deduplicationScope: "queue"
  fifoThroughputLimit: "perQueue"
```

### Queue with Dead-Letter Queue

```yaml
spec:
  redrivePolicy:
    deadLetterTargetRef: "order-events-dlq"
    maxReceiveCount: 3
```

### Encryption with KMS

```yaml
spec:
  encryptionType: "kms"
  kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
```

## Governance

SQS resources follow the three-tier governance cascade:

1. **Organization-wide** — Set via `KropathConfig.spec.mandatory.sqs` and `spec.defaults.sqs`
2. **Resource type** — Set via `SQSConfig` profiles
3. **Instance** — Set on individual `SQSQueue` resources

Mandatory controls (e.g., org-wide encryption enforcement) always win. Instance values override defaults.

## Naming

Queue names are auto-generated from a template. The default template is `{namespace}-{name}`:

- Namespace: `events-prod`
- CR name: `order-events`
- **Queue name:** `events-prod-order-events`

Override with `spec.nameOverride` if needed.

FIFO queues automatically get a `.fifo` suffix appended by kropath (e.g., `events-prod-order-events.fifo`).

## Deletion

By default, queues are retained when the CR is deleted. To delete the underlying AWS queue:

```yaml
spec:
  deletionPolicy: delete
```
