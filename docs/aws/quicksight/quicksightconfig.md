# QuickSightConfig — Governance Reference

`QuickSightConfig` is a Kubernetes CRD that platform teams use to enforce policies across all QuickSight resources (data sources, datasets, dashboards, and analyses) in a namespace or cluster.

## Overview

Platform teams create named `QuickSightConfig` profiles (for example: `general-policy`, `compliance`, `analytics`) that specify:

- **Import mode governance** — control whether datasets use SPICE (cached) or DIRECT_QUERY (live) to manage costs
- **Naming conventions** — required naming templates for all QuickSight resources
- **Tag and label policies** — mandatory and default tags applied to all resources
- **Synced labels and annotations** — Kubernetes labels and annotations propagated to child resources

Application teams select a profile via `spec.configRef` on their `QuickSightDataSet`, `QuickSightDashboard`, and `QuickSightAnalysis` resources. If the named profile doesn't exist, the system falls back to `general-policy`.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster (provides the governance cascade logic)
- A namespace where resources will be provisioned
- AWS account and region configured via `KropathConfig`

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    # These fields are enforced — application teams cannot override them
    importMode: ""            # "" | "SPICE" | "DIRECT_QUERY" (empty = not enforced)
    namingTemplate: ""        # "" | "{namespace}-{name}" pattern (empty = not enforced)
    tags:
      cost-centre: platform
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}

  defaults:
    # These fields are applied when not overridden by application teams
    importMode: "SPICE"       # Default import mode (SPICE prevents unexpected per-query costs)
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Fields

### Import Mode (`importMode`)

Controls how datasets load data. Prevents unexpected AWS costs by enforcing a default caching strategy.

- **SPICE** — In-memory cached model. Data is imported once, then queried from cache. Charges based on SPICE capacity used.
- **DIRECT_QUERY** — Live query mode. Data is queried directly from the source each time. Charges per query (can be expensive at scale).

The `general-policy` profile ships with `defaults.importMode: "SPICE"` to prevent teams from accidentally using DIRECT_QUERY and incurring per-query costs.

**Mandatory mode** enforces a single import mode for all datasets:
```yaml
spec:
  mandatory:
    importMode: "SPICE"  # All datasets MUST use SPICE
```

**Default mode** provides a fallback when the application team doesn't specify:
```yaml
spec:
  defaults:
    importMode: "SPICE"  # Use SPICE unless overridden at the instance level
```

**Note:** You cannot set `importMode` in both `mandatory` and `defaults` tiers simultaneously. The system will reject the profile with an admission webhook error.

### Naming Template (`namingTemplate`)

Enforces a naming convention for all QuickSight resources. Templates use token substitution:

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

AWS QuickSight requires resource names to:
- Use characters `[a-zA-Z0-9_-]` (letters, digits, hyphens, underscores)
- Be 1–128 characters long
- Not contain whitespace

If a template resolves to an invalid name (unresolved tokens, too long, invalid characters), the resource will be rejected and marked with `status.namingStatus: "invalid-unresolved-tokens"`.

**Note:** Like `importMode`, you cannot set `namingTemplate` in both `mandatory` and `defaults` tiers simultaneously.

### Tags, Labels, and Annotations

Policies control which tags, labels, and Kubernetes annotations are applied to all QuickSight resources.

**Mandatory entries** (`spec.mandatory.tags`, `spec.mandatory.syncedLabels`, `spec.mandatory.syncedAnnotations`) are enforced — application teams cannot override or remove them.

**Default entries** (`spec.defaults.tags`, `spec.defaults.syncedLabels`, `spec.defaults.syncedAnnotations`) are applied unless the application team specifies their own values.

**Tags** are used for naming token resolution (`{tag.<key>}`) and Kubernetes label merging.

**Synced labels** appear in Kubernetes resource labels (prefixed with `aws.kropath.run/`).

**Annotations** are mirrored to Kubernetes resource metadata (prefixed with `aws.kropath.run/`).

**Unlike `importMode` and `namingTemplate`, tags, synced labels, and synced annotations can be set in both tiers simultaneously** — they are merged by the controller (mandatory entries win on key conflicts).

**Example — Multi-tier tagging policy:**
```yaml
spec:
  mandatory:
    tags:
      cost-centre: platform
      compliance: required
    syncedLabels:
      team: analytics-platform
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
# General governance profile — default for all teams
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    importMode: "SPICE"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath

---
# Compliance profile — strict enforcement
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    importMode: "SPICE"  # Enforce SPICE (no per-query costs)
    namingTemplate: "compliance-{namespace}-{name}"
    tags:
      compliance: required
      audit-trail: yes
  defaults:
    tags:
      managed-by: kropath

---
# Analytics profile — flexible with cost tracking
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: analytics
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: analytics
spec:
  mandatory: {}
  defaults:
    importMode: "SPICE"
    namingTemplate: "analytics-{namespace}-{name}"
    tags:
      team: analytics
      cost-tracking: enabled
    syncedLabels:
      workload-type: analytics
```

Application teams select a profile when creating QuickSight resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: orders-dataset
  namespace: analytics
spec:
  configRef: analytics  # Use the analytics profile
  # ... rest of spec
```

## Fallthrough Behavior

If an application team references a profile that doesn't exist, the system falls back to `general-policy` automatically. Always ensure `general-policy` exists in the cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    importMode: "SPICE"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade

When you apply a `QuickSightDataSet`, `QuickSightDashboard`, or `QuickSightAnalysis`, the effective configuration is resolved from multiple governance levels (ADR-010):

1. Global KropathConfig mandatory (highest priority)
2. Namespace KropathConfig mandatory
3. QuickSightConfig profile mandatory
4. Instance override (`spec.importMode`, `spec.tags`, `spec.syncedLabels`, `spec.syncedAnnotations`)
5. QuickSightConfig profile defaults
6. Namespace KropathConfig defaults
7. Global KropathConfig defaults
8. RGD built-in default (lowest priority)

Priority runs top to bottom — level 1 (Global KropathConfig mandatory) always wins; each subsequent level applies only when the levels above it are unset. The `kropath-controller` pre-merges these into `status.effectiveConfig` on each `QuickSightConfig` CR, and the RGDs read a single `effectiveConfig` value.

**Note on `importMode` specifically:** Global `KropathConfig.spec.mandatory.quicksight.importMode` takes absolute priority and cannot be overridden by any profile or instance.

### Example Cascade Resolution — Import Mode

Given:
- Global KropathConfig `spec.mandatory.quicksight.importMode: "SPICE"`
- Compliance profile `spec.defaults.importMode: "DIRECT_QUERY"`
- Instance `spec.importMode: ""` (not specified)

**Result:** The instance uses `SPICE` (global mandatory wins). The profile default is ignored.

### Example Cascade Resolution — Tags

Given:
- Global KropathConfig `spec.mandatory.tags: {cost-centre: org}`
- Profile mandatory `tags: {compliance: required}`
- Instance `spec.tags: {team: analytics}`

**Result:** The merged mandatory tags are `{cost-centre: org, compliance: required}`. The instance `team: analytics` tag is added on top. The resource gets all three tags.

## Org-Wide Governance via KropathConfig

For requirements that apply to all profiles and all resources (for example, "all QuickSight datasets must have a cost-centre tag"), use `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global-governance
  namespace: kro-system
spec:
  mandatory:
    quicksight:
      importMode: "SPICE"  # Org-wide: all datasets must use SPICE
    tags:
      cost-centre: shared-platform  # Org-wide mandatory tag
  # ... other family sections
```

This mandatory tier (level 1) overrides all `QuickSightConfig` mandatory tiers (level 3).

## Deployment

Deploy `QuickSightConfig` CRs to your cluster:

```bash
kubectl apply -f quicksightconfig.yaml
```

Then application teams reference the profile when creating resources:

```bash
kubectl apply -f my-dataset.yaml
```

The `spec.configRef: analytics` selects the analytics profile; if it doesn't exist, `general-policy` is used.

## Common Patterns

### Cost-Conscious Environment

Enforce SPICE and cost tracking tags:

```yaml
spec:
  mandatory:
    importMode: "SPICE"
    tags:
      cost-tracking: enabled
  defaults:
    namingTemplate: "cost-tracked-{namespace}-{name}"
    syncedLabels:
      cost-optimization: enabled
```

### Compliance Environment

Strict naming and audit enforcement:

```yaml
spec:
  mandatory:
    importMode: "SPICE"
    namingTemplate: "compliance-{namespace}-{name}"
    tags:
      compliance: required
      audit-trail: yes
    syncedLabels:
      data-class: sensitive
```

### Multi-Environment with Profiles

Create `dev`, `staging`, `prod` profiles in the same namespace, each with different import modes and naming templates. Application teams select the appropriate profile for their workload environment:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: prod
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod
spec:
  mandatory:
    importMode: "SPICE"  # Prod always uses SPICE
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production

---
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}
  defaults:
    importMode: "SPICE"
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development
```

## Validation Rules

The admission webhook enforces mutual-exclusion rules on scalar governance fields:

- **importMode conflict:** Cannot set `importMode` in both `mandatory` and `defaults` tiers.
  - Error: "importMode cannot be set in both mandatory and defaults tiers"
- **namingTemplate conflict:** Cannot set `namingTemplate` in both `mandatory` and `defaults` tiers.
  - Error: "namingTemplate cannot be set in both mandatory and defaults tiers"

Map fields (tags, syncedLabels, syncedAnnotations) have no mutual-exclusion rule — both tiers can be set and will be merged.

## Troubleshooting

**"My dataset is using the wrong import mode"**
- Check the `configRef` you specified on the dataset
- Verify the named profile exists in the cluster
- If the profile doesn't exist, `general-policy` is used
- Check `status.effectiveConfig.defaults.importMode` on the QuickSightConfig to see what was resolved
- If global KropathConfig has `mandatory.quicksight.importMode` set, that always wins

**"I'm getting 'cannot be set in both mandatory and defaults' error"**
- Check that you haven't set the same field in both `spec.mandatory` and `spec.defaults` for `importMode` or `namingTemplate`
- Scalar fields (importMode, namingTemplate) have a mutual-exclusion rule; map fields (tags, syncedLabels, syncedAnnotations) do not

**"My mandatory tags aren't being enforced"**
- Ensure the `QuickSightConfig` CR has `status.effectiveConfig` populated (the controller writes this)
- Verify `spec.mandatory.tags` are defined (not empty `{}`)
- Check that application team didn't specify a profile that doesn't exist (fallback to `general-policy`)
- Check global `KropathConfig.spec.mandatory.tags` — those override all profile mandatory tags

**"My naming template isn't resolving correctly"**
- Verify all tokens in the template are available (`{namespace}`, `{name}`, `{account_id}`, `{region}`, `{tag.<key>}`)
- Check that the resolved name is valid (matches `[a-zA-Z0-9_-]` and is 1–128 characters)
- Inspect `status.namingStatus` on your QuickSight resource for error details

**"The profile fallback isn't working"**
- Ensure `general-policy` profile exists and has the `aws.kropath.run/resource-name: general-policy` label
- Check the cluster logs for controller errors: `kubectl logs -n kro-system -l app=kropath-controller`

## See Also

- [QuickSightDataSet User Guide](./quicksightdataset.md)
- [QuickSightDashboard User Guide](./quicksightdashboard.md)
- [QuickSightAnalysis User Guide](./quicksightanalysis.md)
- [AWS QuickSight User Guide](https://docs.aws.amazon.com/quicksight/latest/user/what-is.html)
- [Engineering Standards](../engineering-standards.md) — shared governance rules across all families
