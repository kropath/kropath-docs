# RDSConfig — Governance Configuration

The `RDSConfig` resource defines governance profiles that control RDS database behavior across your organization and namespaces. Platform teams create named profiles; developers and operators select the profile they need via `spec.configRef` on each RDS instance, cluster, subnet group, and proxy.

## Overview

`RDSConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., all databases must have encryption enabled, backup retention minimum)
- **Defaults tier** — Baseline values developers can override (e.g., default storage type if not specified)

This two-tier approach lets platform teams enforce critical compliance and operational controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `storageEncrypted` | boolean | If `true`, all instances and clusters must have encryption at rest enabled |
| `kmsKeyID` | string | Forces all instances and clusters to use a specific KMS key (ARN) |
| `deletionProtection` | boolean | If `true`, all instances and clusters have deletion protection enabled |
| `backupRetentionPeriod` | integer | Minimum backup retention days (instances/clusters can retain longer) |
| `multiAZ` | boolean | If `true`, all instances and clusters must deploy as Multi-AZ |
| `publiclyAccessible` | boolean | If `false` (explicitly), all instances are forced private-only |
| `storageType` | string | Forces a specific storage type (e.g., `gp3`, `io1`) |
| `autoMinorVersionUpgrade` | boolean | If `true`, all instances auto-upgrade minor versions |
| `copyTagsToSnapshot` | boolean | If `true`, all snapshots inherit tags from database |
| `performanceInsightsEnabled` | boolean | If `true`, Performance Insights is enabled on all instances/clusters |
| `enableIAMDatabaseAuthentication` | boolean | If `true`, IAM database authentication is required |
| `manageMasterUserPassword` | boolean | If `true`, master password must be managed via AWS Secrets Manager |
| `serverlessV2ScalingMinCapacity` | number | Minimum ACUs for Aurora Serverless v2 clusters |
| `serverlessV2ScalingMaxCapacity` | number | Maximum ACUs for Aurora Serverless v2 clusters |
| `backtrackWindow` | integer | Mandatory backtrack window (seconds) for Aurora MySQL clusters |
| `namingTemplate` | string | Template for resource names |
| `tags` | map | Tags applied to all resources (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Purpose |
|---|---|---|
| `storageEncrypted` | boolean | Default encryption behavior (default: `true` — encrypted) |
| `kmsKeyID` | string | Default KMS key if not specified (default: AWS-managed key) |
| `deletionProtection` | boolean | Default deletion protection (default: `true` — protected) |
| `backupRetentionPeriod` | integer | Default backup retention in days (default: `7`) |
| `multiAZ` | boolean | Default Multi-AZ behavior (default: `false` — single-AZ for cost) |
| `publiclyAccessible` | boolean | Default public accessibility (default: `false` — private-only) |
| `storageType` | string | Default storage type (default: `"gp3"` for instances, `"aurora"` for clusters) |
| `autoMinorVersionUpgrade` | boolean | Default auto-upgrade behavior (default: `true`) |
| `copyTagsToSnapshot` | boolean | Default snapshot tagging (default: `true`) |
| `performanceInsightsEnabled` | boolean | Default Performance Insights (default: `false` for cost) |
| `enableIAMDatabaseAuthentication` | boolean | Default IAM auth (default: `false`) |
| `manageMasterUserPassword` | boolean | Default password management (default: `false` — manual) |
| `serverlessV2ScalingMinCapacity` | number | Default minimum ACUs (default: `0` — no default) |
| `serverlessV2ScalingMaxCapacity` | number | Default maximum ACUs (default: `0` — no default) |
| `backtrackWindow` | integer | Default backtrack window (default: `0` — disabled) |
| `namingTemplate` | string | Default naming template (default: `"{namespace}-{name}"`) |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. Empty values (`""`, `0`, `false`, `[]`, `{}`) can appear in both tiers — they indicate "not set" and don't trigger the mutual-exclusion check.

## Example Profiles

### Conservative Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    storageEncrypted: true
    deletionProtection: true
    backupRetentionPeriod: 7
    multiAZ: false
    publiclyAccessible: false
    storageType: "gp3"
    autoMinorVersionUpgrade: true
    copyTagsToSnapshot: true
    performanceInsightsEnabled: false
    enableIAMDatabaseAuthentication: false
    manageMasterUserPassword: false
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
      team: platform
```

This profile uses sensible defaults: encryption and deletion protection enabled, 7-day backups, private-only access. Developers can override most fields unless the mandatory tier restricts them.

### Production Hardened (production)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    storageEncrypted: true          # All production databases must be encrypted
    deletionProtection: true        # All production databases are protected
    backupRetentionPeriod: 30       # Minimum 30-day backups
    multiAZ: true                   # All production databases are Multi-AZ
    autoMinorVersionUpgrade: true   # All production databases auto-upgrade
    tags:
      environment: production
      compliance: required
  defaults:
    performanceInsightsEnabled: true
    enableIAMDatabaseAuthentication: true
    manageMasterUserPassword: true
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      cost-center: prod-eng
```

This hardened profile enforces strict controls for production workloads: encryption, deletion protection, Multi-AZ deployment, and 30-day minimum backups are mandatory. Performance Insights and IAM authentication are enabled by default.

### Development (development)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}
  defaults:
    storageEncrypted: false         # Dev databases may skip encryption for speed
    deletionProtection: false       # Dev databases can be deleted freely
    backupRetentionPeriod: 1        # Minimal backup retention
    multiAZ: false                  # Single-AZ to reduce cost
    publiclyAccessible: false       # Still private-only by default
    performanceInsightsEnabled: false
    manageMasterUserPassword: false
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development
```

This development profile minimizes cost with single-AZ deployments, minimal backups, and optional encryption. No mandatory controls.

## Profile Selection

Resources select which `RDSConfig` profile to use via `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: app-db
  namespace: default
spec:
  configRef: production          # Uses the 'production' RDSConfig profile
  engine: postgres
  engineVersion: "15.4"
  dbInstanceClass: db.m5.large
  allocatedStorage: 100
```

If `configRef` is omitted or empty, the default `"general-policy"` profile is used.

## Cascade Semantics

When resolving database configuration, kropath merges settings from three sources in this order (lowest to highest priority):

1. **RDSConfig defaults tier** — Platform baseline values
2. **Resource `spec` fields** — Developer overrides
3. **RDSConfig mandatory tier** — Non-negotiable platform controls

The mandatory tier always wins. For example:

- If `RDSConfig.mandatory.deletionProtection = true`, the database has deletion protection regardless of `spec.deletionProtection`
- If `RDSConfig.defaults.backupRetentionPeriod = 7` and `spec.backupRetentionPeriod = 14`, the database uses 14 days (developer override)
- If `RDSConfig.mandatory.backupRetentionPeriod = 30` and `spec.backupRetentionPeriod = 14`, the database uses 30 days (mandatory wins)

## Best Practices

1. **Use mandatory tier sparingly.** Reserve it for compliance-critical controls (encryption, deletion protection, backup retention minimums).
2. **Provide sensible defaults.** The defaults tier should reflect your organization's standard practices without blocking flexibility.
3. **Version your profiles.** Consider naming profiles by compliance/environment level rather than team names (profiles can outlive team reorganizations).
4. **Document trade-offs.** Include comments in your profiles explaining why each control is set the way it is.
5. **Monitor non-compliance.** Use cloud governance tools to audit instances that violate mandatory controls.
