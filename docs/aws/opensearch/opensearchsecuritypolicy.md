# OpenSearchSecurityPolicy — Serverless Access Control

The `OpenSearchSecurityPolicy` resource manages encryption and network access policies for OpenSearch Serverless collections. Security policies are defined as JSON documents that reference collections by name pattern, controlling key management (encryption) and endpoint access (network).

## Purpose

`OpenSearchSecurityPolicy` provides fine-grained control over Serverless collection security:

- **Encryption policies** — Configure AWS-owned or customer-managed KMS key usage
- **Network policies** — Control public vs. VPC endpoint access
- **Collection matching** — Use wildcard patterns to target collections by name

## How It Works

Security policies are prerequisites for collection creation. A collection requires:

1. **At least one encryption policy** matching the collection name pattern
2. **Optionally one network policy** to restrict access (default is public)

The collection references policies implicitly by matching its name against the pattern in the policy JSON document.

### Policy Lookup

When a collection is created, Serverless checks if security policies exist with matching name patterns:

1. Look for encryption policy with `Resource` pattern matching the collection name
2. Look for network policy with `Resource` pattern matching the collection name
3. If encryption policy not found, collection creation fails
4. If network policy not found, default to public access

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `OpenSearchConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the policy name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` keeps policy; `"delete"` removes it |

### Policy Definition

| Field | Type | Default | Purpose |
|---|---|---|---|
| `type` | string | required | Policy type: `"encryption"` or `"network"` |
| `description` | string | `""` | Human-readable description of the policy |
| `policy` | string | required | JSON policy document (schema depends on type) |

### Tags and Governance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | K8s metadata tags (AOSS policies don't support cloud resource tags) |
| `syncedLabels` | map | `{}` | Labels synced to K8s metadata |
| `syncedAnnotations` | map | `{}` | Annotations synced to K8s metadata |

## Status Fields

After creation, the policy reports:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | Effective policy name after naming template substitution |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` (if template has unresolved tokens) |
| `conditions` | array | Standard Kubernetes conditions (Ready, Reconciling, etc.) |

## Encryption Policies

Encryption policies define which KMS key protects collections. All Serverless collections must have a matching encryption policy.

### AWS-Owned Key

AWS manages the key, no extra KMS costs:

```json
{
  "Rules": [
    {
      "ResourceType": "collection",
      "Resource": ["collection/my-app-*"]
    }
  ],
  "AWSOwnedKey": true
}
```

### Customer-Managed KMS Key

You control the key, additional KMS charges apply:

```json
{
  "Rules": [
    {
      "ResourceType": "collection",
      "Resource": ["collection/my-app-*"]
    }
  ],
  "AWSOwnedKey": false,
  "KmsARN": "arn:aws:kms:us-east-1:123456789012:key/abc-def-ghi-jkl"
}
```

## Network Policies

Network policies control how collections are accessed. If no network policy matches a collection, the default is public access.

### Public Access (Default)

Allow access from the internet (requires HTTPS auth):

```json
{
  "Rules": [
    {
      "ResourceType": "collection",
      "Resource": ["collection/public-*"]
    }
  ],
  "AllowFromPublic": true
}
```

### VPC Endpoint Only

Restrict access to VPC endpoints only (no public access):

```json
{
  "Rules": [
    {
      "ResourceType": "collection",
      "Resource": ["collection/private-*"]
    }
  ],
  "AllowFromPublic": false,
  "SourceVPCEs": ["vpce-12345678", "vpce-87654321"]
}
```

## Name Pattern Matching

Policies match collections using resource patterns with wildcards:

| Pattern | Matches |
|---|---|
| `collection/my-collection` | Exact collection name only |
| `collection/my-collection*` | `my-collection`, `my-collection-v2`, `my-collection-prod`, etc. |
| `collection/prod-*` | `prod-search`, `prod-analytics`, `prod-embeddings`, etc. |
| `collection/*-metrics` | `app-metrics`, `platform-metrics`, etc. |

## Governance Cascade

Security policies follow the standard governance cascade for naming and tagging:

1. **OpenSearchConfig mandatory tier** (highest priority)
2. **Policy spec** (developer choice)
3. **OpenSearchConfig defaults tier** (lowest priority)

Note: `type` and `policy` fields are not governance-enforced. Only naming and tagging cascade.

## Naming

The effective policy name is computed from:

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

### Basic Encryption Policy with AWS-Owned Key

For development and non-sensitive workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: dev-encryption
  namespace: dev
spec:
  configRef: development
  type: encryption
  description: "Encryption policy for dev collections with AWS-owned keys"
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/dev-*"]
        }
      ],
      "AWSOwnedKey": true
    }
```

### Customer-Managed KMS Key Policy

For production workloads with compliance requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: prod-encryption-cmk
  namespace: observability
spec:
  configRef: production
  type: encryption
  description: "Encryption policy for production with customer-managed KMS key"
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/observability-*"]
        }
      ],
      "AWSOwnedKey": false,
      "KmsARN": "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    }
```

### Network Policy Restricting to VPC

For private collections accessible only via VPC endpoints:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: private-network
  namespace: internal
spec:
  configRef: production
  type: network
  description: "Network policy restricting to VPC endpoints"
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/internal-*"]
        }
      ],
      "AllowFromPublic": false,
      "SourceVPCEs": ["vpce-internal-api"]
    }
```

### Combined Setup for Sensitive Data

Encryption with CMK + network restriction:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: sensitive-encryption
  namespace: compliance
spec:
  configRef: pci
  type: encryption
  description: "PCI-compliant encryption with customer-managed key"
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/compliance-*"]
        }
      ],
      "AWSOwnedKey": false,
      "KmsARN": "arn:aws:kms:us-east-1:123456789012:key/cmk-sensitive-data"
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: sensitive-network
  namespace: compliance
spec:
  configRef: pci
  type: network
  description: "PCI-compliant network policy (VPC only)"
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/compliance-*"]
        }
      ],
      "AllowFromPublic": false,
      "SourceVPCEs": ["vpce-compliant-apps"]
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: customer-data
  namespace: compliance
spec:
  configRef: pci
  type: SEARCH
  description: "Customer data index (PCI compliance required)"
```

### Multiple Collection Groups with Different Policies

Using multiple policies and wildcard patterns:

```yaml
---
# Public analytics collections (AWS-owned key)
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: analytics-public
spec:
  type: encryption
  policy: |
    {
      "Rules": [{"ResourceType": "collection", "Resource": ["collection/analytics-*"]}],
      "AWSOwnedKey": true
    }
---
# Private internal collections (CMK + VPC restricted)
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: internal-encryption
spec:
  type: encryption
  policy: |
    {
      "Rules": [{"ResourceType": "collection", "Resource": ["collection/internal-*"]}],
      "AWSOwnedKey": false,
      "KmsARN": "arn:aws:kms:us-east-1:123456789012:key/internal"
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: internal-network
spec:
  type: network
  policy: |
    {
      "Rules": [{"ResourceType": "collection", "Resource": ["collection/internal-*"]}],
      "AllowFromPublic": false,
      "SourceVPCEs": ["vpce-internal"]
    }
```

## Policy Updates

When updating a security policy's JSON document:

1. Edit the `spec.policy` field with the new JSON
2. Apply the change
3. The ACK controller handles version management internally (transparent to you)

## Best Practices

- **Namespace your patterns** — Use `collection/namespace-*` to isolate by namespace or team
- **Create policies before collections** — Ensure encryption policy exists before creating a matching collection
- **Use descriptive descriptions** — Help team members understand policy purpose and scope
- **Review network access** — Explicitly decide between public and VPC-only access
- **CMK for compliance** — Use customer-managed keys for regulatory/compliance requirements
- **Centralize governance** — Store policies in platform namespace (`kro-system` or similar)

## Related Concepts

- **Serverless collections** — See [OpenSearchCollection](opensearchcollection.md)
- **Governance profiles** — See [OpenSearchConfig](opensearchconfig.md)
- **Managed domains** — See [OpenSearchDomain](opensearchdomain.md)
- **KMS key management** — See AWS KMS documentation
