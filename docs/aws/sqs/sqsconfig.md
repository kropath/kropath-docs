# SQSConfig — Governance Configuration

The `SQSConfig` resource defines governance profiles that control SQS queue behavior across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each queue.

## Overview

`SQSConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., encryption that all queues must use)
- **Defaults tier** — Baseline values developers can override (e.g., default visibility timeout if not specified on the queue)

This two-tier approach lets platform teams enforce critical compliance controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `encryptionType` | string | Encryption enforcement: `sqs-managed` \| `kms` \| `none` |
| `kmsMasterKeyId` | string | KMS key for SSE-KMS (requires `encryptionType: kms`) |
| `visibilityTimeout` | integer | Hard ceiling on visibility timeout (seconds) |
| `messageRetentionPeriod` | integer | Hard ceiling on message retention (seconds) |
| `delaySeconds` | integer | Hard ceiling on delivery delay (seconds) |
| `maximumMessageSize` | integer | Hard ceiling on message size (bytes) |
| `namingTemplate` | string | Template for queue names (cannot be overridden) |
| `tags` | map | Tags applied to all queues (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the queue level:

| Field | Type | Purpose |
|---|---|---|
| `encryptionType` | string | Default encryption when queue doesn't specify |
| `kmsMasterKeyId` | string | Default KMS key |
| `visibilityTimeout` | integer | Default visibility timeout (30 sec recommended) |
| `messageRetentionPeriod` | integer | Default retention (4 days = 345600 sec recommended) |
| `delaySeconds` | integer | Default delivery delay |
| `maximumMessageSize` | integer | Default message size limit |
| `namingTemplate` | string | Default naming template |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `0`, or `""` can appear in both — they indicate "not set".)

## Example Profiles

### Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    encryptionType: "sqs-managed"
    visibilityTimeout: 30
    messageRetentionPeriod: 345600  # 4 days
    delaySeconds: 0
    maximumMessageSize: 262144  # 256 KB
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

### Compliance-Hardened (pci)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    encryptionType: "kms"
    kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/abc123"
    visibilityTimeout: 120
    messageRetentionPeriod: 604800  # 7 days
    syncedLabels:
      compliance: pci
      data-classification: restricted
  defaults:
    delaySeconds: 0
    maximumMessageSize: 131072  # 128 KB
    namingTemplate: "pci-{namespace}-{name}"
```

## Using Profiles

Select a profile on any queue:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SQSQueue
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: pci  # Select the PCI compliance profile
  fifo: true
```

If a named profile does not exist, queues fall back to `general-policy`.

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
    sqs:
      encryptionType: "kms"
      kmsMasterKeyId: "arn:aws:kms:us-east-1:123456789012:key/org-key"
  defaults:
    sqs:
      visibilityTimeout: 30
      messageRetentionPeriod: 345600
```

**Org mandatory** (e.g., `mandatory.sqs.encryptionType`) applies with **highest priority** — namespace profiles and queues cannot override it.

**Org defaults** (e.g., `defaults.sqs.visibilityTimeout`) act as fallback values — used only when a namespace profile or queue does not specify a value.

## Governance Cascade

When a queue is created, kropath evaluates settings in this order (first match wins):

1. **Queue-level spec** — What the developer specified on the queue CR
2. **Mandatory tier** — SQSConfig mandatory controls (mandatory tier always wins)
3. **Defaults tier** — SQSConfig defaults
4. **Org-wide settings** — KropathConfig controls
5. **Hardcoded defaults** — kropath fallback defaults

For **mandatory fields**, the cascade is:
- Org mandatory → SQSConfig mandatory → cannot be overridden by queue

For **numeric ceilings** (visibility timeout, retention period, message size):
- Org mandatory and SQSConfig mandatory act as hard ceilings; queue values are clamped

For **string fields** (encryption type, naming template):
- Org mandatory and SQSConfig mandatory override completely

## Monitoring

Verify a profile:

```bash
kubectl get sqsconfig general-policy -n kro-system -o yaml
kubectl describe sqsconfig pci -n kro-system
```

Check what profile a queue is using:

```bash
kubectl describe sqsqueue order-events -n payments-prod | grep configRef
```

Inspect the effective configuration written by the controller:

```bash
kubectl get sqsconfig general-policy -n kro-system -o jsonpath='{.status.effectiveConfig}' | jq
```

The `status.effectiveConfig` field shows the merged configuration that queues actually use — a combination of org-wide, profile, and queue-level settings.
