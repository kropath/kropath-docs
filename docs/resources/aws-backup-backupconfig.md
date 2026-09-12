# BackupConfig

`BackupConfig` is a governance configuration resource that lets you define mandatory and default settings for AWS Backup resources across your cluster. Instead of requiring every backup vault, plan, and selection to specify encryption, retention, Vault Lock, continuous backup (PITR), and malware scanning independently, you can create named configuration profiles and let the kropath controller apply them consistently.

## Scope

This resource is AWS-only. BackupConfig governs AWS Backup resources (via `BackupVault`, `BackupPlan`, and `BackupSelection` RGDs). There is no GCP or Azure equivalent yet.

## What it solves

Managing AWS Backup resources at scale creates several operational challenges:

- **Inconsistent governance** — different teams set different encryption keys, retention periods, and compliance controls, making audit and compliance difficult
- **Compliance drift** — once resources are created, enforcing new requirements (e.g., "all vaults must use customer-managed KMS") requires manual updates
- **Manual defaults** — every resource spec must list sensible defaults (encryption, retention, PITR settings), creating noise and inconsistency
- **No central policy** — when a compliance requirement changes, you must update every resource individually

`BackupConfig` solves this by providing:

- **Governance profiles** — define reusable profiles like `general-policy`, `compliance`, or `dev` that encode your organization's backup posture
- **Mandatory enforcement** — platform teams set fields that override user input (e.g., "all vaults must use customer-managed encryption for compliance")
- **Sensible defaults** — declare defaults for optional fields so user specs are cleaner and every resource has a consistent baseline
- **Scalable compliance** — update one profile to enforce a new requirement across all resources using that profile

## Core concepts

### Mandatory vs. defaults tiers

`BackupConfig` has two independent tiers of settings:

**Mandatory fields** (enforced):
- Override any user specification for that field
- Useful for compliance: "all backup vaults must use customer-managed KMS encryption"
- If mandatory is empty or zero, it is not enforced (user can override)

**Defaults fields** (applied when user doesn't specify):
- Provide sensible fallback values
- Applied only when the user leaves the field empty
- Useful for convenience: "35-day retention by default, but let power users override for critical workloads"

**Important:** Setting the same field in both mandatory and defaults tiers is an API validation error. The BackupConfig CRD uses `x-kubernetes-validations` to reject any CR where a field is set to a non-zero/non-empty value in both tiers simultaneously. You must choose one tier per field.

### Governance cascade

The kropath controller pre-merges settings from three sources and writes them to `status.effectiveConfig`:

1. **Org-wide** (`KropathConfig.spec.backup.*`) — applies to all backup resources across the cluster
2. **Per-profile** (`BackupConfig.spec.mandatory/defaults.*`) — applies to resources using this profile
3. **Instance** (`BackupVault/BackupPlan/BackupSelection.spec.*`) — developer override for a specific resource

RGDs read the merged result from `status.effectiveConfig`, ensuring a single source of truth.

### Boolean and zero-value semantics

For boolean fields like `enableContinuousBackup` and `enableMalwareScan`, `false` is used as the zero-value sentinel ("not set / not enforced"). An explicit `false` is indistinguishable from "not set" — it falls through to the next tier. Mandatory enforcement can only force `true`, never force `false`.

For numeric fields like `vaultLockMinRetentionDays`, zero is the sentinel ("not set / not enforced"). Non-zero values enforce that setting.

### Profile patterns

Common profiles codify organizational postures:

**general-policy** — the default, cost-conscious baseline:
- AWS-managed encryption (default)
- 35-day default retention
- Vault Lock disabled (default)
- PITR disabled (default)
- Malware scanning disabled (default)
- All overridable per-instance

**compliance** — stricter, suitable for regulated workloads:
- Customer-managed KMS encryption (required)
- 90-day minimum retention (enforced)
- Vault Lock: minimum 90 days, maximum 365 days (enforced)
- PITR enabled (required)
- Cold storage after 30 days (default)
- Malware scanning enabled (required)
- Instance specs cannot override mandatory fields

**dev** — development-friendly, minimal overhead:
- AWS-managed encryption (default)
- 7-day default retention
- Vault Lock disabled (default)
- PITR disabled (default)
- Malware scanning disabled (default)
- All overridable per-instance

## Configuration fields

### Mandatory tier

Fields in this tier override any instance `spec` setting:

| Field | Type | Meaning |
|---|---|---|
| `encryptionKeyARN` | string | KMS key ARN for vault encryption (immutable after creation). Empty = not enforced. |
| `vaultLockMinRetentionDays` | integer | Minimum days Vault Lock enforces (0 = not enforced). |
| `vaultLockMaxRetentionDays` | integer | Maximum days Vault Lock enforces (0 = not enforced). |
| `enableContinuousBackup` | boolean | Require PITR on all backup rules (`true` = required; `false` = not enforced). |
| `defaultLifecycleDeleteAfterDays` | integer | Minimum backup retention before deletion (0 = not enforced). |
| `defaultLifecycleMoveToColdStorageAfterDays` | integer | Days before moving recovery points to cold storage (0 = not enforced). |
| `enableMalwareScan` | boolean | Require malware scanning on backup plans (`true` = required; `false` = not enforced). |
| `scannerRoleARN` | string | IAM role for backup malware scanning. Empty = not enforced. |
| `iamRoleARN` | string | IAM role for backup service operations. Empty = not enforced. |
| `namingTemplate` | string | Cloud resource name template (e.g., `"backup-{namespace}-{name}"`). Empty = use defaults tier. |
| `tags` | map | Cloud resource tags. Merged with defaults and instance tags. |
| `syncedLabels` | map | Labels to sync to both K8s and cloud tags. |
| `syncedAnnotations` | map | Annotations to sync to both K8s metadata and cloud tags. |

### Defaults tier

Fields here apply when an instance leaves the field empty:

| Field | Type | Default value | Meaning |
|---|---|---|---|
| `encryptionKeyARN` | string | `""` (AWS-managed) | Fallback KMS key. Empty = AWS-managed key. |
| `vaultLockMinRetentionDays` | integer | `0` | Fallback: Vault Lock not configured. |
| `vaultLockMaxRetentionDays` | integer | `0` | Fallback: Vault Lock not configured. |
| `enableContinuousBackup` | boolean | `false` | Fallback: PITR disabled. |
| `defaultLifecycleDeleteAfterDays` | integer | `35` | Fallback: 35-day retention. |
| `defaultLifecycleMoveToColdStorageAfterDays` | integer | `0` | Fallback: no cold storage transition. |
| `enableMalwareScan` | boolean | `false` | Fallback: malware scanning disabled. |
| `scannerRoleARN` | string | `""` | Fallback: must be specified when scanning is enabled. |
| `iamRoleARN` | string | `""` | Fallback: must be specified per-instance. |
| `namingTemplate` | string | `"{namespace}-{name}"` | Default cloud resource naming. |
| `tags` | map | `{}` | Merged with mandatory and instance tags. |
| `syncedLabels` | map | `{}` | Merged with mandatory and instance labels. |
| `syncedAnnotations` | map | `{}` | Merged with mandatory and instance annotations. |

### KropathConfig additions

`KropathConfig` backup section governs org-wide blanket rules across all profiles. Org-wide fields added to `spec.mandatory.backup` and `spec.defaults.backup`:

| Field | Type | Semantics |
|---|---|---|
| `encryptionKeyARN` | string | Org-wide KMS key enforcement (mandatory) or default (defaults) |
| `vaultLockMinRetentionDays` | integer | Org-wide Vault Lock minimum retention enforcement |
| `vaultLockMaxRetentionDays` | integer | Org-wide Vault Lock maximum retention enforcement |
| `enableContinuousBackup` | boolean | Org-wide PITR enforcement (mandatory) or default (defaults) |
| `defaultLifecycleDeleteAfterDays` | integer | Org-wide retention enforcement (mandatory) or default (defaults) |
| `defaultLifecycleMoveToColdStorageAfterDays` | integer | Org-wide cold storage transition enforcement |
| `enableMalwareScan` | boolean | Org-wide malware scanning enforcement (mandatory) or default (defaults) |
| `scannerRoleARN` | string | Org-wide scanner IAM role enforcement (mandatory) or default (defaults) |

**Fields NOT in KropathConfig (and why):**

| Field | Reason |
|---|---|
| `iamRoleARN` | Per-selection choice — depends on which resources are being backed up and cross-account requirements |
| `scheduleExpression` | Per-rule choice — backup schedule cadence varies by workload criticality |
| `targetBackupVaultName` | Per-rule choice — different rules may target different vaults |

## Complete example

Here's a complete multi-profile setup:

```yaml
---
# Org-wide settings (applied to all backup resources)
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global
  namespace: kro-system
spec:
  mandatory:
    backup:
      encryptionKeyARN: "arn:aws:kms:us-east-1:123456789012:key/org-master-key"
  defaults:
    backup:
      defaultLifecycleDeleteAfterDays: 90

---
# Default profile: sensible, cost-conscious baseline
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    encryptionKeyARN: ""  # AWS-managed key
    vaultLockMinRetentionDays: 0
    vaultLockMaxRetentionDays: 0
    enableContinuousBackup: false
    defaultLifecycleDeleteAfterDays: 35
    defaultLifecycleMoveToColdStorageAfterDays: 0
    enableMalwareScan: false
    namingTemplate: "{namespace}-backup-{name}"
    tags:
      environment: development
      managed-by: kropath

---
# Compliance profile: stricter, for regulated workloads
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    encryptionKeyARN: "arn:aws:kms:us-east-1:123456789012:key/compliance-key"
    vaultLockMinRetentionDays: 90
    vaultLockMaxRetentionDays: 365
    enableContinuousBackup: true
    defaultLifecycleDeleteAfterDays: 90
    enableMalwareScan: true
    scannerRoleARN: "arn:aws:iam::123456789012:role/BackupMalwareScanner"
    tags:
      compliance-tier: pci
      data-classification: sensitive
  defaults:
    defaultLifecycleMoveToColdStorageAfterDays: 30
    namingTemplate: "compliance-backup-{namespace}-{name}"
    tags:
      environment: production

---
# Development profile: minimal overhead and retention
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}
  defaults:
    encryptionKeyARN: ""  # AWS-managed key
    vaultLockMinRetentionDays: 0
    vaultLockMaxRetentionDays: 0
    enableContinuousBackup: false
    defaultLifecycleDeleteAfterDays: 7
    defaultLifecycleMoveToColdStorageAfterDays: 0
    enableMalwareScan: false
    namingTemplate: "{namespace}-backup-{name}"
    tags:
      environment: development
      cost-center: engineering
```

When a backup resource references one of these profiles via `spec.configRef`, the controller merges its settings with org-wide `KropathConfig` settings and writes the result to the profile's `status.effectiveConfig`.

## Using profiles with instances

Once your profiles are deployed, backup resources select them via `spec.configRef`:

```yaml
---
# Backup vault using the compliance profile
apiVersion: aws.kropath.run/v1alpha1
kind: BackupVault
metadata:
  name: prod-vault
  namespace: databases
spec:
  configRef: compliance  # Use the compliance profile
  # All other fields left empty to inherit from the compliance profile
```

In this example:
- Encryption key is forced to the compliance KMS key (mandatory)
- Vault Lock is enforced at 90–365 days minimum–maximum (mandatory)
- Retention defaults to 90 days (mandatory)
- Developer cannot override any mandatory fields

```yaml
---
# High-availability backup plan
apiVersion: aws.kropath.run/v1alpha1
kind: BackupPlan
metadata:
  name: critical-workload-plan
  namespace: production
spec:
  configRef: compliance  # Use the compliance profile
  rules:
    - ruleName: daily-backup
      targetBackupVaultName: prod-vault
      scheduleExpression: cron(0 5 * * ? *)  # 5 AM UTC daily
      enableContinuousBackup: ""  # Empty: defaults to true (mandatory)
      # Retention defaults to 180 days; developer can override
```

Here:
- PITR is forced to enabled (mandatory)
- Retention defaults to 180 days
- Cold storage transition defaults to 90 days
- Developer can customize the schedule and other plan-specific settings

```yaml
---
# Development backup selection using minimal settings
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: dev-databases
  namespace: development
spec:
  configRef: dev  # Use the dev profile
  backupPlanRef: critical-workload-plan
  listOfTags:
    - conditionType: STRINGEQUALS
      conditionKey: backup-enabled
      conditionValue: "true"
```

Here:
- Retention defaults to 7 days (from dev profile)
- Encryption defaults to AWS-managed (from dev profile)
- Malware scanning is not required (from dev profile)

## BackupSelection naming exemption

`BackupSelection` has no standalone ARN — it is a child resource of `BackupPlan`, identified by `backupPlanId` plus a system-assigned `selectionId`. The naming convention does not apply:

- No `spec.nameOverride`
- No `status.resourceName` or `status.predictedArn`
- No `namingTemplate` field on BackupSelection instances
- Only `status.id` (the system-assigned `selectionId`) is exposed

Consequently, `BackupConfig` has no `namingTemplate` for BackupSelection — it applies only to BackupVault and BackupPlan.

## BackupPlan naming

`BackupPlan` uses a display name that you choose (`spec.name`), but AWS assigns it an opaque UUID (`planId`) internally. The ARN format is `arn:aws:backup:{region}:{account_id}:backup-plan:{planId}`, not based on the display name. `status.planARN` is available only after the AWS API returns `planId`, which happens post-creation.

Consequently:
- `status.planARN` is not available pre-creation (the UUID is unknown until the plan is created)
- `status.planId` contains the AWS-assigned UUID once the plan is created
- `status.namingStatus` tracks the naming state (reconciling, succeeded, failed)
- The naming template applies to the display name, not to the ARN

## Vault Lock lifecycle

Vault Lock is a compliance control that makes a backup vault immutable for a minimum and maximum retention period. Once locked, no one — not even the AWS account owner — can delete or modify recovery points before the minimum retention expires.

**Important behaviors:**

1. **Separate provisioning step:** The ACK CRD exposes Vault Lock as status-only. Vault Lock is provisioned via a separate AWS API call (`PutBackupVaultLockConfiguration`). Once locked, it cannot be unlocked — you must wait for the maximum retention period to expire.

2. **One-way lifecycle:** Vault Lock is effectively permanent once activated. Plan accordingly.

3. **Governance enforcement:** `BackupConfig.mandatory.vaultLockMinRetentionDays` and `vaultLockMaxRetentionDays` let platform teams enforce compliance-mandated retention without requiring developers to manually specify retention periods on each vault.

## Malware scanning behavior

Malware scanning on backup plans is optional by default but can be enforced via `BackupConfig.mandatory.enableMalwareScan=true`. When enabled:

- Malware scanning is injected into each backup rule (`enableContinuousBackup` and `scanSettings`)
- The scanning IAM role is set from `scannerRoleARN` (via the cascade)
- Scanning adds overhead to backup operations; use only on resources where malware threats are a concern

## Tags and label synchronization

Tags, synced labels, and synced annotations cascade from three sources:

1. **Org-wide** (`KropathConfig.mandatory.tags` and `KropathConfig.defaults.tags`)
2. **Profile** (`BackupConfig.mandatory.tags` and `BackupConfig.defaults.tags`)
3. **Instance** (`BackupVault.spec.tags`, `BackupPlan.spec.tags`, etc.)

All three are merged, with instance-level overrides taking precedence. Tags are applied to the AWS backup resource; labels and annotations are stored in the K8s `metadata`.

## Profile selection rules

- **Default fallthrough** — if you omit `spec.configRef` or reference a profile that doesn't exist, kropath automatically uses the `general-policy` profile
- **Profiles in kro-system** — all profiles are deployed to the `kro-system` namespace. Instances in any application namespace can reference them via `spec.configRef`
- **Profile lookup by label** — profiles are found via the `aws.kropath.run/resource-name` label, not by `metadata.name`, so you can rename the CR safely without breaking references

## Best practices

1. **Create profiles for organizational postures, not per-resource.** One `compliance` profile serves all regulated workloads; don't create `compliance-vault-1`, `compliance-vault-2`, etc.

2. **Use mandatory fields sparingly.** Reserve mandatory for hard compliance requirements (encryption, PITR for audit, Vault Lock for immutability). Use defaults for convenience.

3. **Document why mandatory fields exist.** Add annotations or comments to profiles explaining compliance drivers, regulatory requirements, or operational constraints.

4. **Tag at the profile level.** Add environment, cost-center, and data-classification tags to profiles so every resource inheriting that profile carries the tags automatically.

5. **Plan for Vault Lock carefully.** Vault Lock is one-way; once activated, it cannot be reversed. Test retention periods in non-production before enforcing in compliance profiles.

6. **Test profile changes in non-production first.** Profile updates apply to all resources using that profile. Validate in a staging namespace before production, especially changes to mandatory encryption or retention.

7. **Use consistent naming templates.** The `{namespace}-backup-{name}` template is recommended. It ensures backup resource names include the namespace context, reducing confusion in AWS.

8. **Separate recovery and compliance needs.** Use separate profiles for recovery-focused (high-frequency backups) and compliance-focused (long retention, Vault Lock) workloads.

9. **Plan for profile evolution.** When compliance requirements change, update the profile rather than updating every resource individually — that's the power of centralized governance.

10. **Monitor malware scanning overhead.** Malware scanning increases backup duration and cost. Monitor performance and adjust `enableMalwareScan` based on your security posture and budget.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `BackupConfig`
- **Scope**: Namespaced
- **Plural**: `backupconfigs`

Related resources:
- `BackupVault` — individual backup vault RGD
- `BackupPlan` — backup plan RGD
- `BackupSelection` — backup selection RGD
- `KropathConfig` — org-wide configuration (includes `spec.mandatory.backup` and `spec.defaults.backup` sections)
