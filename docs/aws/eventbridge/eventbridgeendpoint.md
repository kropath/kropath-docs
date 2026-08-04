# EventBridgeEndpoint — Global Event Endpoints

The `EventBridgeEndpoint` resource provides automatic multi-region failover for EventBridge event ingestion. Global endpoints route events to event buses in two regions based on Route 53 health checks, with optional event replication to keep both regions synchronized.

## Overview

Use `EventBridgeEndpoint` for:

- **Multi-region failover** — Automatic routing to a secondary region if the primary fails
- **High availability** — Route 53 health checks detect primary region outages
- **Event replication** — Optional synchronization of events across regions
- **Global event ingestion** — Single endpoint for applications worldwide

Global endpoints are an advanced feature for organizations requiring multi-region event infrastructure. Most teams do not need this level of geographic redundancy.

## Prerequisites

Before creating an endpoint, you must have:

1. **Two EventBridgeEventBus resources in different regions** — With identical names
2. **A Route 53 health check** — Monitoring your primary region
3. **IAM role for replication** (if enabling replication) — With permissions to replicate events

## Creating an Endpoint

### Basic Failover Endpoint

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEndpoint
metadata:
  name: global-endpoint
  namespace: platform-prod
spec:
  configRef: general-policy
  description: "Global endpoint for multi-region event ingestion"
  
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/order-events"
    - eventBusArn: "arn:aws:events:us-west-2:123456789012:event-bus/order-events"
  
  routingConfig:
    failoverConfig:
      primary:
        healthCheck: "arn:aws:route53:::healthcheck/abc123"
      secondary:
        route: "us-west-2"
```

This endpoint:
- Routes events to either us-east-1 or us-west-2
- Uses Route 53 health check to detect primary region failures
- Automatically fails over to us-west-2 if us-east-1 becomes unhealthy
- Does not replicate events between regions (replication is disabled by default)

### Failover Endpoint with Replication

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeEndpoint
metadata:
  name: replicated-endpoint
  namespace: payments-prod
spec:
  configRef: general-policy
  description: "Global endpoint with cross-region replication"
  
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/payment-events"
    - eventBusArn: "arn:aws:events:eu-west-1:123456789012:event-bus/payment-events"
  
  routingConfig:
    failoverConfig:
      primary:
        healthCheck: "arn:aws:route53:::healthcheck/hc456"
      secondary:
        route: "eu-west-1"
  
  replicationConfig:
    state: "ENABLED"
  
  roleArn: "arn:aws:iam::123456789012:role/eventbridge-replication"
```

This endpoint:
- Replicates all events from the primary region (us-east-1) to the secondary (eu-west-1)
- When events are sent to the endpoint, they arrive at both regions
- Useful for keeping payment or audit events synchronized across regions
- Requires an IAM role with `events:PutEvents` permission on both buses

## Endpoint Configuration

### Event Bus Specification

Specify two event buses in different regions with identical names:

```yaml
spec:
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/my-bus"
    - eventBusArn: "arn:aws:events:us-west-2:123456789012:event-bus/my-bus"
```

**Requirements:**
- Exactly two event buses
- Different regions
- Identical names (e.g., both named `my-bus`)
- Both must exist before creating the endpoint

### Route 53 Health Check

Specify the health check monitoring your primary region:

```yaml
spec:
  routingConfig:
    failoverConfig:
      primary:
        healthCheck: "arn:aws:route53:::healthcheck/hc-123"
      secondary:
        route: "us-west-2"
```

**How it works:**
1. Events are normally routed to the primary region (us-east-1)
2. Route 53 continuously monitors the primary health check
3. If the health check fails, events are automatically routed to the secondary region
4. When the primary recovers, routing switches back

**Create a health check:**
```bash
aws route53 create-health-check \
  --type CLOUDWATCH_METRIC \
  --alarm-identifier Name=EventBridgePrimaryAlarm,Region=us-east-1 \
  --insufficient-data-health-status Unhealthy
```

### Event Replication

Optionally replicate events across both regions:

**Disabled (default):**
```yaml
spec:
  replicationConfig:
    state: "DISABLED"
```

Events go only to the health-check-determined region.

**Enabled:**
```yaml
spec:
  replicationConfig:
    state: "ENABLED"
  roleArn: "arn:aws:iam::123456789012:role/eventbridge-replication"
```

When enabled:
- All events are sent to BOTH regions simultaneously
- Useful for audit trails or critical business data
- Requires an IAM role with permissions to put events on both buses

**IAM role for replication:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "events:PutEvents",
      "Resource": [
        "arn:aws:events:us-east-1:123456789012:event-bus/payment-events",
        "arn:aws:events:eu-west-1:123456789012:event-bus/payment-events"
      ]
    }
  ]
}
```

**Note:** `roleArn` is required when `replicationConfig.state` is `"ENABLED"`.

### Naming

Endpoint names are generated from a naming template. The default is `{namespace}-{name}`:

- Namespace: `platform-prod`
- CR name: `global-endpoint`
- **Endpoint name:** `platform-prod-global-endpoint`

Override per-endpoint:

```yaml
spec:
  nameOverride: "my-global-endpoint"
```

**AWS constraints:**
- Endpoint names can contain letters, numbers, hyphens (`.`, `-`, `_`, alphanumeric only)
- Maximum 64 characters
- Case-sensitive

**Note:** Unlike other EventBridge resources, endpoint ARNs are global (no region segment) and are assigned by AWS after creation. Endpoints do not have a `status.predictedArn` — only `status.endpointArn` after provisioning.

### Description

Add a human-readable description:

```yaml
spec:
  description: "Global endpoint for multi-region payment event ingestion with failover"
```

### Deletion Policy

```yaml
spec:
  deletionPolicy: "retain"  # Default: keep the endpoint when CR is deleted
  deletionPolicy: "delete"  # Delete the endpoint when CR is deleted
```

## Using Global Endpoints

### Sending Events to a Global Endpoint

Applications send events to the endpoint ARN instead of directly to an event bus:

```bash
aws events put-events \
  --entries '[{"Source": "myapp", "DetailType": "Order Placed", "Detail": "{\"order_id\": \"12345\"}", "Resources": ["arn:aws:events:us-east-1:123456789012:endpoint/platform-prod-global-endpoint"]}]'
```

The endpoint routes the event to:
- **Primary region (us-east-1)** — If health check is healthy
- **Secondary region (us-west-2)** — If primary health check fails
- **Both regions** — If replication is enabled

### Endpoint Resilience

**Failover example:**

1. Primary health check fails (us-east-1 outage detected)
2. Route 53 marks primary as unhealthy
3. EventBridge automatically routes to secondary (us-west-2)
4. Application continues sending events without code changes
5. When primary recovers, routing switches back

This automatic failover happens without application intervention.

## Status and Monitoring

Check endpoint status:

```bash
kubectl describe eventbridgeendpoint global-endpoint -n platform-prod
```

Look for:
- `status.resourceName` — The endpoint name
- `status.endpointArn` — The global ARN (assigned by AWS)
- `status.endpointState` — `ACTIVE`, `CREATING`, `UPDATING`, `DELETING`, or `FAILED`
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens`
- `status.conditions` — Ready, error, or warning states

**Example ARN:**
```
arn:aws:events:region:123456789012:endpoint/platform-prod-global-endpoint
```

Note: This is a global ARN (no region segment), which is unusual for AWS resources.

### Monitor replication

If replication is enabled, check replication lag:

```bash
aws events describe-endpoint --name platform-prod-global-endpoint
```

This shows:
- `ReplicationConfig.State` — `ENABLED` or `DISABLED`
- `RoutingConfig` — Failover configuration
- `CreationTime` — When the endpoint was created

## Use Cases

### E-Commerce Platform

```yaml
spec:
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/orders"
    - eventBusArn: "arn:aws:events:us-west-2:123456789012:event-bus/orders"
  
  replicationConfig:
    state: "ENABLED"  # Keep order events synchronized
  
  roleArn: "arn:aws:iam::123456789012:role/eventbridge-replication"
```

Orders are replicated to both regions for instant access to order history.

### Financial Services

```yaml
spec:
  eventBuses:
    - eventBusArn: "arn:aws:events:us-east-1:123456789012:event-bus/transactions"
    - eventBusArn: "arn:aws:events:ca-central-1:123456789012:event-bus/transactions"
  
  replicationConfig:
    state: "ENABLED"  # Compliance requirement
  
  roleArn: "arn:aws:iam::123456789012:role/eventbridge-compliance"
```

Transaction events are replicated for audit compliance and regulatory requirements.

## Troubleshooting

### Endpoint not routing events

1. Verify the endpoint is in `ACTIVE` state (`status.endpointState`)
2. Check that both event buses exist and have identical names
3. Verify the Route 53 health check is configured correctly
4. Test health check status: `aws route53 get-health-check-status --health-check-id <id>`
5. Check that applications are sending events to the endpoint ARN (not directly to the bus)

### Replication not working

1. Verify `replicationConfig.state` is `ENABLED`
2. Check that `roleArn` is specified
3. Verify the IAM role has `events:PutEvents` on both buses
4. Check CloudWatch Logs for replication errors
5. Verify both event buses are accessible from the primary region

### Failover not triggering

1. Verify the Route 53 health check is configured to detect failures
2. Test the health check manually: `aws route53 get-health-check-status --health-check-id <id>`
3. Check that the secondary region event bus is healthy and accepting events
4. Verify the secondary region has capacity to handle increased traffic

## Cross-Provider Notes

- Global endpoints with automatic failover are AWS EventBridge–specific
- GCP Eventarc has no native multi-region failover equivalent
- Azure Event Grid has limited geo-disaster recovery at the Domain level
- Event replication across regions is unique to AWS EventBridge
- The endpoint ARN format (global, no region) is unusual for AWS resources
