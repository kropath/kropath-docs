---
title: MemoryDBSubnetGroup — VPC Subnet Configuration
description: "The `MemoryDBSubnetGroup` resource represents a named collection of VPC subnets designating the network placement for MemoryDB cluster nodes."
doc_type: reference
---
# MemoryDBSubnetGroup — VPC Subnet Configuration

The `MemoryDBSubnetGroup` resource represents a named collection of VPC subnets designating the network placement for MemoryDB cluster nodes. Subnet groups are required for deploying clusters in a VPC and are commonly shared across multiple clusters.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets subnet group name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Subnet Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subnetIds` | array | required | List of VPC subnet IDs for cluster placement |
| `description` | string | `""` | Human-readable description of the subnet group |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: cache-prod-subnets
  namespace: cache-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  
  # VPC subnets for cluster placement (at least 2 recommended for HA)
  subnetIds:
    - subnet-12345678
    - subnet-87654321
    - subnet-aabbccdd
  
  description: "Subnets for production cache cluster"
  
  # Metadata
  tags:
    service: cache
    environment: production
  syncedLabels:
    team: platform
```

## Subnet Group for High Availability

For resilience, use subnets from multiple availability zones:

```yaml
spec:
  subnetIds:
    - subnet-12345678    # AZ: ap-southeast-2a
    - subnet-87654321    # AZ: ap-southeast-2b
    - subnet-aabbccdd    # AZ: ap-southeast-2c
```

This allows cluster nodes to be distributed across AZs, surviving single-AZ outages.

## Status Fields

After creation:

```yaml
status:
  resourceName: "cache-prod-cache-prod-subnets"   # effectiveName
  namingStatus: "valid"                           # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:subnetgroup/cache-prod-cache-prod-subnets"
  conditions:
    - type: Ready
      status: "True"
      message: "Subnet group is ready"
```

## How to Reference in Clusters

After creating the subnet group, reference it in clusters:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  subnetGroupName: cache-prod-subnets  # Reference by name
  # ... other cluster fields
```

## Governance

`MemoryDBSubnetGroup` has **no functional governance fields** beyond tags, labels, and naming. Platform teams do not enforce subnet selection — those are infrastructure-specific decisions.

Governance fields available:
- **tags** / **syncedLabels** / **syncedAnnotations** — Metadata governance
- **namingTemplate** — Naming convention

See [MemoryDBConfig governance](./memorydbconfig.md) for full governance cascade details.

## Naming

Subnet group names are generated via the governance naming template:

```yaml
# Default: "{namespace}-{name}"
# With namespace=cache-prod, name=cache-prod-subnets
# Result: cache-prod-cache-prod-subnets

# Custom: "sg-{namespace}"
# Result: sg-cache-prod
```

See [Naming Template — Dynamic Tags](../../../concepts/configuration/naming-templates.md) for full syntax.

**AWS constraints:** Starts with letter, alphanumeric + hyphens + underscores.

## Update and Delete

### Add or Remove Subnets

Update the `subnetIds` list:

```yaml
spec:
  subnetIds:
    - subnet-12345678
    - subnet-87654321
    - subnet-aabbccdd    # New subnet
    - subnet-newsubnet   # New subnet
    # Removed: subnet-old (was here, now removed)
```

Push the update — clusters using this subnet group will be updated.

### Delete Subnet Group

By default, subnet groups are retained:

```yaml
spec:
  deletionPolicy: retain
```

To delete the AWS subnet group when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

**Warning:** If clusters are using this subnet group, they must be updated to reference a different subnet group before deletion.

## Tagging

Subnet groups inherit tags from governance:

```yaml
# MemoryDBConfig/general-policy
spec:
  mandatory:
    tags:
      service: memorydb
  defaults:
    tags:
      team: platform

# MemoryDBSubnetGroup instance
spec:
  tags:
    environment: production

# Result in ACK SubnetGroup spec.tags:
#   service: memorydb (mandatory)
#   team: platform (defaults)
#   environment: production (instance)
```

## Example: Multi-Environment Setup

```yaml
---
# Development subnets (single AZ, cost-optimized)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: dev-subnets
  namespace: cache-dev
spec:
  subnetIds:
    - subnet-dev-1a
  description: "Development cache subnets"
  tags:
    environment: development

---
# Staging subnets (dual AZ, high availability)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: staging-subnets
  namespace: cache-staging
spec:
  subnetIds:
    - subnet-staging-2a
    - subnet-staging-2b
  description: "Staging cache subnets"
  tags:
    environment: staging

---
# Production subnets (multi-AZ, maximum resilience)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: prod-subnets
  namespace: cache-prod
spec:
  subnetIds:
    - subnet-prod-2a
    - subnet-prod-2b
    - subnet-prod-2c
  description: "Production cache subnets across 3 AZs"
  tags:
    environment: production

---
# Dev cluster using dev subnets
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: dev-cache
  namespace: cache-dev
spec:
  subnetGroupName: dev-subnets
  nodeType: db.t4g.small
  # ... other fields

---
# Prod cluster using prod subnets
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: prod-cache
  namespace: cache-prod
spec:
  subnetGroupName: prod-subnets
  nodeType: db.r7g.large
  numShards: 3
  numReplicasPerShard: 2
  # ... other fields
```

## Common Tasks

### Create a subnet group for a VPC

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBSubnetGroup
metadata:
  name: my-cache-subnets
  namespace: cache
spec:
  subnetIds:
    - subnet-12345678
    - subnet-87654321
```

### Deploy clusters in multiple subnets for HA

```yaml
spec:
  subnetIds:
    - subnet-az-1
    - subnet-az-2
    - subnet-az-3
```

MemoryDB automatically distributes nodes across AZs.

### Update subnet group with new subnets

```yaml
# Old:
subnetIds:
  - subnet-old-1
  - subnet-old-2

# New:
subnetIds:
  - subnet-new-1
  - subnet-new-2
```

Clusters will be updated to use the new subnets.

## AWS VPC Requirements

- Subnets must be in the same VPC
- At least 2 subnets recommended (across different AZs)
- Subnets must have Internet Gateway or NAT Gateway access for AWS API calls
- Security groups must allow MemoryDB port traffic (default 6379)

See your VPC configuration for subnet IDs.

## Additional Resources

- **Cluster configuration:** [MemoryDBCluster](./memorydbcluster.md)
- **Governance policies:** [MemoryDBConfig](./memorydbconfig.md)
- **AWS VPC documentation:** [VPC Subnets](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html)
- **MemoryDB networking:** [MemoryDB in VPC](https://docs.aws.amazon.com/memorydb/latest/devguide/vpc-subnet-groups.html)
