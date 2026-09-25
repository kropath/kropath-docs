---
title: LambdaFunction — Serverless Compute Functions
description: "The `LambdaFunction` resource wraps AWS Lambda functions."
doc_type: reference
---
# LambdaFunction — Serverless Compute Functions

The `LambdaFunction` resource wraps AWS Lambda functions. It handles function deployment, runtime configuration, resource limits, encryption, tracing, and versioning. Functions are deployed from ZIP files (S3) or container images (ECR).

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the function name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the function resource is deleted: `"retain"` (keep AWS function) or `"delete"` (remove AWS function) |

### Deployment Package

Exactly one of `code.s3Bucket`/`code.s3Key` (ZIP) or `code.imageUri` (container image) must be set;
they are mutually exclusive. All deployment-package fields live under `code`.

**ZIP package from S3:**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `code.s3Bucket` | string | required | S3 bucket containing the ZIP archive |
| `code.s3Key` | string | required | S3 object key for the ZIP file |
| `code.s3ObjectVersion` | string | `""` | Optional S3 version ID; uses latest if empty |

**Container image:**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `code.imageUri` | string | `""` | ECR image URI; e.g. `123456789012.dkr.ecr.us-east-1.amazonaws.com/my-lambda:latest` |

**Container image config overrides** (only valid when using `code.imageUri`):

| Field | Type | Default | Purpose |
|---|---|---|---|
| `imageConfig.command` | array | `[]` | Overrides the container's CMD instruction |
| `imageConfig.entryPoint` | array | `[]` | Overrides the container's ENTRYPOINT instruction |
| `imageConfig.workingDirectory` | string | `""` | Overrides the working directory |

### Runtime Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `runtime` | string | `""` | Runtime identifier (e.g., `python3.12`, `nodejs20.x`, `java17`); required for ZIP packages; `""` = fall through to governance defaults |
| `handler` | string | `""` | Entry-point method (e.g., `index.handler`); required for ZIP packages; ignored for container images |
| `packageType` | string | `"Zip"` | `Zip` or `Image` |
| `architectures` | array | `["x86_64"]` | Processor architecture: `"x86_64"` (Intel) or `"arm64"` (Graviton); array length must be 1 |
| `publish` | boolean | `false` | Publish a numbered version immediately after function creation |

### Resource Limits (Governed by LambdaConfig)

| Field | Type | Default | Constraints | Governance |
|---|---|---|---|---|
| `memorySize` | integer | `0` | 128–10240 MB | `0` = fall through to governance defaults (baseline 128 MB); mandatory tier clamps maximum |
| `timeout` | integer | `0` | 1–900 seconds | `0` = fall through to governance defaults (baseline 3 seconds); mandatory tier clamps maximum |
| `ephemeralStorageSize` | integer | `0` | 512–10240 MB | `0` = fall through to governance defaults (baseline 512 MB); mandatory tier clamps maximum |

### Concurrency

| Field | Type | Default | Purpose |
|---|---|---|---|
| `reservedConcurrentExecutions` | integer | `-1` | Concurrency reservation: `-1` = unreserved (auto-scale), `0` = throttle, `≥1` = reserve that many concurrent invocations |

### Execution Role

Either `role` or `roleRef` can be set; they are mutually exclusive.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `role` | string | `""` | Direct IAM role ARN for function execution |
| `roleRef` | string | `""` | Local `IAMRole` CR name; resolved to ARN via cross-resource reference |

### Environment Variables

| Field | Type | Default | Purpose |
|---|---|---|---|
| `environment` | map[string]string | `{}` | Environment variables injected at Lambda runtime; maps to AWS Lambda's `environment.variables` |

### Encryption (Governed by LambdaConfig)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyArn` | string | `""` | KMS key ARN for environment variable encryption; `""` = fall through to governance defaults; mutually exclusive with `kmsKeyRef` |
| `kmsKeyRef` | string | `""` | Local `KMSKey` CR name; resolved to ARN via cross-resource reference; mutually exclusive with `kmsKeyArn` |

### VPC Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `vpcConfig.subnetIds` | array | `[]` | VPC subnet IDs for function execution |
| `vpcConfig.securityGroupIds` | array | `[]` | VPC security group IDs |
| `vpcConfig.ipv6AllowedForDualStack` | boolean | `false` | Enable IPv6 for dual-stack VPC subnets |

### Observability (Governed by LambdaConfig)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tracingMode` | string | `""` | `""` = fall through to governance defaults; `PassThrough` = log to X-Ray; `Active` = active sampling |
| `loggingConfig.logFormat` | string | `""` | `JSON` or `Text`; defaults to Text |
| `loggingConfig.applicationLogLevel` | string | `""` | `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL` |
| `loggingConfig.systemLogLevel` | string | `""` | `DEBUG`, `INFO`, `WARN` |
| `loggingConfig.logGroup` | string | `""` | Custom CloudWatch log group name; default is `/aws/lambda/<function-name>` |

### Async Invocation and Error Handling

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deadLetterTargetArn` | string | `""` | Legacy DLQ: SQS queue or SNS topic ARN for async failure routing |
| `functionEventInvokeConfig.maximumEventAgeInSeconds` | integer | `0` | Discard async events older than this (60–21600 seconds); `0` = not set |
| `functionEventInvokeConfig.maximumRetryAttempts` | integer | `-1` | Max async retry attempts (0–2); `-1` = AWS default (2 retries) |
| `functionEventInvokeConfig.destinationConfig.onFailure.destination` | string | `""` | ARN (SQS/SNS/Lambda/EventBridge) for failed async invocations |
| `functionEventInvokeConfig.destinationConfig.onSuccess.destination` | string | `""` | ARN (SQS/SNS/Lambda/EventBridge) for successful async invocations |

### SnapStart

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snapStartApplyOn` | string | `""` | `""` = SnapStart disabled; `PublishedVersions` = auto-apply SnapStart when publishing versions |

### Code Signing

Either `codeSigningConfigArn` or `codeSigningConfigRef` can be set; they are mutually exclusive.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `codeSigningConfigArn` | string | `""` | ARN of an AWS CodeSigningConfig |
| `codeSigningConfigRef` | string | `""` | Local `LambdaCodeSigningConfig` CR name; resolved to ARN via cross-resource reference |

### Layers and File System

| Field | Type | Default | Purpose |
|---|---|---|---|
| `layers` | array | `[]` | List of layer version ARNs (max 5 layers) |
| `fileSystemConfigs` | array | `[]` | EFS access point mounts; each: `{arn: "string", localMountPath: "string"}` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective function name in AWS (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if naming is resolved, `"invalid-unresolved-tokens"` if template has unresolvable tokens |
| `predictedArn` | string | ARN prefix before provisioning: `arn:aws:lambda:region:account:function:resourceName` |
| `functionArn` | string | Full ARN from AWS (same as predictedArn for functions; set after provisioning) |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

## Naming Convention

Functions are named using a configurable template. The default template is `{namespace}-{name}`. Available tokens:

- `{name}` — Resource's Kubernetes name
- `{namespace}` — Resource's Kubernetes namespace
- `{configRef}` — Governance profile name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Any tag value (e.g., `{tag.environment}`)

AWS Lambda function names are 1–64 characters and allow `a-z A-Z 0-9 - _ .`.

**Important:** Function names are immutable after creation. Changing the naming template or `nameOverride` on an existing function does not rename the AWS function.

## Complete Examples

### Basic ZIP Function

Deploy a simple Python function from a ZIP file in S3:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: hello-world
  namespace: app-team
spec:
  configRef: general-policy
  code:
    s3Bucket: my-lambda-artifacts
    s3Key: hello-world-v1.0.0.zip
  runtime: python3.12
  handler: index.lambda_handler
  memorySize: 256
  timeout: 30
  tags:
    application: "hello-world"
    version: "1.0.0"
```

Result:
- Function created with name `app-team-hello-world`
- 256 MB memory, 30-second timeout
- Governed by `general-policy` settings
- X-Ray tracing, encryption, and naming follow governance

### Container Image Function

Deploy a function using a container image from ECR:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: api-handler
  namespace: api-team
spec:
  configRef: general-policy
  code:
    imageUri: "123456789012.dkr.ecr.us-east-1.amazonaws.com/api-handler:latest"
  packageType: Image
  memorySize: 512
  timeout: 60
  role: "arn:aws:iam::123456789012:role/lambda-api-execution-role"
```

Result:
- Function deployed using ECR image
- Custom execution role provided directly

### Function with Cross-Resource References

Use IAMRole and KMSKey references for role and encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: db-sync
  namespace: data-team
spec:
  configRef: general-policy
  code:
    s3Bucket: my-lambda-artifacts
    s3Key: db-sync.zip
  runtime: python3.12
  handler: sync.main
  memorySize: 1024
  timeout: 300
  roleRef: lambda-db-sync  # References IAMRole CR
  kmsKeyRef: db-encryption-key  # References KMSKey CR
  layers:
    - "arn:aws:lambda:us-east-1:123456789012:layer:db-client:1"
```

Result:
- Role and encryption key resolved from local CR references
- Execution role ARN and KMS key ARN auto-populated
- Can be updated without changing the function spec
- Layers provide shared database client library

### Function with VPC and EFS

Deploy a function that accesses RDS and EFS:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: rds-processor
  namespace: database-team
spec:
  configRef: general-policy
  code:
    s3Bucket: lambda-code
    s3Key: rds-processor.zip
  runtime: python3.12
  handler: processor.lambda_handler
  memorySize: 3008  # Max for EFS throughput
  timeout: 900
  role: "arn:aws:iam::123456789012:role/lambda-rds-role"
  vpcConfig:
    subnetIds:
      - "subnet-12345678"
      - "subnet-87654321"
    securityGroupIds:
      - "sg-lambda-rds"
  fileSystemConfigs:
    - arn: "arn:aws:elasticfilesystem:us-east-1:123456789012:access-point/fsap-12345678"
      localMountPath: "/mnt/efs"
  tracingMode: Active
```

Result:
- Function executes in VPC subnets
- Accesses RDS through security group
- Mounts EFS for persistent file storage
- Active X-Ray tracing enabled

### Function with Async Invocation

Deploy a function for async processing with DLQ and destinations:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: async-processor
  namespace: processing-team
spec:
  configRef: general-policy
  code:
    s3Bucket: lambda-code
    s3Key: async-processor.zip
  runtime: python3.12
  handler: processor.handle
  memorySize: 512
  timeout: 60
  role: "arn:aws:iam::123456789012:role/lambda-async-role"
  functionEventInvokeConfig:
    maximumEventAgeInSeconds: 3600
    maximumRetryAttempts: 2
    destinationConfig:
      onFailure:
        destination: "arn:aws:sqs:us-east-1:123456789012:dlq"
```

Result:
- Async events processed with retry logic
- Failed invocations routed to DLQ
- Events older than 1 hour discarded

### PCI-Compliant Function

Deploy a function with security governance enforced:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: payment-processor
  namespace: payments
spec:
  configRef: pci-production  # PCI-hardened profile
  code:
    s3Bucket: secure-artifacts
    s3Key: payment-processor.zip
  # runtime: enforced by pci-production mandatory tier
  handler: payment.process
  # memorySize: clamped by pci-production mandatory tier
  # timeout: clamped by pci-production mandatory tier
  # tracingMode: enforced by pci-production mandatory tier
  # kmsKeyArn: enforced by pci-production mandatory tier
  syncedLabels:
    payment-processing: "true"
    audit-required: "true"
  deletionPolicy: retain  # Keep function if K8s resource deleted
```

Result:
- All mandatory governance from `pci-production` profile applied
- Runtime, memory, timeout, tracing, and encryption enforced
- Security and audit labels synced
- Function retained even if Kubernetes resource is deleted

## Governance Cascade

The effective configuration for each function is determined by three tiers:

```
LambdaConfig.mandatory (highest priority)
  ↓
Function spec (middle)
  ↓
LambdaConfig.defaults (lowest priority)
```

For example:
- If `pci-production` has `mandatory.runtime: "python3.12"`, that runtime is always used regardless of function spec
- If function spec provides `memorySize: 512` and defaults suggest 256, the function uses 512
- If mandatory tier has `memorySize: 10240` (hard ceiling), a function requesting 10240+ gets clamped to 10240

## Key Behaviors

### Immutable Function Name After Creation

Once created, a Lambda function's name cannot be changed. The naming template or `nameOverride` determines the name at creation time only.

### Role Resolution

When `roleRef` is set, the controller resolves it to an ARN by reading the `IAMRole` CR's `status.predictedArn`. This allows:
- Changing the role definition without modifying the function spec
- Cleaner references and reduced manual ARN entry
- Automatic role ARN updates if the underlying role changes

### KMS Key Resolution

When `kmsKeyRef` is set, the controller resolves it to a KMS key ID by reading the `KMSKey` CR's `status.predictedArn`. Similar benefits to role references.

### Code Signing Configuration Resolution

When `codeSigningConfigRef` is set, it resolves to a CodeSigningConfig ARN via cross-reference. The function must exist before code signing config creation.

### SnapStart Optimization

SnapStart caches initialized runtime state to reduce cold starts. When `snapStartApplyOn: PublishedVersions` is set, every published version gets SnapStart optimization automatically.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the AWS Lambda function intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS Lambda function (use with caution)

## Troubleshooting

### Function Not Creating

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template has a token that cannot be resolved (e.g., a tag key that doesn't exist). Fix the template or ensure required tags are present.
- If `valid` but function not created, check `status.conditions` for AWS errors (e.g., permission issues, duplicate name, invalid runtime).

### Can't Override Governance Settings

If `LambdaConfig` has a mandatory tier set (e.g., `mandatory.runtime: "python3.12"`), you cannot override that setting at the function level. Only the defaults tier can be overridden. Contact your platform team if you need a different runtime or settings.

### Role or KMS Key Not Resolving

Ensure the referenced `IAMRole` or `KMSKey` CR exists in the same namespace and has `status.predictedArn` populated. The referenced resource must be created before the function references it.

### Layers Not Attaching

Ensure layer ARNs are correct and compatible with the function's architecture and runtime. Lambda only accepts up to 5 layers.

### EFS Not Mounting

Ensure the EFS access point ARN is correct and the function's VPC subnets have proper routing to the EFS mount targets. The function must run in a VPC (via `vpcConfig`) to access EFS.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for complete governance and deployment design
- **ADRs:** ADR-015 covers governance cascade; ADR-010 covers cross-resource references
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/
