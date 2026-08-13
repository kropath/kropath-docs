# LambdaAlias — Function Versioning and Traffic Routing

The `LambdaAlias` resource creates named aliases for Lambda function versions and enables sophisticated traffic routing patterns. Aliases allow stable, long-lived endpoints that can point to different versions without changing client code.

## Overview

AWS Lambda functions have two types of identifiers:

- **Latest** — Always points to `$LATEST`, the unpublished working version
- **Version numbers** — Immutable snapshots (1, 2, 3, ...) published by the function
- **Aliases** — Mutable pointers to versions with optional weighted traffic routing

Aliases enable:
- **Blue-green deployments** — Route 100% traffic to the new version, then switch aliases
- **Canary deployments** — Route 5% to new version, 95% to stable, gradually shift traffic
- **Safe rollbacks** — Quickly switch back to a previous version
- **Environment-specific endpoints** — Prod, staging, dev aliases all point to appropriate versions

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the alias name directly |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS alias) or `"delete"` (remove alias) |

### Target Function

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionRef` | string | required | Local `LambdaFunction` CR name; resolved to function ARN via cross-resource reference |

### Versioning

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionVersion` | string | required | The function version (e.g., `"1"`, `"2"`) or `"$LATEST"` |

### Traffic Routing

| Field | Type | Default | Purpose |
|---|---|---|---|
| `routingConfig.additionalVersionWeights` | map | `{}` | Weighted traffic distribution; key = version, value = weight (0.0–1.0) |

Example: `{"2": 0.1}` routes 10% to version 2, 90% to `functionVersion`.

### Provisioned Concurrency

| Field | Type | Default | Purpose |
|---|---|---|---|
| `provisionedConcurrentExecutions` | integer | `0` | Provisioned concurrency: `0` = not set, `>0` = reserved concurrent invocations for warm starts |

### Async Invocation

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionEventInvokeConfig.maximumEventAgeInSeconds` | integer | `0` | Discard async events older than this (60–21600); `0` = not set |
| `functionEventInvokeConfig.maximumRetryAttempts` | integer | `-1` | Max async retries (0–2); `-1` = AWS default (2) |
| `functionEventInvokeConfig.destinationConfig.onSuccess.destination` | string | `""` | ARN for successful async invocations |
| `functionEventInvokeConfig.destinationConfig.onFailure.destination` | string | `""` | ARN for failed async invocations |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | Kubernetes metadata only (AWS Lambda aliases do not support cloud tags) |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Important:** Aliases do NOT support cloud tags (AWS doesn't tag aliases). `syncedLabels` and `syncedAnnotations` only apply to Kubernetes.

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `aliasArn` | string | ARN of the alias: `arn:aws:lambda:region:account:function:function-name:alias:alias-name` |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

## Naming Convention

**Alias names are not generated from templates.** Either provide `nameOverride` or the Kubernetes resource name is used as the alias name. The resource name becomes the alias name directly.

Example:
- Kubernetes resource name: `staging`
- Alias name in AWS: `staging`
- Alias ARN: `arn:aws:lambda:us-east-1:123456789012:function:my-function:alias:staging`

## Complete Examples

### Blue-Green Deployment

Create stable `prod` and `staging` aliases for blue-green deployments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: prod
  namespace: functions
spec:
  configRef: general-policy
  functionRef: my-api-handler
  functionVersion: "5"  # Current stable version
  deletionPolicy: retain
---
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: staging
  namespace: functions
spec:
  configRef: general-policy
  functionRef: my-api-handler
  functionVersion: "6"  # New version under test
  deletionPolicy: retain
```

Deployment flow:
1. Publish version 6 of the function
2. Create staging alias pointing to version 6
3. Test staging alias
4. Update prod alias to point to version 6
5. All clients using prod alias now use version 6 instantly

### Canary Deployment

Gradually shift traffic from a stable version to a new version:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: canary
  namespace: functions
spec:
  configRef: general-policy
  functionRef: api-service
  functionVersion: "10"  # Stable version (90% traffic)
  routingConfig:
    additionalVersionWeights:
      "11": 0.1  # New version (10% traffic)
  deletionPolicy: retain
```

Deployment flow:
1. Publish version 11 with changes
2. Create alias with 10% weight on version 11
3. Monitor error rates and latency
4. Gradually increase weight: `"11": 0.25`, `"11": 0.5`, etc.
5. When confident, set `functionVersion: "11"` and clear routing config
6. Delete the canary alias and create a new stable one

### Provisioned Concurrency for Low Latency

Reserve concurrent capacity to eliminate cold starts:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: api-prod
  namespace: functions
spec:
  configRef: general-policy
  functionRef: http-api
  functionVersion: "7"
  provisionedConcurrentExecutions: 50
  deletionPolicy: retain
```

Result:
- 50 concurrent invocations always warm and ready
- No cold-start latency for the first 50 simultaneous requests
- Cost per provisioned concurrency (higher but guaranteed latency)

### Async Function with DLQ

Configure async invocation with error handling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: async-processor
  namespace: functions
spec:
  configRef: general-policy
  functionRef: async-handler
  functionVersion: "3"
  functionEventInvokeConfig:
    maximumEventAgeInSeconds: 1800
    maximumRetryAttempts: 1
    destinationConfig:
      onFailure:
        destination: "arn:aws:sqs:us-east-1:123456789012:dlq"
  deletionPolicy: retain
```

Result:
- Async events processed with 1 retry
- Failed events sent to SQS DLQ
- Events older than 30 minutes discarded

### Development Environment Alias

Create a development-specific alias with permissive settings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: dev
  namespace: functions
spec:
  configRef: dev-policy  # Permissive governance profile
  functionRef: my-api
  functionVersion: "$LATEST"  # Always points to latest code
  deletionPolicy: delete  # Clean up on resource deletion
```

Result:
- Alias points to `$LATEST` for continuous development
- Developers can call `function-name:dev` to use latest code
- Alias deleted when Kubernetes resource is deleted

## Governance

Aliases inherit tags, syncedLabels, and syncedAnnotations from the `LambdaConfig` governance profile via `configRef`. 

**Important tag behavior:** AWS Lambda aliases do NOT support cloud tags. Only Kubernetes labels and annotations are supported. Tag fields in the spec are accepted but not applied to AWS.

## Key Behaviors

### Immutable Function Version

Once an alias is created pointing to version X, the `functionVersion` field cannot be changed via Kubernetes update. To switch versions, use the `routingConfig.additionalVersionWeights` for canary deployments or re-create the alias.

**Note:** This is a safety mechanism to prevent accidental version switches that could break production traffic.

### Weighted Traffic Routing

When `additionalVersionWeights` is set, Lambda distributes invocations probabilistically:

```yaml
functionVersion: "10"
routingConfig:
  additionalVersionWeights:
    "11": 0.1  # 10% to version 11, 90% to version 10
```

Each invocation is randomly routed:
- 90% go to version 10
- 10% go to version 11

This is not per-shard or per-container; it's per-invocation probabilistic routing.

### Provisioned Concurrency Costs

Provisioned concurrency costs independently of invocations. Ensure the reserved capacity matches actual load to avoid overprovisioning.

### Function Must Exist

The referenced `LambdaFunction` CR must exist and have a published version corresponding to `functionVersion`. Aliases cannot point to `$LATEST` unless explicitly specified.

## Troubleshooting

### Alias Not Resolving to Function

Verify the `functionRef` resolves to a valid function. The function must exist in the same namespace.

### "Invalid function version"

Ensure the version specified in `functionVersion` has been published. Use `LambdaVersion` resources to publish versions if they don't exist.

### Weighted Routing Not Working

Ensure both versions exist and are valid. Weights must sum to ≤ 1.0 (fractional weights are okay).

### Provisioned Concurrency Not Initializing

Provisioned concurrency initialization can take 5–10 minutes. Check AWS CloudWatch for initialization status.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for alias and versioning design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/aliases.html
