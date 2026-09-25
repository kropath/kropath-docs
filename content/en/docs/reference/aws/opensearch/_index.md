---
title: OpenSearch on kropath
description: Amazon OpenSearch provides managed search and analytics capabilities for logs, metrics, and application data.
doc_type: reference
weight: 380
---
# OpenSearch on kropath

Amazon OpenSearch provides managed search and analytics capabilities for logs, metrics, and application data. The kropath OpenSearch family provides governance-driven resources for deploying and managing OpenSearch Service domains (managed), Serverless collections (auto-scaling), and their associated security policies.

## Resources

- **[OpenSearchConfig](opensearchconfig.md)** — Governance profiles that define encryption, HTTPS enforcement, TLS policy, fine-grained access control, engine version, auto-tune, and standby replicas. Platform teams create named profiles; developers select a profile via `spec.configRef` on each domain, collection, or security policy.

- **[OpenSearchDomain](opensearchdomain.md)** — Managed OpenSearch Service domains with provisioning options including cluster topology, storage, VPC access, encryption, HTTPS, TLS policy, and fine-grained access control. Governance cascades from the selected `OpenSearchConfig` profile.

- **[OpenSearchCollection](opensearchcollection.md)** — Serverless OpenSearch collections for search, time-series, and vector search workloads. Collections auto-scale without cluster topology management. Security policies (encryption and network) must exist before collection creation.

- **[OpenSearchSecurityPolicy](opensearchsecuritypolicy.md)** — Encryption and network access policies for Serverless collections. Encryption policies determine key management (AWS-owned or customer-managed KMS); network policies control public vs. VPC endpoint access. Collections reference policies by name pattern in the policy JSON document.

- **[OpenSearchVPCEndpoint](opensearchvpcendpoint.md)** — VPC endpoints for private connectivity to managed OpenSearch Service domains. Applications in a VPC access the domain without traversing the public internet.

## Getting Started

### 1. Create a Governance Profile

Platform teams define governance profiles for different security and operational requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encryptionAtRestEnabled: true
    nodeToNodeEncryptionEnabled: true
    enforceHTTPS: true
  defaults:
    encryptionAtRestEnabled: true
    nodeToNodeEncryptionEnabled: true
    enforceHTTPS: true
    tlsSecurityPolicy: "Policy-Min-TLS-1-2-2019-07"
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "ENABLED"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
```

### 2. Create a Managed Domain

Developers create managed domains by specifying topology and selecting a governance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: logs
  namespace: observability
spec:
  configRef: general-policy
  instanceType: "m6g.large.search"
  instanceCount: 3
  ebsVolumeSize: 100
  encryptionAtRestEnabled: true
  nodeToNodeEncryptionEnabled: true
  enforceHTTPS: true
```

### 3. Create a Serverless Collection (Optional)

For auto-scaling workloads, create serverless collections instead:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchCollection
metadata:
  name: vector-search
  namespace: ml-services
spec:
  configRef: general-policy
  type: VECTORSEARCH
  description: "Vector embeddings for product catalog"
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchSecurityPolicy
metadata:
  name: vector-search-encryption
  namespace: ml-services
spec:
  configRef: general-policy
  type: encryption
  policy: |
    {
      "Rules": [
        {
          "ResourceType": "collection",
          "Resource": ["collection/ml-services-vector-search*"]
        }
      ],
      "AWSOwnedKey": true
    }
```

## Key Concepts

### Two-Tier Governance

Each `OpenSearchConfig` has two tiers:

- **Mandatory tier** — Platform enforcements that override developer choices (e.g., encryption, HTTPS enforcement, TLS policy)
- **Defaults tier** — Sensible defaults developers can override (e.g., engine version, auto-tune state, naming pattern)

### Encryption and Security

- **Encryption at rest** — Protects data on disk; can use AWS-managed or customer-managed KMS keys
- **Node-to-node encryption** — Encrypts traffic between cluster nodes
- **HTTPS enforcement** — Requires encrypted communication to the domain
- **TLS policy** — Controls minimum TLS version and cipher suites
- **Fine-grained access control (FGAC)** — Optional advanced security with per-user/per-index permissions; requires master user credentials

### Domain vs. Serverless Collections

**Managed Domains:**
- Full cluster control: node types, count, dedicated masters, multi-AZ topology
- Scaling requires manual intervention
- Best for: predictable workloads with specific topology requirements
- Billing: hourly per node

**Serverless Collections:**
- AWS manages all topology and scaling
- No cluster configuration needed
- Best for: variable workloads with automatic scaling
- Billing: on-demand per operation
- Requires separate security policies for encryption and network access

### Naming Templates

Resources are named using configurable templates. The default is `{namespace}-{name}`, but custom templates can include `{account_id}`, `{region}`, and `{tag.KEY}` tokens.

Domain naming constraints: lowercase `a-z`, digits `0-9`, hyphens `-`; must start with a lowercase letter; 3–28 characters.

Collection naming constraints: lowercase `a-z`, digits `0-9`, hyphens `-`; must start with a lowercase letter; 3–32 characters.

### VPC and Network Access

- **Public endpoint** — Domain accessible from the internet (requires HTTPS and auth)
- **VPC endpoint** — Private connectivity through VPC subnets and security groups (no public access)
- **Serverless VPC endpoints** — Network policies control public vs. VPC endpoint access for collections

### Governance Cascade

The effective configuration for each resource is determined by a ten-level priority cascade:

1. **Global `KropathConfig` mandatory** (highest priority)
2. **Namespace-local `KropathConfig` mandatory**
3. **Global `OpenSearchConfig` profile mandatory**
4. **Namespace-local `OpenSearchConfig` profile mandatory**
5. **Resource spec** (developer choice)
6. **Namespace-local `OpenSearchConfig` profile defaults**
7. **Global `OpenSearchConfig` profile defaults**
8. **Namespace-local `KropathConfig` defaults**
9. **Global `KropathConfig` defaults**
10. **RGD built-in defaults** (lowest priority)

This ensures platform teams can enforce critical controls while letting developers handle workload-specific settings.

## Common Patterns

### Multi-Environment Setup

Create separate `OpenSearchConfig` profiles for different environments:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  defaults:
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "DISABLED"  # Save costs in dev
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    encryptionAtRestEnabled: true
    nodeToNodeEncryptionEnabled: true
    enforceHTTPS: true
    advancedSecurityEnabled: true
  defaults:
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "ENABLED"
```

### PCI Compliance Profile

For regulated workloads, create a strict compliance profile:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    encryptionAtRestEnabled: true
    encryptionAtRestKmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/abc-def"  # Customer-managed key
    nodeToNodeEncryptionEnabled: true
    enforceHTTPS: true
    tlsSecurityPolicy: "Policy-Min-TLS-1-2-PFS-2023-10"  # Strict TLS with forward secrecy
    advancedSecurityEnabled: true
  defaults:
    autoTuneDesiredState: "ENABLED"
    tags:
      compliance: pci-dss
      encryption: customer-managed
```

### Private Network Setup

For domains requiring private network access only:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: internal-logs
  namespace: platform
spec:
  configRef: production
  instanceType: "m6g.large.search"
  instanceCount: 3
  ebsVolumeSize: 100
  vpcSubnetIDs:
    - "subnet-12345678"
    - "subnet-87654321"
  vpcSecurityGroupIDs:
    - "sg-opensearch-internal"
  enforceHTTPS: true  # Mandatory via config, but explicit here for clarity
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: internal-logs-endpoint
  namespace: platform
spec:
  domainRef: internal-logs
  vpcSubnetIDs:
    - "subnet-app-1"
    - "subnet-app-2"
  vpcSecurityGroupIDs:
    - "sg-opensearch-endpoint"
```
