# ElastiCacheUserGroup — User Grouping for RBAC

The `ElastiCacheUserGroup` resource groups `ElastiCacheUser` resources to implement role-based access control (RBAC) on Redis and Valkey caches. A single user group is referenced by multiple cache resources to grant consistent access patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the group name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the group in AWS; `"delete"` removes it |

### Group Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engine` | string | required | Cache engine: `"redis"` \| `"valkey"` (Redis/Valkey 6+ only) |
| `userIDs` | array of strings | optional | User IDs to include in the group (can be updated after creation) |
| `description` | string | optional | Human-readable description of the group |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective group name (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

User group names follow the default template `{namespace}-{name}` → e.g., `app-team-cache-admins`.

**Override:** Set `spec.nameOverride` to use a custom name.

## Complete Examples

### Administrator Group

A group for cache administrators with full access:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUserGroup
metadata:
  name: cache-admins
  namespace: infrastructure
spec:
  configRef: general-policy
  engine: valkey
  description: "Cache administrators with full access"
  userIDs:
    - infrastructure-admin  # User with full access
    - infrastructure-backup  # Backup admin user
  deletionPolicy: retain
  tags:
    role: administrator
    access-level: full
```

**Usage:** Apply to caches that need full admin access:
```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: prod-cache
  namespace: production
spec:
  userGroupIDs:
    - infrastructure-cache-admins
  ...
```

### Application User Group

A group for application read-write access:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUserGroup
metadata:
  name: app-users
  namespace: app-team
spec:
  configRef: general-policy
  engine: valkey
  description: "Application service users with read-write access"
  userIDs:
    - app-service  # Main application service
    - app-worker   # Background worker process
  deletionPolicy: retain
  tags:
    role: application
    access-level: read-write
```

**Usage:** Apply to caches used by applications:
```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: session-cache
  namespace: app-team
spec:
  userGroupIDs:
    - app-team-app-users
  ...
```

### Read-Only Monitoring Group

A group for monitoring and analytics with read-only access:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUserGroup
metadata:
  name: monitoring
  namespace: infrastructure
spec:
  configRef: general-policy
  engine: valkey
  description: "Monitoring and analytics users with read-only access"
  userIDs:
    - prometheus-exporter  # Metrics collector
    - analytics-service    # Analytics aggregator
  deletionPolicy: retain
  tags:
    role: monitoring
    access-level: read-only
```

**Usage:** Apply to caches for observability:
```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheReplicationGroup
metadata:
  name: analytics-cache
  namespace: infrastructure
spec:
  userGroupIDs:
    - infrastructure-monitoring
  ...
```

## Governance Cascade

User groups follow standard governance for naming and tagging.

## Key Behaviors

### Users Are Updated Dynamically

The `userIDs` array can be updated after the group is created. Adding or removing users from the group takes effect immediately for all caches using that group.

**Example:** Add a new user to an existing group:
```yaml
# Update the group to include a new user
spec:
  userIDs:
    - existing-user1
    - existing-user2
    - new-user  # Added
```

The change propagates to all caches referencing this group.

### Engine Must Match Users

All users in a group must have matching engine types. A group for `engine: valkey` cannot contain users created for `redis`.

### Empty User Groups Are Allowed

A group can be created with no users and populated later, or users can be removed until the group is empty.

### Multiple Caches Can Share a Group

A single user group is typically referenced by multiple cache resources to enforce consistent access control across your infrastructure.

## Troubleshooting

### "User Not Found" Error

A user ID in the group doesn't correspond to an existing `ElastiCacheUser` resource. Verify the user exists and the ID is correct.

### Engine Mismatch

A user in the group has a different engine type (e.g., Redis user in Valkey group). Ensure all users match the group's engine.

### User Updates Don't Apply

After updating `userIDs`, verify that:
1. The group resource was applied successfully
2. Caches are still referencing the group (user groups are re-applied at next reconciliation)
3. Check `status.conditions` for any errors

## Cross-Family Integration

**Users:** Reference `[ElastiCacheUser](elasticacheuser.md)` resources by ID.

**Cache Integration:** Reference user groups in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md).userGroupIDs` to enable RBAC.

## Next Steps

- Create users with `[ElastiCacheUser](elasticacheuser.md)`
- Group them into `ElastiCacheUserGroup`
- Reference user groups in cache resources for RBAC
- Update group membership as roles and access needs evolve
