# SESConfig — Governance Reference

`SESConfig` is a Kubernetes CRD that platform teams use to enforce policies across all SES configuration sets in a namespace or cluster.

## Overview

Platform teams create named `SESConfig` profiles (for example: `general-policy`, `transactional`, `compliance`) that specify:

- **Naming conventions** — required naming templates for configuration set names
- **Tag and label policies** — mandatory and default tags applied to all configuration sets
- **Deletion policies** — whether resources are retained or deleted when the Kubernetes CR is removed

Application teams select a profile via `spec.configRef` on their `SESConfigurationSet` resource. If the named profile doesn't exist, the system falls back to `general-policy`.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster (provides the governance cascade logic)
- A namespace where resources will be provisioned

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    # These fields are enforced — application teams cannot override them
    namingTemplate: ""            # "" | "{namespace}-{name}" pattern (empty = not enforced)
    tags:
      cost-centre: platform
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}

  defaults:
    # These fields are applied when not overridden by application teams
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Fields

### Naming Template (`namingTemplate`)

Enforces a naming convention for all configuration sets. Templates use token substitution:

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

AWS requires configuration set names to:
- Use characters `[a-zA-Z0-9_-]` (letters, digits, hyphens, underscores)
- Be 1–64 characters long
- Not contain whitespace

If a template resolves to an invalid name (unresolved tokens, too long, invalid characters), the resource will be rejected and marked with `status.namingStatus: "invalid-unresolved-tokens"`.

### Tags, Labels, and Annotations

Policies control which tags, labels, and Kubernetes annotations are applied to all configuration sets.

**Mandatory entries** (`spec.mandatory.tags`, `spec.mandatory.syncedLabels`, `spec.mandatory.syncedAnnotations`) are enforced — application teams cannot override or remove them.

**Default entries** (`spec.defaults.tags`, `spec.defaults.syncedLabels`, `spec.defaults.syncedAnnotations`) are applied unless the application team specifies their own values.

**Tags** are applied to both Kubernetes labels (via `syncedLabels` merge) and used for naming token resolution (`{tag.<key>}`). Tags are NOT forwarded to AWS cloud resources (SES configuration sets do not support cloud tag reconciliation in the current ACK controller version).

**Synced labels** appear in Kubernetes resource labels (prefixed with `aws.kropath.run/`).

**Annotations** are mirrored to Kubernetes resource metadata (prefixed with `aws.kropath.run/`).

**Example — Multi-tier tagging policy:**
```yaml
spec:
  mandatory:
    tags:
      cost-centre: platform
      compliance: required
    syncedLabels:
      team: email-platform
  defaults:
    tags:
      managed-by: kropath
    syncedLabels:
      data-class: internal
    syncedAnnotations:
      provisioner: kropath
```

## Profile-Based Governance

Create multiple profiles for different requirements:

```yaml
---
# General governance profile
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath

---
# Compliance profile
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    namingTemplate: "compliance-{namespace}-{name}"
    tags:
      compliance: required
      audit-trail: yes
  defaults:
    tags:
      managed-by: kropath

---
# Transactional profile — lenient
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfig
metadata:
  name: transactional
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: transactional
spec:
  mandatory: {}
  defaults:
    namingTemplate: "tx-{namespace}-{name}"
    tags:
      email-type: transactional
      managed-by: kropath
    syncedLabels:
      category: transactional
```

Application teams select a profile when creating configuration sets:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfigurationSet
metadata:
  name: order-confirmations
  namespace: email-prod
spec:
  configRef: compliance  # Use the compliance profile
  # ... rest of spec
```

## Fallthrough Behavior

If an application team references a profile that doesn't exist, the system falls back to `general-policy` automatically. Always ensure `general-policy` exists in the cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SESConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade

When you apply a `SESConfigurationSet`, the effective configuration is resolved from ten levels of governance (ADR-015 §5.3):

1. Global KropathConfig mandatory (`KropathConfig.spec.mandatory.tags`)
2. Namespace KropathConfig mandatory
3. Profile mandatory (this SESConfig)
4. Namespace profile mandatory
5. Instance override (`spec.tags`, `spec.syncedLabels`, `spec.syncedAnnotations`)
6. Namespace profile defaults
7. Profile defaults
8. Namespace KropathConfig defaults
9. Global KropathConfig defaults
10. RGD built-in default (e.g., `retain` for deletion policy)

Higher levels override lower levels. The `kropath-controller` pre-merges these into `status.effectiveConfig` on each `SESConfig` CR, and the RGD reads a single `effectiveConfig` value.

### Example Cascade Resolution

Given:
- Global KropathConfig `mandatory.tags: {cost-centre: org}`
- Profile mandatory `tags: {compliance: required}`
- Instance `spec.tags: {team: email}`

**Result:** The merged mandatory tags are `{cost-centre: org, compliance: required}`. The instance `team: email` tag is added on top. The configuration set gets all three tags.

## Org-Wide Governance via KropathConfig

For requirements that apply to all profiles and all configuration sets (for example, "all configuration sets must have a cost-centre tag"), use `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global-governance
  namespace: kro-system
spec:
  mandatory:
    tags:
      cost-centre: shared-platform  # Org-wide mandatory tag
  # ... other family sections
```

This mandatory tier (level 1) overrides all `SESConfig` mandatory tiers (levels 3–4).

## Deployment

Deploy `SESConfig` CRs to your cluster:

```bash
kubectl apply -f sesconfig.yaml
```

Then application teams reference the profile:

```bash
kubectl apply -f my-config-set.yaml
```

The `spec.configRef: compliance` selects the compliance profile; if it doesn't exist, `general-policy` is used.

## Common Patterns

### Strict Compliance Environment
```yaml
spec:
  mandatory:
    namingTemplate: "compliance-{namespace}-{name}"
    tags:
      compliance: required
      audit-trail: yes
    syncedLabels:
      data-class: sensitive
```

### Cost-Optimized Development
```yaml
spec:
  mandatory: {}
  defaults:
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      cost-optimization: enabled
      environment: development
```

### Multi-Environment with Profiles
Create `dev`, `staging`, `prod` profiles in the same namespace, each with different naming templates and tag policies. Application teams select the appropriate profile for their workload environment.

## Troubleshooting

**"My configuration set is using the wrong naming template"**
- Check the `configRef` you specified
- Verify the named profile exists in the cluster
- If the profile doesn't exist, `general-policy` is used
- Inspect `status.namingStatus` on your configuration set resource

**"My mandatory tags aren't being enforced"**
- Ensure the `SESConfig` CR has `status.effectiveConfig` populated (the controller writes this)
- Verify `mandatory.tags` are defined (not empty)
- Check that application team didn't specify a profile that doesn't exist (fallback to `general-policy`)

**"Tags aren't being applied"**
- Check both `KropathConfig` and `SESConfig` tags (both are merged)
- Verify `metadata.labels` on the Kubernetes resource have the `aws.kropath.run/` prefix
- Remember that SES configuration sets do not support cloud tag reconciliation — tags are used for Kubernetes metadata and naming tokens only, not forwarded to AWS

## See Also

- [SESConfigurationSet User Guide](./sesconfigurationset.md)
- [SES Resource Family Overview](./README.md)
- [AWS SES Configuration Sets Guide](https://docs.aws.amazon.com/ses/latest/dg/configuration-sets.html)
