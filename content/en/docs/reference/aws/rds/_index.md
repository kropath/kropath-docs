---
title: RDS — Managed Relational Database Family
description: The RDS family in kropath provides a declarative Kubernetes interface for managing Amazon RDS databases and Aurora clusters.
doc_type: reference
weight: 430
---
# RDS — Managed Relational Database Family

The RDS family in kropath provides a declarative Kubernetes interface for managing Amazon RDS databases and Aurora clusters. Use these resources to provision, configure, and govern relational databases across your AWS infrastructure.

## Resources in This Family

| Resource | Purpose | When to Use |
|---|---|---|
| **[RDSConfig](rdsconfig.md)** | Governance configuration | Defines mandatory and default database settings for your organization |
| **[RDSSubnetGroup](rdssubnetgroup.md)** | VPC subnet placement | Determines which subnets and AZs your databases can use |
| **[RDSInstance](rdsinstance.md)** | Standalone database | Single RDS instance (MySQL, PostgreSQL, Oracle, SQL Server) |
| **[RDSCluster](rdscluster.md)** | Aurora cluster | Distributed Aurora database (MySQL or PostgreSQL) with auto-scaling |
| **[RDSParameterGroup](rdsparametergroup.md)** | Instance engine parameters | Configure engine-level settings for RDS instances |
| **[RDSClusterParameterGroup](rdsclusterparametergroup.md)** | Cluster engine parameters | Configure engine-level settings for Aurora clusters |
| **[RDSProxy](rdsproxy.md)** | Connection pooling | Managed proxy for connection pooling and high-concurrency workloads |

## Quick Start

### 1. Create a Subnet Group (if not already created)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSSubnetGroup
metadata:
  name: app-subnets
  namespace: default
spec:
  description: "Multi-AZ subnet group for RDS"
  subnetIDs:
    - subnet-1a-id
    - subnet-1b-id
```

### 2. Create a Database Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: app-db
  namespace: default
spec:
  configRef: general-policy
  engine: postgres
  engineVersion: "15.4"
  dbInstanceClass: db.m5.large
  allocatedStorage: 100
  dbSubnetGroupName: default-app-subnets  # Matches {namespace}-{name} from subnet group
  masterUsername: postgres
  masterUserPassword:
    name: postgres-secret
    key: password
```

### 3. Retrieve the Database Endpoint

```bash
kubectl get rdsinstance app-db -o jsonpath='{.status.endpoint}'
# Output: default-app-db.abcdef123.us-east-1.rds.amazonaws.com
```

Use this endpoint in your application configuration or connection strings.

## Governance with RDSConfig

`RDSConfig` defines governance profiles that enforce organizational policies:

- **Encryption requirements** — mandate encryption at rest for sensitive data
- **Backup retention** — enforce minimum backup retention periods
- **Deletion protection** — prevent accidental database deletion
- **High availability** — require Multi-AZ for production workloads
- **Monitoring** — enforce Performance Insights or Enhanced Monitoring
- **Naming conventions** — standardize resource naming across teams

See [RDSConfig](rdsconfig.md) for detailed governance configuration.

## Common Scenarios

### Production Database with High Availability

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: prod-db
  namespace: production
spec:
  configRef: production          # Uses hardened governance profile
  engine: postgres
  engineVersion: "15.4"
  dbInstanceClass: db.m5.xlarge
  allocatedStorage: 500
  storageType: gp3
  iops: 3000
  multiAZ: true                  # Automatic failover
  dbSubnetGroupName: prod-multi-az
  masterUsername: admin
  
  # Monitoring
  monitoringInterval: 60
  monitoringRoleARN: arn:aws:iam::123456789012:role/rds-monitoring
  performanceInsightsEnabled: true
  
  # Backup
  backupRetentionPeriod: 30
  preferredBackupWindow: "02:00-04:00"
```

Result: Production-grade database with Multi-AZ failover, comprehensive monitoring, and 30-day backups.

### Development Database (Cost-Optimized)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: dev-db
  namespace: development
spec:
  configRef: development         # Uses cost-optimized profile
  engine: mysql
  dbInstanceClass: db.t3.small
  allocatedStorage: 20
  dbSubnetGroupName: dev-subnets
  masterUsername: admin
```

Result: Single-AZ database with minimal resources for development and testing.

### Aurora Serverless Cluster for Variable Workloads

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSCluster
metadata:
  name: serverless-api-db
  namespace: api-prod
spec:
  configRef: production
  engine: aurora-postgresql
  engineVersion: "15.2"
  databaseName: api
  dbSubnetGroupName: prod-multi-az
  masterUsername: postgres
  
  # Serverless v2 scales automatically
  serverlessV2ScalingConfiguration:
    minCapacity: 1
    maxCapacity: 8
  
  # Monitoring
  enablePerformanceInsights: true
  enableCloudwatchLogsExports:
    - postgresql
```

Result: Aurora cluster that automatically scales from 1–8 ACUs based on demand — pay only for what you use.

## Architecture

### Resource Relationships

```
RDSConfig (governance profiles)
    ↓
    ├─→ RDSSubnetGroup (VPC placement)
    │
    ├─→ RDSInstance (single database)
    │   ├─ Tuned by: RDSParameterGroup
    │   ├─ Proxied by: RDSProxy
    │   ├─ References: KMS key, IAM role, Secrets Manager
    │   └─ Deployed to: Subnet group + security groups
    │
    └─→ RDSCluster (Aurora cluster)
        ├─ Tuned by: RDSClusterParameterGroup
        ├─ Proxied by: RDSProxy
        ├─ References: KMS key, IAM role, Secrets Manager
        ├─ Deployed to: Subnet group + security groups
        └─ Contains: RDSInstance members (read replicas)
```

### Governance Cascade

Three tiers of configuration merge to determine the final database settings:

| Tier | Source | Priority |
|---|---|---|
| 1 (Lowest) | `RDSConfig.spec.defaults.*` | Platform baseline settings |
| 2 (Middle) | `RDSInstance.spec.*` or `RDSCluster.spec.*` | Developer overrides |
| 3 (Highest) | `RDSConfig.spec.mandatory.*` | Non-negotiable platform controls |

The mandatory tier always wins. For example:

- Platform sets `mandatory.deletionProtection: true` → Database always has deletion protection, regardless of instance spec
- Platform sets `defaults.backupRetentionPeriod: 7`, developer specifies `14` → Uses 14 days (developer override)
- Platform sets `mandatory.storageEncrypted: true` → Encryption is forced, cannot be disabled

See [RDSConfig](rdsconfig.md) for detailed governance semantics.

## Supported Engines

### RDS Instances (Single Database)

| Engine | Versions | Notes |
|---|---|---|
| **MySQL** | 5.7, 8.0 | Use `mysql` |
| **PostgreSQL** | 11–16 | Use `postgres` |
| **Oracle** | 19c, 21c, 23c | Use `oracle-ee`, `oracle-se2`, `oracle-ex` |
| **SQL Server** | 2019, 2022 | Use `sqlserver-ex`, `sqlserver-se`, `sqlserver-ee` |

### Aurora Clusters

| Engine | Versions | Notes |
|---|---|---|
| **Aurora MySQL** | Compatible with MySQL 5.7, 8.0 | Use `aurora-mysql` |
| **Aurora PostgreSQL** | Compatible with PostgreSQL 11–16 | Use `aurora-postgresql` |

## Best Practices

1. **Use governance profiles.** Never skip `configRef` — always select an appropriate governance profile (`general-policy`, `production`, `development`, etc.)

2. **Enable Multi-AZ for production.** High-availability deployments require subnets spanning multiple Availability Zones.

3. **Backup retention.** Set minimum `backupRetentionPeriod` to at least 7 days (production should use 30+).

4. **Encryption by default.** Let governance profiles enable encryption — don't burden developers with security choices.

5. **Deletion protection.** Enable `deletionProtection` via governance to prevent accidental database deletion.

6. **Monitoring and alerting.** Enable CloudWatch metrics, Enhanced Monitoring, and Performance Insights for production databases.

7. **Network isolation.** Use security groups to restrict database access to application subnets; avoid `0.0.0.0/0`.

8. **Password management.** Use `manageMasterUserPassword: true` to store master passwords in AWS Secrets Manager instead of Kubernetes Secrets.

9. **Aurora for scalability.** Use Aurora clusters with Serverless v2 for workloads with variable demand.

10. **Parameter groups.** For custom database engine settings, create `RDSParameterGroup` (instance-level) or `RDSClusterParameterGroup` (cluster-level) resources and attach them to your database.

11. **Connection pooling.** For high-concurrency workloads or Lambda functions with frequent scaling, use `RDSProxy` to manage connection pooling and prevent connection storms.

## Related Resources

- **[KMS keys](../kms/index.md)** — Encryption keys for database encryption
- **[Secrets Manager](../secretsmanager/index.md)** — Master password storage
- **[IAM roles](../iam/index.md)** — Enhanced Monitoring role for database metrics
- **[VPC and networking](../ec2/index.md)** — Subnet groups and security groups for database placement

## Troubleshooting

### Database creation hangs in "creating" state

Check that:
1. The subnet group exists and contains valid subnets
2. The KMS key (if specified) exists and is accessible
3. The IAM monitoring role (if specified) exists and has the correct permissions

### Cannot connect to database endpoint

Verify:
1. Security group allows inbound traffic on the database port
2. Application is in the same VPC or has network path to the database subnets
3. Database engine and port are correct in your connection string
4. Master username and password are correct

### Insufficient capacity in the AZ

If you encounter "Insufficient capacity" errors:
1. Try a different Availability Zone by specifying `availabilityZone` in the instance spec
2. Use a different `dbInstanceClass` (some instance types have capacity constraints)
3. Contact AWS Support to increase capacity limits in your region

## References

For design details and architecture decisions, see `kropath-core/docs/families/aws/rds.md` in the kropath GitHub repository.
