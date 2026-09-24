# SNSTopic — Publish/Subscribe Topics

The `SNSTopic` resource creates AWS SNS topics for asynchronous message publishing. Topics receive messages from publishers and deliver them to multiple subscribers.

## Overview

Use `SNSTopic` to create:

- **Standard topics** — Best-effort message ordering, unlimited throughput, flexible scaling
- **FIFO topics** — Strict message ordering, exactly-once processing, per-message-group throughput
- **Encrypted topics** — AWS-managed or customer-managed KMS encryption
- **Topics with delivery policies** — Configure retry behavior, delivery feedback, and data protection

Each topic has:
- **Message behavior settings** — Controlled via governance profiles
- **Encryption** — Org-wide, profile, or instance-level defaults
- **Topic access policy** — Optional resource-based policy for fine-grained access control
- **Delivery feedback** — Per-protocol logging of message delivery status
- **Data protection** — Message data masking and blocking policies

## Topic Types

Choose the topic type that matches your use case:

| Type | Ordering | Deduplication | Throughput | For |
|---|---|---|---|---|
| **Standard** (`fifo: false`) | Best-effort | None | Unlimited | Notifications, broadcasts, general pub/sub |
| **FIFO** (`fifo: true`) | Strict per-group | Content-based | Capped | Order processing, event sourcing, strict sequencing |

## Creating a Topic

### Simple Standard Topic

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: notifications
  namespace: app-prod
spec:
  configRef: general-policy
```

This topic:
- Uses the `general-policy` governance profile
- Inherits encryption, signature version, and tracing from profile defaults
- Is named `app-prod-notifications` (from the naming template)
- Delivers messages in best-effort order
- Can scale to unlimited throughput

### FIFO Topic with Strict Ordering

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
  fifo: true
  contentBasedDeduplication: true
  fifoThroughputScope: "Topic"
```

This topic:
- Delivers messages in strict order within message groups
- Automatically deduplicates messages based on content hash over 5 minutes
- Supports standard FIFO throughput (300 msg/sec per topic)
- Topic name: `payments-prod-order-events.fifo`

### FIFO Topic with High Throughput

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: events
  namespace: analytics
spec:
  configRef: general-policy
  fifo: true
  fifoThroughputScope: "MessageGroup"
  contentBasedDeduplication: false
```

This topic:
- Supports high throughput: 300 msg/sec per message group (not per topic)
- Useful when you have many logical message groups
- Still maintains strict ordering within each group
- Manual deduplication requires message deduplication ID

### Topic with Custom Encryption

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: sensitive-data
  namespace: compliance-prod
spec:
  configRef: pci
  kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/compliance-key"
```

If your governance profile mandates KMS encryption, specifying `kmsMasterKeyId` is required even if you can choose which key.

### Topic with Display Name

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: orders
  namespace: ecommerce
spec:
  configRef: general-policy
  displayName: "Order Events Topic"
```

The display name appears in mobile push notifications and SMS messages for subscribers. It's optional and distinct from the topic name.

## Topic Configuration

### Encryption

Choose how messages are encrypted at rest:

**AWS-managed encryption (default):**

```yaml
spec:
  kmsMasterKeyId: "alias/aws/sns"  # Inherits from profile if not specified
```

AWS manages encryption keys; minimal configuration needed.

**Customer-managed KMS encryption:**

```yaml
spec:
  kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
```

Encrypt messages with a specific KMS key. Required if your governance profile mandates customer-managed encryption.

**No encryption:**

```yaml
spec:
  kmsMasterKeyId: ""  # Empty value disables encryption if profile allows
```

Messages are stored unencrypted (usually forbidden by governance policies).

### Message Signing

Control how message signatures are generated:

**SHA-1 (default):**

```yaml
spec:
  signatureVersion: "1"  # Inherits from profile if not specified
```

AWS-default signature algorithm. Sufficient for most use cases.

**SHA-256:**

```yaml
spec:
  signatureVersion: "2"
```

Stronger cryptographic hashing. Required by some compliance profiles.

### X-Ray Tracing

Enable or disable distributed tracing:

**PassThrough (default):**

```yaml
spec:
  tracingConfig: "PassThrough"  # Inherits from profile if not specified
```

Messages are traceable if sent from an X-Ray-instrumented service.

**Active:**

```yaml
spec:
  tracingConfig: "Active"
```

All messages are sampled for X-Ray tracing. Useful for debugging and observability.

### Delivery Feedback

Log message delivery status per subscription protocol:

```yaml
spec:
  deliveryFeedback:
    http:
      successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
      successFeedbackSampleRate: "100"
    lambda:
      successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
      failureFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback-fail"
      successFeedbackSampleRate: "50"
    sqs:
      successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
      failureFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback-fail"
```

Each protocol is independently configured with:
- `successFeedbackRoleArn` — IAM role for delivery success logs
- `failureFeedbackRoleArn` — IAM role for delivery failure logs
- `successFeedbackSampleRate` — Percentage of successes to log (1–100)

Delivery logs go to CloudWatch.

### Data Protection

Protect message contents by masking or blocking sensitive data:

```yaml
spec:
  dataProtectionPolicy: |
    {
      "Name": "protect-pii",
      "Description": "Mask email addresses and phone numbers",
      "Version": "2021-06-01",
      "Statement": [
        {
          "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/EmailAddress"],
          "Operation": {
            "Deny": {}
          }
        }
      ]
    }
```

Data protection policies prevent specific data types from being published to the topic. If the policy blocks the message, the publish request is rejected.

## Topic Access Policy

Control who can publish to and subscribe to a topic:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AWSPolicyDocument
metadata:
  name: order-topic-policy
  namespace: payments-prod
spec:
  policy: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {"Service": "lambda.amazonaws.com"},
          "Action": ["SNS:Publish"],
          "Resource": "arn:aws:sns:*:*:order-events*"
        },
        {
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::123456789012:role/worker"},
          "Action": ["SNS:Subscribe"],
          "Resource": "arn:aws:sns:*:*:order-events*"
        }
      ]
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
  topicPolicyRef: "order-topic-policy"
```

The policy is applied to the topic itself and controls subscription and publish permissions.

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
    on-call-team: "payments-team"
```

Tags appear on both the AWS topic and Kubernetes labels/annotations. Synced labels and annotations are propagated to Kubernetes.

## Naming

Topic names are auto-generated from a template. The default template is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-events`
- **Topic name:** `payments-prod-order-events`

Override the template in `SNSConfig`, or override per-topic:

```yaml
spec:
  nameOverride: "my-custom-topic"
```

With `nameOverride`, the topic is named exactly `my-custom-topic` (no template applied).

**FIFO suffix:** FIFO topics automatically get `.fifo` appended:
- Standard: `payments-prod-order-events`
- FIFO: `payments-prod-order-events.fifo`

## Deletion Policy

Control what happens to the AWS topic when the CR is deleted:

### Retain (default)

```yaml
spec:
  deletionPolicy: "retain"  # default
```

The AWS topic remains when the CR is deleted. Useful for production topics to prevent accidental deletion.

### Delete

```yaml
spec:
  deletionPolicy: "delete"
```

The AWS topic is deleted when the CR is deleted. Use only for temporary or test topics.

## Monitoring

Check topic status:

```bash
kubectl describe snstopic order-events -n payments-prod
```

Look for:
- `status.resourceName` — The actual topic name in AWS
- `status.predictedArn` — The full ARN
- `status.topicArn` — The actual ARN after provisioning
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (indicates naming errors)
- `status.conditions` — Ready, error, or warning states

Publish a test message:

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:payments-prod-order-events \
  --message '{"order_id": "12345"}'
```

## Subscriptions

A topic without subscriptions publishes messages to no one. Use [`SNSSubscription`](snssubscription.md) to bind delivery endpoints (SQS queues, Lambda functions, HTTP/S webhooks, email addresses, SMS numbers, Firehose streams) to your topic.

Each subscription:
- Independently filters, retries, and delivers messages
- Can be deleted without affecting the topic or other subscriptions
- Optionally routes failed deliveries to a dead-letter SQS queue
- Supports message attribute or body-based filtering

See [SNSSubscription](snssubscription.md) for complete configuration and examples.

## Cross-Provider Notes

- SNS topic names are case-sensitive (unlike S3 bucket names)
- The `.fifo` suffix on topic names is AWS-specific
- Message signing version (`"1"` vs `"2"`) is AWS SNS–specific
- Data protection policies are AWS SNS–specific; other providers use different mechanisms
- Delivery feedback per-protocol is AWS SNS–specific
