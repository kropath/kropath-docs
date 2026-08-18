# MemoryDBUser — User Identity and Authentication

The `MemoryDBUser` resource represents a single user identity for MemoryDB cluster authentication. Users define access permissions (Redis commands, keys, channels) and authentication mode (password or IAM).

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets user name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### Authentication Type

| Field | Type | Default | Purpose |
|---|---|---|---|
| `type` | string | required | `"password"` or `"iam"` |

### Access Control

| Field | Type | Default | Purpose |
|---|---|---|---|
| `accessString` | string | required | Redis ACL string defining command/key/channel permissions (e.g. `"on >password +@all"`) |

### Password Authentication (type: password)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `passwords` | array | [] | List of Kubernetes Secrets containing user passwords (one entry per password rotation/history) |
| `passwords[].secretName` | string | required | Kubernetes Secret name containing the password |
| `passwords[].key` | string | required | Key within the Secret holding the password value |

### IAM Authentication (type: iam)

No additional fields; IAM authentication uses the AWS IAM role attached to the pod/IRSA.

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
  type: password
  deletionPolicy: retain
  
  # Redis access string: on (enabled), >password (password required), +@all (all commands)
  accessString: "on >password +@all"
  
  # Password secret reference(s)
  passwords:
    - secretName: appuser-password
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
  type: password
  
  # Read-only: allow GET and MGET on all keys, deny writes
  accessString: "on >password +@read"
  
  passwords:
    - secretName: readonly-password
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
  type: iam
  
  # IAM auth: pod identity (IRSA) is used instead of password
  accessString: "on ~* +@all"     # All commands on all keys via IAM
  
  # No passwords field — IAM role provides credentials
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
  type: password
  accessString: "on >password +@all"
  passwords:
    - secretName: myuser-pwd
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
     passwords:
       - secretName: myuser-pwd-old
         key: password
       - secretName: myuser-pwd-new  # New password added
         key: password
   ```

2. Applications gradually switch to the new password

3. Remove the old password from the list once all apps are switched:
   ```yaml
   spec:
     passwords:
       - secretName: myuser-pwd-new
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
  type: iam
  accessString: "on ~* +@all"
  # No passwords field
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
  type: password
  accessString: "on >password +@all"
  passwords:
    - secretName: app-user-pwd
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
  type: password
  accessString: "on >password +@read"
  passwords:
    - secretName: monitoring-pwd
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
  type: password
  accessString: "on >password +@all +@admin"
  passwords:
    - secretName: admin-pwd
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
  type: password
  accessString: "on >password +@all"
  passwords:
    - secretName: app-user-pwd
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
