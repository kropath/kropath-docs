---
title: S3VectorsIndex
description: "`S3VectorsIndex` is a Kubernetes resource that represents a vector index within an S3 Vectors vector bucket."
doc_type: reference
---
# S3VectorsIndex

`S3VectorsIndex` is a Kubernetes resource that represents a vector index within an S3 Vectors vector bucket. Indexes store and search vector embeddings using configurable distance metrics and data types.

## Scope

This resource is AWS-only. It wraps the ACK `Index` resource from the S3 Vectors service.

## What it solves

ML similarity search requires:

- **Vector schema** — specify dimensionality, data type, and distance metric
- **Indexing** — efficiently organize embeddings for fast search
- **Search** — find similar vectors using cosine, Euclidean, or dot product distance
- **Encryption** — protect embeddings
- **Metadata** — optionally filter by non-indexed metadata
- **Governance** — inherit encryption and tagging from platform policies

`S3VectorsIndex` streamlines this by providing:

- **Simple YAML spec** — define an index with embedding dimensions and distance metric
- **Governance integration** — inherit encryption from an `S3AdvancedConfig` profile
- **Naming automation** — cloud names generated automatically
- **Mutable encryption** — update index encryption settings without recreating the index
- **Metadata filtering** — optional structured metadata alongside vectors

## Core concepts

### Vector properties

Every index requires:

```yaml
spec:
  dataType: "float32"           # 32-bit floating point vectors
  dimension: 768                # Number of dimensions
  distanceMetric: "cosine"      # "cosine", "euclidean", or "dot_product"
```

**Data types**:
- `float32` — 32-bit IEEE 754 float (standard for ML embeddings)
- `int8` — 8-bit signed integer (quantized embeddings)

**Distance metrics**:
- **cosine** — measures angle between vectors; range [0, 2]
- **euclidean** — measures straight-line distance; range [0, ∞]
- **dot_product** — dot product similarity; range [-∞, ∞]

### Immutable properties

These properties are immutable after creation; changing them requires index recreation:
- `dataType`
- `dimension`
- `distanceMetric`
- Metadata configuration

Mutable properties:
- `tags`
- `encryptionConfiguration` (in-place updates supported)

### Naming

Index names are generated from a template using:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |

**Default template**: `{namespace}-{name}`

**Example**: CR in namespace `recommendation-svc` named `product-embeddings` produces index name `recommendation-svc-product-embeddings`.

## Complete example

Here's a vector index for product similarity search:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: S3VectorsIndex
metadata:
  name: product-embeddings
  namespace: recommendation-svc
spec:
  # Reference the parent vector bucket
  vectorBucketRef: ml-embeddings
  
  # Vector properties (immutable after creation)
  dataType: "float32"
  dimension: 768
  distanceMetric: "cosine"
  
  # Optional: metadata configuration
  metadataConfiguration:
    nonFilterableMetadataKeys:
      - "internal_id"  # These metadata fields are not indexed
      - "debug_info"
  
  # Optional: index-level encryption (can be updated later)
  encryptionConfiguration:
    sseType: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization
  tags:
    model: sentence-transformers
    distance: cosine
    use-case: product-recommendations
  
  # Labels to sync to cloud
  syncedLabels:
    team: ml-platform
    environment: production
```

## Updating indexes

Most index properties are immutable, but encryption can be updated:

```yaml
spec:
  encryptionConfiguration:
    sseType: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/87654321-4321-4321-4321-210987654321"
```

To change vector properties (dimension, distance metric), recreate the index with a new CR.

## Metadata filtering

Indexes can store structured metadata alongside vectors:

```yaml
spec:
  metadataConfiguration:
    nonFilterableMetadataKeys:
      - "internal_debug"  # Won't be indexed for filtering
```

Metadata is optional; applications can store any structured data with vectors.

## Similarity search

Once the index is ready, applications query it via the S3 Vectors API:

```python
# Example: find top-K similar products
import boto3

s3vectors = boto3.client('s3vectors')

response = s3vectors.search_index(
    IndexName='recommendation-svc-product-embeddings',
    Vector=[0.1, 0.2, 0.3, ...],  # Your vector (768 dims)
    TopK=10,
    Metadata={'category': 'electronics'}  # Optional filter
)

for result in response['Results']:
    print(f"Similar to: {result['MetadataKey']}, Score: {result['Score']}")
```

## Naming and organization

Use naming conventions to organize indexes by model and use case:

- `product-embeddings` — for product similarity
- `content-embeddings` — for content recommendations
- `user-intent-embeddings` — for intent classification

Prefix indexes with their business domain for clarity.

## Cross-references

Indexes reference:
- `S3VectorsVectorBucket` resources (via `vectorBucketRef` or bucket name)
- `S3AdvancedConfig` profiles (via `spec.configRef`)
- KMS keys (via `spec.encryptionConfiguration.kmsKeyRef`)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3VectorsIndex`
- **Scope**: Namespaced
