# OpenSearchCollection — Serverless Search Collections

The `OpenSearchCollection` resource provisions serverless OpenSearch Serverless collections for search, time-series, and vector search workloads. Collections auto-scale without cluster topology management. Encryption and network access are controlled through separate `OpenSearchSecurityPolicy` resources.

## Purpose

`OpenSearchCollection` provides a managed, auto-scaling search platform:

- **No cluster management** — AWS manages scaling, availability, and topology automatically
- **Collection types** — SEARCH, TIMESERIES, or VECTORSEARCH (immutable after creation)
- **Serverless billing** — Pay per operation instead of per node
- **Security policies** — Encryption and network access via separate `OpenSearchSecurityPolicy` resources
- **Standby replicas** — Optional HA for improved reliability

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `OpenSearchConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the collection name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` keeps collection; `"delete"` removes it |

### Collection Configuration

| Field | Type | Default | Immutable | Purpose |
|---|---|---|---|---|
| `type` | string | `"SEARCH"` | Yes | Collection type: `SEARCH`, `TIMESERIES`, or `VECTORSEARCH` |
| `description` | string | `""` | No | Human-readable description |
| `standbyReplicas` | string | `"ENABLED"` | Yes | HA standby replicas: `ENABLED` or `DISABLED` |

### Tags and Governance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | K8s metadata tags (AOSS collections don't support cloud resource tags) |
| `syncedLabels` | map | `{}` | Labels synced to K8s metadata |
| `syncedAnnotations` | map | `{}` | Annotations synced to K8s metadata |

## Status Fields

After creation, the collection reports:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective collection name after naming template substitution |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` (if template has unresolved tokens) |
| `predictedArn` | string | Collection ARN (e.g., `arn:aws:aoss:us-east-1:123:collection/abc123`) (populated after creation) |
| `conditions` | array | Standard Kubernetes conditions (Ready, Reconciling, etc.) |

## Collection Types

| Type | Use Case | Auto-Scale Dimension |
|---|---|---|
| `SEARCH` | Full-text search, logs, metrics | Search capacity |
| `TIMESERIES` | Time-series data, metrics, analytics | Ingestion and search capacity |
| `VECTORSEARCH` | Vector embeddings, semantic search | Vector indexing and search capacity |

## Security Policies

Collections require associated security policies before they can be created:

- **Encryption policy** — Controls KMS key usage (AWS-owned or customer-managed)
- **Network policy** — Controls access (public or VPC endpoint only)

Security policies reference collections by name pattern in the policy JSON document.

### Creating Encryption Policies

Collections must have an encryption policy matching their name pattern before creation:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: my-collection-encryption
spec:
  configRef: general-policy
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/ml-services-embeddings*"]
        }
      ],
      "AWSOwnedKey": true
    }
```

### Network Access

By default, Serverless collections are accessible via public endpoints. Restrict access with a network policy:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: my-collection-network
spec:
  type: network
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/ml-services-embeddings*"]
        }
      ],
      "AllowFromPublic": false,
      "SourceVPCEs": ["vpce-12345678"]
    }
```

## Governance Cascade

When resolving configuration, fields cascade through this priority:

1. **OpenSearchConfig mandatory tier** (highest priority)
2. **Collection spec** (developer choice)
3. **OpenSearchConfig defaults tier** (lowest priority)

Currently, only `standbyReplicas` is governance-enforced for collections. Other fields (type, description) are developer-controlled.

## Naming

The effective collection name is computed from:

1. **nameOverride** (if set) — Use this name directly
2. **namingTemplate** (if set) — Apply the template with token substitution
3. **Fallback** — Use metadata.name

### Naming Constraints

- Lowercase `a-z`, digits `0-9`, hyphens `-`
- Must start with a lowercase letter
- 3–32 characters
- Pattern: `^[a-z][a-z0-9-]{2,31}$`

### Template Tokens

- `{name}` — CR metadata.name
- `{namespace}` — CR metadata.namespace
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Value of tag KEY
- `{configRef}` — Profile name

## Examples

### Basic Search Collection

Minimal SEARCH collection for full-text search:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: articles
  namespace: content-services
spec:
  configRef: general-policy
  type: SEARCH
  description: "Full-text search for articles and blog posts"
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: articles-encryption
  namespace: content-services
spec:
  configRef: general-policy
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/content-services-articles*"]
        }
      ],
      "AWSOwnedKey": true
    }
```

### Vector Search Collection

Collection for semantic search with vector embeddings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: embeddings
  namespace: ml-services
spec:
  configRef: general-policy
  type: VECTORSEARCH
  description: "Vector embeddings for product recommendations"
  standbyReplicas: "ENABLED"  # HA for production workload
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: embeddings-encryption
  namespace: ml-services
spec:
  configRef: general-policy
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/ml-services-embeddings*"]
        }
      ],
      "AWSOwnedKey": true
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: embeddings-network
  namespace: ml-services
spec:
  configRef: general-policy
  type: network
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/ml-services-embeddings*"]
        }
      ],
      "AllowFromPublic": false,
      "SourceVPCEs": ["vpce-api-1", "vpce-api-2"]
    }
```

### Time-Series Collection with CMK

Collection for metrics with customer-managed encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: metrics
  namespace: observability
spec:
  configRef: production
  type: TIMESERIES
  description: "Metrics and performance data"
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: metrics-encryption
  namespace: observability
spec:
  configRef: production
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/observability-metrics*"]
        }
      ],
      "AWSOwnedKey": false,
      "KmsARN": "arn:aws:kms:us-east-1:123456789012:key/abc-def-ghi"
    }
```

### Development Collection (Low Cost)

Cost-optimized collection with standby replicas disabled:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: dev-search
  namespace: dev
spec:
  configRef: development
  type: SEARCH
  standbyReplicas: "DISABLED"  # No HA to save costs
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: dev-search-encryption
  namespace: dev
spec:
  configRef: development
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/dev-dev-search*"]
        }
      ],
      "AWSOwnedKey": true
    }
```

## Immutable Fields

After collection creation, these fields cannot be changed:

- `type` — Collection type (SEARCH, TIMESERIES, VECTORSEARCH)
- `standbyReplicas` — Standby replica setting (ENABLED, DISABLED)

To change these, delete the collection and create a new one.

## Deletion Behavior

| Policy | Behavior |
|---|---|
| `retain` (default) | Serverless collection persists; K8s CR deleted |
| `delete` | Serverless collection deleted when K8s CR deleted |

## Security Considerations

- **Encryption policy required** — Collections cannot exist without a matching encryption policy
- **Name pattern matching** — Security policies use wildcard patterns to match collections (e.g., `collection/namespace-*`)
- **Public access by default** — Unless a network policy restricts access, collections are publicly accessible
- **No cloud tags** — AOSS collections don't support AWS resource tags; use K8s labels and annotations instead

## Performance and Scaling

Serverless collections automatically scale based on:

- **Search workload** — Concurrent queries and result set size
- **Ingestion workload** — Ingest rate and document size (for TIMESERIES)
- **Vector operations** — Vector dimension and similarity search complexity (for VECTORSEARCH)

No manual scaling, capacity planning, or node management required.

## Related Concepts

- **Governance profiles** — See [OpenSearchConfig](opensearchconfig.md)
- **Security policies** — See [OpenSearchSecurityPolicy](opensearchsecuritypolicy.md)
- **Managed domains alternative** — See [OpenSearchDomain](opensearchdomain.md)
- **VPC connectivity** — Collections use network security policies, not VPC endpoints (unlike managed domains)
