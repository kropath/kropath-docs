# EBS Recycle Bin

The **EBS Recycle Bin family** enables you to recover from accidental EBS snapshot and AMI deletions. Recycle Bin rules define retention policies that keep deleted resources for a specified period, preventing permanent data loss.

## Resources

| Resource | Purpose |
|---|---|
| **RecycleBinConfig** | Governance CRD for defining retention and locking policies across your cluster |
| **RecycleBinRule** | Creates and manages retention rules for EBS snapshots and EC2 AMIs |

## Quick Start

### 1. Create a Governance Profile

Define a retention policy profile in the `kro-system` namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    retentionPeriodValue: 7
    retentionPeriodUnit: "DAYS"
    lockRule: false
    unlockDelayValue: 30
    unlockDelayUnit: "DAYS"
```

### 2. Create a Retention Rule

Create a rule to retain deleted EBS snapshots:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-prod-snapshots
spec:
  configRef: general-policy
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 7
  retentionPeriodUnit: "DAYS"
```

The rule is identified by a system-generated `identifier` (e.g., `abc12345678`). Access it via `status.ruleIdentifier`.

## Retention Levels

### Region-Level Rules

Retain all deleted resources of a type in a region:

```yaml
spec:
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 30
  retentionPeriodUnit: "DAYS"
  # Omit resourceTags for region-level retention
```

### Tag-Level Rules

Retain only deleted resources matching specific tags:

```yaml
spec:
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 30
  retentionPeriodUnit: "DAYS"
  resourceTags:
    - resourceTagKey: "environment"
      resourceTagValue: "production"
```

## Rule Locking

Lock rules to prevent accidental deletion:

```yaml
spec:
  lockRule: true
  unlockDelayValue: 30
  unlockDelayUnit: "DAYS"
```

Locked rules transition through a one-way lifecycle:
- **locked** — Rule is protected; cannot be modified or deleted
- **pending_unlock** — Unlock delay period has started (30 days default)
- **unlocked** — Rule is no longer protected; can now be deleted

To unlock a rule, use the AWS console or CLI — the declarative spec does not reverse a lock.

## Key Concepts

### Retention Period Range

Valid retention periods: **1–3650 days**

- `0` = not enforced (skipped in governance cascade)
- Empty string = not enforced (skipped in governance cascade)

### Mandatory vs. Defaults

`RecycleBinConfig` defines two governance tiers:

- **Mandatory** — Platform enforcement (e.g., "all rules must retain for at least 90 days")
- **Defaults** — Sensible baselines when a rule spec is empty (e.g., "7-day retention if not specified")

Mandatory settings override instance specs; defaults apply only when the instance omits a value.

### Naming Convention

Rules have **no user-specified names**. Each rule is identified by a system-generated 11-character alphanumeric `identifier`:

- Example identifier: `abc12345678`
- ARN: `arn:aws:rbin:<region>:<account-id>:rule/<identifier>`
- Access via `status.ruleIdentifier` in the RecycleBinRule CR

## Deletion Policy

Control what happens when a RecycleBinRule CR is deleted:

```yaml
spec:
  deletionPolicy: "retain"  # retain | delete
```

- **retain** (default) — Rule remains in AWS; CR is deleted but the underlying AWS rule persists
- **delete** — Rule is deleted from AWS when the CR is deleted

## Tagging and Labels

Tag and label your rules for cost tracking and resource organization:

```yaml
spec:
  tags:
    environment: "production"
    cost-center: "engineering"
  syncedLabels:
    managed-by: "kropath"
    cost-tracking: "enabled"
```

Tags and labels defined in `RecycleBinConfig` (both mandatory and defaults tiers) are merged into every rule using that profile.

## Governance Cascade

Rules resolve field values through a multi-level cascade:

1. `KropathConfig` mandatory tier (org-wide enforcement)
2. `KropathConfig` local mandatory tier (namespace-level enforcement)
3. `RecycleBinConfig` mandatory tier (per-profile enforcement)
4. `RecycleBinConfig` local mandatory tier (namespace-local enforcement)
5. Instance `spec` value
6. `RecycleBinConfig` defaults tier (per-profile default)
7. `RecycleBinConfig` global defaults tier
8. `KropathConfig` local defaults tier
9. `KropathConfig` global defaults tier
10. RGD built-in default (if any)

Mandatory tiers always win; instance specs are overridden by mandatory rules.

## Design Reference

- **Family Design:** See `kropath-core/docs/families/aws/ebsrecyclebin.md`
- **Resource Specs:** See `kropath-core/docs/specs/aws/aws-ebsrb-01-recyclebinconfig.md` and `aws-ebsrb-02-recyclebinrule.md`
- **Governance Design:** See ADR-015 in `kropath-core/docs/adr/`

---

- [RecycleBinConfig Guide](recyclebinconfig.md) — Create governance profiles
- [RecycleBinRule Guide](recyclebinrule.md) — Create and manage retention rules
