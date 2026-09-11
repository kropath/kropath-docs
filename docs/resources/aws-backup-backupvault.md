# BackupVault

`BackupVault` is a Kubernetes-native wrapper around AWS Backup vaults. A backup vault is a logical container for recovery points with encryption, optional Vault Lock compliance controls, and lifecycle policies. Use `BackupVault` to provision backup vaults with consistent governance via `BackupConfig`.

## Overview

A backup vault stores recovery points created by backup plans. Every backup operation targets a vault. Vaults support:

- **Encryption** — AWS-managed (default) or customer-managed KMS keys
- **Vault Lock** — optional compliance control that prevents deletion/modification during a retention period
- **Lifecycle policies** — automatic archival to cold storage and deletion after retention expires
- **PITR support** — continuous backup and recovery to any point in time
- **Tags** — AWS resource tags for cost allocation, automation, and resource discovery

## Governance via BackupConfig

`BackupVault` reads governance from `BackupConfig` profiles via `spec.configRef`. The `BackupConfig` cascade enforces or defaults:

- Encryption key (`encryptionKeyARN`)
- Vault Lock retention periods (`vaultLockMinRetentionDays`, `vaultLockMaxRetentionDays`)
- Lifecycle policies (retention and cold-storage transition days)
- IAM roles for backup operations
- Naming templates
- Tags and labels

## Schema

### Spec fields

```yaml
spec:
  configRef: general-policy        # Profile name; defaults to "general-policy" if profile doesn't exist
  nameOverride: ""                 # Custom vault name (optional; bypasses naming template)
  deletionPolicy: retain           # "retain" | "delete" — whether to delete the vault when the CR is deleted
  
  # Encryption (immutable after creation)
  encryptionKeyRef: ""             # K8s CR name of a KMSKey; RGD reads status.arn
  encryptionKeyARN: ""             # Direct KMS key ARN (for keys not managed by kropath)
  
  # Vault Lock (compliance control)
  vaultLockMinRetentionDays: 0     # Minimum retention in days (0 = not configured)
  vaultLockMaxRetentionDays: 0     # Maximum retention in days (0 = not configured)
  
  tags:
    environment: prod
    team: platform
```

### Status fields

```yaml
status:
  resourceName: prod-backup-vault   # Effective name after template substitution
  predictedArn: arn:aws:backup:us-east-1:123456789012:backup-vault:prod-backup-vault
  namingStatus: valid               # "valid" | "invalid-unresolved-tokens"
  vaultARN: arn:aws:backup:us-east-1:123456789012:backup-vault:prod-backup-vault
  creationDate: "2026-01-15T10:30:00Z"
  locked: true                      # Whether Vault Lock is active
  lockDate: "2026-04-15T00:00:00Z"  # When Vault Lock becomes immutable
  minRetentionDays: 90              # Actual retention enforced by Vault Lock
  maxRetentionDays: 365
  conditions:
    - type: Ready
      status: "True"
      reason: VaultReady
      message: Backup vault is ready
```

## Encryption

Encryption is immutable after vault creation — you cannot change the KMS key once the vault exists. Choose your encryption strategy before creating the vault.

**AWS-managed encryption** — the default:
- Free
- No key management overhead
- AWS rotates keys annually
- Suitable for non-sensitive, development, or cost-conscious workloads

**Customer-managed KMS** — use via `BackupConfig.mandatory.encryptionKeyARN`:
- Pay for KMS key operations
- Full control over key rotation and access
- Required for compliance (HIPAA, PCI-DSS, etc.)
- Enforced by compliance profiles

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupVault
metadata:
  name: prod-vault
  namespace: production
spec:
  configRef: compliance     # Compliance profile forces customer-managed KMS
  deletionPolicy: retain    # Never auto-delete this vault
```

The `compliance` BackupConfig enforces `encryptionKeyARN` to the organization's compliance KMS key. The vault inherits this key — no further specification is needed.

## Vault Lock

Vault Lock is a compliance feature that makes recovery points immutable for a retention period. Once locked:

- Recovery points cannot be deleted before the minimum retention period expires
- Recovery points cannot be modified or archived before maximum retention
- Even the AWS account owner cannot bypass these restrictions

**Use Vault Lock for:**
- Regulated workloads (healthcare, finance)
- Long-term archive and immutability requirements
- Compliance with regulations that require data immutability (e.g., data retention laws)

**Important:** Vault Lock is one-way. Once activated, you must wait out the maximum retention period if you want to unlock the vault. Test retention periods carefully in non-production before enabling in production.

**Setting Vault Lock via BackupConfig:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    vaultLockMinRetentionDays: 90
    vaultLockMaxRetentionDays: 365
```

All vaults using the `compliance` profile are locked with these retention periods enforced. Developers cannot override.

## Lifecycle and cold storage

Backup recovery points can be automatically archived to cold storage after a retention period, then deleted after a maximum retention. This reduces storage costs for long-term backups.

**Lifecycle policy structure:**

- **Delete after X days** — recovery points are deleted X days after creation
- **Move to cold storage after Y days** — recovery points are archived to cold storage Y days after creation (Y must be < X)

Cold storage is cheaper but slower to restore — it can take 12 hours to retrieve data. Use for compliance archives and rarely-accessed backups.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: high-availability
spec:
  defaults:
    defaultLifecycleDeleteAfterDays: 180     # Keep for 6 months
    defaultLifecycleMoveToColdStorageAfterDays: 90   # Cold storage after 3 months
```

Vaults using this profile keep recovery points for 180 days, moving to cold storage after 90 days.

## Deletion policy

The `deletionPolicy` annotation controls what happens when the `BackupVault` CR is deleted:

- `retain` (default) — the vault remains in AWS and is not deleted
- `delete` — the vault is deleted from AWS (only if it contains no recovery points; AWS fails deletion if recovery points exist)

Use `retain` for production vaults to prevent accidental deletion. Use `delete` for development and testing.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupVault
metadata:
  name: dev-vault
  namespace: development
spec:
  configRef: dev
  deletionPolicy: delete
```

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupVault
metadata:
  name: critical-databases
  namespace: production
spec:
  configRef: compliance
  deletionPolicy: retain
  tags:
    cost-center: "data-platform"
    team: "databases"
```

This vault:
- Uses the `compliance` profile, inheriting customer-managed encryption, Vault Lock (90–365 days), and other compliance settings
- Will not be deleted when the CR is deleted
- Carries cost-allocation tags

## Related resources

- [`BackupConfig`](./backupconfig.md) — governance and profile configuration
- [`BackupPlan`](./backupplan.md) — backup rules and schedules
- [`BackupSelection`](./backupselection.md) — resource selection for backup
- [`KropathConfig`](../controller/krop-config.md) — org-wide configuration

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `BackupVault`
- **Scope**: Namespaced
- **Plural**: `backupvaults`
