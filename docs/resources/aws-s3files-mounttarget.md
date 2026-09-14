# S3FilesMountTarget

`S3FilesMountTarget` is a Kubernetes resource that represents a mount target exposing an S3 Files file system in a VPC subnet. Mount targets enable NFS-compatible access from EC2 instances or containers within the VPC.

## Scope

This resource is AWS-only. It provides VPC integration for S3 Files file systems.

## What it solves

S3 Files file systems need VPC endpoints:

- **Subnet placement** — mount the file system in a specific VPC subnet
- **Security groups** — restrict access via security group rules
- **IP addressing** — optionally assign specific IPv4/IPv6 addresses
- **Multi-AZ mounting** — support failover via multiple mount targets

## Naming exemption (KRO-236)

S3Files mount targets are identified by system-assigned mount target IDs, not names.

## Complete example

```yaml
---
# Create a mount target for the file system
apiVersion: aws.kropath.run/v1alpha1
kind: S3FilesMountTarget
metadata:
  name: analytics-mt-1a
  namespace: data-science
spec:
  # Reference the parent file system
  fileSystemRef: analytics-fs
  
  # VPC subnet for the mount target
  subnetRef: subnet-analytics-1a
  
  # Security groups controlling access
  securityGroupRefs:
    - sg-analytics-nfs
  
  # IP address type
  ipAddressType: IPV4_ONLY
  
  # Optional: specific IPv4 address (auto-assigned if omitted)
  ipv4Address: ""
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    zone: us-east-1a
    purpose: analytics
```

For multi-AZ resilience, create multiple mount targets in different subnets:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: S3FilesMountTarget
metadata:
  name: analytics-mt-1b
  namespace: data-science
spec:
  fileSystemRef: analytics-fs
  subnetRef: subnet-analytics-1b
  securityGroupRefs:
    - sg-analytics-nfs
  deletionPolicy: retain
```

## Mount targets and security

Security groups control which EC2 instances can access the NFS endpoint:

```yaml
# Example security group rule (created outside kropath)
# Allows port 2049 (NFS) from application servers
ingress:
  - protocol: tcp
    port: 2049
    sourceSecurityGroup: sg-app-servers
```

## Accessing the file system

EC2 instances in the VPC can mount the file system:

```bash
# Get the mount target's IP/DNS
MOUNT_IP=$(kubectl get s3filesmounttarget analytics-mt-1a \
  -o jsonpath='{.status.mountTargetIP}')

# Mount via NFS
mount -t nfs $MOUNT_IP:/data /mnt/data
```

## Cross-references

Mount targets reference:
- `S3FilesFileSystem` resources (via `fileSystemRef` or file system ID)
- VPC subnets (via `subnetRef` or subnet ID)
- Security groups (via `securityGroupRefs` or security group IDs)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3FilesMountTarget`
- **Scope**: Namespaced
