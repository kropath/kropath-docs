# LambdaCodeSigningConfig — Code Provenance and Validation

The `LambdaCodeSigningConfig` resource defines code signing policies for Lambda functions. Code signing ensures that function code has been signed by trusted private keys and has not been tampered with since signing.

## Overview

Code signing provides:
- **Code provenance** — Cryptographic proof that code originated from authorized sources
- **Tamper detection** — AWS Lambda verifies signatures before executing code
- **Compliance** — Meet regulatory requirements for code integrity
- **Policy enforcement** — Warn or reject unsigned/invalidly signed code

To use code signing:
1. Create a `LambdaCodeSigningConfig` that references your signing profile
2. Attach the config to functions via `codeSigningConfigRef` or `codeSigningConfigArn`
3. Lambda verifies signatures on every function invocation

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `LambdaConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior on resource deletion: `"retain"` (keep AWS config) or `"delete"` (remove config) |

### Code Signing Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `allowedPublishers.signingProfileVersionArns` | []string | required | Array of AWS Signer signing profile ARNs (e.g., `["arn:aws:signer:us-east-1:123456789012:/signing-profile/my-profile:version/1"]`) |

### Validation Policy

| Field | Type | Default | Purpose |
|---|---|---|---|
| `untrustedArtifactOnDeployment` | string | `"Warn"` | Policy for unsigned/invalid code: `"Warn"` = allow with warnings; `"Enforce"` = reject unsigned code |

**Security note:**
- `"Enforce"` (strict) — Only signed code executes; unsigned code is rejected at invocation
- `"Warn"` (permissive) — Unsigned code is allowed but warnings are logged; use for testing/migration

### Metadata

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | `""` | Human-readable description of this signing config |
| `tags` | map | `{}` | AWS tags; merged with governance tags (code signing configs support cloud tags) |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Important:** Code signing configs support cloud tags via `spec.tags` → AWS tags. `syncedLabels` and `syncedAnnotations` only apply to Kubernetes.

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `codeSigningConfigId` | string | AWS-assigned ID for this config (e.g., `csc-12345abc`) |
| `codeSigningConfigArn` | string | Full ARN of the config: `arn:aws:lambda:region:account:code-signing-config:csc-12345abc` |
| `conditions[]` | array | Standard Kubernetes conditions tracking reconciliation progress |

**Note:** Code signing config IDs start with `csc-` and are assigned by AWS.

## Naming Convention

**Code signing configs do not have user-defined names.** AWS assigns a unique ID (`status.codeSigningConfigId`). The Kubernetes resource name is purely for organization within Kubernetes.

## Complete Examples

### Basic Code Signing Configuration

Create a code signing config for a trusted signing profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaCodeSigningConfig
metadata:
  name: prod-signing
  namespace: security
spec:
  configRef: general-policy
  allowedPublishers:
    signingProfileVersionArns:
      - "arn:aws:signer:us-east-1:123456789012:/signing-profile/prod-profile:version/1"
  untrustedArtifactOnDeployment: "Enforce"  # Reject unsigned code
  description: "Production code signing policy"
  tags:
    environment: "production"
    compliance: "required"
```

Result:
- Code signing config created with ID (e.g., `csc-12345abc`)
- Functions using this config must have signed code
- Unsigned code is rejected at invocation time

### Function Using Code Signing

Attach code signing config to a function:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaFunction
metadata:
  name: secure-processor
  namespace: security
spec:
  configRef: general-policy
  code:
    s3Bucket: signed-lambda-code
    s3Key: secure-processor.zip  # Must be signed by prod profile
  runtime: python3.12
  handler: processor.lambda_handler
  codeSigningConfigRef: prod-signing  # References the CodeSigningConfig CR
  # Alternatively, use codeSigningConfigArn directly:
  # codeSigningConfigArn: "arn:aws:lambda:us-east-1:123456789012:code-signing-config:csc-12345abc"
```

Result:
- Function requires code signed by the specified profile
- Unsigned or invalidly signed code is rejected
- Signed code is verified before execution

### Permissive Signing Policy for Migration

Temporarily allow unsigned code during a gradual migration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaCodeSigningConfig
metadata:
  name: migration-signing
  namespace: security
spec:
  configRef: general-policy
  allowedPublishers:
    signingProfileVersionArns:
      - "arn:aws:signer:us-east-1:123456789012:/signing-profile/migration-profile:version/1"
  untrustedArtifactOnDeployment: "Warn"  # Allow unsigned (temporary)
  description: "Temporary config for migration; unsigned code allowed with warnings"
  tags:
    migration-phase: "2"
```

Result:
- Functions using this config can have unsigned code
- CloudWatch logs show warnings for unsigned code
- Signed code is still verified when present

### Cross-Account Signing Profile

Reference a signing profile from another AWS account:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaCodeSigningConfig
metadata:
  name: corporate-signing
  namespace: security
spec:
  configRef: general-policy
  allowedPublishers:
    signingProfileVersionArns:
      - "arn:aws:signer:us-east-1:999999999999:/signing-profile/corporate-profile:version/2"
  untrustedArtifactOnDeployment: "Enforce"
  description: "Corporate signing profile from central security account"
  tags:
    signing-account: "999999999999"
    compliance: "sox"
```

Result:
- Function code must be signed by the corporate signing profile
- Cross-account signing profile enables centralized code signing governance

## Code Signing Workflow

### 1. Create and Publish Signing Profile

In AWS Signer, create a signing profile and publish a version. Get the profile ARN:

```bash
aws signer describe-signing-profile --profile-name prod-profile
# Returns ARN like: arn:aws:signer:us-east-1:123456789012:/signing-profile/prod-profile
```

### 2. Create CodeSigningConfig in Kubernetes

Reference the signing profile in a Kubernetes CodeSigningConfig resource.

### 3. Attach to Functions

Functions reference the CodeSigningConfig via `codeSigningConfigRef` or `codeSigningConfigArn`.

### 4. Sign Code Before Upload

Before uploading code to S3, sign it using AWS Signer:

```bash
aws signer sign-payload \
  --profile-name prod-profile \
  --payload-format JSON \
  --payload file://lambda-code.zip \
  --output json > signed-lambda-code.zip.signature
```

Upload both the code and signature to S3.

### 5. Lambda Verifies on Invocation

When the function is invoked, Lambda:
1. Retrieves the code from S3
2. Checks the signature against the signing profile
3. Allows or rejects invocation based on the policy

## Governance

**Note:** Code signing configs inherit governance through `configRef` if specified, but code signing typically doesn't have resource-specific governance. Governance primarily applies to tag/label/annotation merging.

## Key Behaviors

### Signature Verification at Invocation

Signature validation happens every time a function is invoked. Rejected invocations return an error immediately.

### Policy Applies to New and Updated Functions

- Existing functions without code signing are unaffected unless explicitly updated to use a code signing config
- New functions with code signing must have signed code or have `codeSigningPolicyAllowUnsigned: true`

### Signing Profile Must Exist

The referenced signing profile in AWS Signer must exist and be active. AWS Lambda checks the profile on every invocation.

### Version-Specific Signing Profiles

Signing profile ARNs include a version (e.g., `:version/2`). If you change the version, existing functions continue using the old version until you update them.

## Troubleshooting

### "Invalid signature" at Invocation

Code was not signed with the specified signing profile, or the code was modified after signing. Re-sign the code and re-upload.

### "Code signing config not found"

Ensure the referenced CodeSigningConfig CR exists and has a valid `status.codeSigningConfigArn`.

### "Signing profile not found"

Verify the signing profile exists in AWS Signer and the ARN is correct (check account ID and region).

### Unsigned Code Rejected

If `codeSigningPolicyAllowUnsigned: false`, all code must be signed. Either:
- Sign the code using the signing profile
- Change policy to `allowUnsigned: true` temporarily for testing

### Migration Too Slow with Strict Policy

Use a separate config with `codeSigningPolicyAllowUnsigned: true` during migration, then switch to strict policy once all code is signed.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for code signing design
- **AWS Lambda documentation:** https://docs.aws.amazon.com/lambda/latest/dg/code-signing.html
- **AWS Signer documentation:** https://docs.aws.amazon.com/signer/latest/developerguide/
