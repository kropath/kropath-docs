---
title: S3VectorsVectorBucket
description: "`S3VectorsVectorBucket` is a Kubernetes resource that represents an Amazon S3 Vectors vector bucket — purpose-built storage for vector embeddings used in AI/ML similarity search workloads."
doc_type: reference
---
# S3VectorsVectorBucket

`S3VectorsVectorBucket` is a Kubernetes resource that represents an Amazon S3 Vectors vector bucket — purpose-built storage for vector embeddings used in AI/ML similarity search workloads.

## Scope

This resource is AWS-only. It wraps the ACK `VectorBucket` resource from the S3 Vectors service. GCP and Azure have different vector storage services (Vertex AI Vector Search, Azure AI Search).

## What it solves

AI/ML workloads using vector embeddings need:

- **Vector storage** — store dense embeddings from ML models
- **Similarity search** — quickly find similar vectors using cosine, Euclidean, or dot product distance
- **Encryption** — protect ML model outputs
- **Naming** — cloud bucket names should follow your organization's scheme
- **Governance tags** — track embeddings by model, dataset, or application
- **Status tracking** — know when a bucket is ready

`S3VectorsVectorBucket` streamlines this by providing:

- **Simple YAML spec** — define a bucket with encryption settings
- **Governance integration** — inherit encryption from an `S3AdvancedConfig` profile
- **Naming automation** — cloud names generated automatically
- **ARN tracking** — see the bucket's predicted ARN
- **Index hosting** — parent container for vector indexes

## Core concepts

### Vector embeddings

Vector embeddings are dense representations of text, images, or other data produced by machine learning models (BERT, GPT embeddings, etc.). Typically 768–3072 dimensions of 32-bit floats.

S3 Vectors stores these efficiently and supports fast similarity search across millions of vectors.

### Indexes within buckets

A vector bucket contains multiple indexes, each with its own schema:

```
VectorBucket
  ├─ ImageEmbeddings (768-dim cosine)
  ├─ TextEmbeddings (1024-dim Euclidean)
  └─ ProductMetadata (512-dim dot product)
```

### Encryption

Vector buckets support encryption:

```yaml
spec:
  encryptionConfiguration:
    sseType: "aws:kms"  # Customer-managed encryption
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

## Complete example

Here's a vector bucket for ML embeddings in a recommendation system:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: S3VectorsVectorBucket
metadata:
  name: ml-embeddings
  namespace: recommendation-svc
spec:
  # Use the compliance profile for encryption
  configRef: compliance
  
  # Encryption configuration
  encryptionConfiguration:
    sseType: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  
  # Deletion policy: retain
  deletionPolicy: retain
  
  # Tags for organization and cost tracking
  tags:
    model-family: embeddings
    ml-platform: sagemaker
    cost-center: ai-ml
  
  # Labels to sync to cloud
  syncedLabels:
    environment: production
    team: ml-platform
```

Then create indexes within this bucket:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: S3VectorsIndex
metadata:
  name: product-embeddings
  namespace: recommendation-svc
spec:
  # Reference the parent bucket
  vectorBucketRef: ml-embeddings
  
  # Vector properties
  dataType: "float32"
  dimension: 768
  distanceMetric: "cosine"
  
  # Optional: index-level encryption override
  encryptionConfiguration:
    sseType: "aws:kms"
    kmsKeyARN: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

## Naming

Vector bucket names are generated from a template using:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |

**Default template**: `{namespace}-{name}`

## Cross-references

Vector buckets reference:
- `S3AdvancedConfig` profiles (via `spec.configRef`)
- KMS keys (via `spec.encryptionConfiguration.kmsKeyRef`)

Vector buckets are referenced by:
- `S3VectorsIndex` resources (via `vectorBucketRef` or bucket name)

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `S3VectorsVectorBucket`
- **Scope**: Namespaced
