# RecycleBinRule — Retention Rules for EBS Snapshots and AMIs

The `RecycleBinRule` resource creates and manages AWS Recycle Bin retention rules that protect your EBS snapshots and EC2 AMIs from accidental deletion. Each rule defines how long deleted resources remain recoverable before permanent deletion.

## Overview

`RecycleBinRule` is the sole resource in the EBS Recycle Bin family. It wraps the ACK `recyclebin.services.k8s.aws/Rule` CR and enables you to:

- Retain deleted EBS snapshots or EC2 AMIs for a specified period
- Lock rules to prevent accidental changes
- Tag rules for cost tracking and resource organization
- Apply governance policies from `RecycleBinConfig` profiles

Rules are identified by system-generated **11-character alphanumeric identifiers** (e.g., `abc12345678`), not user-specified names.

## Creating a Retention Rule

### Basic Region-Level Rule

Retain all deleted EBS snapshots in the region for 7 days:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-all-snapshots
spec:
  configRef: general-policy
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 7
  retentionPeriodUnit: "DAYS"
```

This rule applies to **all deleted snapshots** in the region. There is no filtering by tags.

### Tag-Level Rule

Retain only production EBS snapshots:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-prod-snapshots
spec:
  configRef: general-policy
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 30
  retentionPeriodUnit: "DAYS"
  resourceTags:
    - resourceTagKey: "environment"
      resourceTagValue: "production"
```

This rule applies only to deleted snapshots tagged with `environment: production`.

### Multi-Filter Tag Rule

Retain snapshots matching multiple tag filters:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-sensitive-prod
spec:
  configRef: compliance
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 90
  retentionPeriodUnit: "DAYS"
  resourceTags:
    - resourceTagKey: "environment"
      resourceTagValue: "production"
    - resourceTagKey: "data-classification"
      resourceTagValue: "sensitive"
```

### AMI Retention Rule

Retain deleted AMIs (EC2 images):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-prod-amis
spec:
  configRef: general-policy
  resourceType: EC2_IMAGE
  retentionPeriodValue: 30
  retentionPeriodUnit: "DAYS"
```

## Rule Locking

Lock a rule to prevent accidental modification or deletion:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: locked-prod-rule
spec:
  configRef: compliance
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 90
  retentionPeriodUnit: "DAYS"
  lockRule: true
  unlockDelayValue: 30
  unlockDelayUnit: "DAYS"
```

### Lock Lifecycle

Once locked, a rule transitions through a **one-way lifecycle**:

1. **locked** — Rule is protected; cannot be modified or deleted
2. **pending_unlock** — An unlock request has been initiated; awaiting the unlock delay
3. **unlocked** — The unlock delay has expired; rule can now be modified or deleted

To unlock a locked rule, use the AWS console or CLI:

```bash
aws rbin unlock-rule \
  --identifier <rule-identifier>
```

(Replace `<rule-identifier>` with your rule's 11-character ID from `status.ruleIdentifier`.)

**Important:** The declarative Kubernetes spec does not support reverting a rule from locked to unlocked via a spec change. Unlock operations must be performed through the AWS console or CLI. The `status.lockState` field reflects the current lock state.

## Governance from Profiles

Rules inherit retention and locking policies from `RecycleBinConfig` profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: simple-rule
spec:
  configRef: compliance
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 30
  retentionPeriodUnit: "DAYS"
```

The controller looks up the `compliance` profile's `effectiveConfig` and applies:
- Mandatory fields from `RecycleBinConfig.mandatory` (overrides any instance value)
- Defaults from `RecycleBinConfig.defaults` (used only if a governance field is not set)

### Governance Cascade

Retention and locking fields resolve in priority order:

1. **Mandatory tier** (KropathConfig, then RecycleBinConfig) — enforced; cannot be overridden
2. **Instance spec** — provided by the RecycleBinRule CR
3. **Defaults tier** (RecycleBinConfig, then KropathConfig) — used if instance spec is empty
4. **Built-in default** — RGD default if all above are unset

**Example:** If a profile mandatory tier sets `retentionPeriodValue: 90` and a rule spec sets `retentionPeriodValue: 7`, the rule uses **90 days** (mandatory wins).

## Tagging and Labels

Tag your rules for cost tracking, automation, and organization:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: tracked-rule
spec:
  configRef: general-policy
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 14
  retentionPeriodUnit: "DAYS"
  tags:
    environment: "production"
    cost-center: "engineering"
    application: "database"
  syncedLabels:
    managed-by: "kropath"
    cost-tracking: "enabled"
```

**Tags** appear in AWS Recycle Bin as rule metadata. **SyncedLabels** appear both as Kubernetes labels on the RecycleBinRule CR AND as AWS tags (prefixed with `aws.kropath.run/`).

Tags and labels from the governance profile are **merged** into the rule; you can add rule-specific tags without removing profile tags.

## Deletion Policy

Control what happens when a RecycleBinRule CR is deleted:

```yaml
spec:
  deletionPolicy: "retain"  # retain | delete
```

- **retain** (default) — Kubernetes CR is deleted, but the underlying AWS Recycle Bin rule persists
- **delete** — Kubernetes CR is deleted AND the underlying AWS Recycle Bin rule is deleted from AWS

Use `retain` for production rules you want to keep in AWS even if the CR is removed; use `delete` for temporary or test rules.

## Complete Examples

### Development Rule with Defaults

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: dev-snapshot-retention
  namespace: dev
spec:
  configRef: dev-policy
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 3
  retentionPeriodUnit: "DAYS"
  tags:
    environment: "dev"
```

### Production Rule with Mandatory Enforcement

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: prod-critical-snapshots
  namespace: production
spec:
  configRef: compliance
  deletionPolicy: "retain"  # Keep rule in AWS even if CR is deleted
  resourceType: EBS_SNAPSHOT
  retentionPeriodValue: 90
  retentionPeriodUnit: "DAYS"
  lockRule: true
  unlockDelayValue: 30
  unlockDelayUnit: "DAYS"
  resourceTags:
    - resourceTagKey: "criticality"
      resourceTagValue: "high"
  tags:
    compliance-requirement: "pci-dss"
    audit-scope: "required"
  syncedLabels:
    compliance-controlled: "true"
    audit-required: "true"
```

The `compliance` profile mandatory tier may enforce additional retention or locking — the rule follows all mandatory policies.

### AMI Rule with Tag Filtering

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RecycleBinRule
metadata:
  name: retain-golden-amis
spec:
  configRef: general-policy
  resourceType: EC2_IMAGE
  retentionPeriodValue: 60
  retentionPeriodUnit: "DAYS"
  resourceTags:
    - resourceTagKey: "image-type"
      resourceTagValue: "golden"
    - resourceTagKey: "maintained-by"
      resourceTagValue: "platform-team"
  description: "Retain platform-maintained golden AMIs for 60 days"
  tags:
    purpose: "golden-image-protection"
    team: "platform"
```

## Status Fields

After creation, the RecycleBinRule CR's status reflects the rule's AWS state:

```yaml
status:
  ruleIdentifier: "abc12345678"
  ruleArn: "arn:aws:rbin:us-east-1:123456789012:rule/abc12345678"
  ruleStatus: "available"
  lockState: "locked"
  conditions:
    - type: "Ready"
      status: "True"
      reason: "RuleAvailable"
      message: "Recycle Bin rule is available in AWS"
```

| Field | Meaning |
|---|---|
| `ruleIdentifier` | System-generated 11-character ID (e.g., `abc12345678`) |
| `ruleArn` | Full AWS ARN for the rule |
| `ruleStatus` | AWS status: typically `available` or `unavailable` |
| `lockState` | Lock state: `locked`, `pending_unlock`, `unlocked`, or `null` (never locked) |
| `conditions` | Standard Kubernetes conditions for rule readiness |

## Configuration Reference

### Spec Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `configRef` | string | No | `"general-policy"` | Name of the RecycleBinConfig profile to use |
| `resourceType` | string | Yes | — | `EBS_SNAPSHOT` or `EC2_IMAGE` |
| `retentionPeriodValue` | integer | Yes | — | Number of days (1–3650) |
| `retentionPeriodUnit` | string | No | `"DAYS"` | Always `"DAYS"` (only unit currently supported) |
| `description` | string | No | — | Human-readable description (max 255 chars) |
| `resourceTags` | array | No | — | Tag filters for tag-level rules (omit for region-level) |
| `lockRule` | boolean | No | `false` | Whether to lock the rule on creation |
| `unlockDelayValue` | integer | No | `30` | Unlock delay in days (7–3650); only used if `lockRule: true` |
| `unlockDelayUnit` | string | No | `"DAYS"` | Always `"DAYS"` |
| `tags` | map | No | — | AWS cloud tags for the rule |
| `syncedLabels` | map | No | — | Labels synced to K8s and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | No | — | Annotations synced to K8s (prefixed `aws.kropath.run/`) |
| `deletionPolicy` | string | No | `"retain"` | `"retain"` or `"delete"` |

### Retention Period Range

Valid values: **1–3650 days**

- `1–3650` = required retention period in days

### Unlock Delay Range

Valid values when `lockRule: true`: **0–3650 days**

- `0` = not enforced (uses AWS default, typically 7 days)
- `7–3650` = valid unlock delay period

## Troubleshooting

### Rule creation fails with "resourceType is required"

You forgot to specify the resource type. Add:

```yaml
spec:
  resourceType: EBS_SNAPSHOT  # or EC2_IMAGE
```

### Rule inherits wrong governance settings

Verify the profile name in `spec.configRef` exists and has the expected policies:

```bash
kubectl get recyclebinconfig <profile-name> -n kro-system -o yaml
kubectl get recyclebinconfig <profile-name> -n kro-system -o jsonpath='{.status.effectiveConfig}'
```

### Locked rule cannot be deleted

Locked rules must be unlocked first via AWS console or CLI before the CR can be deleted. Set `deletionPolicy: delete` if you want the CR deletion to trigger AWS rule deletion.

### Rule state shows "pending_unlock" but unlock delay hasn't elapsed

The unlock process has been initiated. The rule will automatically transition to `unlocked` after the unlock delay expires.

## Reference

- **Family Overview:** See [EBS Recycle Bin](index.md)
- **Governance Configuration:** See [RecycleBinConfig](recyclebinconfig.md)
- **Family Design:** See `kropath-core/docs/families/aws/ebsrecyclebin.md`
- **Resource Spec:** See `kropath-core/docs/specs/aws/aws-ebsrb-02-recyclebinrule.md`
- **AWS Recycle Bin Docs:** [AWS EBS Recycle Bin](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/recycle-bin.html)
