# RDSInstance — Creating and Managing RDS Database Instances

The `RDSInstance` resource creates and manages a standalone AWS RDS database instance. This is the primary resource for non-Aurora relational database workloads using MySQL, PostgreSQL, Oracle, or SQL Server engines.

## What It Does

An RDS instance:
- Provisions a managed, single-node or Multi-AZ relational database
- Handles automated backups, patching, and failover (if Multi-AZ)
- Encrypts data at rest and in transit
- Integrates with AWS Secrets Manager for password management
- Supports monitoring via CloudWatch and Performance Insights

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `RDSConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the DB instance identifier directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` |

### Engine Configuration (Required)

| Field | Type | Purpose |
|---|---|---|
| `engine` | string | Database engine: `mysql`, `postgres`, `oracle-ee`, `sqlserver-ex`, etc. |
| `engineVersion` | string | Version (e.g., `8.0.35`, `15.4`); omit for AWS default |

### Compute

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dbInstanceClass` | string | (required) | Instance size (e.g., `db.m5.large`, `db.t3.medium`) |

### Storage

| Field | Type | Default | Purpose |
|---|---|---|---|
| `allocatedStorage` | integer | `20` | Initial storage in GiB |
| `storageType` | string | fallthrough | Storage type: `gp2`, `gp3`, `io1`, `io2` (falls through to governance) |
| `iops` | integer | `0` | Provisioned IOPS (for `io1`/`io2`/`gp3`) |
| `storageThroughput` | integer | `0` | MB/s throughput for `gp3` |
| `maxAllocatedStorage` | integer | `0` | Enable storage autoscaling up to this limit; `0` = disabled |
| `storageEncrypted` | boolean | fallthrough | Encryption at rest (falls through to governance) |
| `kmsKeyID` | string | fallthrough | KMS key ARN for encryption (falls through to governance) |

### Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dbSubnetGroupName` | string | `""` | Name of the DB subnet group for VPC placement |
| `vpcSecurityGroupIDs` | array | `[]` | VPC security group IDs for network access control |
| `publiclyAccessible` | boolean | fallthrough | Public internet access (falls through to governance) |
| `port` | integer | `0` | Database port; `0` = engine default (MySQL: 3306, PostgreSQL: 5432) |

### High Availability

| Field | Type | Default | Purpose |
|---|---|---|---|
| `multiAZ` | boolean | fallthrough | Multi-AZ deployment with automatic failover (falls through to governance) |
| `availabilityZone` | string | `""` | Specific AZ (ignored if `multiAZ` = true) |

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
| `dbName` | string | `""` | Initial database name (omit if engine is Oracle) |
| `characterSetName` | string | `""` | Character encoding (Oracle only) |

### Deletion Protection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deletionProtection` | boolean | fallthrough | Prevent accidental deletion (falls through to governance) |

### Backup

| Field | Type | Default | Purpose |
|---|---|---|---|
| `backupRetentionPeriod` | integer | fallthrough | Backup retention in days; 0 = no backups (falls through to governance) |
| `preferredBackupWindow` | string | `""` | Daily backup window (e.g., `"07:00-09:00"`) |
| `copyTagsToSnapshot` | boolean | fallthrough | Copy instance tags to snapshots (falls through to governance) |

### Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `preferredMaintenanceWindow` | string | `""` | Weekly maintenance window (e.g., `"Mon:00:00-Mon:03:00"`) |
| `autoMinorVersionUpgrade` | boolean | fallthrough | Automatic minor version upgrades (falls through to governance) |

### Monitoring

| Field | Type | Default | Purpose |
|---|---|---|---|
| `monitoringInterval` | integer | `0` | Enhanced Monitoring interval in seconds (0 = disabled; 1, 5, 10, 15, 30, 60 = enabled) |
| `monitoringRoleARN` | string | `""` | IAM role ARN for Enhanced Monitoring |
| `performanceInsightsEnabled` | boolean | fallthrough | CloudWatch Performance Insights (falls through to governance) |
| `performanceInsightsRetentionPeriod` | integer | `7` | PI retention: 7 or 731 days |

### Logging

| Field | Type | Default | Purpose |
|---|---|---|---|
| `enableCloudwatchLogsExports` | array | `[]` | CloudWatch log types (engine-specific: `error`, `general`, `slowquery`, `postgres`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** DB instance identifiers must be 1–63 characters with lowercase letters, digits, and hyphens
- **Predictable ARN:** `arn:aws:rds:<region>:<account-id>:db:<instance-name>`

Use `nameOverride` to set a custom identifier if the default template doesn't fit your naming scheme.

## Complete Example: Production PostgreSQL Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: analytics-db
  namespace: data-prod
spec:
  configRef: production
  nameOverride: ""  # Use default naming
  deletionPolicy: retain
  
  # Engine
  engine: postgres
  engineVersion: "15.4"
  
  # Compute
  dbInstanceClass: db.m5.large
  
  # Storage
  allocatedStorage: 500
  storageType: gp3
  iops: 3000
  storageThroughput: 125
  maxAllocatedStorage: 1000
  
  # Networking
  dbSubnetGroupName: prod-multi-az-subnets
  vpcSecurityGroupIDs:
    - sg-0a1b2c3d4e5f6g7h8
  port: 5432
  
  # High Availability
  multiAZ: true
  
  # Authentication
  masterUsername: admin
  masterUserPassword:
    name: analytics-db-secret
    key: password
  
  # Database
  dbName: analytics
  
  # Monitoring
  monitoringInterval: 60
  monitoringRoleARN: arn:aws:iam::123456789012:role/rds-monitoring
  performanceInsightsEnabled: true
  enableCloudwatchLogsExports:
    - postgresql
  
  # Backup and Maintenance
  preferredBackupWindow: "03:00-05:00"
  preferredMaintenanceWindow: "Sun:05:00-Sun:06:00"
  
  # Tags
  tags:
    environment: production
    team: analytics
    cost-center: data-eng
  syncedLabels:
    backup-policy: daily
    monitoring: required
```

Result:
- PostgreSQL 15.4 instance named `data-prod-analytics-db`
- Multi-AZ deployment with 500 GiB `gp3` storage and autoscaling to 1 TiB
- Encryption enabled via governance (production profile)
- Deletion protected via governance
- Automatic 30-day backups via governance
- Performance Insights and PostgreSQL logs exported to CloudWatch
- Enhanced Monitoring every 60 seconds

## Development Instance (Cost-Optimized)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: dev-db
  namespace: database-dev
spec:
  configRef: development
  engine: mysql
  engineVersion: "8.0.35"
  dbInstanceClass: db.t3.small
  allocatedStorage: 20
  
  # Use defaults from 'development' profile
  # - Single-AZ (no multiAZ)
  # - No encryption (dev profile allows)
  # - Minimal backups
  
  dbSubnetGroupName: dev-subnets
  masterUsername: admin
```

Result:
- MySQL 8.0 instance with minimal cost
- Single-AZ deployment
- No encryption (dev profile allows)
- Minimal backup retention

## Status Fields

After creation, the instance exposes status fields for monitoring:

| Field | Type | Meaning |
|---|---|---|
| `status.resourceName` | string | The resolved DB instance identifier (from naming template or override) |
| `status.predictedArn` | string | The predicted AWS ARN (formatted before creation) |
| `status.namingStatus` | string | `"valid"` if all naming tokens resolved, `"invalid-unresolved-tokens"` otherwise |
| `status.endpoint` | string | Database endpoint (available after creation) |
| `status.port` | integer | Database port (available after creation) |
| `status.dbInstanceStatus` | string | AWS status: `creating`, `available`, `modifying`, `deleting`, etc. |

Use the endpoint to configure application connection strings:

```bash
kubectl get rdsinstance dev-db -o jsonpath='{.status.endpoint}'
# Output: database-dev-dev-db.abcdefg123.us-east-1.rds.amazonaws.com
```

## Best Practices

1. **Always set backupRetentionPeriod.** Even in dev environments, keep at least 1-day backups to recover from accidental data loss.
2. **Use Multi-AZ for production.** Automatic failover provides high availability.
3. **Enable monitoring.** Enhanced Monitoring and Performance Insights help diagnose issues early.
4. **Encryption by default.** Let governance handle encryption — don't require developers to remember to enable it.
5. **Deletion protection.** Set `deletionPolicy: retain` and enable `deletionProtection` via governance to prevent accidental deletion.
6. **Security groups.** Restrict network access to application subnets; avoid `0.0.0.0/0`.
7. **Parameter groups.** For custom database settings, create a separate `RDSParameterGroup` and reference it by name.

## Cross-Family References

RDS instances can be referenced by other resources:

- **RDS Proxy:** Can sit in front of an instance for connection pooling
- **Secrets Manager:** Stores the master user password (if `manageMasterUserPassword = true`)
- **KMS:** Encrypts the database (if `storageEncrypted = true`)
- **IAM:** Provides Enhanced Monitoring role and optional IAM database authentication
- **Application workloads:** Connect via the endpoint and port
