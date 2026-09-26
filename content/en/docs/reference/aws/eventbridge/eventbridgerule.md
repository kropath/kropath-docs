---
title: EventBridgeRule — Event Routing Rules
description: "The `EventBridgeRule` resource creates AWS EventBridge rules that route events on an event bus to one or more targets."
doc_type: reference
---
# EventBridgeRule — Event Routing Rules

The `EventBridgeRule` resource creates AWS EventBridge rules that route events on an event bus to one or more targets. Rules match events based on content patterns or schedules, then deliver them to Lambda functions, SQS queues, SNS topics, and other AWS services.

## Overview

Use `EventBridgeRule` to:

- **Route events by content** — Match events based on JSON patterns (e.g., `source` or `detail-type`)
- **Trigger on schedule** — Use cron expressions or fixed rates (e.g., every 5 minutes)
- **Deliver to multiple targets** — Send matched events to Lambda, SQS, SNS, Kinesis, ECS, and more
- **Implement retry policies** — Configure retry limits and dead-letter queues per target
- **Enable/disable rules** — Control rule execution without deletion

Each rule has:
- **Event matching** — Pattern-based or schedule-based matching (mutually exclusive)
- **Event bus association** — Route events from a kropath-managed or external event bus
- **Target configuration** — Where to deliver matched events
- **Retry and dead-lettering** — Resilience configuration per target

## Creating a Rule

### Simple Content-Based Rule

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: order-processor
  namespace: payments-prod
spec:
  configRef: general-policy
  eventBusRef: "order-events"  # Reference the EventBridgeEventBus by CR name
  eventPattern: '{"source": ["com.myapp.orders"], "detail-type": ["Order Placed"]}'
  targets:
    - id: order-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:process-order"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-invoke-lambda"
```

This rule:
- Matches events from `com.myapp.orders` source with detail type `Order Placed`
- Routes to a Lambda function
- Uses `order-events` event bus (resolved from the EventBridgeEventBus CR named `order-events`)

### Schedule-Based Rule (Cron)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: daily-report-generator
  namespace: analytics
spec:
  configRef: general-policy
  eventBusName: "default"  # Use the AWS default event bus
  scheduleExpression: "cron(0 20 * * ? *)"  # Run at 8 PM UTC daily
  targets:
    - id: report-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:generate-report"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-invoke-lambda"
```

This rule:
- Triggers every day at 8 PM UTC (cron expression)
- Runs a Lambda function to generate a daily report
- Uses the AWS default event bus

### Schedule-Based Rule (Rate)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: health-check
  namespace: platform
spec:
  configRef: general-policy
  eventBusName: "default"
  scheduleExpression: "rate(5 minutes)"  # Run every 5 minutes
  targets:
    - id: health-check-lambda
      arn: "arn:aws:lambda:us-east-1:123456789012:function:health-check"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-invoke-lambda"
```

This rule:
- Triggers every 5 minutes
- Calls a health-check Lambda function
- Useful for periodic polling and monitoring tasks

### Rule Targeting an SQS Queue

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: order-notifier
  namespace: payments-prod
spec:
  configRef: general-policy
  eventBusRef: "order-events"
  eventPattern: '{"source": ["com.myapp.orders"]}'
  targets:
    - id: notify-customer
      arn: "arn:aws:sqs:us-east-1:123456789012:order-notifications"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-send-sqs"
```

This rule:
- Routes matched events to an SQS queue
- Uses a role that grants EventBridge `sqs:SendMessage` on that queue

> **Retry policies and dead-letter configuration are not supported.** The `Target` type exposes
> only `id`, `arn`, `roleARN`, `input`, and `inputPath`. Per-target `retryPolicy` and
> `deadLetterConfig` are not available on `EventBridgeRule`; to catch failed deliveries today, monitor the
> rule's `FailedInvocations` metric in the `AWS/Events` namespace.

### Rule with Multiple Targets

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EventBridgeRule
metadata:
  name: event-broadcast
  namespace: platform
spec:
  configRef: general-policy
  eventBusRef: "domain-events"
  eventPattern: '{"source": ["myapp"]}'
  targets:
    - id: process-events
      arn: "arn:aws:lambda:us-east-1:123456789012:function:event-processor"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-invoke-lambda"

    - id: archive-events
      arn: "arn:aws:kinesis:us-east-1:123456789012:stream/events"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-send-kinesis"

    - id: notify-external
      arn: "arn:aws:sns:us-east-1:123456789012:domain-events-topic"
      roleARN: "arn:aws:iam::123456789012:role/eventbridge-send-sns"
```

This rule:
- Routes matched events to three different targets
- Sends to Lambda for processing, Kinesis for archival, and SNS for external notifications
- Each target has its own IAM role and configuration

## Rule Configuration

### Event Bus Association

Choose how to specify the event bus:

**Kropath-managed bus (recommended):**

```yaml
spec:
  eventBusRef: "order-events"  # Reference by CR name
```

The rule resolves the EventBridgeEventBus CR named `order-events` in the same namespace and reads its `status.resourceName` for the actual AWS event bus name.

**External or default bus:**

```yaml
spec:
  eventBusName: "default"  # AWS default event bus

  # Or an external partner bus:
  # spec:
  #   eventBusName: "external-partner-bus"
```

Directly specify the AWS event bus name (immutable after creation).

**Note:** Exactly one of `eventBusRef` or `eventBusName` must be set.

### Event Pattern Matching

Match events based on JSON structure:

```yaml
spec:
  eventPattern: '{"source": ["com.myapp.orders"], "detail-type": ["Order Placed"]}'
```

The pattern is a JSON object that matches event fields:

**Simple field matching:**
```json
{"source": ["myapp"]}
```
Matches events where `source` equals `"myapp"`.

**Multiple values:**
```json
{"detail-type": ["Order Placed", "Order Shipped", "Order Delivered"]}
```
Matches if `detail-type` is any of these values.

**Nested field matching:**
```json
{"detail": {"status": ["completed"]}}
```
Matches if `detail.status` equals `"completed"`.

**Complex pattern:**
```json
{
  "source": ["orders"],
  "detail-type": ["Order Placed"],
  "detail": {
    "amount": [{"numeric": [">", 100]}],
    "currency": ["USD"]
  }
}
```
Matches large orders in USD (numeric operators: `<`, `<=`, `>`, `>=`).

### Schedule Expressions

Schedule rules using cron or rate expressions:

**Cron format:**
```yaml
scheduleExpression: "cron(0 20 * * ? *)"  # 8 PM UTC every day
scheduleExpression: "cron(0 10 ? * MON-FRI *)"  # 10 AM UTC weekdays
scheduleExpression: "cron(0 0 1 * ? *)"  # 1st of every month at midnight UTC
```

**Rate format:**
```yaml
scheduleExpression: "rate(5 minutes)"  # Every 5 minutes
scheduleExpression: "rate(1 hour)"  # Every hour
scheduleExpression: "rate(7 days)"  # Every 7 days
```

**Note:** Exactly one of `eventPattern` or `scheduleExpression` must be set.

### Rule State

Control whether the rule is active:

**Enabled (default):**
```yaml
spec:
  state: "ENABLED"
```

The rule is active and processes events.

**Disabled:**
```yaml
spec:
  state: "DISABLED"
```

The rule is defined but not processing events. Useful for temporarily pausing event processing without deletion.

### Target Configuration

Each target specifies where events are delivered and how to handle delivery:

```yaml
targets:
  - id: unique-target-id
    arn: "arn:aws:service:region:account-id:resource"
    roleARN: "arn:aws:iam::account-id:role/eventbridge-role"  # Only for role-authorized targets
    input: '{"fixed": "payload"}'  # Optional: send a fixed JSON payload
    inputPath: "$.detail"  # Optional: extract a portion of the event
```

These five fields are the whole of the `Target` type. Nested parameter blocks (`ecsParameters`,
`kinesisParameters`, `inputTransformer`, `retryPolicy`, `deadLetterConfig`, …) are intentionally
omitted from `EventBridgeRule`.

**How EventBridge authorizes the call depends on the target type:**

| Target type | Authorization |
|---|---|
| Kinesis, Step Functions, ECS, Batch, API Gateway, API Destinations, cross-account event buses | EventBridge assumes the role in `roleARN` |
| Lambda, SNS, SQS, CloudWatch Logs | A **resource-based policy on the target itself**; `roleARN` is not used |

For a Lambda target this means setting `roleARN` achieves nothing — the function needs a
resource-based policy granting `events.amazonaws.com` invoke rights, conditioned on the rule ARN
(`aws lambda add-permission`). kropath has no resource for that yet, so it must be granted with the
AWS CLI today.

**Supported targets:**
- AWS Lambda functions
- Amazon SQS queues (with optional FIFO parameters)
- Amazon SNS topics
- Amazon Kinesis streams
- AWS ECS tasks
- AWS Batch jobs
- API Gateway endpoints
- API Destinations (HTTP endpoints)
- AWS Systems Manager OpsCenter

**Input transformation:**
- `input` — Send a constant JSON payload (ignores the matched event)
- `inputPath` — Extract a portion of the event using JSONPath

### Naming

Rule names are generated from a naming template. The default is `{namespace}-{name}`:

- Namespace: `payments-prod`
- CR name: `order-processor`
- **Rule name:** `payments-prod-order-processor`

Override per-rule:
```yaml
spec:
  nameOverride: "my-custom-rule"
```

**AWS constraints:**
- Rule names can contain letters, numbers, hyphens (`.`, `-`, `_`, alphanumeric only)
- Maximum 64 characters
- Case-sensitive

### Deletion Policy

```yaml
spec:
  deletionPolicy: "retain"  # Default: keep the rule when CR is deleted
  deletionPolicy: "delete"  # Delete the rule when CR is deleted
```

## Status and Monitoring

Check rule status:

```bash
kubectl describe eventbridgerule order-processor -n payments-prod
```

Look for:
- `status.resourceName` — The actual rule name in AWS
- `status.predictedArn` — The ARN (varies by event bus)
- `status.ruleArn` — The actual ARN after provisioning
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens`
- `status.conditions` — Ready, error, or warning states

**Example ARN (custom bus):**
```
arn:aws:events:us-east-1:123456789012:rule/payments-prod-order-events/payments-prod-order-processor
```

**Example ARN (default bus):**
```
arn:aws:events:us-east-1:123456789012:rule/payments-prod-order-processor
```

## Disabling a Rule for Maintenance

Temporarily disable without deleting:

```bash
kubectl patch eventbridgerule order-processor -n payments-prod -p '{"spec":{"state":"DISABLED"}}'
```

Re-enable:
```bash
kubectl patch eventbridgerule order-processor -n payments-prod -p '{"spec":{"state":"ENABLED"}}'
```

## Troubleshooting

### Events not reaching targets

1. Verify the rule is `ENABLED` (`status.state`)
2. Check the event pattern matches your events (test with `aws events test-event-pattern`)
3. For a role-authorized target, verify the role in `roleARN` grants the action on that target. For
   a Lambda or SNS target, verify the target's own resource-based policy instead
   (`aws lambda get-policy` / `aws sns get-topic-attributes`)
4. Check CloudWatch Logs for the Lambda function (if target is Lambda)
5. Check the rule's `FailedInvocations` metric in the `AWS/Events` namespace

### Rule naming errors

If `status.namingStatus` is `invalid-unresolved-tokens`, a naming template token could not be resolved (e.g., a tag reference to a non-existent tag).

## Cross-Provider Notes

- EventBridge rules with JSON event patterns are AWS-specific
- Schedule expressions (cron and rate) are AWS EventBridge native; GCP and Azure use different scheduler services
- The target ARN format and role requirements vary by target service (Lambda, SQS, SNS, etc.)
- Per-target dead-letter queues exist in the AWS EventBridge API but are not exposed by `EventBridgeRule` (see the Target field list above)
