---
title: RDSCluster — Creating and Managing Aurora Database Clusters
description: "The `RDSCluster` resource creates and manages an AWS Aurora database cluster (Aurora MySQL or Aurora PostgreSQL) or Multi-AZ DB cluster."
doc_type: reference
---
# RDSCluster — Creating and Managing Aurora Database Clusters

The `RDSCluster` resource creates and manages an AWS Aurora database cluster (Aurora MySQL or Aurora PostgreSQL) or Multi-AZ DB cluster. Aurora is a cloud-optimized database engine that combines the performance of commercial databases with the simplicity and cost-effectiveness of open-source engines.

## What It Does

An Aurora cluster:
- Provisions a managed, distributed relational database with read replicas
- Handles automated failover across multiple Availability Zones
- Scales storage automatically — no need to pre-provision capacity
- Supports serverless auto-scaling via Serverless v2
- Provides high throughput and low-latency read replicas
- Encrypts data at rest and in transit
- Integrates with AWS Secrets Manager for password management

## What It Doesn't Do

This resource creates the **cluster control plane** only. Individual **database instances** that join the cluster are created separately via `RDSInstance` resources with `spec.dbClusterIdentifier` set to the cluster name.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `RDSConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the cluster identifier directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` |

### Engine Configuration (Required)

| Field | Type | Purpose |
|---|---|---|
| `engine` | string | Database engine: `aurora-mysql`, `aurora-postgresql`, `mysql`, `postgres` |
| `engineVersion` | string | Version (e.g., `8.0.mysql_aurora.3.04.0`, `15.2`); omit for AWS default |

### Storage

| Field | Type | Default | Purpose |
|---|---|---|---|
| `storageEncrypted` | boolean | fallthrough | Encryption at rest (falls through to governance) |
| `kmsKeyID` | string | fallthrough | KMS key ARN for encryption (falls through to governance) |

### Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dbSubnetGroupName` | string | `""` | Name of the DB subnet group for VPC placement |
| `vpcSecurityGroupIDs` | array | `[]` | VPC security group IDs for network access control |
| `port` | integer | `0` | Database port; `0` = engine default (Aurora MySQL: 3306, Aurora PostgreSQL: 5432) |
| `publiclyAccessible` | boolean | fallthrough | Public internet access (for Multi-AZ DB clusters only; falls through to governance) |

### Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `masterUsername` | string | (required on create) | Master user name |
| `masterUserPassword` | object | null | Kubernetes Secret reference with password (mutually exclusive with `manageMasterUserPassword`) |
| `manageMasterUserPassword` | boolean | fallthrough | Use AWS Secrets Manager for password (falls through to governance) |
| `enableIAMDatabaseAuthentication` | boolean | fallthrough | IAM-based authentication (falls through to governance) |

### Database

| Field | Type | Default | Purpose |
|---|---|---|---|
| `databaseName` | string | `""` | Initial database name (up to 64 alphanumeric characters) |

### Deletion Protection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deletionProtection` | boolean | fallthrough | Prevent accidental deletion (falls through to governance) |

### Backup

| Field | Type | Default | Purpose |
|---|---|---|---|
| `backupRetentionPeriod` | integer | fallthrough | Backup retention in days (1–35; falls through to governance) |
| `preferredBackupWindow` | string | `""` | Daily backup window (e.g., `"07:00-09:00"`) |
| `copyTagsToSnapshot` | boolean | fallthrough | Copy cluster tags to snapshots (falls through to governance) |

### Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `preferredMaintenanceWindow` | string | `""` | Weekly maintenance window (e.g., `"Mon:00:00-Mon:03:00"`) |
| `autoMinorVersionUpgrade` | boolean | fallthrough | Automatic minor version upgrades (falls through to governance) |

### Monitoring (Multi-AZ DB Clusters only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `monitoringInterval` | integer | `0` | Enhanced Monitoring interval in seconds (0 = disabled) |
| `monitoringRoleARN` | string | `""` | IAM role ARN for Enhanced Monitoring |
| `enablePerformanceInsights` | boolean | fallthrough | CloudWatch Performance Insights (falls through to governance) |
| `performanceInsightsRetentionPeriod` | integer | `7` | PI retention: 7 or 731 days |

### Logging

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enableCloudwatchLogsExports` | array | `[]` | CloudWatch log types (engine-specific: `error`, `general`, `slowquery`, `postgres`) |

### Serverless v2 Auto-Scaling

| Field | Type | Default | Purpose |
|---|---|---|---|
| `serverlessV2ScalingConfiguration.minCapacity` | number | `0` | Minimum Aurora Capacity Units (ACUs); 0 = not serverless v2 |
| `serverlessV2ScalingConfiguration.maxCapacity` | number | `0` | Maximum ACUs (up to 128 ACUs) |

When both are non-zero, the cluster auto-scales between `minCapacity` and `maxCapacity` based on workload demand.

### Aurora Backtrack (Aurora MySQL only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `backtrackWindow` | integer | `0` | Backtrack window in seconds (0 = disabled); limited to recent 72 hours |

Backtracking allows you to revert the cluster to a previous point in time without restoring from a backup — useful for recovering from accidental data changes.

### Aurora Features

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enableHTTPEndpoint` | boolean | `false` | Enable Aurora Serverless Data API for HTTPS-based queries |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** Cluster identifiers must be 1–63 characters with lowercase letters, digits, and hyphens
- **Predictable ARN:** `arn:aws:rds:<region>:<account-id>:cluster:<cluster-name>`

Use `nameOverride` to set a custom identifier if the default template doesn't fit your naming scheme.

## Complete Example: Production Aurora PostgreSQL Cluster with Serverless v2

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSCluster
metadata:
  name: serverless-analytics
  namespace: data-prod
spec:
  configRef: production
  deletionPolicy: retain
  
  # Engine
  engine: aurora-postgresql
  engineVersion: "15.2"
  
  # Storage & Encryption (falls through to governance)
  # storageEncrypted and kmsKeyID come from RDSConfig mandatory tier
  
  # Networking
  dbSubnetGroupName: prod-multi-az-subnets
  vpcSecurityGroupIDs:
    - sg-prod-aurora-access
  port: 5432
  
  # Authentication
  masterUsername: admin
  masterUserPassword:
    name: analytics-cluster-secret
    key: password
  
  # Database
  databaseName: analytics
  
  # Serverless v2 Auto-Scaling
  serverlessV2ScalingConfiguration:
    minCapacity: 2      # Minimum 2 ACUs (handles baseline load)
    maxCapacity: 16     # Scale up to 16 ACUs during peak
  
  # Backup & Maintenance
  preferredBackupWindow: "03:00-05:00"
  preferredMaintenanceWindow: "Sun:05:00-Sun:06:00"
  
  # Logging (optional)
  enableCloudwatchLogsExports:
    - postgresql
  
  # Tags
  tags:
    environment: production
    team: analytics
    cost-center: data-eng
  syncedLabels:
    tier: critical
    backup-policy: daily
```

Result:
- Aurora PostgreSQL cluster named `data-prod-serverless-analytics`
- Serverless v2 scaling between 2–16 ACUs (auto-scales based on workload)
- Multi-AZ deployment (via subnet group)
- Encryption enabled via production governance profile
- Deletion protected via governance
- Automatic 30-day backups via governance
- Performance Insights and PostgreSQL logs exported to CloudWatch

## Example: Aurora MySQL with Backtrack

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSCluster
metadata:
  name: transactional-db
  namespace: app-prod
spec:
  configRef: production
  engine: aurora-mysql
  engineVersion: "8.0.mysql_aurora.3.04.0"
  
  # Aurora Backtrack (MySQL only)
  # Allows reverting to any point in the last 72 hours
  backtrackWindow: 259200  # 72 hours in seconds
  
  dbSubnetGroupName: app-prod-subnets
  vpcSecurityGroupIDs:
    - sg-app-db-access
  masterUsername: admin
  databaseName: transactions
  
  # Standard backup settings
  backupRetentionPeriod: 35  # Maximum retention
  preferredBackupWindow: "02:00-04:00"
```

Result:
- Aurora MySQL cluster with 72-hour backtrack capability
- 35-day backup retention (maximum allowed)
- Can instantly revert to any point within the last 72 hours (useful for accidental data deletion)

## Adding Cluster Members

Once a cluster is created, you can add read replicas and instances to it by creating `RDSInstance` resources that reference the cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: writer-instance
  namespace: data-prod
spec:
  configRef: production
  engine: aurora-postgresql
  dbInstanceClass: db.r5.large
  dbClusterIdentifier: data-prod-serverless-analytics  # Reference the cluster
  
  # Note: This instance does NOT specify storage allocation or engine version
  # Those come from the cluster configuration

---
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: reader-instance
  namespace: data-prod
spec:
  configRef: production
  engine: aurora-postgresql
  dbInstanceClass: db.r5.large
  dbClusterIdentifier: data-prod-serverless-analytics  # Same cluster
```

The first instance typically serves as the writer; additional instances act as read-only replicas. The cluster automatically distributes traffic and handles failover.

## Status Fields

After creation, the cluster exposes status fields for monitoring:

| Field | Type | Meaning |
|---|---|---|
| `status.resourceName` | string | The resolved cluster identifier (from naming template or override) |
| `status.predictedArn` | string | The predicted AWS ARN (formatted before creation) |
| `status.namingStatus` | string | `"valid"` if all naming tokens resolved, `"invalid-unresolved-tokens"` otherwise |
| `status.endpoint` | string | Cluster write endpoint (available after creation) |
| `status.readerEndpoint` | string | Cluster read-only endpoint (available after creation) |
| `status.port` | integer | Database port (available after creation) |
| `status.dbClusterStatus` | string | AWS status: `creating`, `available`, `modifying`, `deleting`, etc. |

Use the endpoints to configure application connection strings:

```bash
# Write endpoint (all instances)
kubectl get rdscluster serverless-analytics -o jsonpath='{.status.endpoint}'
# Output: data-prod-serverless-analytics.abcdefg123.us-east-1.rds.amazonaws.com

# Read-only endpoint (read replicas only)
kubectl get rdscluster serverless-analytics -o jsonpath='{.status.readerEndpoint}'
# Output: data-prod-serverless-analytics.cluster-ro-abcdefg123.us-east-1.rds.amazonaws.com
```

## Best Practices

1. **Serverless v2 for variable workloads.** Use `serverlessV2ScalingConfiguration` if your workload has variable demand; pay only for what you use.
2. **Always enable backups.** Set `backupRetentionPeriod` to at least 7 days (production should use 30+).
3. **Enable backtrack for Aurora MySQL.** Backtrack provides instant recovery from accidental changes.
4. **Use separate instances for read traffic.** Create read-only `RDSInstance` resources with higher `dbInstanceClass` to handle analytical workloads without impacting transactional traffic.
5. **Monitor via CloudWatch.** Enable Enhanced Monitoring and Performance Insights to detect performance issues.
6. **Encryption and deletion protection.** Let governance profiles handle these — don't rely on developers to remember.
7. **Multi-AZ by default.** Use a subnet group spanning 3+ Availability Zones for automatic failover.
8. **Data API for serverless applications.** Enable `enableHTTPEndpoint` if your serverless functions need HTTPS-based database access.

## Cross-Family References

RDS clusters can be referenced by other resources:

- **RDS Instances:** Join the cluster via `spec.dbClusterIdentifier`
- **RDS Proxy:** Can sit in front of a cluster for connection pooling
- **Secrets Manager:** Stores the master user password (if `manageMasterUserPassword = true`)
- **KMS:** Encrypts the database (if `storageEncrypted = true`)
- **IAM:** Provides Enhanced Monitoring role and optional IAM database authentication
- **Application workloads:** Connect via the cluster endpoint and port
