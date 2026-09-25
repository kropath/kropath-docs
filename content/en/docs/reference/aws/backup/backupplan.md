---
title: BackupPlan
description: "`BackupPlan` is a Kubernetes-native wrapper around AWS Backup plans."
doc_type: reference
---
# BackupPlan

`BackupPlan` is a Kubernetes-native wrapper around AWS Backup plans. A backup plan defines backup rules — the schedule, target vault, retention, and recovery options — for backup operations. Use `BackupPlan` to provision backup plans with consistent governance via `BackupConfig`.

## Overview

A backup plan is a set of rules that define when and how to back up your resources. Each rule specifies:

- **Schedule** — when backups run (e.g., daily at 5 AM UTC)
- **Target vault** — which backup vault stores recovery points
- **Retention** — how long recovery points are kept
- **Recovery options** — whether continuous backup (PITR) is enabled, malware scanning, etc.

A backup plan can have multiple rules targeting different resources with different schedules.

## Governance via BackupConfig

`BackupPlan` reads governance from `BackupConfig` profiles via `spec.configRef`. The `BackupConfig` cascade enforces or defaults:

- PITR enablement (`enableContinuousBackup`)
- Retention and lifecycle policies (`defaultLifecycleDeleteAfterDays`, `defaultLifecycleMoveToColdStorageAfterDays`)
- Malware scanning (`enableMalwareScan`, `scannerRoleARN`)
- Lifecycle policies
- Naming templates
- Tags and labels

## Schema

### Spec fields

```yaml
spec:
  configRef: compliance      # Profile name; defaults to "general-policy" if doesn't exist
  displayName: ""                   # Human-readable display name (optional; derived from metadata.name if empty)
  deletionPolicy: retain            # "retain" | "delete"
  
  rules:
    - ruleName: hourly-backup
      targetBackupVaultName: prod-vault
      scheduleExpression: cron(0 * * * ? *)  # Every hour
      enableContinuousBackup: ""    # Empty: inherit from config
      startWindowMinutes: 60        # Backup must start within 60 minutes of schedule time
      completionWindowMinutes: 120  # Backup must complete within 120 minutes
      
      # Lifecycle
      lifecycle:
        deleteAfterDays: 35
        moveToColdStorageAfterDays: 0
      
      # Malware scanning per rule
      scanActions:
        - malwareScanner: STANDARD
          scanMode: FULL_SCAN
      
      # Recovery options
      recoveryPointTags:
        backup-type: "hourly"
        retention-period: "35-days"
  
  tags:
    environment: prod
    team: platform
```

### Status fields

```yaml
status:
  planId: 00000000-0000-0000-0000-000000000000  # AWS-assigned plan ID (UUID)
  planARN: arn:aws:backup:us-east-1:123456789012:backup-plan:00000000-0000-0000-0000-000000000000
  versionId: 1
  creationDate: "2026-01-15T10:30:00Z"
  lastExecutionDate: "2026-01-16T10:45:00Z"
  namingStatus: valid
  conditions:
    - type: Ready
      status: "True"
      reason: PlanReady
      message: Backup plan is ready
```

## Naming

`BackupPlan` uses a display name that you choose, but AWS assigns it an opaque UUID internally. The ARN format is `arn:aws:backup:{region}:{account_id}:backup-plan:{planId}`, not based on your chosen name.

**Important:** `status.planARN` is NOT available until after the plan is created and AWS returns the `planId`. You cannot reference the ARN in `status.predictedArn` pre-creation.

The naming template applies to the display name only:

```yaml
spec:
  configRef: general-policy  # Uses naming template "{namespace}-backup-{name}"
  # Display name becomes: "production-backup-critical-databases"
  # But the ARN uses the UUID: "arn:aws:backup:...:backup-plan:00000000-..."
```

## Backup rules

Each rule in `spec.rules` defines a single backup operation:

```yaml
rules:
  - ruleName: daily-full-backup
    targetBackupVaultName: prod-vault
    scheduleExpression: cron(0 2 * * ? *)  # 2 AM UTC daily
    enableContinuousBackup: true
    lifecycle:
      deleteAfterDays: 90
    scanActions:
      - malwareScanner: STANDARD
        scanMode: FULL_SCAN
```

**Rule fields:**

- `ruleName` — identifier for this rule (must be unique within the plan)
- `targetBackupVaultName` — name of the `BackupVault` to store recovery points
- `scheduleExpression` — cron expression defining backup schedule
- `startWindowMinutes` — how long after the schedule time backup can start (default: immediate)
- `completionWindowMinutes` — deadline for backup completion
- `enableContinuousBackup` — whether PITR is enabled (empty: inherit from config)
- `lifecycle` — retention and cold-storage settings
- `scanActions` — per-rule malware scanning configuration
- `recoveryPointTags` — tags to apply to recovery points (for organization and filtering)

## PITR (Continuous Backup)

Point-in-time recovery (PITR) lets you restore data to any moment, not just to backup snapshots. PITR requires:

- Supported resource type (RDS, DynamoDB, etc. — check AWS documentation)
- Continuous backup enabled on the source resource
- Backup plan rule with `enableContinuousBackup: true`

**Cost:** PITR incurs additional storage and API costs compared to snapshot-only backups.

**Enable PITR via BackupConfig:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: compliance
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    enableContinuousBackup: true    # Required for all backup rules
```

Backup plans using the `compliance` profile enforce PITR on all rules.

## Malware scanning

AWS Backup can scan recovery points for malware during backup operations. Scanning adds time and cost but provides additional security for sensitive workloads.

**Enable malware scanning via BackupConfig:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupConfig
metadata:
  name: compliance
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    enableMalwareScan: true
    scannerRoleARN: "arn:aws:iam::123456789012:role/BackupMalwareScanner"
```

Backup plans using the `compliance` profile enforce malware scanning on all rules and use the specified IAM role.

**Scanning configuration per rule:**

```yaml
rules:
  - ruleName: scan-ebs-volumes
    scanActions:
      - malwareScanner: STANDARD
        scanMode: FULL_SCAN
```

## Deletion policy

The `deletionPolicy` annotation controls what happens when the `BackupPlan` CR is deleted:

- `retain` (default) — the plan remains in AWS
- `delete` — the plan is deleted from AWS

Use `retain` for production plans. Use `delete` for development and testing.

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupPlan
metadata:
  name: dev-plan
spec:
  configRef: dev
  deletionPolicy: delete
```

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: BackupPlan
metadata:
  name: critical-databases
  namespace: production
spec:
  configRef: compliance
  deletionPolicy: retain
  
  rules:
    - ruleName: hourly-incremental
      targetBackupVaultName: prod-vault
      scheduleExpression: cron(0 * * * ? *)  # Every hour
      enableContinuousBackup: ""  # Inherit from compliance profile (PITR enforced via mandatory)
      lifecycle:
        deleteAfterDays: 35
        moveToColdStorageAfterDays: 0
    
    - ruleName: weekly-full-with-scan
      targetBackupVaultName: prod-vault
      scheduleExpression: cron(0 3 ? * 1 *)  # Monday 3 AM UTC
      enableContinuousBackup: ""
      lifecycle:
        deleteAfterDays: 180
        moveToColdStorageAfterDays: 90
      scanActions:
        - malwareScanner: STANDARD
          scanMode: FULL_SCAN
  
  tags:
    cost-center: "data-platform"
    criticality: "high"
```

This plan:
- Uses the `compliance` profile, inheriting PITR enablement and malware scanning
- Has two rules: an hourly incremental backup and a weekly full backup with scanning
- Keeps recovery points for 35 days (hourly) or 180 days (weekly)
- Will not be deleted when the CR is deleted

## Related resources

- [`BackupConfig`](./backupconfig.md) — governance and profile configuration
- [`BackupVault`](./backupvault.md) — storage container for recovery points
- [`BackupSelection`](./backupselection.md) — resource selection for backup
- `KropathConfig` — org-wide configuration

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `BackupPlan`
- **Scope**: Namespaced
- **Plural**: `backupplans`
