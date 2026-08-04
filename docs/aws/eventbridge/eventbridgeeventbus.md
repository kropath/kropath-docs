# EventBridgeEventBus — Event Buses

The `EventBridgeEventBus` resource creates AWS EventBridge event buses. Event buses are the primary mechanism for routing events within AWS EventBridge. You can create custom event buses to isolate application events, manage event subscriptions, and enforce organizational governance.

## Overview

Use `EventBridgeEventBus` to create:

- **Custom event buses** — Isolated event channels for specific applications or teams
- **Governed event buses** — With compliance tagging and naming enforcement
- **Scalable event ingestion** — Event buses automatically scale to handle high event volumes
- **Event filtering and routing** — Route events using EventBridge Rules (see EventBridgeRule)

Each event bus has:
- **Naming** — Generated from a template or custom name
- **Tags and labels** — For cost allocation, compliance, and resource discovery
- **Deletion policy** — Control what happens when the bus is deleted
- **Governance profile** — Select a profile to apply organizational controls

## Creating an Event Bus

### Simple Event Bus

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: order-events
  namespace: payments-prod
spec:
  configRef: general-policy
```

This event bus:
- Uses the `general-policy` governance profile
- Is named `payments-prod-order-events` (from the naming template)
- Has default tags and labels from the profile
- Retains the bus when deleted (default deletion policy)

### Event Bus with Custom Naming

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: notifications
  namespace: app-prod
spec:
  configRef: general-policy
  nameOverride: "app-notifications-bus"
```

This event bus:
- Uses the custom name `app-notifications-bus` (no template applied)
- Ignores the default naming template
- Useful when you need a specific bus name for external integrations

### Event Bus with Compliance Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: sensitive-events
  namespace: compliance-prod
spec:
  configRef: pci
  tags:
    application: sensitive-data-pipeline
  syncedLabels:
    data-class: restricted
```

This event bus:
- Uses the `pci` compliance profile (mandatory naming and tagging enforced)
- Adds application-specific tags
- Syncs Kubernetes labels to both AWS tags and Kubernetes labels
- Subject to PCI compliance controls

## Event Bus Configuration

### Governance Profile Selection

All EventBridge resources inherit governance from a profile via `spec.configRef`:

```yaml
spec:
  configRef: general-policy  # Default; applies general-policy profile
```

Profile selection determines:
- **Naming template** — How the bus name is constructed
- **Mandatory tags** — Tags that cannot be removed
- **Default tags** — Tags applied if not specified
- **Synced labels/annotations** — Kubernetes metadata synced to AWS and back

If a named profile does not exist, the bus falls back to `general-policy`.

### Naming

Event bus names are generated from a naming template. The default is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-events`
- **Bus name:** `payments-prod-order-events`

**Override per-bus:**

```yaml
spec:
  nameOverride: "my-custom-bus"
```

With `nameOverride`, the bus is named exactly `my-custom-bus` (no template applied).

**AWS constraints:**
- Custom event bus names can contain letters, numbers, hyphens (`.`, `-`, `_`, alphanumeric only)
- Maximum 256 characters
- Cannot use the reserved name `"default"` (reserved for AWS default event bus)
- Case-sensitive

### Tags and Labels

Add organization and application metadata:

```yaml
spec:
  tags:
    team: event-platform
    cost-center: "5678"
    environment: production
  syncedLabels:
    application: order-processor
    data-class: internal
  syncedAnnotations:
    slack-channel: "#events-platform"
    on-call: "events-team"
```

**Tags** appear on the AWS EventBridge event bus. Use them for cost allocation, access control, and resource discovery.

**Synced labels** appear on both the AWS event bus (as tags) and as Kubernetes labels. Useful for marking resources with organizational metadata.

**Synced annotations** appear on Kubernetes resources only. Use for operational metadata like contact information or alerting rules.

Tags from the governance profile are automatically merged with these user-specified tags.

### Deletion Policy

Control what happens to the AWS event bus when the CR is deleted:

**Retain (default):**

```yaml
spec:
  deletionPolicy: "retain"
```

The AWS event bus remains when the CR is deleted. Use for production buses to prevent accidental deletion.

**Delete:**

```yaml
spec:
  deletionPolicy: "delete"
```

The AWS event bus is deleted when the CR is deleted. Use only for temporary or test buses.

## Using Event Buses

### Define Rules on the Event Bus

Create routing rules to process events:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: order-processor
  namespace: payments-prod
spec:
  configRef: general-policy
  eventBusRef: "order-events"  # Reference the event bus CR by name
  eventPattern: '{"source": ["com.myapp.orders"]}'
  targets:
    - id: order-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:process-order"
```

### Archive Events for Replay

Archive events from the bus for compliance or replay:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: order-archive
  namespace: payments-prod
spec:
  configRef: general-policy
  eventBusRef: "order-events"  # Reference the event bus CR
  eventPattern: '{"source": ["com.myapp.orders"]}'
  retentionDays: 90  # Keep archived events for 90 days
```

## Status and Monitoring

Check event bus status:

```bash
kubectl describe eventbridgeeventbus order-events -n payments-prod
```

Look for:
- `status.resourceName` — The actual event bus name in AWS
- `status.predictedArn` — The full ARN (before provisioning)
- `status.eventBusArn` — The actual ARN after provisioning
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (indicates naming errors)
- `status.conditions` — Ready, error, or warning states

**Example ARN:**
```
arn:aws:events:us-east-1:123456789012:event-bus/payments-prod-order-events
```

### List all event buses

```bash
kubectl get eventbridgeeventbus -n payments-prod
```

### Send a test event

```bash
aws events put-events \
  --entries '[{"Source": "com.myapp.orders", "DetailType": "Order Placed", "Detail": "{\"order_id\": \"12345\"}", "EventBusName": "payments-prod-order-events"}]'
```

## Governance and Compliance

### Example: PCI Compliance

For PCI-regulated workloads, use the `pci` profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: payment-events
  namespace: payments-prod
spec:
  configRef: pci
  tags:
    compliance-scope: pci
```

The profile enforces:
- Mandatory naming prefix (e.g., `pci-payments-prod-payment-events`)
- Required compliance tags (`compliance-profile: pci`)
- Required labels on Kubernetes resources
- All inherited from the `pci` EventBridgeConfig profile

### Example: HIPAA Compliance

For HIPAA-regulated healthcare events:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: patient-events
  namespace: healthcare-prod
spec:
  configRef: hipaa
  syncedLabels:
    pii-sensitivity: high
```

The profile enforces:
- HIPAA-compliant naming
- 7-year minimum archive retention (via EventBridgeArchive with this bus reference)
- PII handling restrictions
- Audit trail annotations

## Cross-Provider Notes

- EventBridge custom event buses are AWS-specific. GCP uses Eventarc Channels; Azure uses Event Grid Domains.
- Event bus names are case-sensitive in AWS (unlike S3 bucket names).
- The default event bus (`"default"`) is reserved and managed by AWS; it cannot be created or deleted via kropath.
- AWS-managed encryption on event buses is automatic; per-bus encryption configuration is not supported.
- Event bus quotas: AWS limits you to 10 custom event buses per account by default (contact AWS to increase).
