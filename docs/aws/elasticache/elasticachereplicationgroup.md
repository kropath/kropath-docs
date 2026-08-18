# ElastiCacheReplicationGroup — Production Redis and Valkey Caches

The `ElastiCacheReplicationGroup` resource represents production-grade Redis and Valkey caches in AWS ElastiCache. It supports multi-shard cluster mode, Multi-AZ with automatic failover, encryption, parameter group tuning, snapshot scheduling, and user-based RBAC authentication for Valkey/Redis 6+.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the replication group ID directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (safe) keeps the cache in AWS when the resource is deleted; `"delete"` removes it |

### Cache Engine and Version

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engine` | string | `"valkey"` | Cache engine: `"valkey"` (recommended) \| `"redis"` (legacy) \| `"memcached"` (not for replication groups; use `ElastiCacheCluster`) |
| `engineVersion` | string | `""` | Specific version (e.g., `"7.0"`, `"7.1.0"`); empty uses AWS default |
| `description` | string | required | Human-readable description of the cache's purpose |

### Cluster Topology

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheNodeType` | string | required | Node size (e.g., `"cache.r7g.large"`, `"cache.m6g.xlarge"`) |
| `numNodeGroups` | integer | nil (1 shard) | Number of shards in cluster mode; nil or 0 = cluster-mode-disabled (single primary + replicas) |
| `replicasPerNodeGroup` | integer | nil (AWS default) | Read replicas per shard (0–5) |
| `nodeGroupConfiguration` | array | optional | Per-shard AZ and slot configuration (advanced) |

### High Availability

| Field | Type | Default | Purpose |
|---|---|---|---|
| `multiAZEnabled` | boolean | nil (governed) | Distribute replicas across availability zones; coupled with automatic failover |
| `automaticFailoverEnabled` | boolean | nil (governed) | Automatically promote a replica to primary on failure; forces `multiAZEnabled: true` |

**Coupling rule:** If governance or instance sets `multiAZEnabled: true`, `automaticFailoverEnabled` is forced to `true`.

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `atRestEncryptionEnabled` | boolean | nil (governed) | Encrypt data at rest using KMS; **IMMUTABLE after creation** |
| `transitEncryptionEnabled` | boolean | nil (governed) | TLS encryption for data in transit (mutable) |
| `kmsKeyID` | string | `""` | KMS key ID or ARN; empty uses AWS-managed default |

**Critical:** At-rest encryption cannot be changed after the replication group is created. Set it correctly at creation time.

### Authentication & Access Control

| Field | Type | Default | Purpose |
|---|---|---|---|
| `userGroupIDs` | array of strings | optional | User group IDs for RBAC (Valkey/Redis 6+ only); references `ElastiCacheUserGroup` resources |

### Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheSubnetGroupName` | string | `""` | Required for VPC clusters; references an `ElastiCacheSubnetGroup` |
| `securityGroupIDs` | array of strings | optional | VPC security groups controlling network access |
| `port` | integer | 0 (engine default: 6379) | TCP port for the cache |
| `networkType` | string | `"ipv4"` | Address type: `"ipv4"` \| `"ipv6"` \| `"dual_stack"` |

### Parameter Tuning

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheParameterGroupName` | string | `""` | Reference to `ElastiCacheParameterGroup` for engine-specific tuning |

### Snapshots & Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snapshotRetentionLimit` | integer | nil (governed) | Snapshot retention floor in days; mandatory tier enforces minimum; 0 = disable (blocked if governance mandates retention) |
| `snapshotWindow` | string | `""` | Preferred time window for automated snapshots (e.g., `"05:00-06:00"`) |
| `preferredMaintenanceWindow` | string | `""` | Preferred time for AWS maintenance (e.g., `"sun:05:00-sun:06:00"`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Advanced Options

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dataTieringEnabled` | boolean | nil | Enable data tiering for r6gd/r7gd node types (hot/cold storage) |
| `logDeliveryConfigurations` | array | optional | Send slow-log and engine-log to CloudWatch Logs |
| `notificationTopicARN` | string | `""` | SNS topic for ElastiCache event notifications |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective replication group ID (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if naming template has unresolved tokens |
| `predictedArn` | string | ARN of the replication group: `arn:aws:elasticache:region:account:replicationgroup:resourceName` |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

Replication group IDs are constrained to 1–40 characters, lowercase alphanumeric + hyphens, and must start with a letter.

**Default template:** `{namespace}-{name}` → e.g., `app-team-session-cache`

The resource applies `.lowerAscii()` post-processing to ensure lowercase compliance.

**Override:** Set `spec.nameOverride` to bypass the template.

## Complete Examples

### Basic Replicated Cache with HA

A multi-AZ replicated cache for a production workload with automatic failover:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: session-cache
  namespace: app-team
spec:
  configRef: general-policy
  engine: valkey
  engineVersion: "7.1"
  cacheNodeType: cache.r7g.large
  description: "Session store for e-commerce platform"
  multiAZEnabled: true
  automaticFailoverEnabled: true
  snapshotRetentionLimit: 7
  cacheSubnetGroupName: app-team-subnets
  deletionPolicy: retain
  tags:
    team: platform
    cost-center: engineering
```

**Result:**
- Replication group created with name `app-team-session-cache`
- Multi-AZ with automatic failover enabled
- Snapshots retained for 7 days
- Deployed to `app-team-subnets` VPC
- Protected from accidental deletion

### Cluster Mode (Sharded) Cache

A large cache using cluster mode to scale horizontally across multiple shards:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: distributed-cache
  namespace: data-team
spec:
  configRef: production
  engine: valkey
  cacheNodeType: cache.m6g.xlarge
  numNodeGroups: 6  # 6 shards
  replicasPerNodeGroup: 2  # 2 read replicas per shard = 18 total nodes
  description: "Distributed cache for analytics pipeline"
  multiAZEnabled: true
  automaticFailoverEnabled: true
  cacheSubnetGroupName: data-team-vpc
  cacheParameterGroupName: cluster-optimized
  snapshotWindow: "03:00-04:00"
  deletionPolicy: retain
```

**Result:**
- 6 shards × 3 nodes (1 primary + 2 replicas) = 18 nodes total
- Sharding distributes load and scales the dataset
- Each shard has replicas for HA
- Parameter group applies cluster-optimized settings

### Encrypted Cache with KMS and User RBAC

A security-hardened cache for payment processing with custom KMS encryption and user-based access control:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: payment-cache
  namespace: payments
spec:
  configRef: pci  # PCI-DSS governance profile
  engine: valkey
  engineVersion: "7.0"
  cacheNodeType: cache.r7g.large
  description: "Payment authorization cache (PCI-DSS)"
  atRestEncryptionEnabled: true
  transitEncryptionEnabled: true
  kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  userGroupIDs:
    - payments-app  # RBAC: restrict access to payment app users
    - payments-admins
  cacheSubnetGroupName: payments-vpc
  multiAZEnabled: true
  automaticFailoverEnabled: true
  snapshotRetentionLimit: 30
  notificationTopicARN: "arn:aws:sns:us-east-1:123456789012:elasticache-events"
  deletionPolicy: retain
  tags:
    compliance: pci-dss
    data-classification: payment-card
  syncedLabels:
    audit-required: "true"
```

**Result:**
- Encryption enforced both at rest and in transit
- Customer-managed KMS key for encryption
- RBAC via user groups (payment apps can only access with authorized credentials)
- Snapshots retained for 30 days (compliance requirement)
- Event notifications sent to SNS for monitoring

## Governance Cascade

The effective encryption and HA settings are determined by governance + spec:

**At-rest encryption (mandatory, highest priority):** `KropathConfig` org-wide mandatory → Profile mandatory → Instance spec

**Snapshot retention:** Profile mandatory sets a floor; instance value must be >= floor or 0 is rejected

**High availability:** Profile defaults suggest HA; instance can override defaults but not mandatory HA policies

All effective values are merged into the referenced `ElastiCacheConfig` CR's `status.effectiveConfig` before this resource reads them.

## Key Behaviors

### At-Rest Encryption Is Immutable

Once you create a replication group with `atRestEncryptionEnabled: true` (or `false`), you cannot change it. Updating the field after creation is rejected by the CRD validation.

**To migrate:** Create a new replication group with different encryption settings and migrate traffic.

### Automatic Failover Forces Multi-AZ

If you set `automaticFailoverEnabled: true`, the RGD automatically forces `multiAZEnabled: true`. You cannot have failover without Multi-AZ replicas.

### Snapshot Retention Floor

If governance sets `mandatory.snapshotRetentionLimit: 7`, your instance value must be >= 7. Setting `spec.snapshotRetentionLimit: 0` (to disable snapshots) is rejected. The governance mandatory floor takes precedence.

### Cluster Mode Sharding

When you set `numNodeGroups > 1`, the cache uses cluster mode to shard data across multiple primaries. Each shard has replicas for HA.

- **Advantages:** Scales to larger datasets, higher throughput
- **Disadvantages:** Requires application support for slot-aware operations
- **Default:** `numNodeGroups: nil` or `0` = cluster-mode-disabled (single primary with replicas)

### Parameter Group Coupling

The `cacheParameterGroupName` must refer to an existing `ElastiCacheParameterGroup` in the same AWS account. Mismatched or missing parameter groups cause provisioning to fail.

### Naming Is Immutable

The replication group ID (derived from the naming template or `nameOverride`) is set at creation and cannot be changed. Changing the template or override on an existing resource does not rename the AWS resource.

## Troubleshooting

### Cache Won't Create: "Invalid Naming"

Check `status.namingStatus`:
- If `"invalid-unresolved-tokens"`, the naming template references a tag that doesn't exist. Add the tag or fix the template.
- If `"valid"` but creation still fails, check AWS permissions and `status.conditions` for detailed errors.

### Can't Enable/Disable At-Rest Encryption After Creation

This is by design—at-rest encryption is immutable. If you need to change encryption, create a new replication group and migrate data.

### Snapshot Retention Too Low

If governance sets a retention floor (e.g., 7 days), your resource must respect that floor. Attempting to set `snapshotRetentionLimit: 0` or less than the floor is rejected. Update your resource or contact platform team to adjust governance.

### Multi-AZ Failover Automatically Enabled

If you set `multiAZEnabled: true`, `automaticFailoverEnabled` is automatically forced to `true`. This is correct behavior—failover requires Multi-AZ replicas.

### Cluster Mode Data Slot Errors

Cluster mode requires applications to be slot-aware (use `CLUSTER SLOTS`, hash tags, or a client library that handles redirection). Legacy applications expecting a single keyspace will fail with redirection errors. Consider using cluster-mode-disabled (single shard with replicas) if your application doesn't support clustering.

## Cross-Family Integration

**Subnet Groups:** Reference `[ElastiCacheSubnetGroup](elasticachesubnetgroup.md)` via `cacheSubnetGroupName` for VPC placement.

**Parameter Groups:** Reference `[ElastiCacheParameterGroup](elasticacheparametergroup.md)` via `cacheParameterGroupName` for engine tuning.

**User Groups:** Reference `[ElastiCacheUserGroup](elasticacheusergroup.md)` via `userGroupIDs` for RBAC (Valkey/Redis 6+).

**KMS Keys:** Use KMS key IDs or ARNs for customer-managed encryption.

## Next Steps

- Set up VPC subnets with `[ElastiCacheSubnetGroup](elasticachesubnetgroup.md)`
- Tune engine settings with `[ElastiCacheParameterGroup](elasticacheparametergroup.md)`
- Enable RBAC with `[ElastiCacheUser](elasticacheuser.md)` and `[ElastiCacheUserGroup](elasticacheusergroup.md)`
- Review governance policies in `[ElastiCacheConfig](elasticacheconfig.md)`
