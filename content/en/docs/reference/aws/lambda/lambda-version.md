---
title: LambdaVersion — Immutable Function Snapshots
description: "The `LambdaVersion` resource publishes immutable versions of Lambda functions."
doc_type: reference
---
# LambdaVersion — Immutable Function Snapshots

The `LambdaVersion` resource publishes immutable versions of Lambda functions. A version captures the exact code, configuration, and dependencies at a point in time, enabling safe rollbacks and canary deployments.

## Overview

Lambda function lifecycle has two states:

- **`$LATEST`** — The working version; mutable and unpublished
- **Numbered versions** (1, 2, 3, ...) — Immutable snapshots published from `$LATEST`

Versions enable:
- **Rollback to known-good state** — If version 5 breaks, revert to version 4
- **Gradual deployment** — Use aliases to route traffic to different versions
- **Audit trail** — Every version is timestamped and immutable
- **Concurrent versions** — Run multiple versions of the same function simultaneously

When you publish a version, Lambda snapshots:
- Function code
- Runtime configuration (memory, timeout, environment variables)
- IAM role and execution context
- All attached layers
- Layer content and configuration

Once published, a version cannot be modified. To make changes, edit `$LATEST`, then publish a new version.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS version) or `"delete"` (remove version) |

### Target Function

| Field | Type | Default | Purpose |
|---|---|---|---|
| `functionRef` | string | required | Local `LambdaFunction` CR name; resolved to function ARN |

### Publishing

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | `""` | Human-readable description of this version (e.g., "Fixed DB connection pool") |
| `codeSHA256` | string | `""` | Only publish if function code SHA256 matches this value (safety check); `""` = publish unconditionally |

### Provisioned Concurrency

| Field | Type | Default | Purpose |
|---|---|---|---|
| `provisionedConcurrentExecutions` | integer | `0` | Provisioned concurrency: `0` = not set, `>0` = reserved concurrent invocations for warm starts |

**Note:** Provisioned concurrency is set per version, not globally. Different versions can have different concurrency reservations. Only set when `> 0`.

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
| `tags` | map | `{}` | Kubernetes metadata only (AWS Lambda versions do not support cloud tags) |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Important:** Lambda versions do NOT support cloud tags (AWS doesn't tag versions). `syncedLabels` and `syncedAnnotations` only apply to Kubernetes.

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `versionNumber` | integer | The published version number (1, 2, 3, ...) assigned by AWS |
| `functionArn` | string | ARN of this specific version: `arn:aws:lambda:region:account:function:name:version` |
| `codeSha256` | string | SHA-256 hash of the deployed code |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

**Note:** Versions are identified by number, not by Kubernetes resource name. The same function publishes a new version on each LambdaVersion resource.

## Naming Convention

**Versions do not have user-defined names.** AWS assigns version numbers automatically (1, 2, 3, ...). The Kubernetes resource name is purely for organization within Kubernetes.

Example:
- Kubernetes resource name: `v1-0-0-release`
- Version number in AWS: `42` (auto-assigned)
- Version ARN: `arn:aws:lambda:us-east-1:123456789012:function:my-function:42`

## Complete Examples

### Basic Version Publishing

Publish a snapshot of the current `$LATEST`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: v1-release
  namespace: functions
spec:
  functionRef: my-function
  description: "Initial v1.0.0 release"
```

Result:
- Function `$LATEST` is published as version 1
- Version 1 ARN: `arn:aws:lambda:us-east-1:account:function:my-function:1`
- Version 1 is immutable and can be referenced by aliases and URLs

### Version with Provisioned Concurrency

Publish a version with reserved warm capacity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: v2-hotstart
  namespace: functions
spec:
  functionRef: api-handler
  description: "v2.0.0 with performance improvements (500 reserved concurrency)"
  provisionedConcurrentExecutions: 500
```

Result:
- Version 2 published with 500 reserved concurrent invocations
- All invocations on version 2 start hot (no cold starts)
- Cost includes provisioned concurrency rate

### Version for Canary Testing

Publish a version specifically for canary deployment testing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: canary-test
  namespace: functions
spec:
  functionRef: api-service
  description: "Canary: Updated authorization logic (5% test traffic)"
```

Result:
- Version published and ready for canary routing
- Use a LambdaAlias with `additionalVersionWeights: {"5": 0.05}` to route 5% traffic

### Version with Async Configuration

Publish a version with async error handling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: async-v3
  namespace: functions
spec:
  functionRef: async-processor
  description: "v3.0.0 with improved async error handling"
  functionEventInvokeConfig:
    maximumEventAgeInSeconds: 3600
    maximumRetryAttempts: 2
    destinationConfig:
      onFailure:
        destination: "arn:aws:sqs:us-east-1:123456789012:async-dlq"
```

Result:
- Version published with async config for on-failure routing
- Failed async events automatically sent to DLQ

### Rollback Version

Create a version as a known-good rollback point:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: stable-rollback
  namespace: functions
spec:
  functionRef: critical-service
  description: "Stable v5.0.0 - rollback point for incidents"
  provisionedConcurrentExecutions: 100
```

Usage:
1. When v6 is released with issues
2. Quickly update the `prod` alias to point to this version
3. Incident resolved; traffic reverted to known-good state

## Deployment Workflow

### 1. Develop and Test on $LATEST

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: my-api
  namespace: services
spec:
  configRef: general-policy
  code:
    s3Bucket: lambda-code
    s3Key: my-api-v2.0.0.zip
  runtime: python3.12
  handler: api.lambda_handler
  # ... other config
```

Update the function spec, deploy, and test. This updates `$LATEST`.

### 2. Test the New Version

Invoke the function via the function name (which uses `$LATEST`):

```bash
aws lambda invoke --function-name my-api /tmp/response.json
```

Run your test suite, verify behavior, check logs, and monitor metrics.

### 3. Publish a Version

Once confident, create a LambdaVersion resource:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaVersion
metadata:
  name: v2-release
  namespace: services
spec:
  functionRef: my-api
  description: "v2.0.0: Added rate limiting"
  provisionedConcurrentExecutions: 100
```

AWS assigns version number (e.g., version 5) and returns the ARN.

### 4. Route Traffic with Aliases

Create or update a LambdaAlias to use the new version:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: prod
  namespace: services
spec:
  configRef: general-policy
  functionRef: my-api
  functionVersion: "5"  # Points to the newly published version
  deletionPolicy: retain
```

All traffic via the `prod` alias now uses version 5.

### 5. Rollback if Needed

If version 5 has issues, update the alias to point to a previous version:

```yaml
# Update the same alias
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaAlias
metadata:
  name: prod
  namespace: services
spec:
  configRef: general-policy
  functionRef: my-api
  functionVersion: "4"  # Rolled back to version 4
  deletionPolicy: retain
```

Rollback is instant; traffic immediately switches to version 4.

## Governance

**Note:** Versions inherit governance through `configRef` if specified, but versions typically don't have resource-specific governance. Governance primarily applies to tag/label/annotation merging. Provisioned concurrency and async config are version-specific settings.

## Key Behaviors

### Versions are Immutable

Once published, a version cannot be modified. The code, configuration, and all dependencies are frozen. To make changes, edit `$LATEST` and publish a new version.

### Version Numbers Auto-Increment

Version numbers are assigned by AWS and always increment (1, 2, 3, ...). You cannot choose a version number.

### Provisioned Concurrency is Per-Version

Each version can have different provisioned concurrency. This allows:
- Version 4 (stable): 100 reserved concurrent invocations
- Version 5 (canary): 10 reserved concurrent invocations

Total cost = sum of provisioned concurrency across all versions.

### Function Must Exist

The referenced `LambdaFunction` CR must exist. The function's `$LATEST` is what gets published.

### Delayed Publishing

When you create a LambdaVersion resource, Lambda publishes `$LATEST` at that moment. If there are uncommitted changes to the function, they're included in the version.

## Troubleshooting

### Version Not Creating

Check that the referenced function exists and is in a valid state. If the function has an error, version publishing fails.

### Provisioned Concurrency Not Initializing

Provisioned concurrency initialization can take 5–10 minutes. Check AWS CloudWatch for initialization status. Concurrent invocations before initialization completes may see cold starts.

### Stale Version in Use

If clients are caching a version number or ARN, updating the alias doesn't affect them. They continue using the old version until you restart their processes.

### Too Many Versions

AWS doesn't limit version count, but storage costs increase. Clean up old versions if they're no longer needed by setting a retention policy in your deployment automation.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for versioning design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/versions-intro.html
