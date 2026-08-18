# EFSFileSystem — Creating and Managing Shared Storage

The `EFSFileSystem` resource represents a single Amazon EFS (Elastic File System) shared file system. This guide covers all configuration fields, governance semantics, and real-world usage patterns.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `EFSConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the EFSFileSystem resource is deleted: `"retain"` (safe) or `"delete"` |

### Storage Configuration (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encrypted` | boolean (pointer) | *governed* | Enable encryption at rest; `null` = defer to governance cascade |
| `kmsKeyId` | string | `""` | KMS key ID/ARN for encryption (requires `encrypted: true`); `""` = use AWS-managed key |
| `performanceMode` | string | *governed* | `generalPurpose` (default) or `maxIO`; **immutable after creation** |
| `backupEnabled` | boolean (pointer) | *governed* | Enable automatic backup integration; `null` = defer to governance cascade |

### Throughput Configuration (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `throughputMode` | string | *governed* | `bursting`, `elastic`, or `provisioned` |
| `provisionedThroughputInMiBps` | number | `0` | Required when `throughputMode: provisioned`; valid range 1–3414 MiBps |

### Lifecycle Policies (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `transitionToIA` | string | *governed* | Transition to Infrequent Access (e.g., `AFTER_30_DAYS`, `AFTER_7_DAYS`) |
| `transitionToArchive` | string | *governed* | Transition to Archive tier (same interval options) |
| `transitionToPrimaryStorage` | string | *governed* | Back-transition from IA/Archive; only `AFTER_1_ACCESS` supported |

### Availability and Resilience

| Field | Type | Default | Purpose |
|---|---|---|---|
| `availabilityZoneName` | string | `""` | AZ name for One Zone mode (e.g., `"us-east-1a"`); `""` = Regional multi-AZ |
| `replicationOverwriteProtection` | string | *governed* | `ENABLED` or `DISABLED`; prevents accidental overwrites during replication |
| `replicationConfiguration` | object | optional | Cross-region replication destination |
| `replicationConfiguration.region` | string | required | Target AWS region |
| `replicationConfiguration.availabilityZoneName` | string | `""` | Target AZ for One Zone destination |
| `replicationConfiguration.kmsKeyId` | string | `""` | KMS key in target region for encryption |

### File System Policy

| Field | Type | Default | Purpose |
|---|---|---|---|
| `policy` | string | `""` | Resource-based JSON policy (max 20,000 chars); `""` = no policy |

### Metadata and Tags (Governed)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance mandatory and default tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Performance Modes

Performance mode determines optimization for your workload and **cannot be changed after file system creation**. Choose carefully:

| Mode | Latency Optimization | Throughput Optimization | Use Case | One Zone? |
|---|---|---|---|---|
| `generalPurpose` (default) | ✓ High — optimized for web serving, general file serving | General | Most workloads (web, app servers, machine learning) | ✓ Yes |
| `maxIO` | — Lower latency not prioritized | ✓ High — optimized for high levels of throughput and operations per second | Big data analytics, media processing, genomics analysis | ✗ Not available |

**Important:** If you need to change performance mode, you must:

1. Delete the `EFSFileSystem` CR
2. Create a new file system with the desired performance mode
3. Migrate data (mount both, copy, remount clients)

## Throughput Modes

Throughput mode controls how the file system scales:

| Mode | Behavior | Best For | Configuration |
|---|---|---|---|
| `bursting` | Throughput scales with file system size (max 100 MiBps for larger file systems) | Development, testing, small production workloads | No additional config needed |
| `elastic` | Automatically scales throughput up to 500 MiBps in response to workload | Production workloads with variable demand; cost-effective for scaling | No additional config needed |
| `provisioned` | Fixed provisioned throughput; pay for provisioned amount regardless of usage | Workloads with predictable, sustained throughput requirements | Set `provisionedThroughputInMiBps` (1–3414) |

## Lifecycle Policies and Data Tiering

EFS automatically transitions infrequently accessed data to cheaper storage classes. Configure one or more transitions:

### Transition to Infrequent Access (IA)

Automatically moves data to the IA storage class after a period of inactivity. Retrieval is cheaper than standard but incurs a per-request cost:

```yaml
spec:
  transitionToIA: AFTER_30_DAYS
```

Options: `AFTER_1_DAY`, `AFTER_7_DAYS`, `AFTER_14_DAYS`, `AFTER_30_DAYS`, `AFTER_60_DAYS`, `AFTER_90_DAYS`, `AFTER_180_DAYS`, `AFTER_270_DAYS`, `AFTER_365_DAYS`

### Transition to Archive

Automatically moves data to the Archive storage class after a long period of inactivity. Cheapest storage tier but retrieval is more expensive:

```yaml
spec:
  transitionToArchive: AFTER_90_DAYS
```

### Transition Back to Primary Storage

Optionally transition data back from IA or Archive to primary storage after access:

```yaml
spec:
  transitionToPrimaryStorage: AFTER_1_ACCESS
```

Only `AFTER_1_ACCESS` is supported; data is promoted immediately upon first access.

## Encryption

### AWS-Managed Encryption (Default)

```yaml
spec:
  encrypted: true
  kmsKeyId: ""  # AWS-managed key (aws/elasticfilesystem)
```

### Customer-Managed Encryption

```yaml
spec:
  encrypted: true
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012
```

Encryption is applied at rest. Encryption in transit can be enforced via NFS security labels or VPC security groups.

**Mandatory Encryption:** Platform teams can enforce encryption via `EFSConfig.mandatory.encrypted: true`, preventing instances from creating unencrypted file systems.

## One Zone File Systems

By default, file systems are created in Regional mode across multiple availability zones for high resilience. One Zone file systems reduce cost and latency:

```yaml
spec:
  availabilityZoneName: us-east-1a
```

**Tradeoffs:**

- ✓ Lower cost, lower latency within the AZ
- ✗ Limited to a single AZ; single point of failure
- ✗ Cannot use `maxIO` performance mode

If `availabilityZoneName` is omitted, the file system is Regional (multi-AZ).

## Replication and Disaster Recovery

Configure cross-region replication for disaster recovery:

```yaml
spec:
  replicationConfiguration:
    region: eu-west-1
    availabilityZoneName: eu-west-1a    # For One Zone destination
    kmsKeyId: arn:aws:kms:eu-west-1:...  # Target region KMS key
```

AWS creates a read-only replica in the destination region. Data is replicated asynchronously; the replica can be promoted to a full read-write file system if needed.

**Protection:** Set `replicationOverwriteProtection: ENABLED` (governance default) to prevent accidental overwrites of the replica:

```yaml
spec:
  replicationOverwriteProtection: DISABLED  # Only if you want to allow overwrites
```

## Backup

EFS integrates with AWS Backup. Enable automatic backup:

```yaml
spec:
  backupEnabled: true
```

Backups are retained according to your AWS Backup policies. This is controlled via governance cascade, allowing platform teams to mandate backups org-wide via `EFSConfig.mandatory.backupEnabled: true`.

## Complete Example: Production Data Pipeline Storage

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSFileSystem
metadata:
  name: ml-training-storage
  namespace: ml-workloads
spec:
  configRef: general-policy
  deletionPolicy: retain

  # Storage
  encrypted: true
  kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/abcdef-prod-key
  performanceMode: maxIO          # Optimized for high throughput (e.g., ML training)
  
  # Throughput
  throughputMode: elastic
  
  # Backup and lifecycle
  backupEnabled: true
  transitionToIA: AFTER_60_DAYS       # Transition cold training data to IA
  transitionToArchive: AFTER_180_DAYS # Then to Archive after 6 months
  
  # Tags and governance
  tags:
    application: ml-training
    environment: production
    cost-centre: data-science
  syncedLabels:
    team: ml-platform
    data-classification: internal
  syncedAnnotations:
    data-retention-policy: "12-months"
```

Result:

- Highly-available, multi-AZ storage suitable for ML workloads requiring high throughput
- All data encrypted at rest with customer-managed KMS key
- Automatic daily backups
- Automatic lifecycle transitions: cold data → IA after 60 days → Archive after 180 days
- Production governance (mandatory encryption, backup enabled) enforced via `general-policy` config

## Example: Development/Test One Zone File System

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSFileSystem
metadata:
  name: dev-scratch-storage
  namespace: development
spec:
  configRef: general-policy
  deletionPolicy: delete           # Delete when the CR is removed

  # One Zone for cost savings in dev
  availabilityZoneName: us-east-1a
  
  # Default governance from general-policy
  performanceMode: generalPurpose
  throughputMode: bursting
  backupEnabled: false            # No backup needed for dev data
  
  tags:
    environment: development
    temporary: "true"
```

Result:

- Single-AZ file system for cost savings
- Bursting throughput (scales with file system size)
- No backup (faster development iteration)
- AWS resource deleted when the Kubernetes CR is removed

## Status Fields

After creation, inspect status to retrieve AWS resource details:

```bash
kubectl get efsfilesystem ml-training-storage -n ml-workloads -o yaml
```

| Status Field | Example | Purpose |
|---|---|---|
| `status.fileSystemId` | `fs-0123456789abcdef0` | AWS file system ID (system-assigned) |
| `status.fileSystemArn` | `arn:aws:elasticfilesystem:...` | Full ARN of the file system |
| `status.lifeCycleState` | `available` | Lifecycle state (`creating`, `available`, `updating`, `deleting`, `deleted`, `error`) |
| `status.conditions[].type` | `Ready` | Standard Kubernetes condition type |
| `status.conditions[].status` | `True` | Condition status |

## Immutability Constraints

These fields **cannot be changed after file system creation**:

- **`performanceMode`** — Changing this requires deletion and recreation

Attempting to update an immutable field will result in a validation error:

```bash
$ kubectl patch efsfilesystem ml-training-storage --patch '{"spec":{"performanceMode":"generalPurpose"}}'
# Error: performanceMode is immutable after creation
```

## Deletion and Cleanup

### Retain (Default)

```yaml
spec:
  deletionPolicy: retain
```

When the `EFSFileSystem` CR is deleted, the AWS file system is **preserved**. You must manually delete the AWS resource via the AWS console or CLI if needed. This is the safe default for production.

### Delete

```yaml
spec:
  deletionPolicy: delete
```

When the `EFSFileSystem` CR is deleted, the AWS file system is **immediately deleted**. Use only in development/test environments. Data loss is permanent and immediate.

## Governance Cascade

Field resolution follows the three-tier cascade:

1. `EFSConfig.mandatory.<field>` (enforced, cannot override)
2. `spec.<field>` (instance-level override)
3. `EFSConfig.defaults.<field>` (applied if instance leaves field unset)

For example, if the `pci` `EFSConfig` profile sets `mandatory.encrypted: true`, all file systems using the `pci` profile will be encrypted regardless of instance `spec.encrypted`.

Boolean fields use pointer semantics to distinguish "not set" (null) from "explicitly false":

- **`nil`** (unset) → cascade to next tier
- **`false`** (explicit) → opt-out
- **`true`** (explicit) → opt-in

## Cross-Provider Notes

EFS is AWS-specific. Other providers have different file system offerings:

- **GCP Filestore** — Uses tiered instances (BASIC_HDD, BASIC_SSD, HIGH_SCALE_SSD, ENTERPRISE) instead of performance modes
- **Azure Files** — Uses SMB/NFS shares with Standard/Premium tiers instead of bursting/elastic/provisioned throughput
- **Lifecycle transitions** — EFS-specific feature; other providers use different data tiering mechanisms

## Related Topics

- [EFS Access Points](efsaccesspoint.md) — Application-level isolation with POSIX users and directory scoping
- [EFS Mount Targets](efsmounttarget.md) — Network connectivity for NFS clients
- [EFSConfig Governance](efsconfig-governance.md) — Creating and managing governance profiles
