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
  configRef: general-policy              # Profile name; defaults to "general-policy"
  deletionPolicy: retain                 # "retain" | "delete"
  
  # Plan reference (at least one required: backupPlanRef OR backupPlanID)
  backupPlanRef: critical-plan           # Local BackupPlan CR name
  backupPlanID: ""                       # Direct backup plan ID (UUID string)
  
  # IAM role (at least one required: iamRoleRef OR iamRoleARN)
  iamRoleRef: backup-service-role        # Local IAMRole CR name
  iamRoleARN: ""                         # Direct IAM role ARN for backup operations
  
  # Resource selection (at least one of resources, listOfTags, or conditions required)
  resources:
    - "arn:aws:rds:us-east-1:123456789012:db:prod-db-1"
    - "arn:aws:rds:us-east-1:123456789012:db:prod-db-2"
  
  # Tag-based selection (OR logic - match any tag)
  listOfTags:
    - conditionType: "STRINGEQUALS"
      conditionKey: "Environment"
      conditionValue: "Production"
  
  # Tag-based filtering (AND logic - all conditions must match)
  conditions:
    stringEquals:
      - conditionKey: "Environment"
        conditionValue: "Production"
    stringLike:
      - conditionKey: "ServiceName"
        conditionValue: "payment-*"
  
  # Display name
  displayName: prod-selection
  
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

### Tag-based matching (OR logic)

```yaml
listOfTags:
  - conditionType: "STRINGEQUALS"
    conditionKey: "backup-enabled"
    conditionValue: "true"
  
  - conditionType: "STRINGEQUALS"
    conditionKey: "team"
    conditionValue: "data-platform"
```

Matches resources where:
- `backup-enabled` exactly equals `true` OR
- `team` exactly equals `data-platform`

### Conditions-based matching (AND logic)

```yaml
conditions:
  stringEquals:
    - conditionKey: Environment
      conditionValue: Production
  stringLike:
    - conditionKey: Service
      conditionValue: "payment-*"
    - conditionKey: Service
      conditionValue: "billing-*"
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
  backupPlanRef: dev-plan
  iamRoleRef: backup-service-role
  deletionPolicy: delete
  resources:
    - "arn:aws:ec2:us-east-1:123456789012:instance/i-*"
```

## Complete example

```yaml
---
# Select production databases by ARN
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: prod-databases
  namespace: production
spec:
  configRef: compliance
  backupPlanRef: critical-databases
  iamRoleRef: backup-service-role
  deletionPolicy: retain
  
  resources:
    - "arn:aws:rds:us-east-1:123456789012:db:prod-db-1"
    - "arn:aws:rds:us-east-1:123456789012:db:prod-db-2"
  
  tags:
    managed-by: kropath
    data-class: sensitive

---
# Select resources matching tag conditions (OR logic)
apiVersion: aws.kropath.run/v1alpha1
kind: BackupSelection
metadata:
  name: payment-services
  namespace: production
spec:
  configRef: compliance
  backupPlanRef: compliance-plan
  iamRoleRef: backup-service-role
  deletionPolicy: retain
  
  listOfTags:
    - conditionType: "STRINGEQUALS"
      conditionKey: Environment
      conditionValue: Production
  
  conditions:
    stringLike:
      - conditionKey: Service
        conditionValue: "payment-*"
      - conditionKey: Service
        conditionValue: "billing-*"
  
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

But they are NOT applied to AWS backup recovery points (selections don't support that). Resource tags on the selected AWS resources themselves are preserved during backup operations.

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
