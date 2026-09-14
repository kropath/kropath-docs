# S3AdvancedConfig

`S3AdvancedConfig` is a governance configuration resource that lets you define mandatory and default settings for AWS S3 Advanced services — S3 Tables (Iceberg), S3 Vectors (embedding storage), S3 Files (POSIX file systems), and S3 Control (access points). Instead of requiring every resource to specify encryption, public access blocking, and naming independently, you can create named configuration profiles and let the kropath controller apply them consistently across your cluster.

## Scope

This resource is AWS-only. S3AdvancedConfig governs:
- `S3TablesTableBucket`, `S3TablesNamespace`, `S3TablesTable` (Apache Iceberg analytics tables)
- `S3VectorsVectorBucket`, `S3VectorsIndex` (AI/ML embedding storage)
- `S3FilesFileSystem`, `S3FilesAccessPoint`, `S3FilesMountTarget` (POSIX file systems on S3)
- `S3ControlAccessPoint` (fine-grained bucket access management)

GCP and Azure do not have direct equivalents to these AWS services.

## What it solves

Managing S3 Advanced resources at scale creates several operational challenges:

- **Inconsistent governance** — different teams set different encryption types and public access policies, making compliance audits difficult
- **Compliance drift** — once resources are created, enforcing new compliance requirements (e.g., "all table buckets must use customer-managed KMS keys") requires manual updates
- **Manual defaults** — every resource spec must list sensible defaults (secure public access block settings, naming conventions), creating noise and inconsistency
- **No central policy** — when a new compliance requirement arrives, you must update every resource individually

`S3AdvancedConfig` solves this by providing:

- **Governance profiles** — define reusable profiles like `general-policy` or `pci-policy` that encode your organization's requirements
- **Mandatory enforcement** — platform teams set fields that override user input (e.g., "all access points must use VPC-only configuration")
- **Sensible defaults** — declare defaults for optional fields so user specs are cleaner and every resource has a consistent baseline
- **Scalable compliance** — update one profile to enforce a new requirement across all resources using that profile

## Core concepts

### Mandatory vs. defaults tiers

`S3AdvancedConfig` has two independent tiers of settings:

**Mandatory fields** (enforced):
- Override any user specification for that field
- Useful for compliance: "all table buckets must use customer-managed encryption"
- If mandatory is empty, it is not enforced (user can override)

**Defaults fields** (applied when user doesn't specify):
- Provide sensible fallback values
- Applied only when the user leaves the field empty
- Useful for convenience: "secure public access block by default, but let power users opt out if justified"

Mandatory wins over defaults: if both are set for the same field, the default is ignored.

### Governance cascade

The kropath controller pre-merges settings from three sources and writes them to `status.effectiveConfig`:

1. **Org-wide** (`KropathConfig.spec.mandatory.s3Advanced.*`) — applies to all S3 Advanced resources across the cluster
2. **Per-profile** (`S3AdvancedConfig.spec.mandatory/defaults.*`) — applies to resources using this profile
3. **Instance** (`S3TablesTableBucket/S3VectorsIndex/etc.spec.*`) — developer override for a specific resource

RGDs read the merged result from `status.effectiveConfig`, ensuring a single source of truth.

### Profile patterns

Common profiles codify organizational postures:

**general-policy** — the default, sensible baseline:
- Public access block: all protections enabled (secure by default)
- Encryption: AWS-managed (cost-efficient default)
- Naming: `{namespace}-{name}` template
- VPC-only: disabled (internet-accessible by default)

**pci-policy** — stricter, suitable for regulated workloads:
- Encryption: Customer-managed KMS keys (required for compliance)
- Public access block: all protections enforced
- VPC-only: access points restricted to VPC access
- Naming: tightened to enforce naming standards

## Configuration fields

### Encryption fields

Per-service encryption governance:

| Field | Resources | Type | Meaning |
|---|---|---|---|
| `tableBucketEncryption.sseAlgorithm` | S3 Tables buckets | string | Encryption type (`"aws:kms"` or empty for AWS-managed). Empty = not enforced. |
| `tableBucketEncryption.kmsKeyARN` | S3 Tables buckets | string | KMS key ARN. Empty = use service default or AWS-managed key. |
| `vectorBucketEncryption.sseType` | S3 Vectors buckets | string | Encryption type (`"aws:kms"` or empty for SSE-S3). Empty = not enforced. |
| `vectorBucketEncryption.kmsKeyARN` | S3 Vectors buckets | string | KMS key ARN. Empty = not enforced. |
| `vectorIndexEncryption.sseType` | S3 Vectors indexes | string | Encryption type for indexes. Empty = inherit from bucket. |
| `vectorIndexEncryption.kmsKeyARN` | S3 Vectors indexes | string | KMS key ARN for indexes. Empty = inherit from bucket. |
| `filesEncryption.kmsKeyID` | S3 Files file systems | string | KMS key ID/ARN for file system encryption. Empty = service-managed. |

### Access control fields

| Field | Resources | Type | Meaning |
|---|---|---|---|
| `accessPointPublicAccessBlock.blockPublicACLs` | S3 Control access points | boolean | Block public ACLs. Empty = not enforced. |
| `accessPointPublicAccessBlock.blockPublicPolicy` | S3 Control access points | boolean | Block public bucket policies. Empty = not enforced. |
| `accessPointPublicAccessBlock.ignorePublicACLs` | S3 Control access points | boolean | Ignore public ACLs. Empty = not enforced. |
| `accessPointPublicAccessBlock.restrictPublicBuckets` | S3 Control access points | boolean | Restrict public bucket access. Empty = not enforced. |
| `accessPointVpcOnly` | S3 Control access points | boolean | Restrict access points to VPC-only. Empty = internet-accessible by default. |

### Common governance fields

| Field | Type | Meaning |
|---|---|---|
| `tags` | map | Cloud resource tags. Merged with instance tags. |
| `syncedLabels` | map | Labels to sync to both K8s and cloud tags. |
| `syncedAnnotations` | map | Annotations to sync to both K8s and cloud tags. |
| `namingTemplate` | string | Cloud resource name template (e.g., `"{namespace}-{name}"`). |

## Complete example

Here's a complete multi-profile setup:

```yaml
---
# Org-wide settings (applied to all S3 Advanced resources)
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global
  namespace: kro-system
spec:
  mandatory:
    s3Advanced:
      accessPointPublicAccessBlock:
        blockPublicACLs: true
        blockPublicPolicy: true
        ignorePublicACLs: true
        restrictPublicBuckets: true
  defaults:
    s3Advanced: {}

---
# Default profile: sensible, secure baseline
apiVersion: aws.kropath.run/v1alpha1
kind: S3AdvancedConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    tableBucketEncryption:
      sseAlgorithm: ""
      kmsKeyARN: ""
    vectorBucketEncryption:
      sseType: ""
      kmsKeyARN: ""
    vectorIndexEncryption:
      sseType: ""
      kmsKeyARN: ""
    filesEncryption:
      kmsKeyID: ""
    accessPointPublicAccessBlock:
      blockPublicACLs: true
      blockPublicPolicy: true
      ignorePublicACLs: true
      restrictPublicBuckets: true
    accessPointVpcOnly: false
    namingTemplate: "{namespace}-{name}"
    tags:
      environment: general

---
# PCI compliance profile: stricter, for regulated workloads
apiVersion: aws.kropath.run/v1alpha1
kind: S3AdvancedConfig
metadata:
  name: pci-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci-policy
spec:
  mandatory:
    tableBucketEncryption:
      sseAlgorithm: "aws:kms"
      kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    vectorBucketEncryption:
      sseType: "aws:kms"
      kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    vectorIndexEncryption:
      sseType: "aws:kms"
      kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    accessPointVpcOnly: true
    accessPointPublicAccessBlock:
      blockPublicACLs: true
      blockPublicPolicy: true
      ignorePublicACLs: true
      restrictPublicBuckets: true
    tags:
      compliance-tier: pci
  defaults:
    namingTemplate: "{namespace}-{name}"
    filesEncryption:
      kmsKeyID: ""
```

## Using profiles with instances

Once your profiles are deployed, S3 Advanced resources select them via `spec.configRef`:

```yaml
---
# S3 Tables table bucket using the PCI profile
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesTableBucket
metadata:
  name: compliance-analytics
  namespace: data-platform
spec:
  configRef: pci-policy  # Use the PCI profile
  # Encryption is forced to customer-managed KMS (mandatory)
  # Developer cannot override encryption for compliance

---
# S3 Control access point using general-policy
apiVersion: aws.kropath.run/v1alpha1
kind: S3ControlAccessPoint
metadata:
  name: shared-data
  namespace: analytics
spec:
  configRef: general-policy
  accountID: "123456789012"
  bucket: my-data-bucket
  # Public access block defaults to all-true (secure default)
  # VPC-only defaults to false (internet-accessible)
```

## Profile selection rules

- **Default fallthrough** — if you omit `spec.configRef` or reference a profile that doesn't exist, kropath automatically uses the `general-policy` profile
- **Profiles in kro-system** — all profiles are deployed to the `kro-system` namespace. Instances in any application namespace can reference them via `spec.configRef`
- **Profile lookup by label** — profiles are found via the `aws.kropath.run/resource-name` label, not by `metadata.name`, so you can rename the CR safely without breaking references

## Best practices

1. **Create profiles for organizational postures, not per-resource.** One `pci-policy` profile serves all compliance workloads; don't create `pci-bucket-1`, `pci-bucket-2`, etc.

2. **Use mandatory fields sparingly.** Reserve mandatory for hard compliance requirements (encryption, VPC-only access). Use defaults for convenience.

3. **Document why mandatory fields exist.** Add annotations or comments to profiles explaining compliance drivers or operational requirements.

4. **Tag at the profile level.** Add environment and cost-center tags to profiles so every resource inheriting that profile carries the tags automatically.

5. **Test profile changes in non-production first.** Profile updates apply to all resources using that profile; validate in a staging namespace before production.

6. **Plan for profile evolution.** When compliance requirements change, update the profile rather than updating every resource individually — that's the power of centralized governance.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3AdvancedConfig`
- **Scope**: Namespaced
