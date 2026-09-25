---
title: EventBridgeArchive — Event Archiving
description: "The `EventBridgeArchive` resource captures and stores events from an event bus for later replay and compliance."
doc_type: reference
---
# EventBridgeArchive — Event Archiving

The `EventBridgeArchive` resource captures and stores events from an event bus for later replay and compliance. Archives serve audit, compliance, and recovery use cases by preserving event history with configurable retention periods.

## Overview

Use `EventBridgeArchive` to:

- **Archive events for compliance** — Meet regulatory requirements like HIPAA or PCI by storing events
- **Replay events** — Reprocess archived events to recover from application failures
- **Implement audit trails** — Maintain immutable records of all events for accountability
- **Support legal holds** — Retain events for litigation or investigations
- **Selective archiving** — Archive only specific event types using JSON patterns

Each archive has:
- **Event bus association** — Which event bus to archive from
- **Event pattern filter** — Optionally, which events to capture (empty = all events)
- **Retention period** — How long to keep archived events
- **Governance control** — Inherit compliance requirements from EventBridgeConfig

## Creating an Archive

### Simple Archive (All Events)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: order-archive
  namespace: payments-prod
spec:
  configRef: general-policy
  eventBusRef: "order-events"  # Reference the EventBridgeEventBus by CR name
  retentionDays: 90  # Keep archived events for 90 days
```

This archive:
- Captures all events from the `order-events` bus
- Stores events for 90 days
- Inherits governance defaults from the `general-policy` profile
- Is named `payments-prod-order-archive` (from the naming template)

### Selective Archive (Filtered Events)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: compliance-archive
  namespace: compliance-prod
spec:
  configRef: general-policy
  eventBusRef: "domain-events"
  eventPattern: '{"source": ["com.myapp.payments"], "detail-type": ["Payment Processed"]}'
  retentionDays: 365  # Keep for 1 year
  description: "Archive of payment events for compliance"
```

This archive:
- Captures only payment-related events (filtered by pattern)
- Stores events for 365 days (1 year)
- Includes a human-readable description
- Useful for compliance workloads where you only need specific event types

### HIPAA-Compliant Archive

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: healthcare-archive
  namespace: healthcare-prod
spec:
  configRef: hipaa
  eventBusRef: "patient-events"
  eventPattern: '{"source": ["healthcare.myapp"]}'
  description: "7-year archive for HIPAA compliance"
```

This archive:
- Uses the `hipaa` governance profile (enforces 7-year minimum retention)
- Captures healthcare-related events only
- Meets HIPAA retention requirements (configRef enforces `retentionDays: 2555`)

### External Event Bus Archive

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: external-archive
  namespace: integrations
spec:
  configRef: general-policy
  eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/external-partner-bus"
  retentionDays: 30
```

This archive:
- Archives events from an external (non-kropath-managed) event bus
- Uses the direct ARN instead of a CR reference
- Useful for archiving events from partner or third-party event buses

## Archive Configuration

### Event Bus Association

Specify where to archive from:

**Kropath-managed bus (recommended):**

```yaml
spec:
  eventBusRef: "order-events"  # Reference by CR name
```

The archive resolves the EventBridgeEventBus CR named `order-events` and reads its `status.predictedArn` for the actual AWS event bus ARN.

**External bus:**

```yaml
spec:
  eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/external-bus"
```

Directly specify the event bus ARN (immutable after creation).

**Note:** Exactly one of `eventBusRef` or `eventBusArn` must be set.

### Event Pattern Filter

Archive specific events using JSON patterns:

```yaml
spec:
  eventPattern: '{"source": ["com.myapp.payments"], "detail-type": ["Charge Complete"]}'
```

If `eventPattern` is empty, all events from the bus are archived.

**Common filtering patterns:**

Archive only critical events:
```json
{"source": ["myapp"], "detail": {"severity": ["critical"]}}
```

Archive events from specific services:
```json
{"source": ["service-a", "service-b"]}
```

Archive events above a certain amount:
```json
{"detail": {"amount": [{"numeric": [">", 1000]}]}}
```

### Retention Periods

Control how long archived events are stored:

```yaml
spec:
  retentionDays: 90  # 90 days
  retentionDays: 365  # 1 year
  retentionDays: 2555  # 7 years (HIPAA minimum)
  retentionDays: 0  # Indefinite retention
```

**Governance cascade:**

The EventBridgeConfig governance profile can enforce minimum retention:

```yaml
# In EventBridgeConfig mandatory tier
mandatory:
  archiveRetentionDays: 90  # Minimum 90 days
```

If the config specifies `mandatory.archiveRetentionDays: 90`, the archive cannot be configured with fewer than 90 days (e.g., `retentionDays: 30` would be overridden to `90`).

**Retention enforcement table:**

| Config Mandatory | Config Defaults | Instance Spec | Result |
|---|---|---|---|
| 90 | 365 | 30 | Overridden to 90 (minimum enforced) |
| 90 | 365 | 180 | Kept as 180 (exceeds minimum) |
| 0 | 365 | 0 | Kept as 0 (indefinite) |
| 0 | 365 | unset | Applied 365 from defaults |

**Use cases by retention period:**

- **7-14 days** — Operational logging, short-term debugging
- **30-90 days** — PCI compliance, audit trails
- **1 year (365 days)** — General compliance, regulatory requirements
- **7 years (2555 days)** — HIPAA, legal holds, long-term archives

### Description

Add a human-readable description:

```yaml
spec:
  description: "Archive of payment events for compliance audit trail"
```

Useful for documenting the archive's purpose and compliance context.

### Naming

Archive names are generated from a naming template. The default is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-archive`
- **Archive name:** `payments-prod-order-archive`

Override per-archive:

```yaml
spec:
  nameOverride: "pci-payment-archive"
```

**AWS constraints:**
- Archive names can contain letters, numbers, hyphens (`.`, `-`, `_`, alphanumeric only)
- Maximum 48 characters
- Case-sensitive

### Deletion Policy

```yaml
spec:
  deletionPolicy: "retain"  # Default: keep the archive when CR is deleted
  deletionPolicy: "delete"  # Delete the archive when CR is deleted
```

Use `retain` for production archives (safer for compliance data).

## Using Archived Events

### View Archived Events

List events in the archive:

```bash
aws events list-archives --name payments-prod-order-archive
```

### Replay Events

Replay archived events to test changes or recover from failures:

```bash
# Create a replay of events from the past 7 days
aws events start-replay \
  --name my-replay \
  --archive-name payments-prod-order-archive \
  --event-source-arn arn:aws:events:us-east-1:123456789012:event-bus/payments-prod-order-events \
  --event-start-time 2024-01-01T00:00:00Z \
  --event-end-time 2024-01-08T00:00:00Z
```

Events are replayed through rules as if they occurred at their original time. Useful for:
- Testing rule changes
- Recovering from Lambda function errors
- Processing events with updated business logic

### Query Event Archive

Use AWS CloudTrail or custom queries to search archived events.

## Status and Monitoring

Check archive status:

```bash
kubectl describe eventbridgearchive order-archive -n payments-prod
```

Look for:
- `status.resourceName` — The actual archive name in AWS
- `status.predictedArn` — The archive ARN
- `status.archiveArn` — The actual ARN after provisioning
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens`
- `status.conditions` — Ready, error, or warning states

**Example ARN:**
```
arn:aws:events:us-east-1:123456789012:archive/payments-prod-order-archive
```

### Archive metrics

Monitor archive growth and performance:

```bash
aws events describe-archive --name payments-prod-order-archive
```

This shows:
- `EventCount` — Number of events archived
- `SizeInBytes` — Size of the archive
- `CreationTime` — When the archive was created
- `RetentionDays` — Configured retention period

## Governance and Compliance

### HIPAA 7-Year Retention

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: healthcare-events
  namespace: healthcare-prod
spec:
  configRef: hipaa  # Enforces 2555-day (7-year) minimum
  eventBusRef: "patient-events"
  description: "HIPAA-compliant archive of patient events"
```

The `hipaa` profile enforces:
- `mandatory.archiveRetentionDays: 2555` (7 years)
- Cannot be overridden even if you specify fewer days
- Meets HIPAA retention requirements

### PCI 90-Day Retention

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: payment-archive
  namespace: payments-prod
spec:
  configRef: pci  # Enforces 90-day minimum
  eventBusRef: "payment-events"
  eventPattern: '{"source": ["com.myapp.payments"]}'
  description: "PCI-compliant payment event archive"
```

The `pci` profile enforces:
- `mandatory.archiveRetentionDays: 90` (PCI minimum)
- Selective archiving of payment events only
- Meets PCI DSS requirements

## Troubleshooting

### Archive not capturing events

1. Verify the event bus name is correct (`status.conditions`)
2. Test the event pattern with sample events
3. Verify events are being sent to the event bus (check CloudWatch Logs)
4. Confirm the archive is enabled and has not reached its retention limit

### Event replay not working

1. Verify events exist in the archive (`EventCount > 0`)
2. Check that replay start/end times match available events
3. Verify the rules and targets are configured correctly
4. Check CloudWatch Logs for rule invocation failures

## Cross-Provider Notes

- Event archiving and replay is AWS EventBridge–specific
- GCP Eventarc and Azure Event Grid do not have native archive/replay equivalents
- Archive retention governance (`archiveRetentionDays`) is unique to the EventBridge family
- AWS manages archive encryption automatically; per-archive encryption configuration is not available
