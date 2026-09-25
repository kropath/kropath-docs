---
title: EFSAccessPoint — Application-Level Isolation on Shared Storage
description: "The `EFSAccessPoint` resource provides application-level isolation on a shared EFS file system through POSIX user identity enforcement and root directory scoping."
doc_type: reference
---
# EFSAccessPoint — Application-Level Isolation on Shared Storage

The `EFSAccessPoint` resource provides application-level isolation on a shared EFS file system through POSIX user identity enforcement and root directory scoping. Multiple access points can reference the same file system, each presenting a different view with different user contexts and directory limits.

## Core Concepts

Access points solve the problem of safely sharing a single file system across multiple applications with different security and isolation requirements:

- **POSIX User Identity** — All clients mounting through an access point operate as a specific UID/GID, regardless of who mounts it.
- **Root Directory Scoping** — Clients see only a subtree of the file system (e.g., `/app-data`), preventing access to other applications' data.
- **Automatic Directory Creation** — Optionally create missing directories with specified ownership and permissions on first mount.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `EFSConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior when the EFSAccessPoint resource is deleted: `"retain"` or `"delete"` |

### File System Reference (Required; Immutable)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `fileSystemRef` | string | `""` | Name of a sibling `EFSFileSystem` CR in the same namespace; mutually exclusive with `fileSystemId` |
| `fileSystemId` | string | `""` | Direct AWS EFS file system ID for pre-existing file systems not managed by kropath; mutually exclusive with `fileSystemRef` |

Exactly one must be set.

### POSIX User Override (Optional; Immutable)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `posixUser` | object | omitted | POSIX user context for this access point |
| `posixUser.uid` | integer | required | POSIX user ID (0 = root is valid) |
| `posixUser.gid` | integer | required | POSIX group ID (0 = root is valid) |
| `posixUser.secondaryGIDs` | array<integer> | optional | Additional POSIX group IDs for this user |

### Root Directory Scoping (Optional; Immutable)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `rootDirectory` | object | omitted | Scope access to a subdirectory of the file system |
| `rootDirectory.path` | string | `"/"` | Directory path exposed to NFS clients (e.g., `/app-data`) |
| `rootDirectory.creationInfo` | object | optional | Auto-create the directory if it doesn't exist |
| `rootDirectory.creationInfo.ownerUID` | integer | required | UID for directory ownership |
| `rootDirectory.creationInfo.ownerGID` | integer | required | GID for directory ownership |
| `rootDirectory.creationInfo.permissions` | string | required | POSIX permissions (e.g., `"755"`, `"770"`) |

### Metadata and Tags (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## File System References

### Using a Kropath-Managed File System (Recommended)

```yaml
spec:
  fileSystemRef: my-shared-storage
  fileSystemId: ""
```

The access point looks up the sibling `EFSFileSystem` CR named `my-shared-storage` and retrieves its AWS file system ID. This approach is recommended for file systems managed by kropath.

### Using a Pre-Existing File System

```yaml
spec:
  fileSystemRef: ""
  fileSystemId: fs-0123456789abcdef0
```

The access point uses the AWS file system ID directly. This is useful for file systems created outside of kropath or in another cluster.

**Important:** You must specify **exactly one** of `fileSystemRef` or `fileSystemId`; they are mutually exclusive.

## POSIX User Identity

### Default (No POSIX Override)

```yaml
spec:
  posixUser: {}  # Omitted
```

Clients mounting through this access point use their own credentials (as passed by the NFS client or Kubernetes). This is useful when you want to preserve user identity.

### Enforced User Identity

```yaml
spec:
  posixUser:
    uid: 1000
    gid: 1000
```

All clients mounting through this access point operate as UID 1000, GID 1000, regardless of who initiated the mount. Useful for containerized applications that need a consistent user context.

### Root User Access Point

```yaml
spec:
  posixUser:
    uid: 0
    gid: 0
    secondaryGIDs: [100, 200]
```

Access point operates as root (UID 0) with supplementary groups. UID/GID 0 is valid for access points (unlike many Kubernetes securityContexts that restrict root).

### Secondary Groups

```yaml
spec:
  posixUser:
    uid: 1000
    gid: 1000
    secondaryGIDs: [1001, 1002, 1003]  # Additional group memberships
```

The user is a member of the specified secondary groups, useful for controlling access to shared resources.

## Root Directory Scoping

### Default (File System Root)

```yaml
spec:
  rootDirectory: {}  # Omitted
```

Clients see the entire file system (starting at `/`). No directory isolation.

### Fixed Existing Directory

```yaml
spec:
  rootDirectory:
    path: /app-data
```

Clients see only the `/app-data` subtree. If the directory doesn't exist, mounting fails (AWS returns an error).

### Auto-Create Directory

```yaml
spec:
  rootDirectory:
    path: /app-data
    creationInfo:
      ownerUID: 1000
      ownerGID: 1000
      permissions: "755"
```

If `/app-data` doesn't exist, AWS creates it automatically with the specified ownership and permissions (before first client mounts). This is useful for provisioning per-application directories on first use.

### Permission Examples

| Permissions | Meaning | Use Case |
|---|---|---|
| `"700"` | rwx------ (owner only) | Private application data |
| `"755"` | rwxr-xr-x (owner read/write, others read-only) | Shared read-only data |
| `"770"` | rwxrwx--- (owner and group read/write) | Shared team data |
| `"777"` | rwxrwxrwx (everyone) | Temporary scratch space |

## Complete Examples

### Example 1: Isolated Application Data

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSFileSystem
metadata:
  name: shared-storage
  namespace: apps
spec:
  configRef: general-policy
  encrypted: true
  backupEnabled: true
---
apiVersion: aws.kropath.run/v1alpha1
kind: EFSAccessPoint
metadata:
  name: app-a-access
  namespace: apps
spec:
  fileSystemRef: shared-storage
  posixUser:
    uid: 1000
    gid: 1000
  rootDirectory:
    path: /app-a
    creationInfo:
      ownerUID: 1000
      ownerGID: 1000
      permissions: "700"
  tags:
    application: app-a
    team: backend
---
apiVersion: aws.kropath.run/v1alpha1
kind: EFSAccessPoint
metadata:
  name: app-b-access
  namespace: apps
spec:
  fileSystemRef: shared-storage
  posixUser:
    uid: 1001
    gid: 1001
  rootDirectory:
    path: /app-b
    creationInfo:
      ownerUID: 1001
      ownerGID: 1001
      permissions: "700"
  tags:
    application: app-b
    team: backend
```

Result:

- Single shared file system (`shared-storage`)
- Two access points provide isolation: `app-a` sees only `/app-a` and operates as UID 1000; `app-b` sees only `/app-b` and operates as UID 1001
- Each application's data is protected from the other

### Example 2: Pre-Existing File System

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSAccessPoint
metadata:
  name: legacy-app-access
  namespace: legacy
spec:
  fileSystemId: fs-0123456789abcdef0  # Pre-existing AWS file system
  rootDirectory:
    path: /legacy-app
```

Result:

- Access point references a file system not managed by kropath
- Clients see only `/legacy-app`

### Example 3: Shared Read-Only Data

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSAccessPoint
metadata:
  name: shared-datasets
  namespace: data
spec:
  fileSystemRef: data-storage
  rootDirectory:
    path: /shared-datasets
    creationInfo:
      ownerUID: 0
      ownerGID: 0
      permissions: "755"
  tags:
    purpose: shared-read-only
    data-class: internal
```

Result:

- Multiple applications can mount this access point to access shared read-only datasets
- Directory is created with world-readable permissions

## Status Fields

After creation, check status for AWS resource identifiers:

```bash
kubectl get efsaccesspoint app-a-access -n apps -o yaml
```

| Status Field | Example | Purpose |
|---|---|---|
| `status.accessPointId` | `fsap-0123456789abcdef0` | AWS access point ID (system-assigned) |
| `status.accessPointArn` | `arn:aws:elasticfilesystem:...` | Full ARN of the access point |
| `status.lifeCycleState` | `available` | Lifecycle state (`creating`, `available`, `updating`, `deleting`, `deleted`, `error`) |

## Immutability Constraints

These fields **cannot be changed after access point creation** and require deletion and recreation:

- **`fileSystemRef`** — File system reference is locked
- **`fileSystemId`** — Direct file system ID is locked
- **`posixUser`** — POSIX user cannot be changed
- **`rootDirectory`** — Root directory path and creation info cannot be changed

Attempting to update these fields will result in a validation error:

```bash
$ kubectl patch efsaccesspoint app-a-access --patch '{"spec":{"posixUser":{"uid":2000}}}'
# Error: posixUser is immutable after creation
```

**To change these settings:** Delete and recreate the access point. Existing mounts will break and must reconnect; ensure clients can handle reconnection.

## Deletion and Cleanup

### Retain (Default)

```yaml
spec:
  deletionPolicy: retain
```

When the `EFSAccessPoint` CR is deleted, the AWS access point is **preserved**. You must manually delete it via AWS console/CLI if needed. Safe for production.

### Delete

```yaml
spec:
  deletionPolicy: delete
```

When the `EFSAccessPoint` CR is deleted, the AWS access point is **immediately deleted**. Use only in dev/test environments.

## Governance

Access points inherit tag/label/annotation governance from `EFSConfig` via the same cascade as file systems. No access-point-specific governance fields exist.

Platform teams can enforce tagging/syncing requirements via `EFSConfig.mandatory.tags`, `EFSConfig.mandatory.syncedLabels`, etc.

## Integration with Kubernetes RBAC

Access points are perfect for multi-tenant Kubernetes clusters:

1. Namespace A uses `EFSAccessPoint` with `posixUser: uid: 1000`
2. Namespace B uses `EFSAccessPoint` with `posixUser: uid: 1001`
3. Both mount the same file system but see different user contexts and directory trees
4. Kubernetes RBAC ensures Namespace A cannot modify Namespace B's access point

## Cross-Provider Notes

Access points are an AWS EFS-specific feature. Other providers have different isolation mechanisms:

- **GCP Filestore** — Does not have access points; relies on NFS export paths and firewall rules for isolation.
- **Azure Files** — Uses SMB/NFS shares at the share level; no per-mount POSIX user override.

## Related Topics

- [EFSFileSystem](efsfilesystem.md) — Creating and managing shared file systems
- [EFSMountTarget](efsmounttarget.md) — Network connectivity for NFS clients
- [EFS Overview](index.md) — Architecture and governance
