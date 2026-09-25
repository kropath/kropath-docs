---
title: MemoryDB — In-Memory Database Clusters
description: AWS MemoryDB is a fast, durable in-memory database compatible with Redis OSS, used for real-time caching, sessions, and pub/sub messaging.
doc_type: reference
weight: 330
---
# MemoryDB — In-Memory Database Clusters

AWS MemoryDB is a fast, durable in-memory database compatible with Redis OSS, used for real-time caching, sessions, and pub/sub messaging. Kropath provides seven resource kinds to manage MemoryDB clusters and their supporting infrastructure.

## Quick Start

Deploy a complete MemoryDB setup with a cluster, ACL, users, and subnet group:

```yaml
---
# Governance policy
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    tlsEnabled: true
    numReplicasPerShard: 1
    snapshotRetentionLimit: 7
    autoMinorVersionUpgrade: true

---
# In-memory cluster
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  nodeType: db.r7g.large
  numShards: 2
  numReplicasPerShard: 1
  tags:
    service: cache
    team: platform

---
# Access control (user list)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: app-acl
  namespace: cache-prod
spec:
  userNames:
    - appuser
    - adminuser

---
# Single user with password authentication
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
      - name: memorydb-appuser-pwd
        key: password

---
# Subnet group for VPC placement
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: default
  namespace: cache-prod
spec:
  subnetIds:
    - subnet-12345678
    - subnet-87654321

---
# Engine parameter group for tuning
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
```

## Core Resources

| Resource | Purpose |
|----------|---------|
| **[MemoryDBConfig](./memorydbconfig.md)** | Governance profiles (mandatory/defaults tiers) for cluster and ACL setup |
| **[MemoryDBCluster](./memorydbcluster.md)** | The primary in-memory cluster with scaling, replication, TLS, snapshots, and maintenance |
| **[MemoryDBACL](./memorydbackl.md)** | Access control list defining which users can authenticate to clusters |
| **[MemoryDBUser](./memorydbuser.md)** | Individual user identity with password or IAM authentication |
| **[MemoryDBSubnetGroup](./memorydbsubnetgroup.md)** | Named collection of VPC subnets for cluster placement |
| **[MemoryDBParameterGroup](./memorydbparametergroup.md)** | Engine tuning parameters (maxmemory-policy, timeout, etc.) |
| **[MemoryDBSnapshot](./memorydbsnapshot.md)** | Point-in-time RDB snapshots for backup and cluster seeding |

## Governance

All MemoryDB resources follow a unified governance cascade via `MemoryDBConfig` profiles. Platform teams deploy named profiles (`general-policy`, `production`, `dev`) to codify compliance postures; resources select a profile via `spec.configRef`.

**Governance fields** (enforced via `mandatory` / `defaults` tiers):
- **tlsEnabled** — Require TLS in-transit encryption
- **nodeType** / **allowedNodeTypes** — Control compute and memory capacity
- **engineVersion** — Pin engine version
- **numReplicasPerShard** / **snapshotRetentionLimit** — HA and backup requirements
- **autoMinorVersionUpgrade** — Automatic engine updates
- **namingTemplate** — Cluster naming convention
- **tags**, **syncedLabels**, **syncedAnnotations** — Metadata governance

See [MemoryDBConfig governance](./memorydbconfig.md#governance-cascade) for full cascade semantics.

## Common Tasks

### Enable cluster backups

```yaml
spec:
  snapshotRetentionLimit: 14        # days of automatic snapshots
  snapshotWindow: "05:00-09:00"    # daily backup window (UTC)
```

### Create a manual backup

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSnapshot
metadata:
  name: daily-backup
  namespace: cache-prod
spec:
  clusterName: session-store
```

Later, restore from this snapshot:

```yaml
spec:
  snapshotName: daily-backup   # creation-time only
```

### Scale the cluster

```yaml
spec:
  numShards: 3            # horizontal scaling (more shards = more throughput)
  numReplicasPerShard: 2  # vertical HA (more replicas per shard = more resilience)
```

**Note:** Both fields are immutable during normal updates — scale by creating a new cluster restored from a snapshot.

### Enforce security policies

MemoryDBConfig with `mandatory` tier overrides instance selections:

```yaml
# MemoryDBConfig/production
spec:
  mandatory:
    tlsEnabled: true                    # TLS always on
    kmsKeyArn: "arn:aws:kms:..."       # Force specific KMS key
    numReplicasPerShard: 2              # Minimum replicas required
    snapshotRetentionLimit: 30          # Minimum retention days
```

Any `MemoryDBCluster` selecting `configRef: production` will use these settings regardless of instance spec.

## Cross-Provider Notes

MemoryDB is AWS-specific. GCP provides Memorystore for Redis; Azure provides Cache for Redis. Kropath will add `MemoryStoreInstance` and `CacheForRedis` RGDs in future releases.

**Key differences:**
- **Scaling:** MemoryDB supports horizontal sharding; Memorystore does not (standard HA only)
- **Authentication:** MemoryDB uses ACLs + users; Memorystore uses AUTH password; Azure uses access keys
- **Encryption:** MemoryDB has `tlsEnabled` immutable at creation; other providers may allow TLS changes

## Deletion and Lifecycle

By default, all MemoryDB resources use `deletionPolicy: retain`, preserving AWS resources when Kubernetes objects are deleted. Set `deletionPolicy: delete` to remove the AWS resource when the Kubernetes CR is deleted.

**Example:** Delete cluster and snapshots when CR is deleted

```yaml
spec:
  deletionPolicy: delete
```

Snapshots are independent — deleting a cluster does not auto-delete its snapshots.

## Immutability and Updates

These fields are immutable after cluster creation and cannot be changed:

- **tlsEnabled** — Set at creation time only; requires new cluster to change
- **kmsKeyArn** — Set at creation time only; requires new cluster to change
- **numShards** — Horizontal scaling requires a new cluster (restore from snapshot)

All other fields (numReplicasPerShard, engineVersion, parameters, etc.) are updatable via standard patch/update operations.

## Additional Resources

- **Governance cascade details:** [MemoryDBConfig governance](./memorydbconfig.md#governance-cascade)
- **Naming template syntax:** [Naming Template — Dynamic Tags](../../../concepts/naming/dynamic-tag-fields-in-naming-templates.md)
- **Deletion policy semantics:** [ADR-009](https://github.com/kropath/kropath-core/blob/main/docs/adrs/adr-009-resource-lifecycle.md)
- **Label/annotation syncing:** [ADR-015 §6](https://github.com/kropath/kropath-core/blob/main/docs/adrs/adr-015-governance-and-k8s-metadata.md)
