# PipesPipe — Creating and Managing Event Integration Pipes

The `PipesPipe` resource represents an individual Amazon EventBridge Pipe, enabling point-to-point event integration from a source to a target with optional filtering, enrichment, and transformation. This guide covers all configuration fields, governance semantics, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `PipesConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the PipesPipe resource is deleted: `"retain"` (safe, default) or `"delete"` |

### Pipe Basics

| Field | Type | Required | Purpose |
|---|---|---|---|
| `source` | string | Yes | ARN or URL of the event source (SQS, Kinesis, DynamoDB, MSK, Kafka, etc.) — **immutable after creation** |
| `target` | string | Yes | ARN of the event destination (Lambda, Step Functions, SQS, Kinesis, ECS, etc.) |
| `description` | string | Optional | Human-readable description of the pipe's purpose |

### Naming and Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `nameOverride` | string | `""` | Override the naming template; if set, pipe name is exactly this value (must match AWS naming rules) |
| `tags` | map | `{}` | AWS tags; merged with governance mandatory and default tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Desired State (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `desiredState` | string | `""` | `""` (empty) = governed by cascade; `running` = pipe actively processes events; `stopped` = pipe is paused |

### IAM Execution Role

The pipe's execution role grants EventBridge Pipes permissions to read from the source and write to the target.

| Field | Type | Mutually Exclusive | Purpose |
|---|---|---|---|
| `roleARN` | string | with `roleRef` | Direct ARN of the IAM role (e.g., `arn:aws:iam::123456789012:role/pipe-exec-role`) |
| `roleRef` | object | with `roleARN` | Reference to an IAM Role CR in the same namespace; resolved to ARN at reconciliation time |

Use `roleARN` for existing roles; use `roleRef` to reference an `AWSIAMRole` CR managed by another team.

**Example — Direct ARN:**

```yaml
spec:
  roleARN: arn:aws:iam::123456789012:role/pipe-execution-role
```

**Example — CR reference:**

```yaml
spec:
  roleRef:
    from:
      name: pipe-execution-role  # Must exist in same namespace
```

## Source Configuration

### Source Basics

| Field | Type | Immutable | Purpose |
|---|---|---|---|
| `source` | string | Yes | Source ARN or URL. Examples: `arn:aws:sqs:us-east-1:123456789012:events-queue` (SQS), `arn:aws:kinesis:us-east-1:123456789012:stream/event-stream` (Kinesis), `arn:aws:dynamodb:us-east-1:123456789012:table/events/stream/2026-01-01T00:00:00.000` (DynamoDB) |

**Important:** The `source` field is immutable. To change the source, delete the pipe and create a new one.

### Supported Source Types

| Source Type | ARN Format | Batch Polling | Notes |
|---|---|---|---|
| SQS Queue | `arn:aws:sqs:<region>:<account>:<queue-name>` | Yes | Standard or FIFO queues; FIFO respects message group IDs |
| Kinesis Stream | `arn:aws:kinesis:<region>:<account>:stream/<stream-name>` | Yes | Supports starting position (TRIM_HORIZON, LATEST, AT_TIMESTAMP) and batch windowing |
| DynamoDB Stream | `arn:aws:dynamodb:<region>:<account>:table/<table-name>/stream/<timestamp>` | Yes | Supports batch settings and dead-letter configuration |
| MSK Cluster | `arn:aws:kafka:<region>:<account>:cluster/<cluster-name>/<cluster-id>` | Yes | Managed Streaming for Kafka; requires credentials from Secrets Manager |
| Self-Managed Kafka | `smk://<bootstrap-servers>` | Yes | URL format; requires VPC and credential configuration |
| ActiveMQ | `arn:aws:mq:<region>:<account>:broker:<broker-name>:<broker-id>` | Yes | Requires queue name and credentials |
| RabbitMQ | `arn:aws:mq:<region>:<account>:broker:<broker-name>:<broker-id>` | Yes | Requires queue name, virtual host, and credentials |

### Source Parameters (`sourceParameters`)

Each source type has optional configuration:

```yaml
spec:
  sourceParameters:
    filterCriteria:                       # Optional: filter events
      filters:
        - pattern: '{"source": ["orders"]}'
    
    sqsQueueParameters:                   # For SQS source
      batchSize: 10
      maximumBatchingWindowInSeconds: 5
    
    kinesisStreamParameters:              # For Kinesis source
      batchSize: 100
      maximumBatchingWindowInSeconds: 5
      startingPosition: TRIM_HORIZON      # TRIM_HORIZON, LATEST, or AT_TIMESTAMP
      startingPositionTimestamp: "2026-01-01T00:00:00Z"  # For AT_TIMESTAMP
      deadLetterConfig:
        arn: arn:aws:sqs:us-east-1:123456789012:pipe-dlq
      maximumRecordAgeInSeconds: 3600
      maximumRetryAttempts: 2
      onPartialBatchItemFailure: AUTOMATIC_BISECT
      parallelizationFactor: 10
```

For a complete list of source parameter options, see [PipesPipe Spec](https://github.com/kropath/kropath-core/blob/main/docs/specs/aws/aws-pipes-02-pipespipe.md#schema-surface).

## Filtering

Filter events before they reach the target using EventBridge event patterns:

```yaml
spec:
  sourceParameters:
    filterCriteria:
      filters:
        - pattern: '{"detail": {"status": ["completed", "failed"]}}'
```

**Event Pattern Syntax:**

Event patterns use JSON matching. Common patterns:

```json
# Match events from a specific source
{"source": ["orders"]}

# Match events with specific detail values
{"detail": {"status": ["completed"]}}

# Match numeric comparisons
{"detail": {"amount": [{"numeric": [">", 100]}]}}

# Combine conditions (AND)
{"detail": {"status": ["completed"], "priority": ["high"]}}
```

For full EventBridge pattern syntax, see [AWS EventBridge Event Patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html).

## Enrichment

Optionally call an external service (Lambda, Step Functions, API Gateway, API Destination) to enrich events mid-pipeline:

```yaml
spec:
  enrichment: arn:aws:lambda:us-east-1:123456789012:function:enrich-order
  enrichmentParameters:
    inputTemplate: '{"orderId": <$.detail.orderId>, "timestamp": <$.time>}'
    httpParameters:                       # For API Gateway / API Destination
      headerParameters:
        Authorization: Bearer token-123
      queryStringParameters:
        include_context: "true"
```

The enrichment service receives the transformed input and its response is merged with the original event before being sent to the target.

**Enrichment Types:**

| Type | ARN Format | Notes |
|---|---|---|
| Lambda Function | `arn:aws:lambda:<region>:<account>:function:<function-name>` | Synchronous invocation; response merged with original event |
| Step Functions State Machine | `arn:aws:states:<region>:<account>:stateMachine:<state-machine-name>` | Returns result as enrichment data |
| API Gateway | URL | HTTP POST request; response merged |
| API Destination | ARN | Custom HTTP endpoint created via EventBridge |

## Target Configuration

### Target Basics

| Field | Type | Required | Purpose |
|---|---|---|---|
| `target` | string | Yes | Target ARN (destination for events) |
| `targetParameters` | object | Optional | Target-specific configuration (batch size, input transformation, invocation options) |

### Supported Target Types

| Target Type | ARN Format | Notes |
|---|---|---|
| Lambda Function | `arn:aws:lambda:<region>:<account>:function:<function-name>` | Supports async and request-response invocation |
| Step Functions State Machine | `arn:aws:states:<region>:<account>:stateMachine:<state-machine-name>` | Start execution; supports synchronous mode |
| SQS Queue | `arn:aws:sqs:<region>:<account>:<queue-name>` | Send message to queue |
| Kinesis Stream | `arn:aws:kinesis:<region>:<account>:stream/<stream-name>` | Put record to stream with partition key |
| ECS Cluster Task | `arn:aws:ecs:<region>:<account>:cluster/<cluster-name>` | Launch ECS task with overrides |
| Batch Job Queue | `arn:aws:batch:<region>:<account>:job-queue/<queue-name>` | Submit Batch job |
| EventBridge Event Bus | `arn:aws:events:<region>:<account>:event-bus/<bus-name>` | Send event to another event bus |
| API Gateway | URL | HTTP POST to API endpoint |
| API Destination | ARN | Custom HTTP endpoint (created via EventBridge) |
| CloudWatch Logs | `arn:aws:logs:<region>:<account>:log-group:<log-group-name>` | Write log stream entry |
| Redshift Data | `arn:aws:redshift:<region>:<account>:cluster:<cluster-name>` | Execute SQL query |
| SageMaker Pipeline | `arn:aws:sagemaker:<region>:<account>:pipeline:<pipeline-name>` | Start pipeline execution |

### Target Parameters (`targetParameters`)

```yaml
spec:
  targetParameters:
    inputTemplate: '{"id": <$.detail.id>, "timestamp": <$.time>}'  # Transform before send
    
    lambdaFunctionParameters:
      invocationType: FIRE_AND_FORGET       # FIRE_AND_FORGET or REQUEST_RESPONSE
    
    sqsQueueParameters:
      messageGroupID: <$.detail.orderId>    # FIFO message group
      messageDeduplicationID: unique-id-123 # FIFO dedup ID
    
    ecsTaskParameters:
      taskDefinitionARN: arn:aws:ecs:us-east-1:123456789012:task-definition/my-task:1
      launchType: FARGATE
      networkConfiguration:
        awsVPCConfiguration:
          subnets:
            - subnet-12345678
          securityGroups:
            - sg-12345678
      taskCount: 2
```

## Input Transformation

Transform event data before sending to enrichment or target using JSONPath:

```yaml
spec:
  sourceParameters:
    filterCriteria:
      filters:
        - pattern: '{"detail": {"status": ["order"]}}'

  enrichmentParameters:
    inputTemplate: >-
      {
        "orderId": <$.detail.orderId>,
        "customerId": <$.detail.customerId>,
        "amount": <$.detail.amount>
      }
```

**JSONPath Syntax:**

- `<$.detail.orderId>` — Extract `orderId` from event detail
- `<$.time>` — Extract time from root event
- `<$.metadata.source>` — Nested path extraction
- `"literal-string"` — Literal values (keep quotes)

## Naming Conventions

Pipe names are derived from the `nameOverride` field or the governance cascade's `namingTemplate`.

### Default Naming

With `namingTemplate: "{namespace}-{name}"`:

```yaml
metadata:
  namespace: events-prod
  name: order-processor
# Result: events-prod-order-processor
```

### Custom Naming with Template Tokens

```yaml
spec:
  configRef: high-throughput  # Profile has namingTemplate: "realtime-{namespace}-{name}"
# Result: realtime-events-prod-order-processor
```

### Override with `nameOverride`

```yaml
spec:
  nameOverride: my-custom-pipe-name
# Result: my-custom-pipe-name (bypasses template)
```

**AWS Constraints:**
- 1–64 characters
- `A-Za-z0-9._-` only
- Case-sensitive
- Immutable after creation (cannot be changed)

## Deletion Policy

Control what happens to the AWS pipe when the Kubernetes resource is deleted:

| Policy | Behavior |
|---|---|
| `"retain"` (default) | AWS pipe is preserved; only Kubernetes CR is deleted (safe) |
| `"delete"` | AWS pipe is deleted when Kubernetes CR is deleted |

**Recommendation:** Use `"retain"` for production; only use `"delete"` for ephemeral test pipes.

```yaml
spec:
  deletionPolicy: retain     # Safe; preserves AWS pipe
```

## Status Fields

After reconciliation, the pipe CR includes status information:

```yaml
status:
  resourceName: events-prod-order-processor  # The actual pipe name in AWS
  namingStatus: valid                        # "valid" or "invalid-unresolved-tokens"
  predictedArn: arn:aws:pipes:us-east-1:123456789012:pipe/events-prod-order-processor
  currentState: RUNNING                      # RUNNING, STOPPED, CREATING, etc.
  creationTime: "2026-01-15T10:30:00Z"
  lastModifiedTime: "2026-01-15T11:00:00Z"
  stateReason: Pipe is running successfully
  conditions:
    - type: Ready
      status: "True"
      reason: PipeReady
      message: Pipe has been created and is ready
```

## Complete Examples

### Example 1: Simple SQS to Lambda Pipe

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesPipe
metadata:
  name: order-processing
  namespace: events
spec:
  configRef: production
  source: arn:aws:sqs:us-east-1:123456789012:order-queue
  target: arn:aws:lambda:us-east-1:123456789012:function:process-order
  roleARN: arn:aws:iam::123456789012:role/pipe-execution-role
  desiredState: running
  tags:
    environment: production
    team: payments
  syncedLabels:
    team: payments
```

### Example 2: Kinesis to Step Functions with Filtering and Enrichment

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesPipe
metadata:
  name: analytics-ingestion
  namespace: data-platform
spec:
  configRef: high-throughput
  description: Enriches and routes analytics events to Step Functions for processing
  
  source: arn:aws:kinesis:us-east-1:123456789012:stream/analytics-events
  sourceParameters:
    kinesisStreamParameters:
      batchSize: 100
      maximumBatchingWindowInSeconds: 5
      startingPosition: LATEST
      parallelizationFactor: 10
    filterCriteria:
      filters:
        - pattern: '{"detail": {"eventType": ["purchase", "view"]}}'
  
  enrichment: arn:aws:lambda:us-east-1:123456789012:function:enrich-analytics
  enrichmentParameters:
    inputTemplate: '{"eventId": <$.eventId>, "timestamp": <$.timestamp>, "userId": <$.userId>}'
  
  target: arn:aws:states:us-east-1:123456789012:stateMachine:ProcessAnalytics
  targetParameters:
    inputTemplate: '{"event": <$>, "enrichmentResult": <$.enrichmentResult>}'
    stepFunctionStateMachineParameters:
      invocationType: FIRE_AND_FORGET
  
  roleARN: arn:aws:iam::123456789012:role/analytics-pipe-role
  
  desiredState: running
  tags:
    team: data-platform
    cost-centre: analytics
  syncedLabels:
    team: data-platform
    sla: high-priority
```

### Example 3: DynamoDB Stream to SQS with Dead-Letter Queue

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesPipe
metadata:
  name: dynamo-to-queue
  namespace: event-bridge
spec:
  configRef: general-policy
  description: Captures DynamoDB stream events and sends to SQS for async processing
  
  source: arn:aws:dynamodb:us-east-1:123456789012:table/Orders/stream/2026-01-01T00:00:00.000
  sourceParameters:
    dynamoDBStreamParameters:
      batchSize: 25
      startingPosition: LATEST
      maximumRetryAttempts: 2
      deadLetterConfig:
        arn: arn:aws:sqs:us-east-1:123456789012:dynamo-dlq
  
  target: arn:aws:sqs:us-east-1:123456789012:order-events
  targetParameters:
    sqsQueueParameters:
      messageGroupID: <$.detail.orderId>          # For FIFO queue
      messageDeduplicationID: <$.eventID>
    inputTemplate: '{"source": "dynamodb", "record": <$>, "timestamp": <$.eventTimestamp>}'
  
  roleARN: arn:aws:iam::123456789012:role/dynamodb-pipe-role
  
  nameOverride: dynamodb-orders-queue
  deletionPolicy: retain
  tags:
    application: order-service
  syncedLabels:
    application: order-service
```

## Prerequisites and Setup

Before creating pipes, ensure:

1. **Cluster has kropath installed** with AWS provider support
2. **PipesConfig profile exists** — typically `general-policy` (created automatically) or a custom profile for your use case
3. **Source resource is provisioned** — e.g., SQS queue, Kinesis stream, DynamoDB table (managed by their respective families or pre-existing in AWS)
4. **Target resource is provisioned** — e.g., Lambda function, SQS queue, Step Functions state machine
5. **IAM execution role exists** — The role grants EventBridge Pipes permissions to read from source and write to target. See [AWS EventBridge Pipes IAM Permissions](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-permissions.html) for role policies.

## Source Immutability Constraint

**Important:** Once a pipe is created, the `source` field cannot be changed. To use a different source:

1. Delete the `PipesPipe` CR (optionally retain the AWS pipe with `deletionPolicy: retain`)
2. Create a new `PipesPipe` CR with the new source

The cloud pipe name (derived from `nameOverride` or the naming template) is also immutable after creation.

## Governance Cascade

The `desiredState` field uses a governance cascade:

1. **Mandatory** — If `PipesConfig.mandatory.desiredState` is set, use it (enforced)
2. **Instance** — If `spec.desiredState` is explicitly set on the CR, use it (if allowed)
3. **Defaults** — If both above are empty, use `PipesConfig.defaults.desiredState`
4. **Built-in default** — If all tiers are empty, pipe defaults to `running`

**Example:**

```
PipesConfig.production:
  mandatory.desiredState: "running"   # Mandatory enforcement

PipesPipe.spec:
  configRef: production
  desiredState: "stopped"             # Instance tries to set stopped

Result: Pipe will be RUNNING (mandatory wins)
```

## Tag and Label Merging

Tags, syncedLabels, and syncedAnnotations are merged across governance tiers:

1. **Mandatory tags** from PipesConfig (highest priority)
2. **Instance tags** from PipesPipe.spec
3. **Default tags** from PipesConfig (lowest priority)

Final tags = mandatory + instance + defaults (with mandatory winning on key conflict)

**Example:**

```yaml
PipesConfig.production:
  mandatory.tags:
    environment: production
  defaults.tags:
    cost-centre: platform

PipesPipe.spec:
  tags:
    application: order-service

Result:
  Final tags: {environment: production, cost-centre: platform, application: order-service}
```

SyncedLabels are applied as both Kubernetes labels (prefixed `aws.kropath.run/`) and cloud tags.

## Troubleshooting

### Pipe Creation Fails

Check `status.conditions` for detailed error messages. Common issues:

- **Source ARN invalid** — Verify the source resource exists and the ARN is correct
- **Target ARN invalid** — Verify the target resource exists and is accessible
- **IAM role missing or insufficient permissions** — Verify the role has policies granting access to source and target
- **Source immutability** — If changing the source, delete and recreate the pipe

### Naming Status: "invalid-unresolved-tokens"

The naming template contains unrecognized tokens. Verify:

- Template uses valid tokens: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`
- Tag tokens (e.g., `{tag.environment}`) reference tags that are actually set

### Pipe Not Processing Events

- Verify `status.currentState: RUNNING` (not STOPPED)
- Check source parameters (batch size, starting position) are correct
- Verify filter criteria (if set) are matching your events
- Check target permissions — confirm the IAM role allows writing to the target

## Related Topics

- [PipesConfig](pipesconfig.md) — Governance profiles and cascade
- [EventBridge Pipes in AWS Documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-ebpipes.html) — Full AWS reference
- [ADR-010 Governance Cascade](../../adrs/010-consolidated-governance-cascade.md) — Detailed governance specification
- [ADR-015 Governance Fields](../../adrs/015-governance-fields-and-cascades.md) — Complete governance model
