# AWS EFS — Elastic File System

The AWS EFS family within kropath provides abstractions for managing Amazon EFS (Elastic File System), a managed, fully elastic, and highly available shared file storage service. It enables platform engineers to enforce organization-wide controls over encryption, performance modes, backup policies, and lifecycle tiering, while allowing application teams to provision and configure file systems for workloads like machine learning training, containerized applications, and big data processing.

## Overview

EFS is a managed NFS file system that scales elastically and supports concurrent access from multiple compute resources across availability zones. The kropath EFS family provides three resource types to manage the full lifecycle:

- **`EFSFileSystem`**: The core shared file system resource that manages storage configuration, encryption, performance modes, throughput settings, backup policies, and lifecycle tiering.
- **`EFSAccessPoint`**: Provides application-level isolation on a shared file system through POSIX user identity enforcement and root directory scoping.
- **`EFSMountTarget`**: Manages network connectivity to file systems by providing ENIs (Elastic Network Interfaces) in specific VPC subnets for NFS client access.

All three resources are governed through the **`EFSConfig`** CRD, which defines per-profile governance policies (encryption, performance mode, backup defaults, lifecycle transitions, and tag controls) that platform teams create and application teams select via `spec.configRef`.

## Prerequisites and Setup

EFS file systems require:

- **VPC and Subnets**: Mount targets are created in specific subnets within your VPC.
- **Security Groups**: Control network access to mount targets.
- **IAM**: No additional IAM roles are required for basic EFS operations (ACK handles service-linked role creation).

For advanced functionality, EFS integrates with:

- **KMS**: For encryption using customer-managed keys instead of AWS-managed keys.
- **IAM**: For backup and replication scenarios.
- **CloudWatch**: For monitoring file system performance and lifecycle transitions.

## Architecture

EFS follows a governance cascade pattern (ADR-010) where platform engineers define governance policies in `EFSConfig` CRs (one per profile: `general-policy`, `pci`, `hipaa`, etc.), and application teams create instances of `EFSFileSystem`, `EFSAccessPoint`, and `EFSMountTarget` that reference these profiles via `spec.configRef`.

The kropath controller pre-merges governance from `KropathConfig` (org-wide) and the referenced `EFSConfig` profile into `status.effectiveConfig` on the config CR. Resource RGDs read this merged config via `externalRef` and apply the resolved governance to the underlying AWS ACK resources.

## Configuration

### Governance: EFSConfig

Platform teams create and manage `EFSConfig` CRs with `spec.mandatory` and `spec.defaults` sections:

- **`mandatory`** — Fields set here enforce policies that cannot be overridden by instances (e.g., all file systems must be encrypted with a specific KMS key).
- **`defaults`** — Fields here provide baseline configurations that instances can override (e.g., elastic throughput by default, but instances can choose provisioned).

**Example Profiles:**

- `general-policy`: Conservative baseline (encrypted by default, elastic throughput, backups enabled).
- `pci`: Compliance profile (mandatory encryption with org KMS key, mandatory backups, replication protection enabled).
- `hipaa`: Healthcare compliance profile (similar to PCI, with additional lifecycle policies for data retention).

### Resource Instances

**`EFSFileSystem`** (the primary resource):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSFileSystem
metadata:
  name: my-shared-storage
  namespace: data-prod
spec:
  configRef: general-policy        # Governance profile reference
  deletionPolicy: retain           # retain | delete
  encrypted: true                  # or null to defer to governance
  performanceMode: generalPurpose  # generalPurpose | maxIO (immutable)
  throughputMode: elastic          # elastic | bursting | provisioned
  backupEnabled: true              # or null to defer to governance
  transitionToIA: AFTER_30_DAYS    # Lifecycle transition to IA
  tags:
    application: analytics
    environment: production
  syncedLabels:
    team: data-platform
    sensitivity: high
```

**`EFSAccessPoint`** (application-level isolation):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSAccessPoint
metadata:
  name: app-access-point
  namespace: data-prod
spec:
  fileSystemRef: my-shared-storage      # Reference to EFSFileSystem CR
  posixUser:
    uid: 1000
    gid: 1000
  rootDirectory:
    path: /app-data
    creationInfo:
      ownerUID: 1000
      ownerGID: 1000
      permissions: "755"
```

**`EFSMountTarget`** (network connectivity):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSMountTarget
metadata:
  name: mount-target-az1
  namespace: data-prod
spec:
  fileSystemRef: my-shared-storage    # Reference to EFSFileSystem CR
  subnetId: subnet-0a1b2c3d           # VPC subnet ID
  securityGroupIds:
    - sg-0987654321abcdef0
```

## Field Reference

### Governance Cascade

The EFS family uses a three-tier cascade for field resolution:

1. **`EFSConfig.mandatory.<field>`** — Enforced; instance cannot override
2. **`EFSFileSystem.spec.<field>`** — Instance-level override (if governance allows)
3. **`EFSConfig.defaults.<field>`** — Applied if instance leaves field unset

For example, if `EFSConfig.mandatory.encrypted: true`, all file systems are encrypted regardless of instance `spec.encrypted`. If only `defaults.encrypted: true`, instances can set `spec.encrypted: false` to opt out.

### Boolean Fields and Pointer Semantics

Fields like `encrypted` and `backupEnabled` use pointer semantics to distinguish "not set" from "explicitly false":

- **`nil` (unset)** — Defer to the next tier in the cascade
- **`false` (explicit)** — Opt-out; this value takes precedence
- **`true` (explicit)** — Opt-in; this value takes precedence

Only when a field is unset (nil) does the governance cascade apply.

### Immutable Fields

These fields cannot be changed after resource creation:

- **`EFSFileSystem.spec.performanceMode`** — Performance mode is immutable; replacement required for changes
- **`EFSAccessPoint.spec.fileSystemRef`** — File system reference is immutable
- **`EFSAccessPoint.spec.posixUser`** — POSIX user is immutable
- **`EFSAccessPoint.spec.rootDirectory`** — Root directory scoping is immutable

Changes to immutable fields require deleting and recreating the resource.

## Naming and Identity

Unlike many AWS resources, **EFS file systems, access points, and mount targets do not have provider-assigned names**. They are identified by system-assigned IDs:

- `EFSFileSystem`: `fs-` prefix (e.g., `fs-0123456789abcdef0`)
- `EFSAccessPoint`: `fsap-` prefix (e.g., `fsap-0123456789abcdef0`)
- `EFSMountTarget`: `fsmt-` prefix (e.g., `fsmt-0123456789abcdef0`)

The naming convention (templates and `spec.nameOverride`) does **not apply** to EFS resources. The CR's `metadata.name` is purely a Kubernetes identifier; the AWS identity is the system-assigned ID exposed in `status.fileSystemId`, `status.accessPointId`, or `status.mountTargetId`.

## Key Features

### Encryption

- **Encryption at Rest:** Managed by `encrypted` (true/false) and `kmsKeyId` (AWS-managed or customer-managed).
- **Encryption in Transit:** Not configurable via kropath; use NFS security labels or VPC security groups.
- **Governance:** Platform teams can enforce mandatory encryption and specific KMS keys via `EFSConfig.mandatory`.

### Performance and Throughput

- **Performance Mode** (immutable after creation):
  - `generalPurpose` (default) — Suitable for latency-sensitive use cases
  - `maxIO` — Optimized for high levels of aggregate throughput and operations per second (not available on One Zone file systems)

- **Throughput Mode:**
  - `bursting` (default) — Scales throughput based on file system size
  - `elastic` — Automatically adjusts throughput up to 500 MiBps
  - `provisioned` — Fixed provisioned throughput (specify `provisionedThroughputInMiBps`)

### Backup and Lifecycle Policies

- **Automatic Backup:** Controlled by `backupEnabled`; integrates with AWS Backup.
- **Lifecycle Tiering:** Transitions data to cheaper storage classes:
  - `transitionToIA` — Infrequent access (1, 7, 14, 30, 60, 90, 180, 270, 365 days)
  - `transitionToArchive` — Archive tier (same intervals)
  - `transitionToPrimaryStorage` — Transition back from IA/Archive to primary (only `AFTER_1_ACCESS`)

### One Zone File Systems

Set `spec.availabilityZoneName` to create a One Zone file system that uses a single availability zone. This reduces cost and latency for workloads in a specific AZ but limits resilience. If omitted, the file system is created in Regional mode (multi-AZ).

### File System Policy

Set `spec.policy` with a resource-based JSON policy to control access to the file system (e.g., restrict to specific IAM roles or IP ranges). See AWS documentation for policy format.

### Replication

Configure `spec.replicationConfiguration` to enable cross-region replication:

```yaml
spec:
  replicationConfiguration:
    region: eu-west-1              # Target region
    availabilityZoneName: eu-west-1a  # Target AZ (for One Zone destination)
    kmsKeyId: arn:aws:kms:...      # KMS key in target region for encryption
```

Protection against accidental overwrites during replication is controlled by `replicationOverwriteProtection` (governed field).

## Access Points

Access points provide application-level isolation on a shared file system. Each access point can enforce:

- **POSIX User Identity** — All clients mounting through the access point operate as a specific UID/GID.
- **Root Directory Scoping** — Clients see only a subtree of the file system (e.g., `/app-data`).
- **Automatic Directory Creation** — Optionally create missing directories with specified ownership and permissions.

Access points are immutable after creation; to change POSIX user or root directory, delete and recreate.

### File System References

Access points and mount targets reference the parent file system via one of two paths:

1. **`fileSystemRef`** — Reference a sibling `EFSFileSystem` CR by name (recommended for kropath-managed file systems)
2. **`fileSystemId`** — Direct AWS file system ID for pre-existing file systems not managed by kropath

Use exactly one; they are mutually exclusive.

## Mount Targets and Network Configuration

Mount targets are ENIs in specific VPC subnets that enable NFS client access to a file system. AWS enforces **one mount target per AZ per file system**.

When creating mount targets, specify:

- **`subnetId`** (required) — VPC subnet where the ENI will be placed
- **`ipAddress`** (optional) — Fixed private IP within the subnet range; if omitted, AWS auto-assigns
- **`securityGroupIds`** (optional) — Up to 5 security groups for network access control; if omitted, the VPC default security group is used

### Tagging and Mount Targets

AWS EFS does **not currently support direct tagging of mount targets**. Tags are inherited from the parent file system. The `spec.tags` field on `EFSMountTarget` is reserved for future use; it is not passed to the AWS ACK MountTarget CR in Phase 1.

Kubernetes metadata (`metadata.labels`, `metadata.annotations`) **is** applied to the kropath-managed ACK MountTarget CR for K8s-level observability and compliance.

## Deletion Policies

Set `spec.deletionPolicy` to control behavior when a kropath resource is deleted:

- **`retain`** (default) — The AWS resource is preserved when the Kubernetes CR is deleted. Safe default; manual AWS cleanup required.
- **`delete`** — The AWS resource is deleted when the Kubernetes CR is deleted. Useful for dev/test environments; use with caution in production.

## Cross-Provider Notes

EFS is an AWS-specific service. Other cloud providers have different shared file system offerings:

- **GCP Filestore**: Google Cloud's managed NFS service; uses different performance tiers and lifecycle policies.
- **Azure Files**: Azure's SMB/NFS file shares; uses different pricing and performance models.

Naming conventions, immutable fields, and governance structures differ across providers.

## Related Topics

- [Governance Cascade and Effective Config](../resources/governance-cascade.md) — Deep dive into how the three-tier cascade works
- [EFSConfig Governance Profiles](efsconfig-governance.md) — Platform engineering guide to creating and managing profiles
