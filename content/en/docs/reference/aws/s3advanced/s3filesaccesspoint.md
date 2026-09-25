---
title: S3FilesAccessPoint
description: "`S3FilesAccessPoint` is a Kubernetes resource that represents a user-scoped access point for an S3 Files file system."
doc_type: reference
---
# S3FilesAccessPoint

`S3FilesAccessPoint` is a Kubernetes resource that represents a user-scoped access point for an S3 Files file system. Access points provide POSIX user identity enforcement and root directory scoping for multi-tenant file system access.

## Scope

This resource is AWS-only. It provides fine-grained access control for S3 Files file systems.

## What it solves

Multi-tenant file systems need:

- **User identity** — enforce POSIX user/group IDs (uid/gid) for access
- **Root directory scoping** — restrict users to a subdirectory
- **Permission enforcement** — control read/write/execute on created objects
- **Secondary groups** — support POSIX group membership

## Naming exemption (KRO-236)

Like `S3FilesFileSystem`, S3Files access points are identified by system-assigned IDs, not names. The CR does not include naming-related fields.

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3FilesAccessPoint
metadata:
  name: analytics-user-ap
  namespace: data-science
spec:
  # Reference the parent file system
  fileSystemRef: analytics-fs
  
  # POSIX user identity
  posixUser:
    uid: 1001
    gid: 1001
    secondaryGIDs:
      - 1002
      - 1003
  
  # Root directory for this user
  rootDirectory:
    path: "/user/analyst1/"
    creationPermissions:
      ownerUID: 1001
      ownerGID: 1001
      permissions: "755"
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    user: analyst1
    team: data-science
```

Access point creation requires the parent file system to exist first.

## Cross-references

Access points reference:
- `S3FilesFileSystem` resources (via `fileSystemRef` or file system ID)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3FilesAccessPoint`
- **Scope**: Namespaced
