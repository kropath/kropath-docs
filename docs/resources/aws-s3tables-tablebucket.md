# S3TablesTableBucket

`S3TablesTableBucket` is a Kubernetes resource that represents an Amazon S3 Tables table bucket — an Iceberg-native storage container optimized for analytics workloads. Table buckets hold namespaces and tables, and provide built-in maintenance (automatic cleanup of unreferenced Iceberg files) and configurable storage classes.

## Scope

This resource is AWS-only. It wraps the ACK `TableBucket` resource from the S3 Tables service. GCP and Azure do not have direct Iceberg table storage equivalents.

## What it solves

When working with S3 Tables (Iceberg), you need to:

- **Create table buckets before namespaces and tables** — S3 Tables requires the bucket to exist first
- **Set encryption** — choose between AWS-managed (SSE-S3) and customer-managed (KMS) encryption
- **Configure maintenance** — enable automatic cleanup of unreferenced Iceberg metadata files
- **Set default storage class** — choose cost/performance tradeoff for tables within the bucket
- **Apply naming conventions** — cloud resource names should follow your organization's naming scheme
- **Apply governance tags** — every bucket should inherit tags from platform policies
- **Track resource status** — know when a bucket is ready and what its ARN is

`S3TablesTableBucket` streamlines this by providing:

- **Simple YAML spec** — define a bucket with encryption, maintenance, and storage class settings
- **Governance integration** — inherit encryption and tagging requirements from an `S3AdvancedConfig` profile
- **Naming automation** — cloud names are generated automatically using configurable templates
- **ARN tracking** — the resource exposes its predicted ARN so other resources can reference it
- **Status visibility** — see when the bucket is ready and any validation errors

## Core concepts

### Encryption

Table buckets support two encryption modes:

**AWS-managed encryption** (default):
- Encryption type: `"aws:kms"` with AWS-managed key
- No KMS key ARN needed
- Cost-efficient, no key management overhead
- Suitable for non-regulated workloads

**Customer-managed encryption**:
- Encryption type: `"aws:kms"` with a customer-managed KMS key
- Requires KMS key ARN
- Higher security and compliance requirements
- Suitable for regulated workloads (PCI, HIPAA, etc.)

### Maintenance configuration

Unreferenced Iceberg file removal automatically cleans up orphaned files:

- **Enabled**: removes Iceberg files not referenced in the latest table metadata
- **Disabled**: files accumulate (not recommended; increases storage costs)
- Configurable retention: how old files must be before cleanup
- Useful for cost optimization in high-churn analytics workloads

### Storage class

Default storage class applies to new tables created within the bucket:

- **INTELLIGENT_TIERING**: cost-optimized, moves objects between access tiers automatically
- **STANDARD**: frequently accessed data, higher cost
- **GLACIER**: long-term archival, lowest cost but slower access
- Per-table overrides: individual tables can use different storage classes

### Naming convention

Cloud table bucket names are generated from a template using:

| Token | Value | Example |
|---|---|---|
| `{namespace}` | Kubernetes namespace | `analytics-prod` → included in name |
| `{name}` | CR name | CR `main-bucket` → `main_bucket` in name |
| `{account_id}` | AWS account ID | From cluster metadata |
| `{region}` | AWS region | From cluster metadata |
| `{configRef}` | Selected profile name | `general-policy` → included if template uses it |
| `{tag.<key>}` | Tag value | `{tag.env}` → replaced with tag value |

**Default template**: `{namespace}-{name}`

Table bucket names must match `^[0-9a-z-]*$` (lowercase alphanumeric and hyphens). The platform enforces this constraint automatically via `.lowerAscii()` transformation.

**Example**: CR in namespace `analytics-prod` named `main` with template `{namespace}-{name}` becomes cloud bucket name `analytics-prod-main`.

You can also override the entire name with `spec.nameOverride`.

## Complete example

Here's a table bucket for a data platform with customer-managed encryption:

```yaml
---
# First, ensure the compliance profile exists
apiVersion: aws.kropath.run/v1alpha1
kind: S3AdvancedConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    tableBucketEncryption:
      sseAlgorithm: "aws:kms"
      kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  defaults:
    namingTemplate: "{namespace}-{name}"

---
# Create the table bucket in the analytics namespace
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesTableBucket
metadata:
  name: main
  namespace: analytics-prod
spec:
  # Use the compliance profile, which mandates customer-managed encryption
  configRef: compliance
  
  # Encryption is enforced by the profile; this spec is not needed
  # but shown here for clarity
  encryptionConfiguration:
    sseAlgorithm: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  
  # Enable automatic cleanup of unreferenced Iceberg files
  maintenanceConfiguration:
    icebergUnreferencedFileRemoval:
      enabled: true
      unreferencedDays: 30  # Remove files not referenced for 30 days
      nonCurrentDays: 7     # Remove non-current files after 7 days
  
  # Default storage class for tables created in this bucket
  storageClassConfiguration:
    storageClass: INTELLIGENT_TIERING  # Cost-optimized
  
  # Deletion policy: retain (don't delete the AWS bucket when this CR is deleted)
  deletionPolicy: retain
  
  # Tags for cost tracking and billing
  tags:
    cost-center: "analytics-team"
    project: "data-platform"
  
  # Labels that should appear on both K8s resources and cloud tags
  syncedLabels:
    environment: production
    team: data-platform
```

## Storage and retention

By default, S3 Tables buckets retain data indefinitely. The maintenance configuration lets you set policies for:

- **Data cleanup**: automatically remove unreferenced Iceberg files to save storage costs
- **Version retention**: how many table versions to keep before cleanup
- **Archival**: optionally tier old tables to GLACIER for cost savings

See the example above for a typical maintenance configuration.

## Cross-references

Table buckets are referenced by:
- `S3TablesNamespace` resources (via `tableBucketRef` or `tableBucketARN`)
- `S3TablesTable` resources (via `tableBucketRef` or `tableBucketARN`)

Table buckets reference:
- `S3AdvancedConfig` profiles (via `spec.configRef`)
- KMS keys (via `spec.encryptionConfiguration.kmsKeyRef` if using a local KMS key CR)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3TablesTableBucket`
- **Scope**: Namespaced
