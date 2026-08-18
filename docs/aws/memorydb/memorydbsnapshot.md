# MemoryDBSnapshot — Point-in-Time Snapshots and Backups

The `MemoryDBSnapshot` resource represents a point-in-time RDB snapshot of a MemoryDB cluster. Snapshots are used for backup, disaster recovery, and cluster seeding (restoring a new cluster from a prior snapshot).

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets snapshot name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Snapshot Source

**Snapshot from a live cluster:**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `clusterName` | string | required (if `sourceSnapshotName` not set) | Name of the `MemoryDBCluster` to snapshot |

**Snapshot from an existing snapshot:**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `sourceSnapshotName` | string | required (if `clusterName` not set) | Name of an existing `MemoryDBSnapshot` to copy |

(Mutually exclusive — use either `clusterName` or `sourceSnapshotName`, not both.)

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example: Manual Snapshot

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: daily-backup
  namespace: cache-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  
  # Take a snapshot of this cluster
  clusterName: session-store
  
  # Metadata
  tags:
    purpose: backup
    schedule: daily
  syncedLabels:
    backup-type: manual
```

## Complete Example: Copy Existing Snapshot

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: backup-copy
  namespace: cache-prod
spec:
  # Copy from an existing snapshot (instead of live cluster)
  sourceSnapshotName: daily-backup
  
  # New copy has independent lifecycle
```

## Status Fields

After creation:

```yaml
status:
  resourceName: "cache-prod-daily-backup"      # effectiveName
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:snapshot/cache-prod-daily-backup"
  snapshotStatus: "available"                  # creating | available | deleting | updating
  clusterName: "cache-prod-session-store"      # Source cluster (if from live cluster)
  snapshotCreateTime: "2025-01-15T10:30:00Z"   # Creation timestamp
  snapshotSize: "123456789"                    # Size in bytes
  conditions:
    - type: Ready
      status: "True"
      message: "Snapshot is ready"
```

Use `status.predictedArn` to reference the snapshot when restoring.

## Restore from Snapshot

To restore a new cluster from a snapshot, use the snapshot name in the cluster spec:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: restored-cluster
  namespace: cache-prod
spec:
  nodeType: db.r7g.large
  
  # Restore from snapshot (creation-time only)
  snapshotName: daily-backup
  
  # Other fields configure the new cluster
  aclName: app-acl
  subnetGroupName: cache-prod-subnets
```

**Important:** The `snapshotName` field is only used at cluster creation time. You cannot update an existing cluster to restore from a snapshot — create a new cluster instead.

## Automatic vs. Manual Snapshots

**Automatic snapshots** are managed by the cluster itself:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  snapshotRetentionLimit: 30       # Retain automatic snapshots for 30 days
  snapshotWindow: "05:00-09:00"    # Daily snapshot window (UTC)
  # Automatic snapshots created daily; not managed by Kubernetes CRs
```

**Manual snapshots** are explicitly created via `MemoryDBSnapshot` CRs — useful for:
- One-time backups before major changes
- Long-term archive (automatic snapshots auto-expire)
- Cross-region replication
- Testing restore procedures

## Governance

`MemoryDBSnapshot` has **no functional governance fields** beyond tags, labels, and naming. Platform teams do not enforce snapshot retention or naming — those are backup-specific decisions.

Governance fields available:
- **tags** / **syncedLabels** / **syncedAnnotations** — Metadata governance
- **namingTemplate** — Naming convention

See [MemoryDBConfig governance](./memorydbconfig.md) for full governance cascade details.

## Naming

Snapshot names are generated via the governance naming template:

```yaml
# Default: "{namespace}-{name}"
# With namespace=cache-prod, name=daily-backup
# Result: cache-prod-daily-backup

# Custom: "backup-{tag.env}-{name}"
# With tag.env=prod
# Result: backup-prod-daily-backup
```

See [Naming Template — Dynamic Tags](../resources/naming-template-dynamic-tags.md) for full syntax.

**AWS constraints:** Starts with letter, alphanumeric + hyphens.

## Update and Delete

### Snapshots Are Immutable

Once created, snapshot contents cannot be changed. Parameters like `clusterName` and `sourceSnapshotName` are creation-time only and cannot be updated.

To create a different snapshot, create a new `MemoryDBSnapshot` CR.

### Delete Snapshot

By default, snapshots are retained:

```yaml
spec:
  deletionPolicy: retain
```

To delete the AWS snapshot when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

## Tagging

Snapshots inherit tags from governance:

```yaml
# MemoryDBConfig/general-policy
spec:
  mandatory:
    tags:
      service: memorydb
  defaults:
    tags:
      team: platform

# MemoryDBSnapshot instance
spec:
  tags:
    purpose: backup

# Result in ACK Snapshot spec.tags:
#   service: memorydb (mandatory)
#   team: platform (defaults)
#   purpose: backup (instance)
```

## Example: Backup Rotation

Create daily snapshots automatically:

```yaml
---
# Snapshot from yesterday
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: backup-2025-01-14
  namespace: cache-prod
spec:
  clusterName: session-store
  deletionPolicy: retain
  tags:
    date: "2025-01-14"

---
# Today's snapshot
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: backup-2025-01-15
  namespace: cache-prod
spec:
  clusterName: session-store
  deletionPolicy: retain
  tags:
    date: "2025-01-15"

---
# Archive: copy of a 30-day-old snapshot
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: archive-2024-12-16
  namespace: cache-prod
spec:
  sourceSnapshotName: backup-2024-12-16
  deletionPolicy: retain
  tags:
    type: archive
    purpose: long-term-retention
```

## Example: Pre-Maintenance Backup

Before applying updates:

```yaml
---
# Pre-maintenance snapshot
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: pre-upgrade-backup
  namespace: cache-prod
spec:
  clusterName: session-store
  tags:
    purpose: pre-maintenance
    cluster-version: "7.0.0"

---
# After maintenance completes (if needed, restore)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store-rollback
  namespace: cache-prod
spec:
  snapshotName: pre-upgrade-backup
  nodeType: db.r7g.large
  # Use same config as original cluster
```

## Common Tasks

### Create a manual backup

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: manual-backup
  namespace: cache-prod
spec:
  clusterName: session-store
```

### Restore from snapshot

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: restored-cluster
  namespace: cache-prod
spec:
  snapshotName: manual-backup
  nodeType: db.r7g.large
  # ... other cluster fields
```

### Copy snapshot (long-term archive)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: archive-copy
  namespace: cache-prod
spec:
  sourceSnapshotName: backup-from-month-ago
  tags:
    retention: long-term
```

### Take pre-maintenance snapshot

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: pre-maintenance
  namespace: cache-prod
spec:
  clusterName: session-store
  tags:
    purpose: pre-maintenance
    cluster-version: "7.0.0"
```

Then, if anything goes wrong during maintenance, restore:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store-restored
  namespace: cache-prod
spec:
  snapshotName: pre-maintenance
  # ... restore with same configuration
```

## Backup Strategy

**Recommended approach:**

1. **Automatic snapshots** — Retain recent backups via `MemoryDBCluster.snapshotRetentionLimit` (e.g. 30 days)
2. **Manual snapshots** — Create `MemoryDBSnapshot` CRs for:
   - Weekly/monthly archives (tag with `type: archive`)
   - Pre-maintenance backups (tag with `purpose: pre-maintenance`)
   - Cross-region replicas (tag with `purpose: dr`)
3. **Retention policy** — Delete old manual snapshots via `deletionPolicy: delete` after retention period

**Example workflow:**

```yaml
---
# Cluster with 30-day automatic snapshot retention
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  snapshotRetentionLimit: 30
  snapshotWindow: "05:00-09:00"

---
# Weekly manual snapshot (long-term archive)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: weekly-backup-2025-w03
  namespace: cache-prod
spec:
  clusterName: session-store
  deletionPolicy: retain
  tags:
    type: archive
    frequency: weekly

---
# Pre-release snapshot (before cluster upgrade)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: pre-release-7.1-snapshot
  namespace: cache-prod
spec:
  clusterName: session-store
  tags:
    purpose: pre-maintenance
    cluster-version: "7.0.0"
    target-version: "7.1.0"
```

## Additional Resources

- **Cluster configuration:** [MemoryDBCluster](./memorydbcluster.md)
- **Automatic snapshots:** [MemoryDB Snapshots](https://docs.aws.amazon.com/memorydb/latest/devguide/snapshots.html)
- **Disaster recovery patterns:** [MemoryDB Disaster Recovery](https://docs.aws.amazon.com/memorydb/latest/devguide/disaster-recovery-resiliency.html)
- **Backup best practices:** [AWS Backup for MemoryDB](https://docs.aws.amazon.com/memorydb/latest/devguide/backup-restore.html)
