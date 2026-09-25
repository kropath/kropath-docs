---
title: OpenSearchConfig — Governance Profiles
description: "The `OpenSearchConfig` resource defines governance profiles for the OpenSearch family."
doc_type: reference
---
# OpenSearchConfig — Governance Profiles

The `OpenSearchConfig` resource defines governance profiles for the OpenSearch family. Platform teams create named profiles with encryption, HTTPS, TLS policy, fine-grained access control, engine version, auto-tune, and standby replica settings. Developers select a profile via `spec.configRef` on each domain, collection, or security policy.

## Purpose

`OpenSearchConfig` enforces organization-wide policies for search and analytics workloads:

- **Encryption** — Mandatory encryption at rest, node-to-node encryption, KMS key selection
- **HTTPS and TLS** — Enforce encrypted communication and minimum TLS versions
- **Fine-grained access control** — Enforce or disable advanced security features
- **Engine and auto-tune** — Set minimum engine versions, auto-tune behavior
- **Serverless governance** — Control standby replica settings for Serverless collections
- **Naming and tagging** — Standardize resource names and apply org-wide tags

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | (inherited from domain/collection) | N/A | Platform developers use this on resources to select a profile |
| `mandatory` | object | required | Enforcements that cannot be overridden by developers |
| `defaults` | object | required | Sensible defaults that developers can override |

## Mandatory Tier

Fields in the mandatory tier override developer choices and cannot be bypassed. Set a field to its "not enforced" value to allow developers to choose.

### Security Fields

| Field | Type | "Not Enforced" | Enforced Example |
|---|---|---|---|
| `encryptionAtRestEnabled` | boolean | `false` | `true` — forces encryption at rest |
| `nodeToNodeEncryptionEnabled` | boolean | `false` | `true` — forces node-to-node encryption |
| `enforceHTTPS` | boolean | `false` | `true` — forces HTTPS |
| `tlsSecurityPolicy` | string | `""` | `"Policy-Min-TLS-1-2-2019-07"` — enforces TLS version and ciphers |
| `advancedSecurityEnabled` | boolean | `false` | `true` — forces fine-grained access control |

### Configuration Fields

| Field | Type | "Not Enforced" | Enforced Example |
|---|---|---|---|
| `engineVersion` | string | `""` | `"OpenSearch_2.9"` — locks engine version |
| `autoTuneDesiredState` | string | `""` | `"ENABLED"` — forces auto-tuning on or off |
| `standbyReplicas` | string | `""` | `"ENABLED"` — forces standby replicas on/off (collections only) |

### Governance Fields

| Field | Type | Purpose |
|---|---|---|
| `tags` | map | Tags merged into all resources; mandatory tags always applied |
| `syncedLabels` | map | Labels synced to Kubernetes metadata and cloud resource tags |
| `syncedAnnotations` | map | Annotations synced to Kubernetes metadata |
| `namingTemplate` | string | Naming pattern for resources (e.g., `corp-{namespace}-{name}`) |

## Defaults Tier

Fields in the defaults tier provide sensible fallbacks for developers who don't specify them. Developers can override any defaults field by setting it on their resource.

### Security Defaults

| Field | Default Value | Rationale |
|---|---|---|
| `encryptionAtRestEnabled` | `true` | Encryption is the secure default |
| `nodeToNodeEncryptionEnabled` | `true` | Cluster communication should be encrypted |
| `enforceHTTPS` | `true` | Public endpoints should require HTTPS |
| `tlsSecurityPolicy` | `"Policy-Min-TLS-1-2-2019-07"` | TLS 1.2+ blocks legacy weak ciphers |
| `advancedSecurityEnabled` | `false` | Requires additional master user setup; opt-in |

### Configuration Defaults

| Field | Default Value |
|---|---|
| `engineVersion` | `"OpenSearch_2.9"` |
| `autoTuneDesiredState` | `"ENABLED"` |
| `standbyReplicas` | `"ENABLED"` |

### Governance Defaults

| Field | Default Value |
|---|---|
| `tags` | `{}` |
| `syncedLabels` | `{}` |
| `syncedAnnotations` | `{}` |
| `namingTemplate` | `"{namespace}-{name}"` |

## Example Profiles

### General Production Profile

A balanced profile for most production workloads:

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
      environment: production
```

### Development Profile (Cost-Optimized)

For development and testing, with lower defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}  # No enforcements; developers choose
  defaults:
    encryptionAtRestEnabled: true
    nodeToNodeEncryptionEnabled: false  # Optional for dev
    enforceHTTPS: false  # Optional for internal dev domains
    tlsSecurityPolicy: ""  # Use AWS default
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "DISABLED"  # Save costs
    standbyReplicas: "DISABLED"  # No HA needed
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      managed-by: kropath
      environment: development
```

### PCI Compliance Profile

For regulated workloads with strict encryption requirements:

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
    # Encryption must use customer-managed KMS key (enforced at domain level with encryptionAtRestKmsKeyID)
    nodeToNodeEncryptionEnabled: true
    enforceHTTPS: true
    tlsSecurityPolicy: "Policy-Min-TLS-1-2-PFS-2023-10"  # Forward secrecy required
    advancedSecurityEnabled: true  # FGAC required for audit/compliance
  defaults:
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "ENABLED"
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      managed-by: kropath
      compliance: pci-dss
      encryption: customer-managed
```

### No Encryption Profile (Non-Production Testing Only)

For isolated testing environments without security requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: testing
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: testing
spec:
  mandatory: {}  # No enforcements
  defaults:
    encryptionAtRestEnabled: false  # No encryption for test data
    nodeToNodeEncryptionEnabled: false
    enforceHTTPS: false
    tlsSecurityPolicy: ""
    engineVersion: "OpenSearch_2.9"
    autoTuneDesiredState: "DISABLED"
    standbyReplicas: "DISABLED"
    namingTemplate: "test-{namespace}-{name}"
    tags:
      managed-by: kropath
      environment: testing
```

## Governance Cascade

When a domain or collection resolves its configuration, it follows this priority order:

1. **Mandatory tier** (highest priority) — Cannot be overridden
2. **Resource spec** (developer choice) — Overrides defaults
3. **Defaults tier** (lowest priority) — Fallback if not specified

### Example Resolution

Given this `OpenSearchConfig`:

```yaml
spec:
  mandatory:
    encryptionAtRestEnabled: true
    enforceHTTPS: false  # Not enforced
  defaults:
    encryptionAtRestEnabled: true
    enforceHTTPS: true
    tlsSecurityPolicy: "Policy-Min-TLS-1-2-2019-07"
```

And a domain spec like:

```yaml
spec:
  encryptionAtRestEnabled: false  # Developer tries to disable
  enforceHTTPS: false             # Developer disables
  tlsSecurityPolicy: ""           # Not set
```

The result is:

- `encryptionAtRestEnabled`: **`true`** (mandatory wins over developer's `false`)
- `enforceHTTPS`: **`false`** (developer's choice wins; mandatory not set)
- `tlsSecurityPolicy`: **`"Policy-Min-TLS-1-2-2019-07"`** (defaults applied)

## Multi-Profile Setup

Platform teams typically create multiple profiles for different use cases. Developers select the appropriate profile for their workload:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  # General production settings
  mandatory:
    encryptionAtRestEnabled: true
  defaults:
    autoTuneDesiredState: "ENABLED"
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  # PCI-specific requirements
  mandatory:
    encryptionAtRestEnabled: true
    tlsSecurityPolicy: "Policy-Min-TLS-1-2-PFS-2023-10"
    advancedSecurityEnabled: true
```

Developers then select a profile on their resource:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: logs
spec:
  configRef: general-policy  # Use general-policy profile
```

## Naming Templates

The `namingTemplate` field supports dynamic tokens for generating resource names:

| Token | Replaced with | Example |
|---|---|---|
| `{name}` | CR metadata.name | `my-domain` |
| `{namespace}` | CR metadata.namespace | `observability` |
| `{account_id}` | AWS account ID | `123456789012` |
| `{region}` | AWS region | `us-east-1` |
| `{tag.KEY}` | Value of tag KEY (mandatory or instance tags) | `production` (from `tag.env`) |
| `{configRef}` | Profile name | `general-policy` |

### Template Examples

- `"{namespace}-{name}"` → `observability-logs`
- `"{account_id}-{region}-{name}"` → `123456789012-us-east-1-logs`
- `"prod-{namespace}-{name}"` → `prod-observability-logs`
- `"{tag.env}-{namespace}-{name}"` (with tag `env: production`) → `production-observability-logs`

### Naming Constraints

**Managed domains:**
- Lowercase `a-z`, digits `0-9`, hyphens `-`
- Must start with a lowercase letter
- 3–28 characters
- Pattern: `^[a-z][a-z0-9\-]{2,27}$`

**Serverless collections:**
- Lowercase `a-z`, digits `0-9`, hyphens `-`
- Must start with a lowercase letter
- 3–32 characters
- Pattern: `^[a-z][a-z0-9-]{2,31}$`

## Related Concepts

- **Two-tier governance** — See the [OpenSearch on kropath guide](index.md#two-tier-governance)
- **Governance cascade** — See the [full cascade documentation](index.md#governance-cascade)
- **Domain provisioning** — See [OpenSearchDomain](opensearchdomain.md)
- **Serverless collections** — See [OpenSearchCollection](opensearchcollection.md)
- **Security policies** — See [OpenSearchSecurityPolicy](opensearchsecuritypolicy.md)
