---
title: RecycleBinConfig — Governance for Recycle Bin Rules
description: "The `RecycleBinConfig` resource defines governance policies for the EBS Recycle Bin family."
doc_type: reference
---
# RecycleBinConfig — Governance for Recycle Bin Rules

The `RecycleBinConfig` resource defines governance policies for the EBS Recycle Bin family. Platform teams deploy named profiles (e.g., `general-policy`, `compliance`) to enforce retention and locking standards. Recycle Bin rule instances select a profile via `spec.configRef` to inherit those controls.

## Overview

`RecycleBinConfig` is a per-resource-type configuration CRD that establishes two tiers of governance:

- **Mandatory tier** — Platform enforcement that overrides instance spec (e.g., "all rules must retain for at least 90 days and be locked")
- **Defaults tier** — Sensible baselines that apply when a rule spec is empty (e.g., "if no retention period is specified, default to 7 days")

Each field can be set in **only one** tier at a time — the schema prevents both tiers being set simultaneously. This ensures clear precedence: mandatory always wins; defaults only apply when a rule instance doesn't specify a value.

## Creating a Governance Profile

Create a `RecycleBinConfig` in the `kro-system` namespace to define a reusable profile:

### General Policy (Permissive)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    retentionPeriodValue: 7
    retentionPeriodUnit: "DAYS"
    lockRule: false
    unlockDelayValue: 30
    unlockDelayUnit: "DAYS"
```

This profile enforces no mandatory policies but provides sensible defaults: 7-day retention without locking.

### Compliance Profile (Strict)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: compliance
  namespace: kro-system
spec:
  mandatory:
    retentionPeriodValue: 90
    retentionPeriodUnit: "DAYS"
    lockRule: true
    unlockDelayValue: 30
    unlockDelayUnit: "DAYS"
  defaults: {}
```

This profile enforces strict retention (minimum 90 days) and mandatory locking with a 30-day unlock delay. No defaults; mandatory rules always apply.

## Governance Fields

| Field | Type | Mandatory semantics | Defaults semantics |
|---|---|---|---|
| `retentionPeriodValue` | integer (1–3650) | Minimum enforced retention; overrides instance value | Baseline retention if instance omits |
| `retentionPeriodUnit` | string | Enforces the unit (typically `DAYS`) | Default unit if instance omits |
| `lockRule` | boolean | Forces all rules to be locked | Default locking behavior (false = don't lock by default) |
| `unlockDelayValue` | integer (7–3650) | Enforces minimum unlock delay | Default delay if instance omits (when locking is used) |
| `unlockDelayUnit` | string | Enforces the delay unit | Default unit if instance omits |
| `tags` | map | Mandatory cloud tags merged into all rules using this profile | Default cloud tags; overridable per-instance |
| `syncedLabels` | map | Merged into K8s labels AND cloud tags (prefixed `aws.kropath.run/`); cannot be removed | Baseline synced labels; overridable per-instance |
| `syncedAnnotations` | map | Merged into K8s annotations (prefixed `aws.kropath.run/`); cannot be removed | Baseline synced annotations; overridable per-instance |

## Complete Examples

### Development Profile

Permissive profile for non-production environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: dev-policy
  namespace: kro-system
spec:
  defaults:
    retentionPeriodValue: 3
    retentionPeriodUnit: "DAYS"
    lockRule: false
    unlockDelayValue: 7
    unlockDelayUnit: "DAYS"
    tags:
      environment: "dev"
      cost-center: "engineering"
    syncedLabels:
      managed-by: "kropath"
```

### Production Profile with Compliance Tags

Strict profile with mandatory retention and tagging:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: prod-compliant
  namespace: kro-system
spec:
  mandatory:
    retentionPeriodValue: 30
    retentionPeriodUnit: "DAYS"
    lockRule: true
    unlockDelayValue: 30
    unlockDelayUnit: "DAYS"
    tags:
      compliance: "required"
      data-classification: "sensitive"
    syncedLabels:
      audit-required: "true"
      compliance-controlled: "true"
  defaults:
    tags:
      team: "platform"
```

Rules using this profile must retain for at least 30 days, be locked on creation, and include both the mandatory compliance tags and default team tag.

## Status Fields

After the `RecycleBinConfig` is created and the controller reconciles it, `status.effectiveConfig` contains the pre-merged governance ready for Recycle Bin rule instances to consume:

```yaml
status:
  effectiveConfig:
    mandatory:
      retentionPeriodValue: 90
      retentionPeriodUnit: "DAYS"
      lockRule: true
      unlockDelayValue: 30
      unlockDelayUnit: "DAYS"
      tags:
        compliance: "required"
        # ... org-wide tags from KropathConfig merged in
      syncedLabels:
        managed-by: "kropath"
    defaults:
      retentionPeriodValue: 7
      retentionPeriodUnit: "DAYS"
      lockRule: false
      unlockDelayValue: 30
      unlockDelayUnit: "DAYS"
      tags: {}
      syncedLabels: {}
    aws:
      region: "us-east-1"
      accountId: "123456789012"
```

A Recycle Bin rule reads `effectiveConfig` to determine which governance policies apply, then merges instance spec values according to the cascade rules (mandatory always wins, then instance spec, then defaults).

## Deployment Strategy

1. **Create the CRD profiles** in `kro-system` namespace during cluster setup
2. **Reference the profile** in each Recycle Bin rule via `spec.configRef`
3. **Update governance** by editing the `RecycleBinConfig` CR; all rules using that profile automatically inherit the updated settings
4. **Tier-specific changes**: Update only the mandatory tier for platform enforcement, only defaults for baseline settings

## Key Behaviors

### Dual-Tier Validation

The `RecycleBinConfig` schema prevents misconfiguration by disallowing both tiers to be set simultaneously for scalar fields:

```yaml
# This is REJECTED:
spec:
  mandatory:
    retentionPeriodValue: 90
  defaults:
    retentionPeriodValue: 7  # ❌ Both tiers set for the same field
# Error: "retentionPeriodValue cannot be set in both mandatory and defaults"
```

Maps like `tags`, `syncedLabels`, and `syncedAnnotations` can be set in both tiers (they merge).

### Namespace Scope

A `RecycleBinConfig` named `general-policy` in `kro-system` is the org-wide profile. You can also create namespace-local profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: general-policy  # Same name, different namespace
  namespace: app-team
spec:
  # Local overrides for the app-team namespace
```

The controller merges both sources: org-wide settings + namespace-local settings. Both must not set the same scalar field in the same tier.

### Tag and Label Merging

Tags, syncedLabels, and syncedAnnotations use **additive merge semantics** — tags from both `KropathConfig` (org-wide) and `RecycleBinConfig` (Recycle Bin-specific) coexist in `status.effectiveConfig`. This allows:

- Org teams to apply cost-center tags to all resources
- Recycle Bin teams to add rule-specific tracking tags
- No tier-specific conflicts for maps (no "both tiers must be empty" rule)

## Retention Period Range

Valid retention periods: **0–3650 days**

- `0` = not enforced (skipped in governance cascade)
- `1–3650` = valid retention period (number of days)
- Non-zero mandatory values override all lower-priority values

### Unlock Delay Range

Valid unlock delays (when locking is enabled): **0–3650 days**

- `0` = not enforced (skipped in governance cascade)
- `7–3650` = valid unlock delay (minimum 7 days when enforced)

If `lockRule: true` and `unlockDelayValue: 0` (not enforced), the rule uses AWS's default unlock delay (7 days).

## Troubleshooting

### "cannot be set in both mandatory and defaults"

You've set the same scalar field in both the mandatory and defaults tiers. Decide whether it's a platform enforcement (mandatory) or a sensible baseline (defaults), and remove it from the other tier.

Maps like `tags` and `syncedLabels` can be set in both tiers without this error — they merge instead.

### Recycle Bin rule not inheriting governance settings

Ensure the `RecycleBinConfig` CR has the label `aws.kropath.run/resource-name: <its-name>`. The label is auto-injected by the controller, but if missing, re-apply the CR:

```bash
kubectl apply -f recyclebinconfig.yaml -n kro-system
```

Verify the label:

```bash
kubectl get recyclebinconfig general-policy -n kro-system --show-labels
```

## Reference

- **Family Design:** See `kropath-core/docs/families/aws/ebsrecyclebin.md`
- **Resource Spec:** See `kropath-core/docs/specs/aws/aws-ebsrb-01-recyclebinconfig.md`
- **ADR Reference:** ADR-015 §4 covers governance CRD design and the mandatory/defaults tier pattern
- **Controller Behavior:** The `kropath-controller` writes `status.effectiveConfig` after merging all sources
