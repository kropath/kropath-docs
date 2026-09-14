# S3TablesTable

`S3TablesTable` is a Kubernetes resource that represents an Apache Iceberg table within an S3 Tables namespace. Tables are the primary data storage unit in S3 Tables, supporting Iceberg schema, partitioning, and sort order for analytics workloads.

## Scope

This resource is AWS-only. It wraps the ACK `Table` resource from the S3 Tables service. GCP and Azure do not have equivalent Iceberg table services.

## What it solves

When working with Iceberg tables in S3, you need to:

- **Define schema** — specify columns, types, and required fields
- **Set partitioning** — partition tables for query performance (e.g., by date, region)
- **Configure encryption** — choose between AWS-managed and customer-managed encryption per table
- **Set storage class** — choose cost/performance tradeoff
- **Apply naming** — cloud table names should follow your organization's naming scheme
- **Apply governance** — inherit tags from platform policies
- **Track status** — know when a table is ready and detect configuration errors

`S3TablesTable` streamlines this by providing:

- **Schema as code** — define Iceberg schema in YAML alongside governance settings
- **Governance integration** — inherit encryption from an `S3AdvancedConfig` profile
- **Partitioning support** — specify partition transforms (identity, date, month, year, hour, bucket, truncate)
- **Sort order** — optional clustering hint for query optimization
- **ARN tracking** — see the table's predicted ARN and metadata location
- **Naming automation** — cloud names generated automatically with configurable templates

## Core concepts

### Schema definition

Iceberg schemas specify columns with types and nullability:

```yaml
metadata:
  iceberg:
    schema:
      fields:
        - id: 1
          name: event_id
          type: string
          required: true
        - id: 2
          name: event_time
          type: timestamp
          required: true
        - id: 3
          name: user_id
          type: string
          required: false
        - id: 4
          name: event_data
          type: string  # JSON encoded
          required: false
```

Schema is immutable after creation. Iceberg's hidden partitioning and schema evolution let you add columns later without rewriting data.

### Partitioning

Partitions organize data for query efficiency:

```yaml
metadata:
  iceberg:
    partitionSpec:
      fields:
        - fieldID: 2        # References field id 2 (event_time)
          sourceID: 2
          name: event_day
          transform: day     # Partition by day
        - fieldID: 3
          sourceID: 3
          name: user_id
          transform: identity  # No transformation
```

Common transforms:
- **identity**: use the column value as-is
- **year, month, day, hour**: temporal bucketing
- **bucket(N)**: hash-based bucketing into N buckets
- **truncate(L)**: truncate string to L characters

### Naming

Cloud table names are derived from `{namespace}_{name}` by default (note: underscores instead of hyphens, as S3 Tables requires `^[0-9a-z_]*$`).

**Default template**: `{namespace}_{name}` with automatic hyphen-to-underscore replacement

**Example**: CR in namespace `analytics-prod` named `user-events` produces table name `analytics_prod_user_events`.

### Encryption

Tables inherit encryption from their parent table bucket by default. Per-table overrides are supported but immutable after creation:

- **AWS-managed** (default): `sseAlgorithm: ""` or omitted
- **Customer-managed**: `sseAlgorithm: "aws:kms"` with KMS key ARN

## Complete example

Here's a multi-partition analytics table with Iceberg schema:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesTable
metadata:
  name: user-events
  namespace: analytics-prod
spec:
  # Reference the parent table bucket
  tableBucketRef: analytics
  
  # Reference the namespace within the bucket
  namespaceRef: events
  
  # Table format (always ICEBERG for S3 Tables)
  format: ICEBERG
  
  # Iceberg schema: columns and types
  metadata:
    iceberg:
      schema:
        fields:
          - id: 1
            name: event_id
            type: string
            required: true
          - id: 2
            name: event_time
            type: timestamp
            required: true
          - id: 3
            name: user_id
            type: string
            required: true
          - id: 4
            name: event_type
            type: string
            required: true
          - id: 5
            name: event_data
            type: string  # JSON
            required: false
      
      # Partition by date and user (common for analytics)
      partitionSpec:
        fields:
          - fieldID: 2
            sourceID: 2
            name: event_day
            transform: day
          - fieldID: 3
            sourceID: 3
            name: user_id
            transform: identity
      
      # Sort order for query optimization
      writeOrder:
        fields:
          - sourceID: 2
            transform: identity
            direction: asc
            nullOrder: nulls_last
  
  # Optional: per-table storage class override
  storageClassConfiguration:
    storageClass: INTELLIGENT_TIERING
  
  # Deletion policy: retain (don't delete table when CR is deleted)
  deletionPolicy: retain
  
  # Tags for cost tracking
  tags:
    domain: analytics
    data-retention: long-term
  
  # Labels to sync to both K8s and cloud
  syncedLabels:
    team: data-platform
    sla: 99-5
```

After creating this table, you can query it via Athena, EMR, or other Iceberg-compatible tools.

## Schema evolution

Iceberg supports schema evolution — you can add new columns without rewriting existing data. However, the `spec.metadata.iceberg.schema` is **immutable after table creation** (enforced by the ACK CRD). To evolve your table schema, use the Iceberg-compatible service API:

**Option 1: Athena**
```sql
ALTER TABLE database.table_name ADD COLUMNS (session_id string);
```

**Option 2: AWS SDK or another Iceberg tool**
Refer to the AWS S3 Tables API documentation for schema evolution operations.

The table will reflect schema changes automatically in subsequent queries and analytics workloads. Iceberg tracks column IDs internally, so renaming and reordering columns are also supported through the service API.

## Storage and partitioning

Table data is stored in the S3 bucket using Iceberg's standard format:

- **Data files**: Parquet or ORC files in S3
- **Manifest files**: track which data files belong to each partition
- **Metadata files**: immutable snapshots of table schema and data
- **Maintenance**: S3 Tables can automatically remove orphaned files via the parent bucket's maintenance configuration

## Cross-references

Tables reference:
- `S3TablesTableBucket` (via `tableBucketRef` or `tableBucketARN`)
- `S3TablesNamespace` (via `namespaceRef` or `namespace` ARN)
- `S3AdvancedConfig` profiles (via `spec.configRef`)
- KMS keys (via `spec.encryptionConfiguration.kmsKeyRef` if per-table encryption override is needed)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3TablesTable`
- **Scope**: Namespaced
