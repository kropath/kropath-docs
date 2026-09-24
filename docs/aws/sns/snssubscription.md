# SNSSubscription — Subscribe Endpoints to Topics

The `SNSSubscription` resource binds delivery endpoints (SQS queues, Lambda functions, HTTP/S URLs, email addresses, SMS numbers, Firehose streams, or mobile applications) to SNS topics. Subscriptions deliver published messages to multiple targets, enabling one-to-many pub/sub architectures.

## Overview

Use `SNSSubscription` to:

- **Subscribe SQS queues** — Fan out messages to SQS for buffered, independent processing
- **Trigger Lambda functions** — React to events with serverless compute
- **Deliver to HTTP/S endpoints** — Push notifications to webhooks
- **Send email and SMS** — Notify users directly
- **Stream to Firehose** — Aggregate and transform messages at scale
- **Filter and route** — Use attribute or body-based filter policies to select messages
- **Manage reliability** — Configure retry policies and dead-letter queues per subscription

Each subscription binds exactly one endpoint to one topic and can be independently deleted or modified without affecting the topic or other subscriptions.

## Topic Association

Subscriptions must reference a topic. Choose between a local kropath-managed `SNSTopic` or an external topic by ARN:

### Local Topic Reference

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSSubscription
metadata:
  name: order-events-sqs-consumer
  namespace: orders-prod
spec:
  configRef: general-policy
  topicRef: order-events           # References SNSTopic/order-events in same namespace
  protocol: sqs
  endpoint: arn:aws:sqs:us-east-1:123456789012:orders-prod-events
```

This subscription:
- Routes messages from `SNSTopic/order-events` to the specified SQS queue
- Automatically resolves the topic's ARN even if it has a custom name override or is FIFO
- Fails with a clear error if `SNSTopic/order-events` does not exist

### External Topic ARN

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSSubscription
metadata:
  name: external-topic-subscription
  namespace: integrations
spec:
  configRef: general-policy
  topicArn: arn:aws:sns:us-east-1:123456789012:third-party-events
  protocol: sqs
  endpoint: arn:aws:sqs:us-east-1:123456789012:received-events
```

This subscription:
- Routes messages from an externally managed SNS topic to an SQS queue
- Uses the literal ARN without any lookup or validation
- Useful for subscribing to topics in other AWS accounts or managed by other teams

**Exactly one of `topicRef` or `topicArn` must be set.** You cannot subscribe a single endpoint to multiple topics — create separate subscription CRs for each topic.

## Delivery Protocols

Subscriptions support all seven AWS SNS delivery protocols. Choose based on your architecture:

### SQS — Buffered, Independent Processing

```yaml
spec:
  protocol: sqs
  endpoint: arn:aws:sqs:us-east-1:123456789012:order-queue
```

Messages are queued in SQS for asynchronous processing. Subscribers process at their own rate without blocking the publisher. Choose this for loose coupling and independent scaling.

### Lambda — Serverless Compute

```yaml
spec:
  protocol: lambda
  endpoint: arn:aws:lambda:us-east-1:123456789012:function:order-processor
```

Each message triggers a Lambda invocation. SNS invokes the function synchronously; the invocation is retried if it fails (subject to the delivery policy). Choose this for event-driven workflows and simple, inline transformations.

### Application — Mobile Push Notifications

```yaml
spec:
  protocol: application
  endpoint: arn:aws:sns:us-east-1:123456789012:endpoint/GCM/android-app/12345678-1234-1234-1234-123456789012
```

SNS delivers messages to a mobile application via AWS's SNS Platform Application, enabling push notifications to iOS, Android, and other platforms registered with the platform application. The `endpoint` must be a Platform Endpoint ARN (not a Platform Application ARN). Choose this when you need to reach mobile devices with push notifications.

### HTTP / HTTPS — Webhook Delivery

```yaml
spec:
  protocol: https
  endpoint: https://example.com/sns-webhook
  # Subscription requires confirmation by the receiver
```

SNS sends messages as HTTP POST requests. Email or URL-based confirmation is required before delivery begins.

### Email — Direct Email Notifications

```yaml
spec:
  protocol: email
  endpoint: alerts@example.com
  # Subscription requires confirmation by the email owner
```

SNS sends messages as formatted emails. The recipient must confirm the subscription by clicking a link in a confirmation email.

### Email-JSON — Raw JSON in Email

```yaml
spec:
  protocol: email-json
  endpoint: alerts@example.com
```

Like email, but the message body is the raw JSON SNS message format (metadata included).

### SMS — Text Message Delivery

```yaml
spec:
  protocol: sms
  endpoint: +1-555-0123
```

SNS sends the message as an SMS text message. No confirmation step is required.

### Firehose — Data Stream Integration

```yaml
spec:
  protocol: firehose
  endpoint: arn:aws:firehose:us-east-1:123456789012:deliverystream/events-stream
  subscriptionRoleArn: arn:aws:iam::123456789012:role/sns-firehose-delivery
  # subscriptionRoleArn is required for Firehose
```

SNS delivers messages to a Kinesis Data Firehose delivery stream. SNS requires an IAM role with permission to invoke PutRecord on the stream. Choose this for high-volume archival, transformation, and analytics.

## Message Filtering

Filter which messages are delivered to this subscription based on message attributes or content:

### Filter by Message Attributes (default)

```yaml
spec:
  filterPolicy: |
    {
      "eventType": ["order.created", "order.cancelled"],
      "priority": ["high"]
    }
  filterPolicyScope: MessageAttributes
```

Messages are delivered only if their SNS message attributes match the policy. Unmatched messages are silently discarded.

### Filter by Message Body

```yaml
spec:
  filterPolicy: |
    {
      "body": {
        "orderId": [{"numeric": [">", 1000]}],
        "status": ["completed", "shipped"]
      }
    }
  filterPolicyScope: MessageBody
```

SNS parses the message as JSON and applies the filter to the body content.

### No Filter (default)

```yaml
spec:
  filterPolicy: ""  # Empty or omitted
```

All messages are delivered unfiltered.

## Message Delivery Behavior

### Raw Message Delivery

By default, SNS wraps published messages in a JSON envelope with metadata (timestamp, signature, topic ARN). For JSON-aware protocols (SQS, HTTP/S, Firehose), you can unwrap this:

```yaml
spec:
  rawMessageDelivery: true
```

The endpoint receives the message body directly, without SNS metadata wrapping.

### Per-Subscription Delivery Policy

Configure retry behavior and timeouts for this subscription:

```yaml
spec:
  deliveryPolicy: |
    {
      "healthyRetryPolicy": {
        "numRetries": 10,
        "numMaxDelayRetries": 0,
        "minDelayTarget": 20,
        "maxDelayTarget": 60,
        "numNoDelayTransportErrorRetries": 0,
        "numNonTransportErrorRetries": 3
      },
      "throttlePolicy": {
        "maxReceiveRate": 100
      }
    }
```

If not specified, the topic's delivery policy is used.

## Dead-Letter Queue

Route failed deliveries to an SQS queue for analysis:

```yaml
spec:
  redrivePolicy:
    deadLetterQueueRef: events-dlq  # References SQSQueue/events-dlq in same namespace
```

When a message cannot be delivered after retries are exhausted, it is sent to the dead-letter queue. The DLQ must be an `SQSQueue` CR in the same namespace.

Omit `redrivePolicy` entirely if no DLQ is needed.

## Confirmation Flow

Subscriptions to email, email-json, and HTTP/S endpoints require confirmation before delivery begins:

```bash
kubectl describe snssubscription external-webhook -n prod
```

Look for:
- `status.pendingConfirmation: "true"` — Awaiting subscriber confirmation
- `status.subscriptionArn: ""` — Not yet assigned (empty while pending)

Once the subscriber confirms:
- `status.pendingConfirmation: ""` — Confirmation received
- `status.subscriptionArn: "arn:aws:sns:..."` — Subscription active

Subscriptions to SQS, Lambda, SMS, Firehose, and application (mobile) endpoints activate immediately with no confirmation step.

## Tags and Labels

Add organization and application metadata:

```yaml
spec:
  tags:
    team: platform
    cost-center: "1234"
  syncedLabels:
    application: event-processor
    data-class: internal
  syncedAnnotations:
    slack-channel: "#platform-alerts"
    on-call-team: "platform-team"
```

Tags and Kubernetes labels/annotations are synchronized across AWS and Kubernetes. Note: the ACK SNS `Subscription` CRD does not support `spec.tags` directly — all tags are applied via Kubernetes metadata labels.

## Deletion Policy

Control what happens to the AWS subscription when the CR is deleted:

### Retain (default)

```yaml
spec:
  deletionPolicy: retain
```

The AWS subscription remains when the CR is deleted. Useful for production subscriptions to prevent accidental deletion.

### Delete

```yaml
spec:
  deletionPolicy: delete
```

The AWS subscription is deleted when the CR is deleted. Use only for temporary or test subscriptions.

## Complete Example

A realistic subscription combining multiple features:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSSubscription
metadata:
  name: order-events-dlq
  namespace: payments-prod
spec:
  configRef: general-policy
  
  # Topic association
  topicRef: order-events
  
  # Delivery target
  protocol: sqs
  endpoint: arn:aws:sqs:us-east-1:123456789012:order-processor
  
  # Filtering
  filterPolicy: |
    {
      "eventType": ["order.created", "order.updated"],
      "priority": ["high", "urgent"]
    }
  filterPolicyScope: MessageAttributes
  
  # Delivery behavior
  rawMessageDelivery: false
  deliveryPolicy: |
    {
      "healthyRetryPolicy": {
        "numRetries": 3,
        "minDelayTarget": 20,
        "maxDelayTarget": 60
      }
    }
  
  # Dead-letter queue
  redrivePolicy:
    deadLetterQueueRef: order-dlq
  
  # Organization
  tags:
    team: payments
    environment: production
  syncedLabels:
    application: order-processor
  
  deletionPolicy: retain
```

This subscription:
- Delivers high-priority order events to an SQS queue
- Filters by event type and priority
- Retries up to 3 times on failure
- Routes failed messages to `SQSQueue/order-dlq`
- Retains the AWS subscription if the CR is deleted

## Naming

Subscriptions do not have user-defined names in AWS. Each subscription is identified by its subscription ARN, which includes a system-assigned UUID assigned by AWS at creation time. The CR name (`metadata.name`) is used for Kubernetes identification only.

There is no `effectiveName`, `nameOverride`, `status.resourceName`, or `status.predictedArn` on subscriptions — only `status.subscriptionArn` (available after confirmation).

## Monitoring

Check subscription status:

```bash
kubectl describe snssubscription order-events-consumer -n prod
```

Look for:
- `status.subscriptionArn` — The full subscription ARN (populated after confirmation)
- `status.pendingConfirmation` — `"true"` if awaiting confirmation, empty otherwise
- `status.conditions` — Ready, error, or warning states

Test message delivery with the AWS CLI:

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:order-events \
  --message '{"orderId": "12345", "status": "created"}' \
  --message-attributes 'eventType={DataType=String,StringValue=order.created},priority={DataType=String,StringValue=high}'
```

Messages matching the subscription's filter policy will be delivered to the endpoint.

## Endpoint Immutability

The delivery endpoint (`spec.endpoint`) cannot be changed after creation. If you need to change the endpoint, delete the subscription and create a new one. This is an AWS SNS constraint — the ACK controller enforces it at the CRD level.

## Cross-Provider Notes

- **AWS SNS subscriptions are independent resources**, not nested under topics. GCP Pub/Sub and Azure Service Bus embed subscriptions as sub-resources.
- **Confirmation is AWS SNS–specific** — email and HTTP/S subscriptions require out-of-band confirmation. GCP Pub/Sub and Azure Service Bus activate immediately.
- **Dead-letter queues route to SQS** — this is AWS-specific. GCP Pub/Sub uses a separate dead-letter topic; Azure Service Bus uses a built-in `$DeadLetterQueue` sub-queue.
- **Message filtering syntax** differs across providers — AWS uses JSON filter policies; GCP uses CEL expressions; Azure uses SQL-like rules.
