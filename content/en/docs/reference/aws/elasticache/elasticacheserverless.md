---
title: ElastiCacheServerless — Auto-Scaling Caches
description: "The `ElastiCacheServerless` resource represents serverless auto-scaling caches in AWS ElastiCache."
doc_type: reference
---
# ElastiCacheServerless — Auto-Scaling Caches

The `ElastiCacheServerless` resource represents serverless auto-scaling caches in AWS ElastiCache. Serverless caches automatically scale ECPUs and storage based on demand without requiring manual node type or capacity planning. They support Valkey and Redis engines and are ideal for dynamic workloads with unpredictable traffic patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the cache name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps cache in AWS; `"delete"` removes it |

### Engine Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engine` | string | `"valkey"` | Cache engine: `"valkey"` (recommended) \| `"redis"`; **IMMUTABLE after creation** |
| `engineVersion` | string | `""` | Specific version; empty uses AWS default |
| `description` | string | required | Human-readable cache description |

**Critical:** Engine choice cannot be changed after creation. Select carefully.

### Auto-Scaling Limits

| Field | Type | Default | Purpose |
|---|---|---|---|
| `dataStorageMaximumGB` | integer | required | Maximum storage in GB (1–3000); determines max dataset size |
| `ecpuPerSecondMaximum` | integer | required | Maximum throughput in ECPUs/second; scales compute automatically |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `kmsKeyID` | string | `""` | KMS key ID or ARN; empty uses AWS-managed default |

**Note:** Serverless caches always encrypt both at rest and in transit—no configuration required.

### Authentication & Access Control

| Field | Type | Default | Purpose |
|---|---|---|---|
| `userGroupID` | string | optional | User group ID for RBAC (Valkey/Redis 6+ only) |

### Networking

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subnetIDs` | array of strings | required | VPC subnets for the cache |
| `securityGroupIDs` | array of strings | optional | VPC security groups for network access |

### Snapshots

| Field | Type | Default | Purpose |
|---|---|---|---|
| `snapshotRetentionLimit` | integer | nil (governed) | Snapshot retention floor in days (0 = disable) |
| `snapshotWindow` | string | `""` | Preferred time for automated snapshots |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective cache name (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `predictedArn` | string | ARN: `arn:aws:elasticache:region:account:serverlesscache:resourceName` |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

Serverless cache names are stored lowercase. Names follow the default template `{namespace}-{name}`.

**Override:** Set `spec.nameOverride` to use a custom name.

## Complete Examples

### Basic Auto-Scaling Cache

A serverless cache for variable-load workloads that scales automatically:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheServerless
metadata:
  name: analytics-cache
  namespace: analytics-team
spec:
  configRef: general-policy
  engine: valkey
  description: "Auto-scaling analytics cache"
  dataStorageMaximumGB: 50
  ecpuPerSecondMaximum: 500
  subnetIDs:
    - subnet-12345678
    - subnet-87654321
  snapshotRetentionLimit: 3
  deletionPolicy: retain
  tags:
    team: analytics
    workload-type: variable-load
```

**Result:**
- Cache auto-scales up to 50 GB storage and 500 ECPUs/second
- Snapshots retained for 3 days
- Always encrypted
- Deployment completed in minutes without capacity planning

### Large Serverless Cache with Custom KMS Key

A serverless cache for a critical workload with encryption and RBAC:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheServerless
metadata:
  name: production-cache
  namespace: production
spec:
  configRef: production
  engine: valkey
  engineVersion: "7.0"
  description: "Production serverless cache with RBAC"
  dataStorageMaximumGB: 500  # Large dataset support
  ecpuPerSecondMaximum: 2000  # High throughput
  kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  userGroupID: prod-apps  # User group for RBAC
  subnetIDs:
    - subnet-prod-1
    - subnet-prod-2
    - subnet-prod-3
  securityGroupIDs:
    - sg-prod-internal
  snapshotRetentionLimit: 30
  snapshotWindow: "03:00-04:00"
  deletionPolicy: retain
  tags:
    environment: production
    compliance: pci-dss
  syncedLabels:
    audit-required: "true"
```

**Result:**
- Scales to 500 GB with up to 2000 ECPUs/second
- Encrypted with customer-managed KMS key
- RBAC via user group
- Snapshots retained 30 days for compliance
- Event monitoring via security group

### Development Serverless Cache

A minimal serverless cache for testing and development:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheServerless
metadata:
  name: dev-cache
  namespace: development
spec:
  configRef: dev
  engine: valkey
  description: "Development serverless cache"
  dataStorageMaximumGB: 10  # Small dataset
  ecpuPerSecondMaximum: 100  # Light load
  subnetIDs:
    - subnet-dev-1
  snapshotRetentionLimit: 0  # No snapshots
  deletionPolicy: delete  # Auto-cleanup when resource deleted
```

**Result:**
- Minimal cost (10 GB max, 100 ECPUs)
- No snapshot overhead
- Auto-deleted when resource is removed (safe for non-prod)

## Governance Cascade

Encryption is always enabled on serverless caches, but KMS key selection and snapshot retention are governed:

**KMS Key:** Uses customer-managed key if `kmsKeyID` is set; otherwise AWS-managed default

**Snapshot Retention:** Governance may set a mandatory floor; instance value must respect it

## Key Behaviors

### Engine Is Immutable

Once created with `engine: valkey` (or `redis`), the engine cannot be changed. To switch engines, create a new serverless cache and migrate.

### Auto-Scaling Is Automatic

Serverless caches scale compute (ECPUs) and storage independently based on demand, up to the maximums you set. No manual intervention needed.

### No Node Type or Replica Planning

Unlike replication groups, serverless abstracts away node types, replicas, and clustering. AWS handles all HA and scaling internally.

### Always Encrypted

Both at-rest and in-transit encryption are always enabled. You only choose the KMS key (AWS-managed vs customer-managed).

## Troubleshooting

### Cache Won't Create: "Invalid Naming"

Check `status.namingStatus`. If `"invalid-unresolved-tokens"`, fix the naming template or add missing tags.

### Can't Change Engine After Creation

Engine is immutable. Create a new serverless cache with the desired engine and migrate data.

### Snapshot Retention Lower Than Governance Floor

If governance mandates a retention floor, increase your instance's `snapshotRetentionLimit` or contact platform team.

### High Costs Due to Over-Provisioning

Review `dataStorageMaximumGB` and `ecpuPerSecondMaximum` settings. Consider lower limits if your actual load is lower, or use a replication group with fixed node types if you want predictable costs.

## Cross-Family Integration

**User Groups:** Reference `[ElastiCacheUserGroup](elasticacheusergroup.md)` via `userGroupID` for RBAC.

**Subnets:** Specify VPC subnets directly via `subnetIDs` (no separate subnet group resource).

**KMS Keys:** Use KMS key IDs or ARNs for custom-managed encryption.

## Next Steps

- Enable RBAC with `[ElastiCacheUser](elasticacheuser.md)` and `[ElastiCacheUserGroup](elasticacheusergroup.md)`
- Review governance policies in `[ElastiCacheConfig](elasticacheconfig.md)`
- Compare with `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` for fixed-capacity needs
