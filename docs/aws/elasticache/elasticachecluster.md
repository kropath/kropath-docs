# ElastiCacheCluster — Memcached and Development Caches

The `ElastiCacheCluster` resource represents standalone cache clusters without replication. It supports Memcached (multi-node) and single-node Redis/Valkey for development and testing environments. For production Redis/Valkey deployments with failover, use `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` instead.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the cluster ID directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the cluster in AWS; `"delete"` removes it |

### Engine and Version

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engine` | string | required | `"memcached"` (multi-node) \| `"redis"` \| `"valkey"` (single-node only) |
| `engineVersion` | string | `""` | Specific version; empty uses AWS default |
| `description` | string | required | Human-readable cluster description |

### Cluster Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheNodeType` | string | required | Node size (e.g., `"cache.t3.micro"`, `"cache.m6g.large"`) |
| `numCacheNodes` | integer | default=1 | Number of nodes; 1 for single-node Redis/Valkey; 1+ for Memcached |

### Encryption (Redis/Valkey Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `transitEncryptionEnabled` | boolean | nil (governed) | TLS encryption for data in transit (mutable) |
| `atRestEncryptionEnabled` | boolean | ignored | At-rest encryption is NOT supported on standalone clusters (governance may surface a condition) |

**Note:** Standalone clusters do not support at-rest encryption. If governance mandates it, the RGD surfaces a status condition but cannot enforce it.

### Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheSubnetGroupName` | string | `""` | VPC subnet group for VPC-deployed clusters |
| `securityGroupIDs` | array | optional | VPC security groups for network access |
| `port` | integer | 0 (engine default) | TCP port (11211 for Memcached, 6379 for Redis/Valkey) |
| `networkType` | string | `"ipv4"` | `"ipv4"` \| `"ipv6"` \| `"dual_stack"` |

### Parameter Tuning

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cacheParameterGroupName` | string | `""` | Reference to `ElastiCacheParameterGroup` for engine tuning |

### Snapshots (Redis/Valkey Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snapshotRetentionLimit` | integer | nil (governed) | Snapshot retention floor in days |
| `snapshotWindow` | string | `""` | Preferred time window for automated snapshots |

### Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `preferredMaintenanceWindow` | string | `""` | Preferred time for AWS maintenance |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective cluster ID (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `predictedArn` | string | ARN: `arn:aws:elasticache:region:account:cluster:resourceName` |
| `conditions[]` | array | Standard kro conditions; may include governance enforcement notes |

## Naming Convention

Cluster IDs are constrained to 1–50 characters, lowercase alphanumeric + hyphens, and must start with a letter.

**Default template:** `{namespace}-{name}` → e.g., `dev-team-test-cache`

**Override:** Set `spec.nameOverride` to use a custom name.

## Complete Examples

### Single-Node Redis for Development

A development cache for testing without replication or persistence:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheCluster
metadata:
  name: dev-cache
  namespace: development
spec:
  configRef: dev
  engine: redis
  engineVersion: "7.0"
  cacheNodeType: cache.t3.micro  # Small, affordable node
  numCacheNodes: 1  # Single node (no replication)
  description: "Development Redis cache"
  transitEncryptionEnabled: false  # Dev: no encryption overhead
  snapshotRetentionLimit: 0  # Dev: no snapshots
  deletionPolicy: delete  # Auto-cleanup
  tags:
    environment: development
```

**Result:**
- Single Redis node for testing
- No HA or replication
- Minimal cost
- Auto-deleted when resource is removed

### Memcached Multi-Node Cluster

A Memcached cluster for session caching with multiple nodes:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheCluster
metadata:
  name: session-cache
  namespace: app-team
spec:
  configRef: general-policy
  engine: memcached
  engineVersion: "1.6"
  cacheNodeType: cache.m6g.large
  numCacheNodes: 3  # Multi-node Memcached
  description: "Session cache with 3-node cluster"
  cacheSubnetGroupName: app-team-cache-subnets
  cacheParameterGroupName: memcached-optimized
  deletionPolicy: retain
  tags:
    team: app-team
    cache-type: session
```

**Result:**
- 3 Memcached nodes for high throughput
- VPC deployment
- Parameter tuning applied
- Protected from accidental deletion

### Production Single-Node Valkey (HA Alternative)

A single Valkey node for small production workloads (consider replication groups for mission-critical):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheCluster
metadata:
  name: metadata-cache
  namespace: production
spec:
  configRef: production
  engine: valkey
  engineVersion: "7.0"
  cacheNodeType: cache.r7g.xlarge  # Large node for volume
  numCacheNodes: 1
  description: "Metadata cache (single-node)"
  transitEncryptionEnabled: true
  cacheSubnetGroupName: prod-vpc-subnets
  cacheParameterGroupName: valkey-production
  snapshotRetentionLimit: 7
  snapshotWindow: "03:00-04:00"
  deletionPolicy: retain
  tags:
    environment: production
    cache-type: metadata
  syncedLabels:
    critical: "true"
```

**Result:**
- Single large Valkey node
- TLS encryption enabled
- Snapshots for backup (7-day retention)
- Production governance applied

**Note:** This is a single point of failure. For mission-critical caches, use `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` with Multi-AZ failover.

## Governance Cascade

Cluster resources follow standard governance for encryption and snapshot retention.

**At-Rest Encryption Limitation:** If governance mandates at-rest encryption, clusters surface a status condition indicating the limitation but cannot enforce it (AWS doesn't support at-rest encryption on standalone clusters). Use replication groups for encryption-critical workloads.

## Key Behaviors

### Memcached Multi-Node Clustering

Memcached clusters scale horizontally by adding nodes. Each node stores independent partitions of the cache. The client library must support consistent hashing or slot-aware routing.

### Redis/Valkey Single-Node Only

Standalone clusters support only single Redis/Valkey nodes. Multi-node Redis/Valkey requires `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)`.

### No Automatic Failover

Clusters have no replicas or failover. If the node fails, the cache is unavailable until AWS restarts it.

### No At-Rest Encryption

Standalone clusters don't support at-rest encryption. For compliance requirements, use replication groups instead.

### Snapshots for Backup (Redis/Valkey Only)

Redis/Valkey clusters support automated snapshots for backup, but there's no automatic failover if the node fails. Plan backup intervals appropriately.

## Troubleshooting

### "At-Rest Encryption Not Supported" Condition

Governance mandates at-rest encryption, but standalone clusters don't support it. Options:
1. Use a `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` instead
2. Contact platform team to waive encryption requirement for this workload
3. Accept the governance warning and proceed without encryption

### Cluster Won't Create: "Invalid Node Configuration"

- For Memcached: `numCacheNodes` must be 1+
- For Redis/Valkey: `numCacheNodes` must be 1 (single-node only)

Adjust and reapply.

### Snapshot Window Too Late for RPO

If your backup window doesn't match your RTO/RPO requirements, adjust `snapshotWindow`. Note: Snapshots block the cache during backup.

### No Failover on Node Failure

Standalone clusters have no replicas to promote. For high availability, use `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` with Multi-AZ and automatic failover.

## Comparison: Cluster vs Replication Group

| Feature | Cluster | Replication Group |
|---|---|---|
| **Memcached** | Supported (multi-node) | Not supported |
| **Redis/Valkey** | Single-node only | Multi-shard + replicas |
| **Automatic Failover** | No | Yes (Multi-AZ) |
| **At-Rest Encryption** | No | Yes |
| **Snapshots** | Yes | Yes |
| **Use Case** | Dev/test, Memcached, low-availability | Production, HA required |

## Cross-Family Integration

**Subnet Groups:** Reference `[ElastiCacheSubnetGroup](elasticachesubnetgroup.md)` via `cacheSubnetGroupName` for VPC placement.

**Parameter Groups:** Reference `[ElastiCacheParameterGroup](elasticacheparametergroup.md)` via `cacheParameterGroupName` for engine tuning.

## Next Steps

- Use for development/testing Redis/Valkey (single-node)
- Use for Memcached multi-node deployments
- For production Redis/Valkey, consider `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` with HA
- Set up VPC subnets with `[ElastiCacheSubnetGroup](elasticachesubnetgroup.md)`
