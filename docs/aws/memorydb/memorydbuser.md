# MemoryDBUser — User Identity and Authentication

The `MemoryDBUser` resource represents a single user identity for MemoryDB cluster authentication. Users define access permissions (Redis commands, keys, channels) and authentication mode (password or IAM).

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets user name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Access Control

| Field | Type | Default | Purpose |
|---|---|---|---|
| `accessString` | string | required | Redis ACL string defining command/key/channel permissions (e.g. `"on >password +@all"`) |

### Authentication Mode

| Field | Type | Default | Purpose |
|---|---|---|---|
| `authenticationMode.type` | string | required | `"password"` or `"iam"` |
| `authenticationMode.passwords` | array | [] | List of Kubernetes Secret references containing user passwords (required when `type="password"`) |
| `authenticationMode.passwords[].name` | string | required | Kubernetes Secret name containing the password |
| `authenticationMode.passwords[].key` | string | required | Key within the Secret holding the password value |
| `authenticationMode.passwords[].namespace` | string | optional | Namespace of the Secret (defaults to resource namespace) |

**Note on ACK field mapping:** The ACK `User` CRD exposes this field as `spec.authenticationMode.type_` (with a trailing underscore, a Go reserved-word workaround). The kropath schema uses `spec.authenticationMode.type` (no underscore) for cleaner UX — the RGD template automatically maps between them.

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example: Password-Based User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: appuser
  namespace: cache-prod
spec:
  deletionPolicy: retain
  
  # Redis access string: on (enabled), >password (password required), +@all (all commands)
  accessString: "on >password +@all"
  
  # Authentication mode with password
  authenticationMode:
    type: password
    passwords:
      - name: appuser-password
        key: password
  
  # Tags
  tags:
    service: cache
    role: application
```

## Complete Example: Read-Only User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: readonly-user
  namespace: cache-prod
spec:
  # Read-only: allow GET and MGET on all keys, deny writes
  accessString: "on >password +@read"
  
  authenticationMode:
    type: password
    passwords:
      - name: readonly-password
        key: password
```

## Complete Example: IAM-Based User

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: iam-app-user
  namespace: cache-prod
spec:
  # IAM auth: pod identity (IRSA) is used instead of password
  accessString: "on ~* +@all"     # All commands on all keys via IAM
  
  authenticationMode:
    type: iam
    # No passwords field for IAM — pod IRSA role provides credentials
```

## Access String Syntax

The `accessString` field defines Redis ACL permissions. Common patterns:

| Pattern | Meaning |
|---------|---------|
| `on` | User enabled |
| `off` | User disabled |
| `>password` | Require this password |
| `~*` | All keys |
| `~key1` `~key2` | Specific keys |
| `~prefix:*` | Key pattern |
| `+@all` | All commands |
| `+@read` | Read commands (GET, MGET, etc.) |
| `+@write` | Write commands (SET, DEL, etc.) |
| `+@admin` | Admin commands |
| `+get` `+set` | Specific commands |
| `-@all +@read` | Deny all, allow read |

**Examples:**

```yaml
# Full access (use cautiously)
accessString: "on >password +@all"

# Read-only
accessString: "on >password +@read"

# Write-only (monitoring)
accessString: "on >password +@write"

# Specific commands on specific keys
accessString: "on >password ~cache:* +get +set -del"

# Admin operations
accessString: "on >password +@admin +@read +@write"

# Application user (most commands except admin)
accessString: "on >password +@all -@admin"
```

## Password Management

### Single Password

```yaml
spec:
  accessString: "on >password +@all"
  authenticationMode:
    type: password
    passwords:
      - name: myuser-pwd
        key: password
```

Create the Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myuser-pwd
  namespace: cache-prod
type: Opaque
stringData:
  password: "your-secure-password-here"
```

### Password Rotation (Multiple Passwords)

To rotate passwords without downtime:

1. Add the new password to the list:
   ```yaml
   spec:
     authenticationMode:
       type: password
       passwords:
         - name: myuser-pwd-old
           key: password
         - name: myuser-pwd-new  # New password added
           key: password
   ```

2. Applications gradually switch to the new password

3. Remove the old password from the list once all apps are switched:
   ```yaml
   spec:
     authenticationMode:
       type: password
       passwords:
         - name: myuser-pwd-new
           key: password
   ```

## IAM Authentication

For pod identity (IRSA):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: iam-user
  namespace: cache-prod
spec:
  accessString: "on ~* +@all"
  authenticationMode:
    type: iam
    # No passwords field for IAM
```

The pod must have an IAM role with MemoryDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "memorydb:*",
      "Resource": "*"
    }
  ]
}
```

## Status Fields

After creation:

```yaml
status:
  resourceName: "cache-prod-appuser"           # effectiveName
  namingStatus: "valid"                        # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:user/cache-prod-appuser"
  userStatus: "active"                         # active | modifying | deleting
  aclNames:                                    # List of ACLs this user belongs to
    - production-acl
  conditions:
    - type: Ready
      status: "True"
      message: "User is ready"
```

## Governance

`MemoryDBUser` has **no functional governance fields** beyond tags, labels, and naming. Platform teams do not enforce access strings or authentication types — those are per-user decisions.

Governance fields available:
- **tags** / **syncedLabels** / **syncedAnnotations** — Metadata governance
- **namingTemplate** — Naming convention

See [MemoryDBConfig governance](./memorydbconfig.md) for full governance cascade details.

## Naming and ARN

User names are generated via the governance naming template:

```yaml
# Default: "{namespace}-{name}"
# With namespace=cache-prod, name=appuser
# Result: cache-prod-appuser

# Custom: "user-{tag.env}-{name}"
# With tag.env=prod
# Result: user-prod-appuser
```

See [Naming Template — Dynamic Tags](../resources/naming-template-dynamic-tags.md) for full syntax.

**AWS constraints:** Starts with letter, alphanumeric + hyphens.

## Update and Delete

### Change Access Permissions

Update the `accessString`:

```yaml
spec:
  accessString: "on >password +@read"  # Changed from +@all
```

Push the update — the user's permissions change immediately.

### Rotate Password

Add new password to `passwords` array, test it, then remove old password.

### Delete User

By default, users are retained:

```yaml
spec:
  deletionPolicy: retain
```

To delete the AWS user when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

**Warning:** If the user is a member of an ACL attached to a cluster, the cluster will lose access. Remove the user from all ACLs before deletion.

## Tagging

Users inherit tags from governance:

```yaml
# MemoryDBConfig/general-policy
spec:
  mandatory:
    tags:
      service: memorydb
  defaults:
    tags:
      team: platform

# MemoryDBUser instance
spec:
  tags:
    role: application

# Result in ACK User spec.tags:
#   service: memorydb (mandatory)
#   team: platform (defaults)
#   role: application (instance)
```

## Example: Multi-User Setup

```yaml
---
# Application user (read/write)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: app-user
  namespace: cache-prod
spec:
  accessString: "on >password +@all"
  authenticationMode:
    type: password
    passwords:
      - name: app-user-pwd
        key: password
  tags:
    role: application

---
# Monitoring user (read-only)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: monitoring-user
  namespace: cache-prod
spec:
  accessString: "on >password +@read"
  authenticationMode:
    type: password
    passwords:
      - name: monitoring-pwd
        key: password
  tags:
    role: monitoring

---
# Admin user (full access)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: admin-user
  namespace: cache-prod
spec:
  accessString: "on >password +@all +@admin"
  authenticationMode:
    type: password
    passwords:
      - name: admin-pwd
        key: password
  tags:
    role: admin

---
# Group into ACL
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: production-acl
  namespace: cache-prod
spec:
  userNames:
    - app-user
    - monitoring-user
    - admin-user

---
# Attach to cluster
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  aclName: production-acl
  # ... other cluster fields
```

## Common Tasks

### Create a full-access user

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBUser
metadata:
  name: app-user
  namespace: cache-prod
spec:
  accessString: "on >password +@all"
  authenticationMode:
    type: password
    passwords:
      - name: app-user-pwd
        key: password
```

### Create a read-only user

```yaml
spec:
  accessString: "on >password +@read"
```

### Restrict to specific keys

```yaml
spec:
  accessString: "on >password ~cache:* +get +set"
```

### Disable a user temporarily

```yaml
spec:
  accessString: "off"  # User cannot authenticate
```

## Additional Resources

- **ACL management:** [MemoryDBACL](./memorydbackl.md)
- **Cluster configuration:** [MemoryDBCluster](./memorydbcluster.md)
- **Governance policies:** [MemoryDBConfig](./memorydbconfig.md)
- **AWS ACL and user documentation:** [MemoryDB Access Control](https://docs.aws.amazon.com/memorydb/latest/devguide/acls.html)
- **Redis ACL syntax:** [Redis ACL Reference](https://redis.io/docs/management/acl/)
