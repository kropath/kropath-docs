---
title: S3FilesFileSystem
description: "`S3FilesFileSystem` is a Kubernetes resource that represents a managed file system interface backed by an S3 bucket — providing NFS/SMB-compatible access to S3 data."
doc_type: reference
---
# S3FilesFileSystem

`S3FilesFileSystem` is a Kubernetes resource that represents a managed file system interface backed by an S3 bucket — providing NFS/SMB-compatible access to S3 data. S3 Files enables workloads that require POSIX file semantics (directories, permissions, locking) to work with S3 object storage.

## Scope

This resource is AWS-only. It wraps the ACK `FileSystem` resource from the S3 Files service. GCP's Cloud Storage FUSE provides client-side mounting; Azure Blob NFS is configured on storage accounts differently.

## What it solves

When working with S3 via NFS/SMB, you need to:

- **Mount S3 buckets** — provide POSIX file system access to S3 data
- **Set encryption** — protect data in transit and at rest
- **Manage IAM roles** — grant file system read/write permissions
- **Configure prefixes** — scope access to a prefix within a bucket
- **Set import/expiration rules** — control data lifecycle
- **Apply governance** — inherit encryption and tagging from platform policies
- **Track status** — know when the file system is ready and its ID

`S3FilesFileSystem` streamlines this by providing:

- **Simple YAML spec** — define a file system with bucket, role, and encryption settings
- **Governance integration** — inherit encryption from an `S3AdvancedConfig` profile
- **Cross-reference support** — reference S3 buckets and IAM roles by CR name or ARN
- **Prefix scoping** — optionally restrict access to a bucket prefix
- **Status visibility** — track file system readiness and configuration

## Core concepts

### Naming exemption (KRO-236)

**Important:** S3 Files file systems have no cloud-side name field. They are identified by a system-assigned `fileSystemID` (e.g., `fs-1234567890abcdef0`). Unlike other resources, `S3FilesFileSystem` CRs do NOT include `spec.nameOverride`, `status.resourceName`, or naming templates. The cloud identity is the file system ID only.

### Bucket and prefix

A file system mounts an S3 bucket (optionally scoped to a prefix):

```yaml
spec:
  # Reference by CR name (resolves to ARN)
  bucketRef: my-data-bucket
  
  # Optional: scope to a prefix (e.g., /analytics/data/)
  prefix: "/analytics/data/"
```

If you specify a prefix, the file system access is limited to objects under that prefix.

### Encryption

File systems support encryption using KMS:

```yaml
spec:
  # AWS-managed encryption (default)
  kmsKeyID: ""  # Service-managed key
  
  # OR customer-managed encryption
  kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

Encryption is optional but recommended for sensitive data.

### IAM role

A file system requires an IAM role granting read/write access to the S3 bucket:

```yaml
spec:
  # Reference by CR name (resolves to ARN)
  roleRef: s3-files-role
```

The role must have `s3:GetObject`, `s3:PutObject`, and `s3:ListBucket` permissions on the target bucket.

### Data import and expiration

Optional rules control data lifecycle:

```yaml
spec:
  importDataRules:
    - prefix: "/logs/"
      sizeLessThan: 1000000000  # 1 GB
      trigger: "OnDemand"       # Import on access
  
  expirationDataRules:
    - daysAfterLastAccess: 90   # Delete files after 90 days of no access
```

## Complete example

Here's a file system for data scientists accessing a shared analytics bucket:

```yaml
---
# First, ensure the IAM role exists (typically created outside kropath)
# The role should grant s3:GetObject, s3:PutObject, and s3:ListBucket
# on the target bucket

# Create the file system
apiVersion: aws.kropath.run/v1alpha1
kind: S3FilesFileSystem
metadata:
  name: analytics-fs
  namespace: data-science
spec:
  # Use the compliance profile for encryption
  configRef: compliance
  
  # Reference the backing S3 bucket
  bucketRef: shared-analytics-bucket
  
  # Optional: scope to a prefix
  prefix: "/datasets/"
  
  # Encryption: inherited from profile or overridden here
  kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  
  # Reference the IAM role allowing S3 access
  roleRef: analytics-role
  
  # Optional: acknowledge bucket configuration warnings
  acceptBucketWarning: true
  
  # Data expiration: remove files after 180 days of no access
  expirationDataRules:
    - daysAfterLastAccess: 180
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    team: data-science
    purpose: analytics
  
  # Labels to sync to cloud
  syncedLabels:
    environment: production
```

After creation, mount the file system on EC2 or containerized workloads using the NFS mount point (available in status).

## Mounting from EC2 or containers

Once the file system is ready, mount it via NFS:

```bash
# Get the file system's mount target information
kubectl get s3filesfilesystem analytics-fs -o jsonpath='{.status.nfsEndpoint}'

# Mount via NFS from EC2 or container
mount -t nfs <nfs-endpoint> /mnt/data
```

POSIX file semantics (permissions, directories, locking) are fully supported.

## Tags format

Unlike most resources, S3Files file systems tags are stored as an array in the ACK CRD:

```yaml
tags:
  - key: team
    value: data-science
  - key: purpose
    value: analytics
```

However, the kropath CR spec accepts tags as a map (like all other resources). The RGD automatically transforms the map to an array for the ACK CRD.

## Cross-references

File systems reference:
- `S3Bucket` from the S3 family (via `bucketRef` or bucket ARN)
- `IAMRole` from the IAM family (via `roleRef` or role ARN)
- `S3AdvancedConfig` profiles (via `spec.configRef`)
- KMS keys (via `kmsKeyID` or `kmsKeyRef`)

File systems are referenced by:
- `S3FilesAccessPoint` resources (via `fileSystemRef` or file system ID)
- `S3FilesMountTarget` resources (via `fileSystemRef` or file system ID)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3FilesFileSystem`
- **Scope**: Namespaced

## Note: Naming exemption (KRO-236)

S3Files resources (`S3FilesFileSystem`, `S3FilesAccessPoint`, `S3FilesMountTarget`) do not support the standard naming convention because they are identified by system-assigned IDs (fileSystemID, accessPointID, mountTargetID) rather than names. These CRs do not include naming-related fields (`spec.nameOverride`, `status.resourceName`, `status.namingStatus`).
