---
title: StepFunctionsConfig — Governance Reference
description: "`StepFunctionsConfig` is a Kubernetes CRD that platform teams use to enforce policies across all Step Functions resources (state machines and activities) in a namespace or cluster."
doc_type: reference
---
# StepFunctionsConfig — Governance Reference

`StepFunctionsConfig` is a Kubernetes CRD that platform teams use to enforce policies across all Step Functions resources (state machines and activities) in a namespace or cluster.

## Overview

Platform teams create named `StepFunctionsConfig` profiles (for example: `general-policy`, `pci`, `hipaa`) that specify:

- **Observability requirements** — mandatory logging levels, tracing, execution data inclusion
- **Naming conventions** — required naming templates for resource names
- **Tag and label policies** — mandatory and default tags applied to all resources
- **Deletion policies** — whether resources are retained or deleted when the Kubernetes CR is removed

Application teams select a profile via `spec.configRef` on their `StepFunctionsStateMachine` or `StepFunctionsActivity` resource. If the named profile doesn't exist, the system falls back to `general-policy`.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster (provides the governance cascade logic)
- A namespace where resources will be provisioned

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    # These fields are enforced — application teams cannot override them
    loggingLevel: ""              # "" | ALL | ERROR | FATAL | OFF (empty = not enforced)
    tracingEnabled: null          # true | false | null (null = not enforced)
    includeExecutionData: null    # true | false | null
    namingTemplate: ""            # "{namespace}-{name}" pattern (empty = not enforced)
    tags:
      cost-centre: platform
    syncedLabels: {}
    syncedAnnotations: {}

  defaults:
    # These fields are applied when not overridden by application teams
    loggingLevel: "OFF"           # No execution logging by default
    tracingEnabled: false         # X-Ray tracing disabled by default
    includeExecutionData: false   # Execution data not included in logs by default
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Fields

### Logging Level (`loggingLevel`)

Controls execution logging for state machines and activities.

**Valid values:**
- `ALL` — Log all events (start, success, failure, input, output)
- `ERROR` — Log only error events
- `FATAL` — Log only fatal errors
- `OFF` — No execution logging (AWS default)

**Example — Mandatory logging for compliance:**
```yaml
spec:
  mandatory:
    loggingLevel: "ALL"  # All state machines must log everything for audit trail
```

When logging is enabled, you must specify a CloudWatch Logs destination ARN on each state machine resource.

### Tracing (`tracingEnabled`)

Controls AWS X-Ray tracing for state machine executions.

**Example — Mandatory tracing for production:**
```yaml
spec:
  mandatory:
    tracingEnabled: true  # All production state machines must be traced
```

### Execution Data (`includeExecutionData`)

Controls whether execution input and output are included in CloudWatch Logs. Enabling this increases log volume and may expose sensitive data (PII, credentials, business logic).

**Example — Compliance-sensitive environment:**
```yaml
spec:
  mandatory:
    includeExecutionData: false  # Never include execution data in logs
```

### Naming Template (`namingTemplate`)

Enforces a naming convention for all Step Functions resources. Templates use token substitution:

- `{name}` — The resource's `metadata.name`
- `{namespace}` — The resource's Kubernetes namespace
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — The profile name (e.g., `general-policy`)
- `{tag.<key>}` — Merge tag values into the name

**Examples:**
```yaml
spec:
  defaults:
    # Simple namespace-based naming
    namingTemplate: "{namespace}-{name}"

    # Environment-aware naming
    namingTemplate: "{tag.env}-{namespace}-{name}"

    # Account and region aware
    namingTemplate: "{account_id}-{region}-{name}"
```

AWS requires state machine and activity names to:
- Use characters `[a-zA-Z0-9\-_]+` (letters, digits, hyphens, underscores)
- Maximum 80 characters
- Not contain whitespace

If a template resolves to an invalid name (unresolved tokens, too long, invalid characters), the resource will be rejected and marked with `status.namingStatus: "invalid-unresolved-tokens"`.

### Tags, Labels, and Annotations

Policies control which tags, labels, and Kubernetes annotations are applied to all resources.

**Mandatory entries** (`spec.mandatory.tags`, `spec.mandatory.syncedLabels`, `spec.mandatory.syncedAnnotations`) are enforced — application teams cannot override or remove them.

**Default entries** (`spec.defaults.tags`, `spec.defaults.syncedLabels`, `spec.defaults.syncedAnnotations`) are applied unless the application team specifies their own values.

**Tags** are applied to AWS resources (state machines and activities only — aliases don't support cloud tags).

**Synced labels** appear in both Kubernetes resource labels (prefixed with `aws.kropath.run/`) and cloud tags (to satisfy ADR-015 §6.1).

**Annotations** are mirrored to Kubernetes resource metadata.

**Example — Multi-tier tagging policy:**
```yaml
spec:
  mandatory:
    tags:
      cost-centre: platform
      compliance: required
    syncedLabels:
      team: workflows
  defaults:
    tags:
      managed-by: kropath
    syncedLabels:
      data-class: internal
```

## Profile-Based Governance

Create multiple profiles for different requirements:

```yaml
---
# General governance profile
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    loggingLevel: "ERROR"
    tracingEnabled: false
    namingTemplate: "{namespace}-{name}"

---
# PCI-DSS compliance profile
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    loggingLevel: "ALL"        # All events logged for audit
    tracingEnabled: true       # Full tracing for compliance
    includeExecutionData: false  # No sensitive data in logs
    tags:
      compliance: pci-dss
  defaults: {}

---
# Development profile — lenient
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}
  defaults:
    loggingLevel: "OFF"
    tracingEnabled: false
    namingTemplate: "dev-{namespace}-{name}"
```

Application teams select a profile when creating resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsStateMachine
metadata:
  name: order-processor
  namespace: workflows-prod
spec:
  configRef: pci  # Use the PCI-DSS compliance profile
  # ... rest of spec
```

## Fallthrough Behavior

If an application team references a profile that doesn't exist, the system falls back to `general-policy` automatically. Always ensure `general-policy` exists in the cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: StepFunctionsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    loggingLevel: "OFF"
    tracingEnabled: false
    includeExecutionData: false
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade

When you apply a `StepFunctionsStateMachine`, the effective configuration is resolved from ten levels of governance (ADR-015 §5.3):

1. Global KropathConfig mandatory (`KropathConfig.spec.mandatory.stepfunctions.loggingLevel`)
2. Namespace KropathConfig mandatory
3. Profile mandatory (this StepFunctionsConfig)
4. Namespace profile mandatory
5. Instance override (`spec.loggingLevel`, `spec.tracingEnabled`, etc.)
6. Namespace profile defaults
7. Profile defaults
8. Namespace KropathConfig defaults
9. Global KropathConfig defaults
10. RGD built-in default (e.g., `OFF` for logging)

Higher levels override lower levels. The `kropath-controller` pre-merges these into `status.effectiveConfig` on each `StepFunctionsConfig` CR, and the RGD reads a single `effectiveConfig` value.

### Example Cascade Resolution

Given:
- Global KropathConfig `mandatory.stepfunctions.loggingLevel: ""` (not enforced)
- Profile mandatory `loggingLevel: "ALL"`
- Instance `spec.loggingLevel: "ERROR"`

**Result:** The profile mandatory `ALL` wins. The instance `ERROR` cannot override a mandatory tier. The state machine is created with `loggingConfiguration.level: "ALL"`.

## Org-Wide Governance via KropathConfig

For requirements that apply to all profiles and all state machines (for example, "all workflows must be traced for cost analysis"), use `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global-governance
  namespace: kro-system
spec:
  mandatory:
    stepfunctions:
      loggingLevel: "ERROR"  # Org-wide: all state machines must log errors
  # ... other family sections
```

This mandatory tier (level 1) overrides all `StepFunctionsConfig` mandatory tiers (levels 3–4).

## Deployment

Deploy `StepFunctionsConfig` CRs to your cluster:

```bash
kubectl apply -f stepfunctionsconfig.yaml
```

Then application teams reference the profile:

```bash
kubectl apply -f my-state-machine.yaml
```

The `spec.configRef: pci` selects the PCI profile; if it doesn't exist, `general-policy` is used.

## Common Patterns

### Strict Compliance Environment
```yaml
spec:
  mandatory:
    loggingLevel: "ALL"
    tracingEnabled: true
    includeExecutionData: false
    tags:
      compliance: required
      audit-trail: yes
```

### Cost-Optimized Development
```yaml
spec:
  mandatory: {}
  defaults:
    loggingLevel: "OFF"
    tracingEnabled: false
    tags:
      cost-optimization: enabled
```

### Multi-Environment with Profiles
Create `dev`, `staging`, `prod` profiles in the same namespace, each with different logging/tracing/naming policies. Application teams select the appropriate profile for their workload environment.

## Troubleshooting

**"My state machine is using the wrong naming template"**
- Check the `configRef` you specified
- Verify the named profile exists in the cluster
- If the profile doesn't exist, `general-policy` is used
- Inspect `status.namingStatus` on your state machine resource

**"My mandatory loggingLevel isn't being enforced"**
- Ensure the `StepFunctionsConfig` CR has `status.effectiveConfig` populated (the controller writes this)
- Verify `mandatory.loggingLevel` is non-empty (not `""`)
- Check that application team didn't specify a profile that doesn't exist (fallback to `general-policy`)

**"Tags aren't being applied"**
- Check both `KropathConfig` and `StepFunctionsConfig` tags (both are merged)
- Verify `metadata.labels` on the Kubernetes resource have the `aws.kropath.run/` prefix
- Verify cloud resource tags match (view in AWS Console)

## See Also

- [StepFunctionsStateMachine User Guide](./stepfunctionsstatemachine.md)
- [StepFunctionsActivity User Guide](./stepfunctionsactivity.md)
- [Getting Started](./getting-started.md)
