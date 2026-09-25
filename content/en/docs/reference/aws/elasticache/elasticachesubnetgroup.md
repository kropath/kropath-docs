---
title: ElastiCacheSubnetGroup — VPC Subnet Management
description: "The `ElastiCacheSubnetGroup` resource defines which VPC subnets are available for ElastiCache clusters and replication groups."
doc_type: reference
---
# ElastiCacheSubnetGroup — VPC Subnet Management

The `ElastiCacheSubnetGroup` resource defines which VPC subnets are available for ElastiCache clusters and replication groups. It acts as a shared configuration that multiple cache resources can reference, centralizing VPC network placement decisions.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the subnet group name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the subnet group in AWS; `"delete"` removes it |

### Subnet Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | required | Human-readable description of the subnet group |
| `subnetIDs` | array of strings | required | VPC subnet IDs (must be non-empty; minimum 1 subnet, 2+ recommended for Multi-AZ) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective subnet group name (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

Subnet group names are constrained to 1–255 characters, lowercase alphanumeric + hyphens.

**Default template:** `{namespace}-{name}` → e.g., `app-team-cache-subnets`

**Override:** Set `spec.nameOverride` to use a custom name.

## Complete Examples

### Basic Subnet Group (Single Availability Zone)

A simple subnet group with subnets in a single AZ (less recommended for production):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheSubnetGroup
metadata:
  name: cache-subnets
  namespace: app-team
spec:
  configRef: general-policy
  description: "Subnets for app-team cache resources"
  subnetIDs:
    - subnet-12345678
  deletionPolicy: retain
  tags:
    team: app-team
    network-type: cache
```

**Result:**
- Subnet group created with name `app-team-cache-subnets`
- Single subnet (all caches in one AZ)
- Can be referenced by cache resources via `cacheSubnetGroupName`

### Multi-AZ Subnet Group (Recommended)

A subnet group spanning multiple availability zones for high availability:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheSubnetGroup
metadata:
  name: multi-az-subnets
  namespace: production
spec:
  configRef: production
  description: "Multi-AZ subnets for production caches"
  subnetIDs:
    - subnet-prod-az1  # us-east-1a
    - subnet-prod-az2  # us-east-1b
    - subnet-prod-az3  # us-east-1c
  deletionPolicy: retain
  tags:
    environment: production
    high-availability: required
  syncedLabels:
    network-tier: cache
```

**Result:**
- Subnet group spans 3 AZs
- Multi-AZ replication groups automatically distribute replicas across AZs
- Automatic failover can promote replicas in different AZs

### Shared Subnet Group (Multiple Teams)

A centrally managed subnet group used by multiple teams to standardize cache networking:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheSubnetGroup
metadata:
  name: shared-vpc-cache
  namespace: kro-system  # Centrally managed
spec:
  configRef: general-policy
  description: "Shared VPC subnets for all team caches"
  subnetIDs:
    - subnet-shared-1
    - subnet-shared-2
  deletionPolicy: retain
  tags:
    managed-by: platform-team
    access: shared
```

**Usage:** Teams reference this subnet group by name:
```yaml
# In any namespace
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: team-cache
  namespace: team-a
spec:
  cacheSubnetGroupName: kro-system-shared-vpc-cache  # Reference shared subnet group
  ...
```

## Governance Cascade

Subnet groups follow standard governance for naming and tagging. Subnet IDs themselves are not governed—platform teams control which subnets are available.

## Key Behaviors

### Subnets Cannot Be Empty

A subnet group must have at least one subnet. Attempting to create or update with an empty `subnetIDs` array is rejected.

### Naming Is Immutable After Creation

Like other AWS resources, the subnet group name cannot be changed after creation. Plan the name carefully or use `nameOverride`.

### Subnet Updates Affect Running Caches

If you update a subnet group to add or remove subnets, existing caches using that group are not automatically reconfigured. Manual migration may be required for large topology changes.

### Multiple Caches Share the Same Subnets

All caches referencing a subnet group share the same set of subnets. This centralizes VPC placement decisions and simplifies multi-team setups.

## Troubleshooting

### "Empty Subnet IDs" Error

A subnet group must have at least one subnet. Add subnets to the `subnetIDs` array and reapply.

### Caches Can't Connect to Subnet Group

Check:
1. The subnet group exists in the same AWS account and region
2. The subnet IDs are valid and belong to your VPC
3. The VPC and subnets are in the same region as your ElastiCache resources

### Cache Creation Fails with "Invalid Subnet"

If a subnet ID in the group is invalid or deleted:
1. Update the subnet group to use valid subnet IDs
2. Re-create the cache resource

## Cross-Family Integration

**Cache Resources:** Reference subnet groups via `cacheSubnetGroupName` in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` and `[ElastiCacheCluster](elasticachecluster.md)`.

**VPC:** Subnets must belong to the same VPC where your caches will operate.

**Security Groups:** Combine with VPC security groups (referenced in cache resources) to control network access.

## Next Steps

- Create subnet groups for each VPC/environment
- Reference them in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md)` and `[ElastiCacheCluster](elasticachecluster.md)`
- Use shared subnet groups for multi-team environments to standardize networking
