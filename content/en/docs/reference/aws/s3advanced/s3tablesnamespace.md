---
title: S3TablesNamespace
description: "`S3TablesNamespace` is a Kubernetes resource that represents a logical grouping within an S3 Tables table bucket."
doc_type: reference
---
# S3TablesNamespace

`S3TablesNamespace` is a Kubernetes resource that represents a logical grouping within an S3 Tables table bucket. Namespaces organize Apache Iceberg tables for access control and discoverability within a table bucket.

## Scope

This resource is AWS-only. It wraps the ACK `Namespace` resource from the S3 Tables service. GCP and Azure do not have equivalent Iceberg table services.

## What it solves

When working with S3 Tables, organizing tables into namespaces helps:

- **Organize tables** — group related tables by domain, dataset, or business unit
- **Simplify discovery** — find tables by namespace rather than listing a flat bucket
- **Access control** — apply access policies at the namespace level
- **Isolate workloads** — separate analytics, ETL, and data lake tables
- **Track resource status** — know when a namespace is ready and what its ARN is

`S3TablesNamespace` streamlines this by providing:

- **Simple YAML spec** — define a namespace with a reference to its parent table bucket
- **Cross-reference support** — reference a table bucket via CR name or ARN
- **Governance integration** — inherit tags from an `S3AdvancedConfig` profile
- **Status visibility** — see when the namespace is ready

## Core concepts

### Namespace hierarchy

A namespace belongs to exactly one table bucket:

```
TableBucket
  └─ Namespace A
      ├─ Table 1
      └─ Table 2
  └─ Namespace B
      └─ Table 3
```

Namespaces are scoped to their parent bucket. You cannot move tables between namespaces or buckets; they must be re-created.

### Cross-references

Namespaces reference their parent table bucket via:
- **`spec.tableBucketRef`**: Reference a local `S3TablesTableBucket` CR name (resolved to ARN)
- **`spec.tableBucketARN`**: Direct ARN of an existing table bucket

Use `tableBucketRef` for co-managed resources in the same cluster; use `tableBucketARN` for referencing buckets created outside kropath.

### Naming

Namespaces are identified by their ARN, which is system-generated after creation. The namespace name within S3 Tables is derived from the `{namespace}-{name}` template by default.

**Default template**: `{namespace}-{name}`

**Example**: CR in namespace `analytics-prod` named `events` produces namespace name `analytics-prod-events` within the table bucket.

## Complete example

Here's a namespace for event analytics within a table bucket:

```yaml
---
# First, create the parent table bucket
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesTableBucket
metadata:
  name: analytics
  namespace: analytics-prod
spec:
  configRef: general-policy
  encryptionConfiguration:
    sseAlgorithm: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  deletionPolicy: retain

---
# Create a namespace within the bucket for event data
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesNamespace
metadata:
  name: events
  namespace: analytics-prod
spec:
  # Reference the parent table bucket
  tableBucketRef: analytics
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    domain: events
    team: data-platform
```

After applying this, you can inspect the namespace status:

```bash
kubectl describe s3tablesnamespace events -n analytics-prod
```

Once the resource is ready, check the ACK-provided status fields for the namespace ARN and other details. The ARN is available in the status once the namespace is successfully created in S3 Tables.

## Using namespaces with tables

Once a namespace is created, tables reference it:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3TablesTable
metadata:
  name: user-events
  namespace: analytics-prod
spec:
  # Reference the parent table bucket
  tableBucketRef: analytics
  
  # Reference the namespace within that bucket
  namespaceRef: events
  
  # Define the Iceberg schema
  format: ICEBERG
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
      partitionSpec:
        fields:
          - fieldID: 2
            sourceID: 2
            name: event_time
            transform: day
```

## Governance

Namespaces inherit tags from their parent table bucket. You can add additional tags at the namespace level for better cost tracking and organization.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3TablesNamespace`
- **Scope**: Namespaced
