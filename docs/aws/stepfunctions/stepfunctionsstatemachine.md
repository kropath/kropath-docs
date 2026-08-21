# StepFunctionsStateMachine — User Guide

`StepFunctionsStateMachine` is a Kubernetes resource that provisions AWS Step Functions state machines for serverless workflow orchestration.

## Overview

Use state machines to coordinate complex workflows across AWS services. State machines execute a series of steps defined in Amazon States Language (ASL), a JSON-based declarative workflow definition. kropath supports two types of state machines:

- **STANDARD** — Durable execution with full execution history; ideal for long-running workflows; billed per state transition
- **EXPRESS** — High-throughput execution optimized for short-duration workflows (max 5 minutes); billed per execution

## Prerequisites

- A Kubernetes cluster running kropath-aws
- A `StepFunctionsConfig` resource in your namespace (or in `kro-system` for fallback to `general-policy`)
- An AWS IAM role ARN for state machine execution (if your workflow invokes AWS services)
- A CloudWatch Logs log group ARN (if you enable execution logging)

## Basic Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: order-processor
  namespace: workflows-prod
spec:
  # Workflow definition in Amazon States Language (ASL)
  definition: |
    {
      "Comment": "Process customer orders",
      "StartAt": "ValidateOrder",
      "States": {
        "ValidateOrder": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "validate-order",
            "Payload.$": "$"
          },
          "Next": "ProcessPayment"
        },
        "ProcessPayment": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "process-payment",
            "Payload.$": "$"
          },
          "End": true
        }
      }
    }

  # Execution type: STANDARD (durable) or EXPRESS (high-throughput)
  type: STANDARD

  # IAM role for state machine execution
  roleArn: "arn:aws:iam::123456789012:role/step-functions-role"

  # Optional: execution logging configuration
  loggingLevel: "ERROR"
  logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/order-processor"

  # Optional: enable AWS X-Ray tracing for debugging
  tracingEnabled: true

  # Governance profile selection (defaults to "general-policy" if not specified)
  configRef: "general-policy"

  # Optional: custom tags (merged with governance profile tags)
  tags:
    application: order-service
    cost-center: engineering

  # Optional: Kubernetes labels synced to both K8s and cloud tags
  syncedLabels:
    team: payments

  # Optional: Kubernetes annotations
  syncedAnnotations:
    runbook: "https://wiki.example.com/order-processor"

  # Optional: deletion policy (retain | delete; defaults to retain)
  deletionPolicy: retain

  # Optional: override the computed resource name
  nameOverride: "custom-order-processor"
```

After applying this resource, inspect the status:

```bash
kubectl get stepfunctionsstatemachine -n workflows-prod
kubectl describe stepfunctionsstatemachine order-processor -n workflows-prod
```

You'll see:
- `status.resourceName` — The computed cloud resource name
- `status.predictedArn` — The expected AWS ARN
- `status.stateMachineArn` — The actual AWS ARN (populated after provisioning)
- `status.namingStatus` — Whether the naming template was valid

## Resource Fields

### `spec.definition` (required)

The state machine workflow definition in Amazon States Language (ASL), formatted as a JSON string.

**Validation:** The definition is validated by AWS Step Functions at creation time. kropath passes it through to AWS; ASL syntax errors will be reported by AWS.

**Example:**
```yaml
definition: |
  {
    "StartAt": "Hello",
    "States": {
      "Hello": {
        "Type": "Pass",
        "Result": "Hello World!",
        "End": true
      }
    }
  }
```

### `spec.type` (optional, default: STANDARD)

Execution type: `STANDARD` or `EXPRESS`.

**STANDARD:**
- Durable, long-running workflows
- Full execution history
- Max execution time: 1 year
- Pricing: per state transition (lower cost for infrequent executions)

**EXPRESS:**
- High-throughput, short-duration workflows
- Max execution time: 5 minutes
- Pricing: per execution (lower cost for frequent executions)
- Useful for high-volume event processing

**Important:** The type is immutable after creation. Choose carefully:

```yaml
type: EXPRESS  # High-throughput processing
```

### `spec.roleArn` (optional)

AWS IAM role ARN that Step Functions assumes during execution.

Required if your workflow invokes AWS services (Lambda, SNS, SQS, DynamoDB, etc.).

**Example:**
```yaml
roleArn: "arn:aws:iam::123456789012:role/step-functions-execution-role"
```

The role must have permissions for every AWS service your workflow invokes. For example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:validate-order"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:order-notifications"
    }
  ]
}
```

### `spec.loggingLevel` (optional)

Execution logging level: `ALL`, `ERROR`, `FATAL`, or `OFF`.

- `ALL` — Log all events (state entry, exit, input, output)
- `ERROR` — Log only error events
- `FATAL` — Log only fatal errors
- `OFF` — No execution logging (default; AWS default behavior)

When logging is enabled, you must specify `spec.logDestinationArn`.

**Example:**
```yaml
loggingLevel: "ERROR"
logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/order-processor"
```

If your `StepFunctionsConfig` profile specifies a mandatory logging level, that takes precedence over your instance value.

### `spec.logDestinationArn` (optional)

CloudWatch Logs log group ARN where execution logs are written.

Required when `loggingLevel` is not `OFF`.

**Example:**
```yaml
logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/order-processor"
```

Before creating the state machine, ensure the log group exists:

```bash
aws logs create-log-group --log-group-name /aws/states/order-processor
```

### `spec.includeExecutionData` (optional)

Whether to include execution input and output in CloudWatch Logs.

- `true` — Include input/output (increases log volume, may expose sensitive data)
- `false` — Exclude input/output (default)

**Example:**
```yaml
loggingLevel: "ALL"
includeExecutionData: false  # Don't log execution data due to PII
logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/order-processor"
```

### `spec.tracingEnabled` (optional)

Whether AWS X-Ray tracing is enabled for state machine executions.

- `true` — Enable X-Ray tracing for debugging and performance analysis
- `false` — Disable tracing (default; reduces cost)

**Example:**
```yaml
tracingEnabled: true
```

When tracing is enabled, each execution generates X-Ray traces visible in the AWS X-Ray console.

### `spec.configRef` (optional, default: "general-policy")

Reference to a `StepFunctionsConfig` governance profile.

The profile defines:
- Mandatory logging/tracing requirements
- Naming conventions
- Default tags and labels
- Other governance policies

**Example:**
```yaml
configRef: "pci"  # Use the PCI-DSS compliance profile
```

If the named profile doesn't exist, the system falls back to `general-policy`.

### `spec.tags` (optional)

Custom tags applied to the AWS state machine resource.

Merged with governance profile tags. Mandatory tags from the profile cannot be overridden.

**Example:**
```yaml
tags:
  application: order-service
  cost-center: engineering
```

### `spec.syncedLabels` (optional)

Kubernetes labels synced to both the Kubernetes resource and cloud tags.

These labels appear:
- In Kubernetes `metadata.labels` (prefixed with `aws.kropath.run/`)
- In AWS resource tags (via `allCloudMetadata`)

**Example:**
```yaml
syncedLabels:
  team: payments
  data-class: sensitive
```

Result:
- Kubernetes: `aws.kropath.run/team: payments`, `aws.kropath.run/data-class: sensitive`
- AWS tags: `team: payments`, `data-class: sensitive`

### `spec.syncedAnnotations` (optional)

Kubernetes annotations synced to the Kubernetes resource metadata.

**Example:**
```yaml
syncedAnnotations:
  runbook: "https://wiki.example.com/order-processor"
  alerts: "pd-oncall-engineering"
```

### `spec.deletionPolicy` (optional, default: "retain")

Deletion policy when the Kubernetes resource is deleted.

- `retain` — Keep the AWS state machine (default, safer)
- `delete` — Delete the AWS state machine

**Example:**
```yaml
deletionPolicy: delete  # Clean up when resource is deleted
```

### `spec.nameOverride` (optional)

Bypass the computed naming template and use this exact name for the AWS resource.

If omitted, the resource name is computed from `spec.configRef` and the naming template.

**Example:**
```yaml
nameOverride: "my-custom-sm"
```

Without this field, the default naming template `{namespace}-{name}` would produce `workflows-prod-order-processor`.

## Status Fields

After the state machine is created, inspect the status:

```bash
kubectl get stepfunctionsstatemachine order-processor -n workflows-prod -o yaml
```

**Common status fields:**

- `status.resourceName` — The computed AWS resource name (derived from naming template or `nameOverride`)
- `status.namingStatus` — `valid` or `invalid-unresolved-tokens` (if naming template has unresolved placeholders)
- `status.predictedArn` — Expected AWS ARN format (predicted before provisioning)
- `status.stateMachineArn` — Actual AWS ARN after provisioning (e.g., `arn:aws:states:us-east-1:123456789012:stateMachine:workflows-prod-order-processor`)
- `status.conditions` — Kubernetes standard conditions (ReconcileSucceeded, ReconcileFailed, etc.)

## Naming Conventions

By default, state machine names follow the pattern `{namespace}-{name}` derived from your resource's namespace and metadata name.

Example:
- Namespace: `workflows-prod`
- Resource name: `order-processor`
- Computed name: `workflows-prod-order-processor`

AWS requires state machine names to:
- Use characters `[a-zA-Z0-9\-_]+`
- Maximum 80 characters
- Not contain whitespace

If you need a custom naming pattern (for example, environment-specific prefixes or tag-based tokens), update the `StepFunctionsConfig` profile's `spec.defaults.namingTemplate` or `spec.mandatory.namingTemplate`.

## Examples

### Simple Pass State (No AWS Services)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: hello-world
  namespace: default
spec:
  definition: |
    {
      "StartAt": "SayHello",
      "States": {
        "SayHello": {
          "Type": "Pass",
          "Result": "Hello from Step Functions!",
          "End": true
        }
      }
    }
  type: STANDARD
  deletionPolicy: delete
```

### Lambda Invocation with Error Handling

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: lambda-processor
  namespace: workflows-prod
spec:
  definition: |
    {
      "StartAt": "ProcessData",
      "States": {
        "ProcessData": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "data-processor",
            "Payload.$": "$"
          },
          "Retry": [
            {
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "Next": "HandleError"
            }
          ],
          "End": true
        },
        "HandleError": {
          "Type": "Task",
          "Resource": "arn:aws:sns:us-east-1:123456789012:error-notifications",
          "End": true
        }
      }
    }
  type: STANDARD
  roleArn: "arn:aws:iam::123456789012:role/step-functions-role"
  loggingLevel: "ERROR"
  logDestinationArn: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/lambda-processor"
  tracingEnabled: true
  tags:
    application: data-processing
  configRef: "general-policy"
```

### Express State Machine (High-Throughput)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: event-processor
  namespace: events
spec:
  definition: |
    {
      "StartAt": "Process",
      "States": {
        "Process": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-event",
          "End": true
        }
      }
    }
  type: EXPRESS  # High-throughput for event processing
  roleArn: "arn:aws:iam::123456789012:role/step-functions-role"
  tracingEnabled: false  # Disable for cost optimization
```

## Troubleshooting

**"My state machine isn't being created"**
- Check `kubectl get stepfunctionsstatemachine -n <namespace>` for status
- View detailed events: `kubectl describe stepfunctionsstatemachine <name> -n <namespace>`
- Ensure the `StepFunctionsConfig` profile exists (or `general-policy` fallback is in place)

**"The state machine creation fails with 'definition validation failed'"**
- Your ASL definition has syntax errors
- Use the [AWS Step Functions console](https://console.aws.amazon.com/stepfunctions) to validate your definition
- Correct the JSON and re-apply the resource

**"Execution logging isn't working"**
- Verify `loggingLevel` is not `OFF`
- Verify `logDestinationArn` is a valid CloudWatch Logs log group ARN
- Ensure the IAM role has CloudWatch Logs write permissions
- Check the log group exists: `aws logs describe-log-groups --log-group-name-prefix /aws/states`

**"My governance profile's mandatory fields aren't being enforced"**
- Verify the `StepFunctionsConfig` exists and has `status.effectiveConfig` populated
- Ensure your `configRef` points to the correct profile name
- Check that the profile has `mandatory.loggingLevel` (not `defaults.loggingLevel`) if you want to enforce it

## See Also

- [StepFunctionsConfig Governance Reference](./stepfunctionsconfig.md)
- [StepFunctionsActivity User Guide](./stepfunctionsactivity.md)
- [Getting Started](./getting-started.md)
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [Amazon States Language Reference](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html)
