# EFSMountTarget — Network Connectivity for NFS Access

The `EFSMountTarget` resource provides network connectivity to an EFS file system by creating an Elastic Network Interface (ENI) in a specific VPC subnet. NFS clients mount through mount targets to access the file system. AWS enforces **one mount target per availability zone per file system**.

## Core Concepts

- **ENI Creation** — Each mount target is an elastic network interface with a private IP address in your VPC subnet.
- **Subnet Scoping** — Mount targets are created in specific subnets, enabling clients in those subnets to access the file system.
- **AZ Isolation** — AWS limits one mount target per AZ per file system. For multi-AZ resilience, create mount targets in each AZ.
- **Security Groups** — Control network access to the mount target via security groups (up to 5 per mount target).

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `EFSConfig` governance profile to apply (for tags/labels only) |
| `deletionPolicy` | string | `"retain"` | Behavior when the EFSMountTarget resource is deleted: `"retain"` or `"delete"` |

### File System Reference (Required)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `fileSystemRef` | string | `""` | Name of a sibling `EFSFileSystem` CR in the same namespace; mutually exclusive with `fileSystemId` |
| `fileSystemId` | string | `""` | Direct AWS EFS file system ID for pre-existing file systems not managed by kropath; mutually exclusive with `fileSystemRef` |

Exactly one must be set.

### Network Configuration (Required)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `subnetId` | string | required | VPC subnet ID where the mount target ENI will be placed (e.g., `"subnet-0a1b2c3d"`) |
| `ipAddress` | string | `""` | Fixed private IPv4 address within the subnet's CIDR range; `""` = AWS auto-assigns |
| `securityGroupIds` | array<string> | optional | Up to 5 VPC security group IDs for network access control; empty = VPC default security group |

### Metadata and Tags (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags (reserved for future use; not currently passed to mount targets by AWS) |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

**Note:** AWS EFS does not currently support direct tagging of mount targets. Tags are inherited from the parent file system. The `spec.tags` field is reserved for forward compatibility if AWS adds mount target tagging in the future.

## File System References

### Using a Kropath-Managed File System (Recommended)

```yaml
spec:
  fileSystemRef: my-shared-storage
  fileSystemId: ""
```

The mount target looks up the sibling `EFSFileSystem` CR and retrieves its AWS file system ID. Recommended for file systems managed by kropath.

### Using a Pre-Existing File System

```yaml
spec:
  fileSystemRef: ""
  fileSystemId: fs-0123456789abcdef0
```

The mount target uses the AWS file system ID directly. Useful for file systems created outside of kropath or in another cluster.

**Important:** Exactly one of `fileSystemRef` or `fileSystemId` must be set.

## Network Configuration

### Subnet ID (Required)

```yaml
spec:
  subnetId: subnet-0a1b2c3d
```

Specifies the VPC subnet where the mount target ENI will be created. This is **required** and determines the availability zone and CIDR range for the ENI.

### IP Address Assignment

#### Auto-Assigned (Default)

```yaml
spec:
  ipAddress: ""
```

AWS automatically assigns a private IP address from the subnet's CIDR range. Recommended for most use cases as it avoids manual IP management.

#### Fixed IP Address

```yaml
spec:
  ipAddress: 10.0.1.50
```

Specifies a fixed private IPv4 address within the subnet's CIDR range. Useful if you need a predictable IP (e.g., for DNS records, firewall rules, or static route configuration).

**Important:** The IP must:

- Fall within the subnet's CIDR range
- Not already be in use by another ENI
- Not be a reserved address (network address, broadcast, AWS gateway, etc.)

### Security Groups

#### Default Security Group (Default)

```yaml
spec:
  securityGroupIds: []  # Empty
```

Uses the VPC's default security group for network access control. Simplest option but less restrictive.

#### Custom Security Groups

```yaml
spec:
  securityGroupIds:
    - sg-0987654321abcdef0  # Allow NFS clients
    - sg-1234567890abcdef1  # Allow monitoring
```

Specifies up to 5 security groups for fine-grained network access control. Recommended for production to restrict access to authorized clients.

**Security Group Rules for NFS:**

Inbound rules on your mount target security group must allow:

- **Protocol:** TCP and UDP
- **Port:** 2049 (NFS)
- **Source:** Security group(s) of your NFS clients (EC2, ECS, EKS, etc.)

Example for ECS/EKS:

```
Inbound Rule:
  Protocol: TCP
  Port: 2049
  Source: <security group ID of ECS task/EKS pod>
```

## Complete Examples

### Example 1: Multi-AZ File System with Mount Targets

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSFileSystem
metadata:
  name: app-storage
  namespace: apps
spec:
  configRef: general-policy
  encrypted: true
  backupEnabled: true
---
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: mount-target-us-east-1a
  namespace: apps
spec:
  fileSystemRef: app-storage
  subnetId: subnet-abc123  # us-east-1a
  securityGroupIds:
    - sg-ecs-clients
---
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: mount-target-us-east-1b
  namespace: apps
spec:
  fileSystemRef: app-storage
  subnetId: subnet-def456  # us-east-1b
  securityGroupIds:
    - sg-ecs-clients
---
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: mount-target-us-east-1c
  namespace: apps
spec:
  fileSystemRef: app-storage
  subnetId: subnet-ghi789  # us-east-1c
  securityGroupIds:
    - sg-ecs-clients
```

Result:

- Single file system with three mount targets, one in each AZ
- ECS tasks in any AZ can mount the file system through the nearest mount target
- High resilience: file system remains accessible even if one AZ experiences an outage

### Example 2: Fixed IP for DNS Registration

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: mount-target-dns
  namespace: storage
spec:
  fileSystemRef: shared-storage
  subnetId: subnet-private-1
  ipAddress: 10.0.1.100       # Fixed IP for DNS
  securityGroupIds:
    - sg-nfs-access
  tags:
    purpose: dns-registered
```

Result:

- Mount target has a predictable IP (10.0.1.100)
- You can register this IP in internal DNS (`nfs.internal.example.com`)
- Clients can mount using the DNS name instead of managing changing IPs

### Example 3: Pre-Existing File System

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: legacy-mount-target
  namespace: legacy
spec:
  fileSystemId: fs-0123456789abcdef0  # Pre-existing AWS file system
  subnetId: subnet-legacy
  securityGroupIds:
    - sg-legacy-access
```

Result:

- Mount target for a file system not managed by kropath
- Useful for integrating with legacy infrastructure

## Status Fields

After creation, check status for AWS resource identifiers:

```bash
kubectl get efsmounttarget mount-target-us-east-1a -n apps -o yaml
```

| Status Field | Example | Purpose |
|---|---|---|
| `status.mountTargetId` | `fsmt-0123456789abcdef0` | AWS mount target ID (system-assigned) |
| `status.networkInterfaceId` | `eni-0987654321abcdef0` | ENI ID created for this mount target |
| `status.ipAddress` | `10.0.1.50` | Assigned private IPv4 address |
| `status.availabilityZoneId` | `use1-az1` | AWS AZ ID |
| `status.availabilityZoneName` | `us-east-1a` | Human-readable AZ name |
| `status.lifeCycleState` | `available` | Lifecycle state (`creating`, `available`, `updating`, `deleting`, `deleted`, `error`) |

## Deletion and Cleanup

### Retain (Default)

```yaml
spec:
  deletionPolicy: retain
```

When the `EFSMountTarget` CR is deleted, the AWS mount target is **preserved**. You must manually delete it via AWS console/CLI if needed. Safe for production.

### Delete

```yaml
spec:
  deletionPolicy: delete
```

When the `EFSMountTarget` CR is deleted, the AWS mount target is **immediately deleted**. Clients using this mount target will lose connectivity. Use only in dev/test environments or when you plan to recreate the mount target immediately.

## Mount Target Limitations

### One Per AZ Per File System

AWS enforces **one mount target per availability zone per file system**. Attempting to create a second mount target in the same AZ will fail with an AWS API error:

```
Error: Mount target already exists in Availability Zone
```

To add capacity in an AZ, modify the existing mount target's security groups or subnet configuration instead of creating a new one. For multi-AZ resilience, create mount targets in different AZs.

### Tag Limitation (G-5)

AWS EFS does not currently support direct tagging of mount targets. Tags on `EFSMountTarget` resources are inherited from the parent file system. The `spec.tags` field is reserved for future use.

Kubernetes metadata (`metadata.labels`, `metadata.annotations`) is still applied to the kropath-managed ACK MountTarget CR and can be used for K8s-level observability and RBAC.

## Network Isolation and Security

### VPC Endpoint ENI

Mount target ENIs behave like any other VPC ENI:

- They have a private IP address within the subnet's CIDR range
- They respect VPC security groups for inbound/outbound rules
- They do not have public IPs (access is via private IP only)
- They are subject to VPC Network ACLs

### NFS Security Considerations

1. **Firewall Rules:** Ensure your security groups allow NFS traffic (port 2049, TCP/UDP) from authorized clients only.

2. **Encrypt in Transit:** Consider using TLS-wrapped NFS or VPN for sensitive data crossing untrusted networks. EFS supports NFS security labels for additional granularity.

3. **Client Authentication:** EFS does not natively support authentication; rely on VPC security groups and IAM policies to restrict mount target access.

4. **Monitoring:** Monitor access via CloudWatch metrics and VPC Flow Logs to detect unusual activity.

## Governance

Mount targets inherit tag/label/annotation governance from `EFSConfig` via the same cascade as file systems.

Platform teams can enforce tagging requirements via `EFSConfig.mandatory.tags`, `EFSConfig.mandatory.syncedLabels`, etc.

## Cross-Provider Notes

Mount targets are an AWS EFS-specific concept. Other providers have different network connectivity models:

- **GCP Filestore** — Endpoints are created implicitly when a Filestore instance is provisioned; no separate ENI management.
- **Azure Files** — Private Endpoints are separate Azure resources with their own lifecycle and configuration.

## Related Topics

- [EFSFileSystem](efsfilesystem.md) — Creating and managing shared file systems
- [EFSAccessPoint](efsaccesspoint.md) — Application-level isolation with POSIX users
- [EFS Overview](index.md) — Architecture and governance
- [AWS Documentation: EFS Mount Targets](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs.html) — Official AWS guide
