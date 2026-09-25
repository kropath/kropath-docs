---
title: AWS EventBridge
description: EventBridge is a serverless event bus service that makes it easier to build event-driven applications.
doc_type: reference
weight: 260
---
# AWS EventBridge

EventBridge is a serverless event bus service that makes it easier to build event-driven applications. Use EventBridge to route events between AWS services, custom applications, and SaaS providers.

## EventBridge Resources

Kropath provides four resource kinds for EventBridge:

| Resource | Purpose | Use for |
|---|---|---|
| [EventBridgeConfig](eventbridgeconfig.md) | Governance profiles | Defining organizational policies and compliance requirements |
| [EventBridgeEventBus](eventbridgeeventbus.md) | Event buses | Creating custom event buses and isolating application events |
| [EventBridgeRule](eventbridgerule.md) | Event routing rules | Matching events and delivering them to targets (Lambda, SQS, SNS, etc.) |
| [EventBridgeArchive](eventbridgearchive.md) | Event archiving | Storing events for compliance, audit, and replay |
| [EventBridgeEndpoint](eventbridgeendpoint.md) | Global endpoints | Multi-region failover and event replication |

## Quick Start

### 1. Create an Event Bus

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEventBus
metadata:
  name: my-events
  namespace: app-prod
spec:
  configRef: general-policy
```

### 2. Create a Routing Rule

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: order-processor
  namespace: app-prod
spec:
  eventBusRef: "my-events"
  eventPattern: '{"source": ["myapp.orders"]}'
  targets:
    - id: process-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:order-processor"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-role"
```

### 3. Archive Events for Compliance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: order-archive
  namespace: app-prod
spec:
  eventBusRef: "my-events"
  retentionDays: 90
```

## Architecture

### Event Flow

1. **Publishers** send events to an event bus
2. **Rules** match events using patterns or schedules
3. **Targets** receive and process matched events
4. **Archives** capture events for compliance and replay

```
Publisher
    ↓
Event Bus
    ↓
Rules (match by pattern or schedule)
    ↓
Targets (Lambda, SQS, SNS, etc.)

Archives capture all events for compliance
```

### Governance Cascade

EventBridge resources inherit governance from `EventBridgeConfig` profiles:

```
KropathConfig (org-wide)
    ↓
EventBridgeConfig (per-profile, e.g., "pci", "hipaa")
    ↓
Resource instances (developers can override defaults)
```

Mandatory settings cannot be overridden. Defaults provide sensible baselines.

## Event Patterns

EventBridge rules match events using JSON patterns:

### Simple Matching

```json
{"source": ["myapp"]}
```

### Multiple Values

```json
{"detail-type": ["Order Placed", "Order Shipped"]}
```

### Nested Fields

```json
{"detail": {"status": ["completed"]}}
```

### Numeric Comparisons

```json
{"detail": {"amount": [{"numeric": [">", 100]}]}}
```

Learn more: [EventBridgeRule](eventbridgerule.md#event-pattern-matching)

## Compliance Profiles

### General Policy (default)

```yaml
configRef: general-policy
```

No enforcement; sensible defaults only.

### PCI Compliance

```yaml
configRef: pci
```

Enforces:
- 90-day minimum archive retention
- Mandatory tagging and labels
- Compliance naming prefix

### HIPAA Compliance

```yaml
configRef: hipaa
```

Enforces:
- 7-year (2555-day) minimum retention for archives
- PII handling labels
- Audit trail requirements

## Common Patterns

### Filter and Deliver to SQS

Route specific events to an SQS queue:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: order-to-queue
  namespace: app-prod
spec:
  eventBusRef: "order-events"
  eventPattern: '{"source": ["myapp.orders"]}'
  targets:
    - id: order-queue
      arn: "arn:aws:sqs:us-east-1:123456789012:orders"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-sqs"
      deadLetterConfig:
        arn: "arn:aws:sqs:us-east-1:123456789012:orders-dlq"
```

### Schedule a Periodic Task

Trigger a function every 5 minutes:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: health-check
  namespace: platform
spec:
  eventBusName: "default"
  scheduleExpression: "rate(5 minutes)"
  targets:
    - id: health-check-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:health-check"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-lambda"
```

### Archive Events with Filtering

Archive only payment events for 1 year:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeArchive
metadata:
  name: payment-archive
  namespace: payments-prod
spec:
  eventBusRef: "payment-events"
  eventPattern: '{"source": ["payments"], "detail-type": ["Payment Processed"]}'
  retentionDays: 365
```

### Multi-Region Failover

Create a global endpoint for high availability:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEndpoint
metadata:
  name: global
  namespace: platform-prod
spec:
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/my-bus"
    - eventBusArn: "arn:aws:events:us-west-2:123456789012:event-bus/my-bus"
  routingConfig:
    failoverConfig:
      primary:
        healthCheck: "arn:aws:route53:::healthcheck/hc123"
      secondary:
        route: "us-west-2"
  replicationConfig:
    state: "ENABLED"
  roleArn: "arn:aws:iam::123456789012:role/eventbridge-replication"
```

## Monitoring and Troubleshooting

### Check Event Bus Status

```bash
kubectl describe eventbridgeeventbus my-events -n app-prod
```

### List All Rules

```bash
kubectl get eventbridgerule -n app-prod
```

### View Archive Status

```bash
kubectl describe eventbridgearchive order-archive -n app-prod
```

### Test Event Matching

```bash
aws events test-event-pattern \
  --event-pattern '{"source": ["myapp"]}' \
  --event '{"source": "myapp", "detail": {"status": "started"}}'
```

### Replay Archived Events

```bash
aws events start-replay \
  --name my-replay \
  --archive-name order-archive \
  --event-source-arn arn:aws:events:us-east-1:123456789012:event-bus/my-bus \
  --event-start-time 2024-01-01T00:00:00Z \
  --event-end-time 2024-01-02T00:00:00Z
```

## Best Practices

1. **Use naming templates** — Apply consistent naming via `EventBridgeConfig` profiles
2. **Implement dead-letter queues** — Route failed messages for debugging
3. **Archive for compliance** — Meet regulatory requirements with `EventBridgeArchive`
4. **Use governance profiles** — Enforce organizational policies via `EventBridgeConfig`
5. **Filter at the rule level** — Keep patterns specific to reduce unnecessary processing
6. **Version your rules** — Include version info in rule names for ease of upgrades
7. **Monitor with CloudWatch** — Set up alarms for rule invocation failures
8. **Test event patterns** — Use `test-event-pattern` before deploying rules
9. **Plan retention** — Ensure archive retention aligns with compliance requirements
10. **Document purpose** — Use `description` fields on archives and rules

## Limits

| Limit | Value |
|---|---|
| Custom event buses per account | 10 (default; contact AWS to increase) |
| Rules per event bus | 300 |
| Targets per rule | 5 |
| Archive retention | 0 to 2555+ days (AWS max is configurable) |
| Event size | 256 KB |
| Archived events kept | Indefinite (with retention-based deletion) |

## Next Steps

- **Get started:** [Create an event bus](eventbridgeeventbus.md)
- **Route events:** [Create routing rules](eventbridgerule.md)
- **Archive data:** [Set up event archives](eventbridgearchive.md)
- **Multi-region:** [Configure global endpoints](eventbridgeendpoint.md)
- **Governance:** [Define profiles](eventbridgeconfig.md)

## Resources

- AWS EventBridge documentation: https://docs.aws.amazon.com/eventbridge/
- Event pattern syntax: https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html
- Cron expression syntax: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html
