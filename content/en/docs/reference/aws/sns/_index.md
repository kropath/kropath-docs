---
title: SNS — Publish/Subscribe Topics
description: The SNS family provides resources for creating and managing AWS Simple Notification Service (SNS) topics.
doc_type: reference
weight: 500
---
# SNS — Publish/Subscribe Topics

The SNS family provides resources for creating and managing AWS Simple Notification Service (SNS) topics. Use SNS when you need one-to-many messaging, fan-out patterns, and managed message delivery to multiple subscription types.

## Resources

- **[SNSTopic](./snstopic.md)** — Creates standard and FIFO topics with encryption, delivery policies, and governance controls
- **[SNSConfig](./snsconfig.md)** — Governance profiles that enforce encryption, message signing, tracing, and naming conventions

## Quick Start

Define a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    kmsMasterKeyId: "alias/aws/sns"
    signatureVersion: "1"
    tracingConfig: "PassThrough"
    namingTemplate: "{namespace}-{name}"
```

Then create a topic:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
```

## Common Patterns

### Standard Topic (Unlimited Throughput)

```yaml
spec:
  fifo: false  # default
  kmsMasterKeyId: "alias/aws/sns"
  signatureVersion: "1"
  tracingConfig: "PassThrough"
```

### FIFO Topic (Strict Ordering, Per-Group Throughput)

```yaml
spec:
  fifo: true
  contentBasedDeduplication: true
  fifoThroughputScope: "Topic"
  kmsMasterKeyId: "alias/aws/sns"
```

### Topic with Delivery Feedback

```yaml
spec:
  deliveryFeedback:
    http:
      successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
      failureFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback-fail"
      successFeedbackSampleRate: "100"
    lambda:
      successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
      successFeedbackSampleRate: "50"
```

### Topic with Data Protection

```yaml
spec:
  dataProtectionPolicy: |
    {
      "Name": "protect-pii",
      "Version": "2021-06-01",
      "Statement": [{
        "DataIdentifier": ["arn:aws:dataprotection::aws:data-identifier/EmailAddress"],
        "Operation": {"Deny": {}}
      }]
    }
```

### Topic with Access Policy

```yaml
spec:
  topicPolicyRef: "order-topic-policy"
```

Reference an `PolicyDocument` resource to control who can publish and subscribe.

## Governance

SNS resources follow the three-tier governance cascade:

1. **Organization-wide** — Set via `KropathConfig.spec.mandatory.sns` and `spec.defaults.sns` (encryption, signing, tracing only)
2. **Resource type** — Set via `SNSConfig` profiles (all governance fields)
3. **Instance** — Set on individual `SNSTopic` resources

Mandatory controls (e.g., org-wide encryption enforcement) always win. Instance values override defaults.

## Naming

Topic names are auto-generated from a template. The default template is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-events`
- **Topic name:** `payments-prod-order-events`

Override with `spec.nameOverride` if needed.

FIFO topics automatically get a `.fifo` suffix appended by kropath (e.g., `payments-prod-order-events.fifo`).

## Encryption

Topics support three encryption modes:

- **AWS-managed** (default) — `kmsMasterKeyId: "alias/aws/sns"`
- **Customer-managed** — `kmsMasterKeyId: "arn:aws:kms:region:account:key/id"`
- **No encryption** — `kmsMasterKeyId: ""` (usually forbidden by governance)

## Deletion

By default, topics are retained when the CR is deleted. To delete the underlying AWS topic:

```yaml
spec:
  deletionPolicy: delete
```

## Topic Types

Choose the topic type that matches your use case:

| Type | Ordering | Throughput | For |
|---|---|---|---|
| **Standard** (`fifo: false`) | Best-effort | Unlimited | Notifications, broadcasts, general pub/sub |
| **FIFO** (`fifo: true`) | Strict per-group | Capped at 300 msg/sec per scope | Order processing, event sourcing, strict sequencing |
