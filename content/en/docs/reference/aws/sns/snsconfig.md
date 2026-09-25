---
title: SNSConfig — Governance Configuration
description: "The `SNSConfig` resource defines governance profiles that control SNS topic behavior across your organization and namespaces."
doc_type: reference
---
# SNSConfig — Governance Configuration

The `SNSConfig` resource defines governance profiles that control SNS topic behavior across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each topic.

## Overview

`SNSConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., encryption that all topics must use)
- **Defaults tier** — Baseline values developers can override (e.g., default encryption if not specified on the topic)

This two-tier approach lets platform teams enforce critical compliance controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `kmsMasterKeyId` | string | KMS key ID/ARN/alias for encryption (cannot be overridden) |
| `signatureVersion` | string | Message signature version: `"1"` (SHA-1) \| `"2"` (SHA-256) |
| `tracingConfig` | string | X-Ray tracing mode: `"PassThrough"` \| `"Active"` |
| `dataProtectionPolicy` | string | JSON policy for message data masking/blocking |
| `deliveryFeedback` | object | Per-protocol IAM roles and sample rates for delivery logging |
| `namingTemplate` | string | Template for topic names (cannot be overridden) |
| `tags` | map | Tags applied to all topics (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the topic level:

| Field | Type | Purpose |
|---|---|---|
| `kmsMasterKeyId` | string | Default KMS key for encryption |
| `signatureVersion` | string | Default signature version |
| `tracingConfig` | string | Default tracing mode |
| `dataProtectionPolicy` | string | Default data protection policy |
| `deliveryFeedback` | object | Default delivery feedback configuration |
| `namingTemplate` | string | Default naming template |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `0`, or `""` can appear in both — they indicate "not set".)

## Delivery Feedback Structure

Delivery feedback configuration allows you to log message delivery status per subscription protocol. The `deliveryFeedback` object contains sub-objects for each protocol:

```yaml
deliveryFeedback:
  application:     # HTTP/HTTPS subscriptions to applications
    successFeedbackRoleArn: string
    failureFeedbackRoleArn: string
    successFeedbackSampleRate: string  # percentage 1-100
  http:            # HTTP/HTTPS subscriptions
    successFeedbackRoleArn: string
    failureFeedbackRoleArn: string
    successFeedbackSampleRate: string
  lambda:          # AWS Lambda subscriptions
    successFeedbackRoleArn: string
    failureFeedbackRoleArn: string
    successFeedbackSampleRate: string
  sqs:             # SQS queue subscriptions
    successFeedbackRoleArn: string
    failureFeedbackRoleArn: string
    successFeedbackSampleRate: string
  firehose:        # Amazon Kinesis Data Firehose subscriptions
    successFeedbackRoleArn: string
    failureFeedbackRoleArn: string
    successFeedbackSampleRate: string
```

Each protocol is independently governed: mandatory wins over instance, instance wins over defaults.

## Example Profiles

### Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    kmsMasterKeyId: "alias/aws/sns"
    signatureVersion: "1"
    tracingConfig: "PassThrough"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

This baseline profile:
- Uses AWS-managed SNS encryption key (default)
- Defaults to SHA-1 message signing (AWS default)
- Defaults to PassThrough tracing mode
- Generates topic names from namespace and CR name
- Tags all topics with managed-by label

### Compliance-Hardened (pci)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/pci-key"
    signatureVersion: "2"
    tracingConfig: "Active"
    deliveryFeedback:
      http:
        successFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback"
        failureFeedbackRoleArn: "arn:aws:iam::123456789012:role/sns-feedback-fail"
        successFeedbackSampleRate: "100"
    syncedLabels:
      compliance: pci
      data-classification: restricted
  defaults:
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      compliance-profile: pci
```

This PCI profile:
- Enforces customer-managed KMS encryption
- Requires SHA-256 message signatures
- Activates X-Ray tracing
- Mandates delivery feedback logging with 100% sampling
- Adds compliance labels to all resources

## Using Profiles

Select a profile on any topic:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SNSTopic
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: pci  # Select the PCI compliance profile
```

If a named profile does not exist, topics fall back to `general-policy`.

## Organization-Wide Defaults

Set org-wide controls using the root configuration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    sns:
      kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/org-key"
      signatureVersion: "2"
      tracingConfig: "Active"
  defaults:
    sns:
      kmsMasterKeyId: "alias/aws/sns"
      signatureVersion: "1"
```

**Org mandatory** (e.g., `mandatory.sns.kmsMasterKeyId`) applies with **highest priority** — namespace profiles and topics cannot override it.

**Org defaults** (e.g., `defaults.sns.tracingConfig`) act as fallback values — used only when a namespace profile or topic does not specify a value.

## Governance Cascade

The configuration cascade follows a priority system with mandatory controls always winning:

**For mandatory fields:**
- Org mandatory → SNSConfig mandatory → topic spec is ignored
- Mandatory controls cannot be overridden by developers

**For defaults and overrideable fields:**
- Topic-level spec (if provided) wins
- SNSConfig defaults apply (if topic doesn't specify)
- Org-wide defaults apply (if SNSConfig doesn't specify)
- Hardcoded kropath defaults apply (as final fallback)

**For string fields** (encryption key, signature version, tracing mode):
- Org mandatory and SNSConfig mandatory override topic-level choices completely

**For delivery feedback** (per-protocol IAM roles):
- Governance is per-key: mandatory wins over instance wins over defaults
- Missing fields simply apply default (empty or skip configuration)

## Monitoring

Verify a profile:

```bash
kubectl get snsconfig general-policy -n kro-system -o yaml
kubectl describe snsconfig pci -n kro-system
```

Check what profile a topic is using:

```bash
kubectl describe snstopic order-events -n payments-prod | grep configRef
```

## Subscriptions

`SNSSubscription` CRs also reference `SNSConfig` via `spec.configRef`, following the same governance cascade rules. Tags, synced labels, and annotations defined in `SNSConfig` apply to both topics and their subscriptions. See [`SNSSubscription`](snssubscription.md) for subscription-specific governance and configuration.
