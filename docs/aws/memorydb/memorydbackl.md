# MemoryDBACL — Access Control and User Groups

The `MemoryDBACL` resource represents an access control list (ACL) — a named group of `MemoryDBUser` resources that can be attached to a MemoryDB cluster for authentication and authorization.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `MemoryDBConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses naming template; sets ACL name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` (keep AWS resources) or `"delete"` (remove them) |

### ACL Membership

| Field | Type | Default | Purpose |
|---|---|---|---|
| `userNames` | array | [] | List of `MemoryDBUser` resource names to add to this ACL |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | {} | AWS tags; merged with governance tags |
| `syncedLabels` | map | {} | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Complete Example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: production-acl
  namespace: cache-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  
  # User membership
  userNames:
    - appuser
    - readonly-user
    - admin-user
  
  # Metadata
  tags:
    service: cache
    environment: production
  syncedLabels:
    team: platform
```

## Empty ACL (No Users Initially)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: staging-acl
  namespace: cache-staging
spec:
  # userNames omitted — creates ACL with no users yet
  # Can add users later by updating this list
```

## How ACLs and Users Work Together

1. **Create users** with `MemoryDBUser` resources:
   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: MemoryDBUser
   metadata:
     name: appuser
     namespace: cache-prod
   spec:
     type: password
     accessString: "on >password +@all"
     passwords:
       - secretName: appuser-pwd
         key: password
   ```

2. **Group users into an ACL**:
   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: MemoryDBACL
   metadata:
     name: production-acl
     namespace: cache-prod
   spec:
     userNames:
       - appuser
   ```

3. **Attach ACL to a cluster**:
   ```yaml
   apiVersion: aws.kropath.run/v1alpha1
   kind: MemoryDBCluster
   metadata:
     name: session-store
     namespace: cache-prod
   spec:
     aclName: production-acl
     # ... other cluster fields
   ```

Now, users in the ACL can authenticate to the cluster.

## Status Fields

After creation:

```yaml
status:
  resourceName: "cache-prod-production-acl"     # effectiveName
  namingStatus: "valid"                         # "valid" | "invalid-unresolved-tokens"
  predictedArn: "arn:aws:memorydb:ap-southeast-2:123456789012:acl/cache-prod-production-acl"
  aclStatus: "active"                           # creating | active | modifying | deleting
  conditions:
    - type: Ready
      status: "True"
      message: "ACL is ready"
```

## Governance

`MemoryDBACL` has **no functional governance fields** beyond tags, labels, and naming. Platform teams do not enforce which users belong to which ACL — that is a per-environment decision.

Governance fields available:
- **tags** / **syncedLabels** / **syncedAnnotations** — Metadata governance (shared with all MemoryDB resources)
- **namingTemplate** — Naming convention (shared with all MemoryDB resources)

See [MemoryDBConfig governance](./memorydbconfig.md) for full governance cascade details.

## Naming Template

ACL names are generated via the governance naming template:

```yaml
# Default: "{namespace}-{name}"
# With namespace=cache-prod, name=production-acl
# Result: cache-prod-production-acl

# Custom template: "acl-{namespace}-{tag.env}"
# With tag.env=prod
# Result: acl-cache-prod-prod
```

See [Naming Template — Dynamic Tags](../resources/naming-template-dynamic-tags.md) for full syntax.

**AWS constraints:** Starts with letter, alphanumeric + hyphens, regex `^[a-zA-Z][a-zA-Z0-9\-]*$`.

## Update and Delete

### Add/Remove Users

To modify ACL membership, update the `userNames` list:

```yaml
spec:
  userNames:
    - appuser
    - readonly-user
    - admin-user
    - newuser          # Add new user
    # Removed: second-user (was here, now removed)
```

Push the update — users in the new list are added, users no longer in the list are removed from the ACL.

### Delete ACL

By default, ACLs are retained when the Kubernetes CR is deleted:

```yaml
spec:
  deletionPolicy: retain  # AWS ACL stays
```

To delete the AWS ACL when the CR is deleted:

```yaml
spec:
  deletionPolicy: delete
```

**Warning:** If a cluster is attached to this ACL, the cluster must be updated to reference a different ACL before the ACL can be deleted.

## Tagging and Labels

ACLs inherit tags from governance:

```yaml
# MemoryDBConfig/general-policy
spec:
  mandatory:
    tags:
      service: memorydb
      compliance: pci-dss
  defaults:
    tags:
      team: platform

# MemoryDBACL instance
spec:
  tags:
    environment: production

# Result in ACK ACL spec.tags (after merge):
#   service: memorydb (mandatory)
#   compliance: pci-dss (mandatory)
#   team: platform (defaults)
#   environment: production (instance)
```

Synced labels are also propagated to K8s labels and AWS tags:

```yaml
spec:
  syncedLabels:
    data-class: confidential

# Result in ACK ACL:
#   K8s label: aws.kropath.run/data-class: confidential
#   AWS tag: aws.kropath.run/data-class: confidential
```

## AWS Default ACL

If a cluster does not specify an ACL (`aclName` empty), AWS uses the built-in `"open-access"` ACL, which allows:
- The default user to authenticate with any password
- Full Redis command access

**For production, always create and attach a named ACL** with specific users and access policies.

## Example: Multi-Tier ACLs

```yaml
---
# Read-write users (application)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: app-acl
  namespace: cache-prod
spec:
  userNames:
    - app-rw-user

---
# Read-only users (monitoring/analytics)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: readonly-acl
  namespace: cache-prod
spec:
  userNames:
    - monitoring-user
    - analytics-user

---
# Admin users (operations)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: admin-acl
  namespace: cache-prod
spec:
  userNames:
    - admin-user

---
# Cluster using application ACL
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: session-store
  namespace: cache-prod
spec:
  aclName: app-acl
  # ... other fields

---
# Separate read-only cluster using readonly ACL (cost optimization)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: cache-replica
  namespace: cache-prod
spec:
  aclName: readonly-acl
  # ... other fields
```

## Common Tasks

### Create a minimal ACL

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBACL
metadata:
  name: basic-acl
  namespace: cache-prod
spec:
  userNames:
    - default-user
```

### Grant access to a new user

1. Create the user in `MemoryDBUser`
2. Add username to the ACL's `spec.userNames`
3. Push the update

### Revoke access

1. Remove the username from `spec.userNames`
2. Push the update
3. Optionally delete the `MemoryDBUser` resource (separate CR)

### Tag ACL for cost tracking

```yaml
spec:
  tags:
    cost-centre: engineering
    project: session-store
```

## Additional Resources

- **User management:** [MemoryDBUser](./memorydbuser.md)
- **Cluster configuration:** [MemoryDBCluster](./memorydbcluster.md)
- **Governance policies:** [MemoryDBConfig](./memorydbconfig.md)
- **AWS ACL documentation:** [MemoryDB ACLs](https://docs.aws.amazon.com/memorydb/latest/devguide/acls.html)
