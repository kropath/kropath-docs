---
title: MemoryDBCluster — Creating and Managing In-Memory Clusters
description: "The `MemoryDBCluster` resource represents a single MemoryDB cluster — a durable Redis OSS-compatible in-memory database with horizontal scaling (shards), high availability (replicas), TLS encryption, snapshots, and maintenance windows."
doc_type: reference
---
# MemoryDBCluster — Creating and Managing In-Memory Clusters

The `MemoryDBCluster` resource represents a single MemoryDB cluster — a durable Redis OSS-compatible in-memory database with horizontal scaling (shards), high availability (replicas), TLS encryption, snapshots, and maintenance windows.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets cluster name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Cluster Identity and Size

| Field | Type | Default | Purpose |
|---|---|---|---|
| `nodeType` | string | required | Compute/memory capacity (e.g. `db.r7g.large`); falls through governance cascade |
| `description` | string | `""` | Human-readable cluster description |
| `engineVersion` | string | `""` | Redis engine version (e.g. `7.1.0`); uses latest if empty |
| `numShards` | integer | nil | Number of shards for horizontal scaling; nil = AWS default (1) |
| `numReplicasPerShard` | integer | nil | Read replicas per shard (0–5); nil = AWS default (1) |
| `port` | integer | nil | Cluster port; nil = AWS default (6379) |

### Security and Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tlsEnabled` | boolean | nil | Enable in-transit TLS encryption; immutable after creation; falls through cascade |
| `kmsKeyArn` | string | `""` | KMS key for at-rest encryption; immutable after creation; falls through cascade |
| `aclName` | string | `""` | Name of `MemoryDBACL` to attach; empty = "open-access" default ACL |
| `securityGroupIDs` | array | [] | VPC security group IDs for access control |

### Networking and Placement

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subnetGroupName` | string | `""` | Name of `MemoryDBSubnetGroup` for VPC placement; empty = default |
| `parameterGroupName` | string | `""` | Name of `MemoryDBParameterGroup` for engine tuning; empty = default |

### Backup and Snapshots

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snapshotRetentionLimit` | integer | nil | Days to retain automatic snapshots; nil = AWS default (0 = disabled) |
| `snapshotWindow` | string | `""` | Daily UTC time range for automatic snapshots (e.g. `"05:00-09:00"`) |
| `snapshotName` | string | `""` | Name of existing `MemoryDBSnapshot` to restore from (creation-time only) |
| `snapshotARNs` | array | [] | S3 ARNs of RDB files to restore from (creation-time only) |

### Maintenance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `maintenanceWindow` | string | `""` | Weekly maintenance window (e.g. `"sun:23:00-mon:01:30"`); minimum 60 minutes |
| `autoMinorVersionUpgrade` | boolean | nil | Automatic engine minor-version updates; falls through cascade |

### Notifications

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snsTopicArn` | string | `""` | SNS topic ARN for cluster event notifications |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example: Production Cluster

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  configRef: production          # Apply strict governance
  deletionPolicy: retain         # Keep cluster when CR deleted
  
  # Cluster sizing
  nodeType: db.r7g.large         # Required; falls through cascade
  numShards: 2                   # Horizontal scaling
  numReplicasPerShard: 2         # High availability
  port: 6379                     # Standard Redis port
  description: "Production session cache"
  
  # Security
  tlsEnabled: true               # Immutable after creation
  kmsKeyArn: "arn:aws:kms:ap-southeast-2:123456789012:key/abc..."
  aclName: app-acl               # References MemoryDBACL resource
  securityGroupIDs:
    - sg-12345678
    - sg-87654321
  
  # Networking
  subnetGroupName: cache-prod-subnets
  parameterGroupName: app-params
  
  # Backup
  snapshotRetentionLimit: 30     # Retain for 30 days
  snapshotWindow: "05:00-09:00"  # Daily backup (UTC)
  
  # Maintenance
  maintenanceWindow: "sun:23:00-mon:01:30"
  autoMinorVersionUpgrade: false # Manual control for production
  
  # Notifications
  snsTopicArn: "arn:aws:sns:ap-southeast-2:123456789012:memorydb-alerts"
  
  # Metadata
  tags:
    service: cache
    team: platform
    cost-centre: engineering
  syncedLabels:
    environment: production
    data-class: internal
  syncedAnnotations:
    runbook: https://wiki.example.com/memorydb-runbook
    team-slack: "#platform"
```

## Example: Restore From Snapshot

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: restored-cluster
  namespace: cache-prod
spec:
  nodeType: db.r7g.large
  
  # Restore from a MemoryDBSnapshot
  snapshotName: daily-backup-2025-01-15
  
  # OR from S3 (mutually exclusive with snapshotName)
  # snapshotARNs:
  #   - arn:aws:s3:::my-bucket/cluster.rdb
```

## Governance Cascade

All governance fields follow the cascade rule:

```
mandatory (if set) → spec value → defaults (if set)
```

**Examples:**

```yaml
# If MemoryDBConfig/production has mandatory.tlsEnabled: true
# And instance spec.tlsEnabled: false
# Result: tlsEnabled is FORCED to true

# If MemoryDBConfig/production has mandatory.nodeType: "db.r7g.large"
# And instance spec.nodeType: "db.t4g.small"
# Result: nodeType is FORCED to "db.r7g.large"

# If MemoryDBConfig/production has defaults.snapshotRetentionLimit: 14
# And instance spec.snapshotRetentionLimit is nil
# Result: snapshotRetentionLimit defaults to 14
```

See [MemoryDBConfig governance](./memorydbconfig.md#governance-cascade) for full cascade semantics.

## Immutability and Updates

**Immutable after creation** (cannot be changed; requires new cluster):
- `tlsEnabled` — Governed by cascade at creation time
- `kmsKeyArn` — Governed by cascade at creation time
- `numShards` — Requires restore from snapshot to change

**Updatable** (standard patch/update):
- `numReplicasPerShard` — Add/remove read replicas
- `engineVersion` — Upgrade minor versions
- `parameterGroupName` — Apply different engine parameters
- `maintenanceWindow` — Change maintenance schedule
- `snapshotRetentionLimit` — Adjust backup retention
- `autoMinorVersionUpgrade` — Enable/disable auto-upgrades
- All metadata and tags

**Creation-time only:**
- `snapshotName` and `snapshotARNs` — Used only when creating a cluster; not updatable

## Status Fields

After creation, retrieve cluster information:

```yaml
status:
  resourceName: "cache-prod-session-store"     # effectiveName (lowercase)
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:cluster/cache-prod-session-store"
  clusterEndpoint: "cluster.abc123.ng.0001.apse2.cache.amazonaws.com"
  clusterPort: 6379
  clusterStatus: "available"                   # creating | available | updating | deleting
  conditions:
    - type: Ready
      status: "True"
      message: "Cluster is ready"
```

Use `clusterEndpoint` and `clusterPort` to connect applications.

## ACL and User Authentication

To attach an ACL and users:

1. Create a `MemoryDBACL`:
   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: MemoryDBACL
   metadata:
     name: app-acl
     namespace: cache-prod
   spec:
     userNames:
       - appuser
       - adminuser
   ```

2. Create `MemoryDBUser` resources:
   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: MemoryDBUser
   metadata:
     name: appuser
     namespace: cache-prod
   spec:
     accessString: "on >password +@all"
     authenticationMode:
       type: password
       passwords:
         - name: appuser-pwd
           key: password
   ```

3. Reference the ACL in the cluster:
   ```yaml
   spec:
     aclName: app-acl
   ```

## Scaling the Cluster

### Horizontal Scaling (Shards)

```yaml
spec:
  numShards: 3  # Add more shards for higher throughput
```

Note: Scaling shards requires creating a new cluster and restoring from a snapshot. Cannot be done in-place.

### Vertical HA (Replicas)

```yaml
spec:
  numReplicasPerShard: 2  # Add replicas for higher availability
```

This can be changed via standard update (in-place).

## Parameter Groups

Apply Redis engine configuration:

```yaml
spec:
  parameterGroupName: app-params
```

Create the referenced parameter group:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBParameterGroup
metadata:
  name: app-params
  namespace: cache-prod
spec:
  family: memorydb7
  parameters:
    maxmemory-policy: "allkeys-lru"
    timeout: "300"
    tcp-keepalive: "60"
```

## Deletion and Lifecycle

By default, clusters are retained when the Kubernetes CR is deleted:

```yaml
spec:
  deletionPolicy: retain  # AWS cluster stays (safe default)
```

To delete the AWS cluster when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

**Note:** Snapshots are independent. Deleting a cluster does not auto-delete its snapshots.

## Naming Template Syntax

Cluster names are resolved via the governance template:

```yaml
# Default template: "{namespace}-{name}"
# With namespace=cache-prod, name=session-store
# Result: cache-prod-session-store

# Custom template: "{tag.env}-{namespace}-{name}"
# With tag.env=prod
# Result: prod-cache-prod-session-store
```

See [Naming Template — Dynamic Tags](../../../concepts/configuration/naming-templates.md) for full syntax.

**AWS constraints:** 1–40 characters, starts with letter, alphanumeric + hyphens, no trailing hyphen, no consecutive hyphens, case-insensitive (stored lowercase).

## Common Tasks

### Enable automatic backups

```yaml
spec:
  snapshotRetentionLimit: 14      # Retain for 14 days
  snapshotWindow: "05:00-09:00"   # Daily UTC window
```

### Connect applications via endpoint

```yaml
# After cluster is available, use status.clusterEndpoint
# In the application, connect to:
# cache-prod-session-store.abc123.ng.0001.apse2.cache.amazonaws.com:6379
```

### Rotate encryption key (requires new cluster)

Since `kmsKeyArn` is immutable:

1. Take a snapshot: `MemoryDBSnapshot` with `spec.clusterName`
2. Create new cluster with new `kmsKeyArn` and restore from snapshot
3. Update applications to point to new cluster endpoint
4. Delete old cluster

### Perform maintenance without downtime

```yaml
spec:
  maintenanceWindow: "sun:23:00-mon:01:30"
  autoMinorVersionUpgrade: true
```

MemoryDB will perform updates during the window; replicas ensure availability.

## Additional Resources

- **Governance profiles:** [MemoryDBConfig](./memorydbconfig.md)
- **ACL resources:** [MemoryDBACL](./memorydbackl.md)
- **User management:** [MemoryDBUser](./memorydbuser.md)
- **Subnet groups:** [MemoryDBSubnetGroup](./memorydbsubnetgroup.md)
- **Parameter tuning:** [MemoryDBParameterGroup](./memorydbparametergroup.md)
- **Snapshots:** [MemoryDBSnapshot](./memorydbsnapshot.md)
- **MemoryDB immutability constraints:** [AWS MemoryDB CRD cache](https://github.com/kropath/kropath-core/blob/main/docs/crd-cache/aws/memorydb-controller-v1.4.1.md)
