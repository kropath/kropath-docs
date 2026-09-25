---
title: AWS ElastiCache
description: The ElastiCache resource family provides unified management of Redis, Valkey, and Memcached caches on AWS.
doc_type: reference
weight: 230
---
# AWS ElastiCache

The ElastiCache resource family provides unified management of Redis, Valkey, and Memcached caches on AWS. kropath abstracts the complexity of cluster modes, encryption, high availability, and RBAC behind a simple declarative interface.

## Core Resources

| Resource | Purpose | Typical Use |
|---|---|---|
| [ElastiCacheConfig](elasticacheconfig.md) | Governance and compliance profiles | Platform teams define encryption, HA, and naming policy |
| [ElastiCacheReplicationGroup](elasticachereplicationgroup.md) | Production Redis/Valkey caches | Multi-AZ replicated caches with failover and cluster mode |
| [ElastiCacheServerless](elasticacheserverless.md) | Auto-scaling caches | Dynamic workloads with auto-scaling ECPUs and storage |
| [ElastiCacheCluster](elasticachecluster.md) | Memcached and dev/test | Multi-node Memcached or single-node Redis/Valkey for development |
| [ElastiCacheSubnetGroup](elasticachesubnetgroup.md) | VPC networking | Shared subnet configuration for clusters and replication groups |
| [ElastiCacheParameterGroup](elasticacheparametergroup.md) | Engine tuning | Customize Redis/Valkey/Memcached parameters across clusters |
| [ElastiCacheUser](elasticacheuser.md) | RBAC authentication | Individual user credentials for Redis/Valkey 6+ |
| [ElastiCacheUserGroup](elasticacheusergroup.md) | User grouping | Group users for role-based access control |

## Quick Start

### 1. Governance Setup

Define your organization's ElastiCache policies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    atRestEncryptionEnabled: true
    transitEncryptionEnabled: true
    automaticFailoverEnabled: true
    multiAZEnabled: true
    engine: valkey
    snapshotRetentionLimit: 1
    namingTemplate: "{namespace}-{name}"
```

### 2. Create a Replication Group (Production Cache)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: session-cache
  namespace: app-team
spec:
  configRef: general-policy
  engine: valkey
  engineVersion: "7.0"
  cacheNodeType: cache.r7g.large
  description: "Session cache for e-commerce platform"
  multiAZEnabled: true
  automaticFailoverEnabled: true
  snapshotRetentionLimit: 7
```

### 3. Create a Serverless Cache (Auto-Scaling)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheServerless
metadata:
  name: analytics-cache
  namespace: analytics-team
spec:
  configRef: general-policy
  engine: valkey
  dataStorageMaximumGB: 100
  ecpuPerSecondMaximum: 1000
```

## Governance Cascade

All ElastiCache resources follow a three-tier governance cascade:

**Level 1 (Highest):** Organization-wide encryption enforcement via `KropathConfig`
- Applies to every cache regardless of profile
- Cannot be overridden by resource instances

**Level 2:** Profile-specific policy via `ElastiCacheConfig` (e.g., `general-policy`, `pci`, `production`)
- Defines mandatory controls and reasonable defaults
- Applied when resource specifies `spec.configRef`

**Level 3 (Lowest):** Developer overrides in resource `spec`
- Instance-level choices
- Can override defaults but not mandatory controls
- Examples: `engine`, `cacheNodeType`, `snapshotRetentionLimit`

The controller pre-merges all three tiers and writes the effective configuration to the `ElastiCacheConfig` CR's `status.effectiveConfig` field. All RGDs read this single merged view.

## Naming Convention

By default, cache resources are named using the pattern: `{namespace}-{name}`

This produces names like `app-team-session-cache` for a resource named `session-cache` in the `app-team` namespace.

**Available tokens:**
- `{name}` — Kubernetes resource name
- `{namespace}` — Kubernetes namespace
- `{configRef}` — Selected governance profile
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Any tag key from the merged tags

**Override:** Set `spec.nameOverride` to bypass the naming template entirely.

## Encryption

ElastiCache supports two types of encryption:

**At-rest encryption** — Encrypts data stored in ElastiCache nodes using a KMS key. Once enabled on a replication group, it cannot be disabled. The governance mandatory tier can enforce this across your organization.

**In-transit encryption** — TLS encryption for data moving between client and cache. Mutable after creation; can be enabled or disabled on existing caches.

Use `atRestEncryptionEnabled` and `transitEncryptionEnabled` in governance policies to enforce encryption org-wide.

## High Availability

Replication groups support two HA mechanisms that must be used together:

- **Multi-AZ (`multiAZEnabled`)** — Distributes replicas across availability zones
- **Automatic Failover (`automaticFailoverEnabled`)** — Promotes read replicas to primary on failure

When `multiAZEnabled: true`, `automaticFailoverEnabled` is automatically forced to `true` by the RGD, ensuring each AZ has a replica capable of takeover.

## RBAC: Users and User Groups

Redis/Valkey 6+ support role-based access control via user groups:

1. Create users with `ElastiCacheUser` — define username, passwords/IAM auth, and access strings
2. Group users with `ElastiCacheUserGroup` — create a named group and add users to it
3. Reference the group in `ElastiCacheReplicationGroup.spec.userGroupIDs` — restrict access by role

Example:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUser
metadata:
  name: app-admin
  namespace: app-team
spec:
  accessString: "on >password ~*"  # Full access with password requirement
  authenticationMode:
    type: password
    passwords: ["secret123"]

---
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUserGroup
metadata:
  name: app-admins
  namespace: app-team
spec:
  engine: valkey
  userIDs:
    - app-admin

---
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: prod-cache
  namespace: app-team
spec:
  userGroupIDs:
    - app-admins  # Apply RBAC from the user group
```

## Cross-Family Integration

**KMS Keys:** Use `[KMSKey](../kms/kmskey.md)` resources to manage encryption keys. Reference them via `kmsKeyRef` or use a direct ARN with `kmsKeyArn`.

**VPC & Security Groups:** Specify `cacheSubnetGroupName` and `securityGroupIDs` to place caches in your VPC.

**SNS Notifications:** Provide an SNS topic ARN to receive ElastiCache event notifications.

## Deletion Behavior

All ElastiCache resources support a deletion policy:

- `retain` (default) — Resource is deleted from Kubernetes but kept in AWS
- `delete` — Resource is deleted from both Kubernetes and AWS

Set via `spec.deletionPolicy` on any resource instance.

## Troubleshooting

### Cache Won't Create

Check `status.namingStatus`:
- If `invalid-unresolved-tokens`, the naming template references a tag or token that doesn't exist
- If `valid`, check AWS permissions and `status.conditions` for error messages

### "Mandatory field conflict" Error

An `ElastiCacheConfig` CRD validation error with "must be set in either mandatory or defaults, not both" indicates that a governance field is populated in both tiers. Contact your platform team to adjust the policy.

### Encryption Can't Be Changed After Creation

At-rest encryption on replication groups is immutable. Once set, it cannot be disabled. If you need a cache without encryption, create a new replication group with `atRestEncryptionEnabled: false` and migrate traffic.

### Access Denied to User Group RBAC

Ensure that:
- The user group exists in the same AWS account and region
- Users in the group have been created and have matching passwords/IAM auth
- The replication group's security group permits connections from your client

## Next Steps

- Review [ElastiCacheConfig](elasticacheconfig.md) to understand governance and profiles
- Start with [ElastiCacheReplicationGroup](elasticachereplicationgroup.md) for production caches
- Set up RBAC with [ElastiCacheUser](elasticacheuser.md) and [ElastiCacheUserGroup](elasticacheusergroup.md)
