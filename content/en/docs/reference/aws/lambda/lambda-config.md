---
title: LambdaConfig — Governance for Lambda Resources
description: "The `LambdaConfig` resource defines governance policies for the Lambda family."
doc_type: reference
---
# LambdaConfig — Governance for Lambda Resources

The `LambdaConfig` resource defines governance policies for the Lambda family. Platform teams deploy named profiles (e.g., `general-policy`, `security-hardened`) to enforce compliance controls: runtime requirements, resource limits, encryption, tracing, and tagging standards. Lambda resource instances select a profile via `spec.configRef` to inherit those controls.

## Overview

`LambdaConfig` is a per-resource-type configuration CRD that establishes two tiers of governance:

- **Mandatory tier** — Platform enforcement that overrides instance spec (e.g., "all Lambda functions must use Python 3.12 and run with X-Ray tracing active")
- **Defaults tier** — Sensible baselines that apply when an instance spec is empty (e.g., "if no runtime is specified, default to Python 3.12")

Each field can be set in **only one** tier at a time — the schema prevents both tiers being set simultaneously. This ensures clear precedence: mandatory always wins; defaults only apply when an instance doesn't specify a value.

## Creating a Governance Profile

Create a `LambdaConfig` in the `kro-system` namespace to define a reusable profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    tracingMode: "Active"  # All functions must use X-Ray
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/abc123"  # All env vars encrypted with this key
  defaults:
    runtime: "python3.12"  # Baseline runtime if not specified
    memorySize: 256  # 256 MB baseline
    timeout: 30  # 30-second baseline
    tracingMode: ""  # Mandatory tier covers tracing
```

For a security-focused profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: security-hardened
  namespace: kro-system
spec:
  mandatory:
    runtime: "python3.12"  # Only approved runtimes
    memorySize: 512  # Higher baseline for security scanning
    timeout: 10  # Shorter timeouts to limit blast radius
    tracingMode: "Active"  # Mandatory X-Ray tracing
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/hardened"  # Hardened key for sensitive env vars
  defaults:
    ephemeralStorageSize: 512
```

## Governance Fields

| Field | Type | Mandatory semantics | Defaults semantics |
|---|---|---|---|
| `runtime` | string | Forces a specific runtime; instance cannot override | Applies when instance `spec.runtime` is empty |
| `memorySize` | integer | Hard ceiling; larger values are clamped down | Baseline when instance does not specify |
| `timeout` | integer | Hard ceiling; longer timeouts are clamped down | Baseline when instance does not specify |
| `tracingMode` | string | Forces PassThrough or Active; instance cannot override | Applies when instance `spec.tracingMode` is empty |
| `kmsKeyArn` | string | Forces env var encryption with this key; instance cannot override | Applies when instance `spec.kmsKeyArn` is empty |
| `namingTemplate` | string | Forces a naming pattern; `spec.nameOverride` is the only escape hatch | Applies when instance `spec.nameOverride` is empty |
| `tags` | map | Merged into all Lambda resource cloud tags; mandatory tags cannot be removed | Baseline cloud tags; overridable per-instance |
| `syncedLabels` | map | Merged into K8s labels AND cloud tags (prefixed `aws.kropath.run/`); mandatory labels cannot be removed | Baseline synced labels; overridable per-instance |
| `syncedAnnotations` | map | Merged into K8s annotations (prefixed `aws.kropath.run/`); mandatory annotations cannot be removed | Baseline synced annotations; overridable per-instance |

## Naming Templates

The `namingTemplate` field defines how Lambda function names are constructed. Available tokens:

- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The governance profile name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Any tag value (e.g., `{tag.environment}`)

Examples:

```yaml
defaults:
  namingTemplate: "{namespace}-{name}"
  # Result: app-team-my-function
```

```yaml
mandatory:
  namingTemplate: "{namespace}-{configRef}-{tag.environment}-{name}"
  # Result: app-team-general-policy-production-my-function
```

Lambda function names are 1–64 characters and allow `a-z A-Z 0-9 - _ .`. If a naming template resolves to an invalid name, the function creation fails with a naming error.

## Complete Examples

### Basic Profile for Development

Create a permissive development profile with sensible defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: dev-policy
  namespace: kro-system
spec:
  defaults:
    runtime: "nodejs20.x"
    memorySize: 128
    timeout: 3
    tracingMode: "PassThrough"
    namingTemplate: "{namespace}-{name}"
    tags:
      environment: "dev"
      cost-center: "engineering"
```

### PCI-Compliant Production Profile

Create a hardened production profile with mandatory encryption and tracing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: pci-production
  namespace: kro-system
spec:
  mandatory:
    runtime: "python3.12"  # Only approved runtime
    memorySize: 512  # Minimum for PCI compliance
    timeout: 60
    tracingMode: "Active"  # Mandatory X-Ray tracing
    kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/pci-key"
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      pci-dss: "3.2.1"
      data-classification: "pci"
    syncedLabels:
      pci-protected: "true"
      audit-required: "true"
  defaults:
    ephemeralStorageSize: 512
```

### Profile with Cross-Organization Standards

Mix org-wide tags from `KropathConfig` with Lambda-specific governance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    tracingMode: "Active"
  defaults:
    runtime: "python3.12"
    memorySize: 256
    timeout: 30
    tags:
      team: "platform"
      billing-entity: "engineering"
    syncedLabels:
      managed-by: "kropath"
      cost-tracking: "enabled"
```

## Status Fields

After the `LambdaConfig` is created and the controller reconciles it, `status.effectiveConfig` contains the pre-merged governance ready for Lambda resource instances to consume:

```yaml
status:
  effectiveConfig:
    mandatory:
      runtime: "python3.12"
      memorySize: 512
      timeout: 60
      tracingMode: "Active"
      kmsKeyArn: "arn:aws:kms:us-east-1:123456789012:key/abc"
      namingTemplate: "prod-{namespace}-{name}"
      tags:
        environment: "production"
        # ... org-wide tags from KropathConfig merged in
      syncedLabels:
        managed-by: "kropath"
    defaults:
      runtime: "python3.12"
      memorySize: 256
      timeout: 30
      tracingMode: "PassThrough"
      kmsKeyArn: ""
      namingTemplate: "{namespace}-{name}"
      tags: {}
      syncedLabels: {}
    aws:
      region: "us-east-1"
      accountId: "123456789012"
```

A Lambda function instance reads `effectiveConfig` to determine which governance policies apply, then merges instance spec values according to the cascade rules (mandatory always wins, then instance spec, then defaults).

## Deployment Strategy

1. **Create the CRD profile** in `kro-system` namespace during cluster setup
2. **Reference the profile** in each Lambda function via `spec.configRef`
3. **Update governance** by editing the `LambdaConfig` CR; all instances using that profile automatically inherit the updated settings
4. **Tier-specific changes**: Update only the mandatory tier for platform enforcement, only defaults for baseline settings

## Key Behaviors

### Dual-Tier Validation

The `LambdaConfig` schema prevents misconfiguration by disallowing both tiers to be set simultaneously:

```yaml
# This is REJECTED:
spec:
  mandatory:
    runtime: "python3.12"
  defaults:
    runtime: "nodejs20.x"  # ❌ Both tiers set for the same field
# Error: "runtime must be set in either mandatory or defaults, not both."
```

### Namespace Scope

A `LambdaConfig` named `general-policy` in `kro-system` is the org-wide profile. You can also create namespace-local profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: LambdaConfig
metadata:
  name: general-policy  # Same name, different namespace
  namespace: app-team
spec:
  # Local overrides for the app-team namespace
```

The controller merges both sources: org-wide settings + namespace-local settings. Both must not set the same field in the same tier.

### Tag and Label Merging

Tags, syncedLabels, and syncedAnnotations use **additive merge semantics** — tags from both `KropathConfig` (org-wide) and `LambdaConfig` (Lambda-specific) coexist in `status.effectiveConfig`. This allows:

- Org teams to apply cost-center tags to all resources
- Lambda teams to add Lambda-specific tracking tags
- No tier-specific conflicts (no "both tiers must be empty" rule for maps)

## Troubleshooting

### "must be set in either mandatory or defaults, not both"

You've set the same field in both the mandatory and defaults tiers. Decide whether it's a platform enforcement (mandatory) or a sensible baseline (defaults), and remove it from the other tier.

### Lambda function not inheriting governance settings

Ensure the `LambdaConfig` CR has the label `aws.kropath.run/resource-name: <its-name>`. The label is auto-injected by the controller, but if missing, re-apply the CR:

```bash
kubectl apply -f lambda-config.yaml -n kro-system
```

Verify the label:

```bash
kubectl get lambdaconfig general-policy -n kro-system --show-labels
```

### Override mandatory policy for a specific function

The `spec.nameOverride` field in a Lambda function is the **only** escape hatch for mandatory naming templates. For other mandatory fields (runtime, encryption key, tracing), there is no override — mandatory is by design. Contact your platform team if you need an exception.

## Reference

- **Design:** See `kropath-core/docs/families/aws/lambda.md` for the complete Lambda family governance design
- **ADR reference:** ADR-015 §4 covers governance CRD design and the mandatory/defaults tier pattern
- **Controller behavior:** The `kropath-controller` writes `status.effectiveConfig` after merging all sources
