---
title: PolicyDocument
description: "`PolicyDocument` is a Kubernetes resource that lets you compose, validate, and reuse AWS IAM policy documents."
doc_type: concept
---
# PolicyDocument

`PolicyDocument` is a Kubernetes resource that lets you compose, validate, and reuse AWS IAM policy documents. Instead of embedding raw JSON in your resource specifications, you can structure your policies as YAML and let the kropath controller resolve cross-resource references and merge multiple policies into a single, validated document.

## Scope

This resource is AWS-only. There is no GCP or Azure equivalent yet, so policy document composition on those platforms still follows their provider-specific resource schemas until separate abstractions are introduced.

## What it solves

AWS resources like S3 buckets, SQS queues, and IAM roles require policy documents — but expressing them inline as raw JSON strings has several problems:

- **No validation at apply time** — invalid JSON or semantic policy errors are only caught after the policy is deployed to AWS
- **Manual ARN resolution** — you must pre-resolve ARN values for cross-resource references instead of letting the platform resolve them automatically
- **No merge** — when multiple teams or applications need to contribute statements to a shared policy (e.g., ALB access logging + application grants on the same S3 bucket), you must manually merge them outside the platform
- **Poor ergonomics** — long inline JSON strings are hard to review, diff, and maintain in YAML

`PolicyDocument` fixes all of these by providing:

- **Structured YAML** — define policy statements as typed YAML fields, validated at `kubectl apply` time
- **Automatic ARN resolution** — reference other kropath resources by kind and name; the controller resolves their ARNs automatically
- **Built-in merge** — compose a single policy from multiple named source documents with automatic Sid conflict detection
- **Raw JSON fallback** — when you need complex syntax that doesn't fit the structured model, use the raw `spec.documentJSON` escape hatch

## Core concepts

### Structured statements vs. raw JSON

`PolicyDocument` supports two mutually exclusive approaches:

**Structured statements** (preferred):
```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: my-policy
spec:
  statements:
    - sid: AllowS3Read
      effect: Allow
      principals:
        - type: AWS
          arn: "arn:aws:iam::123456789012:root"
      actions:
        - s3:GetObject
        - s3:ListBucket
      resources:
        - arn: "arn:aws:s3:::my-bucket"
```

**Raw JSON** (escape hatch):
```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: complex-policy
spec:
  documentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "s3:GetObject",
          "Resource": "arn:aws:s3:::bucket/*"
        }
      ]
    }
```

Use structured statements whenever possible — they provide validation, readability, and enable ref resolution and merge. Use raw JSON only when your policy requires syntax that the structured form doesn't support.

### ARN references

Instead of hardcoding ARN values, reference other kropath resources by kind and name:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: lambda-policy
spec:
  statements:
    - sid: AllowLambdaInvoke
      effect: Allow
      actions:
        - lambda:InvokeFunction
      resources:
        - ref:
            kind: LambdaFunction
            name: my-function
            # field: predictedArn (default)
```

The controller resolves the reference by reading `status.predictedArn` from the referenced resource. This means:

- References remain correct even when the resource's `spec.nameOverride` changes
- You don't need to pre-compute ARNs — the platform does it for you
- The policy is automatically updated if the referenced resource's name changes

**Supported reference fields:**

| `ref.kind` | Default `status` field | Example ARN |
|---|---|---|
| `IAMRole` | `predictedArn` | `arn:aws:iam::123456789012:role/my-role` |
| `S3Bucket` | `predictedArn` | `arn:aws:s3:::my-bucket` |
| `LambdaFunction` | `predictedArn` | `arn:aws:lambda:us-east-1:123456789012:function:my-func` |
| `SQSQueue` | `predictedArn` | `arn:aws:sqs:us-east-1:123456789012:my-queue` |
| `KMSKey` | `predictedArn` | `arn:aws:kms:us-east-1:123456789012:alias/my-key` |
| `SecretsManagerSecret` | `predictedArn` | `arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret` |

References are **same-namespace only** — a policy document in one namespace cannot reference resources in another namespace.

### Source composition and merge

Compose a single policy from multiple source documents using `spec.sources`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: my-bucket-policy
  namespace: default
spec:
  # Merge statements from these source documents first
  sources:
    - name: alb-log-delivery-grant
    - name: platform-base-s3-policy
  
  # Then add your own statements
  statements:
    - sid: AllowMyAppRead
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: my-app-role
      actions:
        - s3:GetObject
      resources:
        - arn: "arn:aws:s3:::my-bucket/*"
```

The controller merges statements in order:

```
merged = sources[0].statements + sources[1].statements + ... + own.statements
```

This pattern eliminates manual JSON merging when multiple teams need to contribute to a shared resource policy (e.g., ALB logging + application-specific grants on the same S3 bucket).

**Constraints:**

- All source documents must use structured `spec.statements` — raw JSON sources (`spec.documentJSON`) cannot be merged
- Statement Sids (if non-empty) must be unique across the entire merged document — if two statements share the same Sid, the document is marked invalid until you rename one
- References must exist and be ready — if a source document's references are unresolved, the parent document is blocked and will retry automatically

## RGD integration

### Phase 1 (CRD only, no controller)

In Phase 1, the `PolicyDocument` CRD is deployed but the controller is not running. RGDs read the `spec.documentJSON` field directly, so if you author the policy in structured YAML you must also provide the equivalent JSON in `spec.documentJSON` until Phase 2 is deployed:

```yaml
# In your S3 bucket RGD
variables:
  policyDoc: >-
    ${resources.get(metadata.namespace, "PolicyDocument", spec.bucketPolicyRef)}

resources:
  - id: s3Bucket
    template:
      apiVersion: s3.services.k8s.aws/v1alpha1
      kind: Bucket
      spec:
        policy: ${variables.policyDoc.spec.documentJSON}
```

### Phase 2 (controller with ref resolution)

Once the controller is deployed, it populates `status.resolvedDocumentJSON` with the fully resolved, merged policy. RGDs switch to reading that field:

```yaml
variables:
  policyDoc: >-
    ${resources.get(metadata.namespace, "PolicyDocument", spec.bucketPolicyRef)}

resources:
  - id: s3Bucket
    template:
      apiVersion: s3.services.k8s.aws/v1alpha1
      kind: Bucket
      spec:
        # Now reads the resolved, merged output
        policy: ${variables.policyDoc.status.resolvedDocumentJSON}
```

## Cross-family use cases

`PolicyDocument` works with any AWS resource that requires a policy document:

### S3 bucket policy

One S3 bucket policy per bucket. Supports merge.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: central-logging-bucket-policy
spec:
  sources:
    - name: alb-log-delivery-grant
  statements:
    - sid: AllowDevelopersRead
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: dev-team-role
      actions:
        - s3:GetObject
      resources:
        - arn: "arn:aws:s3:::central-logs/*"
```

### SQS queue policy

One SQS queue policy per queue. Supports merge.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: payment-queue-policy
spec:
  statements:
    - sid: AllowLambdaConsume
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: LambdaFunction
            name: payment-processor
      actions:
        - sqs:ReceiveMessage
        - sqs:DeleteMessage
      resources:
        - ref:
            kind: SQSQueue
            name: payment-events
```

### KMS key policy

One KMS key policy per key. Supports merge.

⚠️ **Important**: KMS key policies require a root account statement that grants the account's principal full access. Include this statement in your policy — the controller will not auto-inject it. This is intentional to keep the security audit trail clear.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: kms-key-policy
spec:
  statements:
    - sid: EnableAccountRootAccess
      effect: Allow
      principals:
        - type: AWS
          # Use the account's root principal
          arn: "arn:aws:iam::123456789012:root"
      actions:
        - "kms:*"
      resources:
        - "*"
    
    - sid: AllowDevelopersUse
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: developer-role
      actions:
        - "kms:Decrypt"
        - "kms:GenerateDataKey"
      resources:
        - "*"
```

### Secrets Manager resource policy

One resource policy per secret. Supports merge.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: api-secret-policy
spec:
  statements:
    - sid: AllowAppAccess
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: LambdaFunction
            name: api-handler
      actions:
        - secretsmanager:GetSecretValue
      resources:
        - ref:
            kind: SecretsManagerSecret
            name: api-credentials
```

### IAM role inline policies

Each inline policy can reference an `PolicyDocument`:

```yaml
# In your IAM role RGD
spec:
  inlinePolicies:
    - name: s3-access
      documentRef: s3-inline-policy  # refs spec.inlinePolicies[].documentRef
```

### IAM role trust policy

The trust policy is a special resource-based policy that controls who can assume the role:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: lambda-execution-trust
spec:
  statements:
    - effect: Allow
      principals:
        - type: Service
          arn: "lambda.amazonaws.com"
      actions:
        - "sts:AssumeRole"
```

Reference it in your IAM role RGD:

```yaml
spec:
  trustPolicyRef: lambda-execution-trust
```

## ALB access logging pattern

A common use case: grant the AWS ELB service account permission to write access logs to your S3 bucket.

This pattern has **no circular dependency** because the ELB service account ARN is fixed per region, not tied to a specific ALB instance.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: alb-log-delivery-grant
  namespace: platform
spec:
  statements:
    - sid: AllowALBAccessLogging
      effect: Allow
      principals:
        - type: Service
          arn: "logdelivery.elasticloadbalancing.amazonaws.com"
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::my-bucket/*"
```

Then reference this document as a source in your application bucket policy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: app-bucket-policy
spec:
  sources:
    - name: alb-log-delivery-grant
  statements:
    - sid: AllowAppTeamAccess
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: app-team-role
      actions:
        - s3:GetObject
      resources:
        - arn: "arn:aws:s3:::my-bucket/*"
```

## Complete example

Here's a complete example that demonstrates structured statements, refs, and merging:

```yaml
---
# Step 1: Define a base policy that grants ALB logging access
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: s3-logging-grant
  namespace: platform
spec:
  statements:
    - sid: AllowELBAccess
      effect: Allow
      principals:
        - type: Service
          arn: "logdelivery.elasticloadbalancing.amazonaws.com"
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::central-logs/*"

---
# Step 2: Define the application team's S3 bucket
apiVersion: aws.kropath.run/v1alpha1
kind: S3Bucket
metadata:
  name: central-logs
spec:
  # ... other bucket configuration ...
  bucketPolicyRef: central-logs-policy

---
# Step 3: Define the bucket policy, sourcing from the logging grant
apiVersion: aws.kropath.run/v1alpha1
kind: PolicyDocument
metadata:
  name: central-logs-policy
  namespace: platform
spec:
  # Include the ALB logging grant as a source
  sources:
    - name: s3-logging-grant
  
  # Add application-specific statements
  statements:
    - sid: AllowAppTeamRead
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: app-team-reader
      actions:
        - "s3:GetObject"
        - "s3:ListBucket"
      resources:
        - ref:
            kind: S3Bucket
            name: central-logs
    - sid: AllowAppTeamWriteToLogs
      effect: Allow
      principals:
        - type: AWS
          ref:
            kind: IAMRole
            name: app-team-writer
      actions:
        - "s3:PutObject"
      resources:
        - arn: "arn:aws:s3:::central-logs/*"
```

When the controller reconciles this, `central-logs-policy.status.resolvedDocumentJSON` will contain all statements from both `s3-logging-grant` and the application-specific grant.

## Statement schema reference

Each statement in `spec.statements[]` maps directly to an AWS IAM policy statement:

| Field | Type | Required? | Notes |
|---|---|---|---|
| `sid` | string | No | Statement ID. Must be unique within the merged document (if non-empty). Recommended for clarity. |
| `effect` | `Allow` \| `Deny` | Yes | The statement's effect. |
| `principals[]` | list | For resource-based policies | Principals who the statement applies to. Omit for identity-based policies. |
| `principals[].type` | `AWS` \| `Service` \| `Federated` | Yes (if principals present) | Principal type. |
| `principals[].arn` | string | No* | Literal ARN. Mutually exclusive with `principals[].ref`. |
| `principals[].ref` | ref object | No* | Reference to a kropath resource. Mutually exclusive with `principals[].arn`. |
| `actions[]` | list of strings | Yes | AWS action strings (e.g., `s3:GetObject`, `iam:GetRole`). |
| `resources[]` | list | For identity-based policies | Resources the statement applies to. Omit for resource-based policies. |
| `resources[].arn` | string | No* | Literal ARN. Mutually exclusive with `resources[].ref`. |
| `resources[].ref` | ref object | No* | Reference to a kropath resource. Mutually exclusive with `resources[].arn`. |
| `conditions[]` | list | No | Conditions that must be satisfied. |
| `conditions[].operator` | string | Yes (if conditions present) | IAM condition operator (e.g., `StringEquals`, `ArnLike`). |
| `conditions[].key` | string | Yes (if conditions present) | IAM condition key (e.g., `aws:SourceVpc`). |
| `conditions[].values[]` | list of strings | Yes (if conditions present) | Condition values. |

*: Exactly one of `arn` or `ref` must be specified for principals and resources.

## Status and readiness

The `PolicyDocument` publishes its readiness via status conditions:

```yaml
status:
  resolvedDocumentJSON: |
    {
      "Version": "2012-10-17",
      "Statement": [...]
    }
  statementCount: 3
  sourceCount: 1
  conditions:
    - type: Ready
      status: "True"
      reason: DocumentResolved
    - type: SidConflict
      status: "False"
    - type: SourceNotReady
      status: "False"
  observedGeneration: 2
```

**Status conditions:**

- **Ready**: The document is fully resolved and `status.resolvedDocumentJSON` is current
- **SidConflict**: Two or more statements share the same non-empty Sid (invalid merge state)
- **SourceNotReady**: A source document or referenced resource is not yet ready

Always check the `Ready` condition before using `status.resolvedDocumentJSON` in your RGDs.

## Common patterns

### Conditional access

Use conditions to restrict access by source VPC, IP address, or other attributes:

```yaml
statements:
  - sid: AllowInVPCOnly
    effect: Allow
    principals:
      - type: AWS
        ref:
          kind: LambdaFunction
          name: internal-function
    actions:
      - s3:GetObject
    resources:
      - arn: "arn:aws:s3:::sensitive-data/*"
    conditions:
      - operator: StringEquals
        key: "aws:SourceVpc"
        values:
          - "vpc-12345678"
```

### Deny statements

Place deny statements after allow statements in your source order so they're easier to audit:

```yaml
spec:
  sources:
    - name: base-allow-statements
  statements:
    - sid: DenyPublicAccess
      effect: Deny
      principals:
        - type: AWS
          arn: "*"
      actions:
        - "*"
      resources:
        - "*"
      conditions:
        - operator: StringLike
          key: "aws:username"
          values:
            - "anonymous"
```

## Troubleshooting

### Document is not Ready

Check the status conditions:

```bash
kubectl describe policydocument my-policy
```

Look for `SourceNotReady` or `SidConflict` conditions. Common causes:

- **SourceNotReady**: A source document is missing or has unresolvable refs. Check that all source names exist and are in the same namespace.
- **SidConflict**: Two statements share the same non-empty Sid. Rename one of them.
- **Unresolvable ref**: A referenced resource doesn't exist or hasn't computed its `predictedArn` yet. Verify the resource exists in the same namespace and is Ready.

### Policy is empty or invalid

Check whether the document uses raw JSON:

```bash
kubectl get policydocument my-policy -o yaml | grep -A5 spec:
```

If `spec.documentJSON` is set, make sure it's valid JSON. If using structured form, verify all required fields (effect, actions) are present.

## Best practices

1. **Use structured statements** whenever possible. Raw JSON is the fallback for complex syntax, not the default.

2. **Name your Sids clearly**. Use descriptive names like `AllowS3Read` instead of generic names. This helps with auditing and debugging.

3. **Leverage sources for common patterns**. Create reusable policy documents for common grants (e.g., ALB logging, platform base policies) and source them in application-specific policies.

4. **Use refs instead of hardcoded ARNs**. Refs keep your policy correct when resource names change and reduce manual ARN computation.

5. **Test policies in a non-production namespace first**. Validate that your policy documents are syntactically and semantically correct before deploying them to production resources.

6. **Keep source documents simple**. Each source should have a clear, single purpose. Complex merge scenarios are easier to understand when broken into multiple focused source documents.

7. **Document your policy structure**. Add comments to explain why certain statements exist, especially deny statements and conditional access rules.

## API reference

Full API documentation:

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `PolicyDocument`
- **Scope**: Namespaced
