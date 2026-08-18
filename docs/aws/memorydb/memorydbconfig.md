# MemoryDBConfig — Governance and Policy Profiles

The `MemoryDBConfig` CRD defines governance policies for MemoryDB resources. Platform teams deploy named profiles (`general-policy`, `production`, `dev`) to enforce compliance, security, and operational standards across all clusters, users, ACLs, and supporting resources.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which governance profile to apply (all MemoryDB resources reference this) |

This is a *namespace-scoped* resource. Resources in the same namespace inherit governance from the named profile in `kro-system` (cluster-wide) and in the resource's namespace (local overrides).

### Mandatory vs. Defaults Tiers

**`mandatory`** — Enforces settings that cannot be overridden by resource specs; used for compliance and security enforcement.

**`defaults`** — Provides sensible values when resource specs are empty; resources can override defaults but not mandatory settings.

## Governance Fields

| Field | Type | Mandatory Default | Defaults Default | Purpose |
|---|---|---|---|---|
| `tlsEnabled` | boolean | false | true | Force or suggest TLS in-transit encryption |
| `kmsKeyArn` | string | "" | "" | Force or suggest KMS encryption key for at-rest encryption |
| `nodeType` | string | "" | "" | Force or suggest compute/memory node type (e.g. `db.r7g.large`) |
| `engineVersion` | string | "" | "" | Force or suggest Redis engine version (e.g. `7.1.0`) |
| `allowedNodeTypes` | array | [] | [] | Allowlist of permitted node types; overridable per-instance via `allowedNodeTypes` |
| `numReplicasPerShard` | integer | 0 | 1 | Minimum or suggested replicas per shard for HA |
| `snapshotRetentionLimit` | integer | 0 | 7 | Minimum or suggested automatic snapshot retention days |
| `autoMinorVersionUpgrade` | boolean | false | true | Force or suggest automatic engine minor-version updates |
| `namingTemplate` | string | "" | "{namespace}-{name}" | Template for generating resource names |
| `tags` | map | {} | {} | Mandatory or default AWS tags (merged across tiers) |
| `syncedLabels` | map | {} | {} | Labels synced to both K8s and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | {} | {} | Annotations synced to K8s (prefixed `aws.kropath.run/`) |

## Complete Example: Production Policy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production  # auto-injected by controller

spec:
  mandatory:
    # Security: enforce TLS and encryption
    tlsEnabled: true
    kmsKeyArn: "arn:aws:kms:ap-southeast-2:123456789012:key/abc12345-1234-1234-1234-abcdef123456"
    
    # HA: require replicas
    numReplicasPerShard: 2
    
    # Backup: enforce retention
    snapshotRetentionLimit: 30
    
    # Updates: disable auto-upgrade (manual control)
    autoMinorVersionUpgrade: false
    
    # Node type restriction
    allowedNodeTypes:
      - db.r7g.large
      - db.r7g.xlarge
      - db.r7g.2xlarge
    
    # Mandatory tags
    tags:
      cost-centre: platform
      compliance: pci-dss
      service: memorydb
    
    # Synced metadata (K8s + AWS)
    syncedLabels:
      environment: production
      data-classification: internal
    
  defaults:
    # Sensible defaults when mandatory not set
    tlsEnabled: true
    engineVersion: "7.1.0"
    numReplicasPerShard: 1
    snapshotRetentionLimit: 7
    autoMinorVersionUpgrade: true
    nodeType: "db.r7g.large"
    
    # Naming template with tag substitution
    namingTemplate: "prod-{namespace}-{name}"
    
    tags:
      team: platform
```

## Governance Cascade

Each field follows the ten-level governance cascade (Kubernetes namespace → organization-wide). The controller pre-merges `KropathConfig` and `MemoryDBConfig` tiers, writing the result to `status.effectiveConfig`.

Resource specs read `status.effectiveConfig` and apply the cascade rule:

```
mandatory (if set) → instance spec → defaults (if set)
```

**Example: TLS enforcement**

```yaml
# MemoryDBConfig/production has mandatory.tlsEnabled: true
# MemoryDBCluster instance has spec.tlsEnabled: false

# Result: Cluster CR spec.tlsEnabled is FORCED to true (mandatory wins)
```

**Example: Node type with allowlist**

```yaml
# MemoryDBConfig/production has:
#   mandatory.allowedNodeTypes: [db.r7g.large, db.r7g.xlarge]
#   mandatory.nodeType: "" (not set in mandatory)
# MemoryDBCluster instance has spec.nodeType: "db.t4g.small"

# Result: Instance spec.nodeType REJECTED (not in allowedNodeTypes)
```

## Immutability Constraints

The `x-kubernetes-validations` rule prevents setting the same field in both mandatory and defaults tiers simultaneously:

```yaml
# INVALID — tlsEnabled cannot be true in both tiers
spec:
  mandatory:
    tlsEnabled: true
  defaults:
    tlsEnabled: true  # ERROR: validates and rejects
```

This prevents ambiguous governance — each tier has a clear, distinct purpose.

## Tagging and Label Sync

**Tags** and **Synced Labels/Annotations** follow additive merge semantics:

1. Org-wide tags from `KropathConfig.spec.mandatory.tags` and `.defaults.tags`
2. MemoryDB-family tags from `MemoryDBConfig.spec.mandatory.tags` and `.defaults.tags`
3. Instance-specific tags from `spec.tags`

All are merged (union) into the final cluster. Mandatory tags cannot be removed by instances.

**Example: Multi-level tag merge**

```yaml
# KropathConfig
spec:
  mandatory:
    tags:
      cost-centre: platform
      compliance: pci-dss
  defaults:
    tags:
      backup-policy: weekly

# MemoryDBConfig
spec:
  mandatory:
    tags:
      service: memorydb
  defaults:
    tags:
      team: platform

# MemoryDBCluster instance
spec:
  tags:
    app: sessions

# Result in ACK Cluster spec.tags (after merge):
#   cost-centre: platform (mandatory org-wide)
#   compliance: pci-dss (mandatory org-wide)
#   service: memorydb (mandatory MemoryDB)
#   backup-policy: weekly (default org-wide)
#   team: platform (default MemoryDB)
#   app: sessions (instance)
```

## Naming Template Syntax

The `namingTemplate` field supports these tokens:

| Token | Replaced With |
|-------|---|
| `{namespace}` | Kubernetes namespace of the resource |
| `{name}` | Kubernetes metadata.name of the resource |
| `{account_id}` | AWS account ID (from effectiveConfig) |
| `{region}` | AWS region (from effectiveConfig) |
| `{configRef}` | The configRef string (e.g. `production`) |
| `{tag.KEY}` | Value of tag `KEY` from merged tags (e.g. `{tag.env}`) |

**Example templates:**

```yaml
# Standard namespace-based naming
namingTemplate: "{namespace}-{name}"
# Result: cache-prod-session-store

# Environment-aware naming
namingTemplate: "{tag.env}-{namespace}-{name}"
# Result: prod-cache-prod-session-store (if tag.env=prod)

# Account + region + name
namingTemplate: "{account_id}-{region}-{name}"
# Result: 123456789012-ap-southeast-2-session-store
```

**AWS constraints for cluster names:**
- 1–40 characters
- Must begin with a letter
- Alphanumeric and hyphens only
- Cannot end with a hyphen
- No consecutive hyphens
- Case-insensitive (stored lowercase)

If the effective name violates these constraints, `status.namingStatus: invalid-unresolved-tokens` and the resource reconciliation pauses.

## Status Fields

After `MemoryDBConfig` is created, the controller writes:

```yaml
status:
  effectiveConfig:
    mandatory:
      tlsEnabled: true
      kmsKeyArn: "arn:aws:kms:..."
      nodeType: "db.r7g.large"
      allowedNodeTypes: [db.r7g.large, db.r7g.xlarge, db.r7g.2xlarge]
      numReplicasPerShard: 2
      snapshotRetentionLimit: 30
      autoMinorVersionUpgrade: false
      namingTemplate: "prod-{namespace}-{name}"
      tags: {cost-centre: platform, ...}
      syncedLabels: {environment: production, ...}
      syncedAnnotations: {...}
    defaults:
      tlsEnabled: true
      engineVersion: "7.1.0"
      ...
    aws:
      region: "ap-southeast-2"
      accountId: "123456789012"
  conditions:
    - type: Valid
      status: "True"
      message: "All fields valid"
```

RGDs read this `status.effectiveConfig` to resolve the governance cascade.

## Complete Example: Multi-Profile Setup

```yaml
---
# General/default policy (permissive)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    tlsEnabled: true
    numReplicasPerShard: 1
    snapshotRetentionLimit: 7
    autoMinorVersionUpgrade: true

---
# Dev policy (low cost)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBConfig
metadata:
  name: dev-policy
  namespace: kro-system
spec:
  defaults:
    tlsEnabled: false
    numReplicasPerShard: 0
    snapshotRetentionLimit: 1
    autoMinorVersionUpgrade: true
    nodeType: "db.t4g.small"

---
# Production policy (strict)
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    tlsEnabled: true
    kmsKeyArn: "arn:aws:kms:..."
    numReplicasPerShard: 2
    snapshotRetentionLimit: 30
    allowedNodeTypes: [db.r7g.large, db.r7g.xlarge]
    tags:
      compliance: pci-dss
      cost-centre: platform

---
# A dev cluster using dev policy
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: dev-cache
  namespace: app-dev
spec:
  configRef: dev-policy
  nodeType: db.t4g.small
  # ... other fields

---
# A prod cluster using production policy
apiVersion: aws.kropath.run/v1alpha1
kind: MemoryDBCluster
metadata:
  name: prod-cache
  namespace: app-prod
spec:
  configRef: production
  # ... other fields (mandatory fields enforced, defaults applied)
```

## Common Patterns

### Require TLS and Modern Engine

```yaml
spec:
  mandatory:
    tlsEnabled: true
    engineVersion: "7.1.0"
```

### Enforce Backup Compliance

```yaml
spec:
  mandatory:
    snapshotRetentionLimit: 14  # minimum 2 weeks
    autoMinorVersionUpgrade: false  # manual control for compliance
```

### Restrict Node Types (Cost Control)

```yaml
spec:
  mandatory:
    allowedNodeTypes:
      - db.t4g.micro
      - db.t4g.small
      - db.r7g.large
  # Anything else is rejected
```

### Standardize Naming

```yaml
spec:
  defaults:
    namingTemplate: "{namespace}-{name}-{tag.env}"
```

## Additional Resources

- **Governance cascade semantics:** [ADR-015](https://github.com/kropath/kropath-core/blob/main/docs/adrs/adr-015-governance-and-k8s-metadata.md)
- **KropathConfig organization-wide governance:** [KropathConfig](../resources/kro-controller-configuration.md)
- **Naming templates with tag substitution:** [Naming Template — Dynamic Tags](../resources/naming-template-dynamic-tags.md)
