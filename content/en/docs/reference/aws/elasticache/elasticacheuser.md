---
title: ElastiCacheUser — RBAC User Credentials
description: "The `ElastiCacheUser` resource defines individual user credentials for Redis and Valkey caches (Redis 6+)."
doc_type: reference
---
# ElastiCacheUser — RBAC User Credentials

The `ElastiCacheUser` resource defines individual user credentials for Redis and Valkey caches (Redis 6+). Users are grouped into `ElastiCacheUserGroup` resources to implement role-based access control (RBAC). Each user has an access string defining what commands and keys they can access.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `ElastiCacheConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets the username directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the user in AWS; `"delete"` removes it |

### User Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `engine` | string | required | Cache engine: `"redis"` \| `"valkey"` (Redis/Valkey 6+ only) |
| `accessString` | string | required | Access control pattern (e.g., `"on >password ~* &*"`) |

### Authentication

| Field | Type | Default | Purpose |
|---|---|---|---|
| `authenticationMode` | object | optional | Authentication method (password or IAM) |
| `authenticationMode.type` | string | `"password"` | `"password"` (plaintext) \| `"iam"` (AWS IAM) |
| `authenticationMode.passwords` | array | optional | Plaintext passwords (for `type: password`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective username (from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions[]` | array | Standard kro conditions (ready, error, etc.) |

## Naming Convention

Usernames follow the default template `{namespace}-{name}` → e.g., `app-team-api-service`.

**Override:** Set `spec.nameOverride` to use a custom username.

## Access String Format

The `accessString` defines which commands and keys a user can access. Common patterns:

| Pattern | Meaning |
|---|---|
| `on` | User is enabled |
| `>password` | Set password requirement (plaintext password) |
| `~*` | User can access all keys (wildcard) |
| `&*` | User can use all commands (wildcard) |
| `~key*` | User can access keys matching `key*` pattern |
| `+get +set` | User can use only GET and SET commands |
| `-del -flushdb` | User cannot use DEL or FLUSHDB commands |

**Examples:**
- `"on >password ~* &*"` — All commands, all keys, password-authenticated
- `"on ~read-* +get +exists"` — Read-only access to keys starting with `read-`, only GET/EXISTS commands
- `"on -@all"` — No command access (default deny)

## Complete Examples

### Admin User with Full Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUser
metadata:
  name: admin
  namespace: infrastructure
spec:
  configRef: general-policy
  engine: valkey
  accessString: "on >adminpass123 ~* &*"  # Full access
  authenticationMode:
    type: password
    passwords:
      - "adminpass123"
  deletionPolicy: retain
  tags:
    role: administrator
```

**Result:**
- Admin user with full command and key access
- Password-authenticated
- Can be grouped with other admins for organizational access

### Read-Only Application User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUser
metadata:
  name: app-service
  namespace: app-team
spec:
  configRef: general-policy
  engine: valkey
  accessString: "on >apppass456 ~* +get +exists +keys +info"  # Read-only commands
  authenticationMode:
    type: password
    passwords:
      - "apppass456"
  deletionPolicy: retain
  tags:
    role: application
    access-level: read-only
```

**Result:**
- Application user with read-only access
- Can perform GET, EXISTS, KEYS, INFO (information queries only)
- Cannot write or modify data

### IAM-Authenticated Service User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUser
metadata:
  name: iam-service
  namespace: infrastructure
spec:
  configRef: general-policy
  engine: valkey
  accessString: "on ~data-* +get +set +del"  # Access to `data-*` keys with write capability
  authenticationMode:
    type: iam  # AWS IAM authentication (no password)
  deletionPolicy: retain
  tags:
    role: service
    auth-type: iam
```

**Result:**
- Service authenticated via AWS IAM (assumed role)
- No password needed—credentials managed by IAM
- Access limited to keys matching `data-*`
- Write access to specific commands (GET, SET, DEL)

### User with Restricted Key Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheUser
metadata:
  name: cache-writer
  namespace: data-team
spec:
  configRef: general-policy
  engine: valkey
  accessString: "on >writepwd789 ~cache:* +set +get +incr +expire"  # Write commands on `cache:*` keys
  authenticationMode:
    type: password
    passwords:
      - "writepwd789"
  deletionPolicy: retain
  tags:
    role: writer
    key-namespace: cache
```

**Result:**
- User can only write to keys starting with `cache:`
- Can perform SET, GET, INCR (increment), EXPIRE (set TTL)
- All other keys and commands are blocked

## Governance Cascade

Users follow standard governance for naming and tagging.

**Password Requirement:** Governance's `mandatory.blockNoPasswordUsers: true` prevents creating users with `noPasswordRequired: true` (password-less authentication).

## Key Behaviors

### Passwords Are Plaintext in Spec

Passwords in `authenticationMode.passwords` are stored as plaintext in the Kubernetes Secret/resource. Use Secrets or external vault integration for production systems.

### IAM Authentication Is Safer

For production workloads, prefer `type: iam` authentication, which delegates credential management to AWS IAM instead of embedding plaintext passwords.

### Access Strings Cannot Be Validated Client-Side

Complex access strings are validated by AWS when applied to the cache. Test in a non-prod environment first.

### Users Must Be Grouped for Caches

Individual users alone don't grant cache access. Create an `[ElastiCacheUserGroup](elasticacheusergroup.md)` containing users, then reference the group in your cache resource.

## Troubleshooting

### "No Password Users Not Blocked" Error

Governance has `mandatory.blockNoPasswordUsers: true`, but you created a user without a password. Add `authenticationMode.passwords` or use IAM auth instead.

### "Invalid Access String" Error

The access string is malformed or contains unsupported patterns. Check AWS documentation for valid access string syntax.

### User Can't Connect to Cache

Check:
1. The user is in a `[ElastiCacheUserGroup](elasticacheusergroup.md)` referenced by the cache
2. The user's engine matches the cache's engine
3. The access string permits the commands you're attempting
4. Network connectivity (security groups) allows client connections

## Cross-Family Integration

**User Groups:** Users are organized into `[ElastiCacheUserGroup](elasticacheusergroup.md)` resources for RBAC.

**Cache Integration:** Reference user groups in `[ElastiCacheReplicationGroup](elasticachereplicationgroup.md).userGroupIDs` to enable RBAC.

**IAM Integration:** Use AWS IAM roles and users for production authentication instead of plaintext passwords.

## Next Steps

- Create users with appropriate access strings
- Group them into `[ElastiCacheUserGroup](elasticacheusergroup.md)`
- Reference user groups in cache resources for RBAC
- Use IAM authentication for production workloads
