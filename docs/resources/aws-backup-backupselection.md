# BackupSelection

`BackupSelection` is a Kubernetes-native wrapper around AWS Backup selections. A backup selection specifies which AWS resources are backed up by a backup plan. Use tag-based matching to automatically include resources in backup operations.

## Overview

A backup selection is a child resource of a backup plan. It specifies:

- **Resource scope** — which resources are backed up (by resource type, tags, ARN patterns, etc.)
- **Tag-based automation** — automatically include resources matching tag criteria
- **Backup behavior** — whether to preserve resource tags, follow resource tags, etc.

One selection can match thousands of resources. When resources are created or modified, backup automatically includes or excludes them based on matching rules.

## Naming exemption

Unlike `BackupVault` and `BackupPlan`, `BackupSelection` has no standalone ARN. It is a child resource of `BackupPlan`, identified by:

- `backupPlanId` — the parent plan's AWS-assigned UUID
- `selectionId` — the selection's system-assigned ID

**Consequently, BackupSelection:**
- Has no `spec.nameOverride` field
- Has no `status.resourceName` or `status.predictedArn`
- Does not use naming templates
- BackupConfig has no `namingTemplate` for BackupSelection

Refer to selections by their system-assigned `status.id` (the `selectionId`).

## Governance via BackupConfig

`BackupSelection` reads governance from `BackupConfig` profiles via `spec.configRef`. The `BackupConfig` cascade enforces or defaults:

- IAM role for backup operations (`iamRoleARN`)
- Naming (not applicable to selections, but present in cascade for other resources)
- Tags and labels (applied to K8s metadata only, not to AWS resource tags)

**Important:** BackupSelection tag behavior differs from BackupVault/BackupPlan:
- Tags are stored in K8s `metadata.labels` and `metadata.annotations`
- Tags are NOT applied to AWS resources (selections cannot tag backup recovery points)
- Tag inheritance from `BackupConfig` still applies via the cascade

## Schema

### Spec fields

```yaml
spec:
  configRef: general-policy    # Profile name; defaults to "general-policy"
  deletionPolicy: retain       # "retain" | "delete"
  backupPlanName: critical-plan  # Name of the parent BackupPlan CR
  
  # Resource selection (at least one must be specified)
  resources:
    - type: "RDS"
      tagCondition:
        key: backup-enabled
        value: "true"
    - type: "EC2"
  
  # List-based resource selection (alternative to tag conditions)
  listOfTags:
    - type: "STRINGEQUALS"
      key: "Environment"
      values: ["Production"]
    - type: "STRINGLIKE"
      key: "Team"
      values: ["*-platform"]
  
  # Selection behavior
  selectionTag:
    type: ASSIGN  # "ASSIGN" | "USE_VAULT_IAM_ROLE"
  
  # Tags for the selection (K8s metadata only)
  tags:
    environment: prod
    team: platform
```

### Status fields

```yaml
status:
  id: 12345678-1234-1234-1234-123456789012  # System-assigned selection ID
  backupPlanID: 87654321-4321-4321-4321-210987654321  # Parent plan's ID
  creationDate: "2026-01-15T10:30:00Z"
  conditions:
    - type: Ready
      status: "True"
      reason: SelectionReady
      message: Backup selection is ready
```

## Resource matching

Backup selections use tag-based and list-based conditions to match resources:

### Tag-based matching

```yaml
resources:
  - type: "RDS"
    tagCondition:
      key: backup-enabled
      value: "true"
  
  - type: "DynamoDB"
    tagCondition:
      key: team
      value: "data-platform"
```

Matches:
- All RDS resources with `backup-enabled=true`
- All DynamoDB tables with `team=data-platform`

### List-based matching

```yaml
listOfTags:
  - type: "STRINGEQUALS"
    key: Environment
    values: ["Production"]
  
  - type: "STRINGLIKE"
    key: Service
    values: ["payment-*", "billing-*"]
```

Matches resources where:
- `Environment` exactly equals `Production` AND
- `Service` matches the pattern `payment-*` or `billing-*` (wildcard patterns supported)

## Resource types

Common resource types for backup:

- `"RDS"` — Relational databases (Aurora, MySQL, MariaDB, PostgreSQL, SQL Server, Oracle)
- `"DynamoDB"` — DynamoDB tables
- `"EC2"` — EC2 instances and volumes
- `"EBS"` — Elastic Block Store volumes
- `"EFS"` — Elastic File System
- `"S3"` — S3 buckets
- `"FSx"` — FSx for Windows/Lustre
- `"Lambda"` — Lambda function code
- `"CloudFormation"` — CloudFormation stacks

See AWS documentation for the full list of supported resource types.

## Selection behavior

The `selectionTag` field controls how tags are handled:

- `ASSIGN` — apply resource tags to recovery points (for tracking and filtering)
- `USE_VAULT_IAM_ROLE` — use the backup vault's IAM role for backup operations

## Deletion policy

The `deletionPolicy` annotation controls what happens when the `BackupSelection` CR is deleted:

- `retain` (default) — the selection remains in AWS
- `delete` — the selection is deleted from AWS

Use `retain` for production selections. Use `delete` for development and testing.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: dev-databases
  namespace: development
spec:
  configRef: dev
  backupPlanName: dev-plan
  deletionPolicy: delete
```

## Complete example

```yaml
---
# Select all production RDS databases and DynamoDB tables
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: prod-databases
  namespace: production
spec:
  configRef: high-availability
  backupPlanName: critical-databases
  deletionPolicy: retain
  
  resources:
    - type: "RDS"
      tagCondition:
        key: environment
        value: "production"
    
    - type: "DynamoDB"
      tagCondition:
        key: team
        value: "data-platform"
  
  selectionTag: ASSIGN
  
  tags:
    managed-by: kropath
    data-class: sensitive

---
# Select resources matching complex patterns
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: payment-services
  namespace: production
spec:
  configRef: compliance
  backupPlanName: compliance-plan
  deletionPolicy: retain
  
  listOfTags:
    - type: "STRINGEQUALS"
      key: Environment
      values: ["Production"]
    
    - type: "STRINGLIKE"
      key: Service
      values: ["payment-*", "billing-*"]
  
  selectionTag: ASSIGN
  
  tags:
    compliance-tier: pci
```

## Tag inheritance from BackupConfig

BackupSelection inherits tags from `BackupConfig` and `KropathConfig`, but these are applied only to K8s `metadata`, not to AWS resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: compliance
spec:
  mandatory:
    tags:
      compliance-tier: pci
      data-retention-law: ccpa
```

When a `BackupSelection` uses the `compliance` profile, these tags appear in `metadata.labels`:

```yaml
metadata:
  labels:
    compliance-tier: pci
    data-retention-law: ccpa
    managed-by: kropath
```

But they are NOT applied to AWS backup recovery points (selections don't support that). Resource tags on the selected AWS resources themselves are preserved and can be applied to recovery points via `selectionTag: ASSIGN`.

## Best practices

1. **Use tag-based selection for automation.** When you add a resource with the matching tags, it is automatically included in backups.

2. **Tag your resources consistently.** Use standard tags like `environment`, `team`, `service`, and `data-class` to enable efficient selection patterns.

3. **Use pattern-based matching for scale.** The `STRINGLIKE` type with wildcard patterns (`payment-*`) scales better than maintaining individual selections for each service.

4. **Combine resource types carefully.** Some resource types have different backup requirements (e.g., EBS vs. RDS). Group similar resource types in one selection and use different selections for different types when needed.

5. **Test selection matching.** Start in non-production and verify that your tag conditions match the intended resources before deploying to production.

6. **Use `retain` for production selections.** Avoid accidental deletion of production backup configurations.

7. **Monitor resource inclusion.** Periodically verify that new resources are being included in backup selections via their tags.

8. **Document selection intent.** Add comments or annotations to selections explaining which resources they cover and why.

## Related resources

- [`BackupConfig`](./backupconfig.md) — governance and profile configuration
- [`BackupVault`](./backupvault.md) — storage container for recovery points
- [`BackupPlan`](./backupplan.md) — backup rules and schedules
- [`KropathConfig`](../controller/krop-config.md) — org-wide configuration

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `BackupSelection`
- **Scope**: Namespaced
- **Plural**: `backupselections`
