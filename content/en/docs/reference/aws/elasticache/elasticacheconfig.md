---
title: ElastiCacheConfig — Governance and Compliance Profiles
description: "The `ElastiCacheConfig` resource defines governance policies for all ElastiCache resources in your organization."
doc_type: reference
---
# ElastiCacheConfig — Governance and Compliance Profiles

The `ElastiCacheConfig` resource defines governance policies for all ElastiCache resources in your organization. Platform teams create named profiles (e.g., `general-policy`, `pci`, `production`) that codify encryption requirements, high availability settings, engine restrictions, and naming conventions. ElastiCache resource instances select a profile via `spec.configRef` to inherit those policies.

## Core Concepts

**Mandatory Tier** — Policies that cannot be overridden. Use for compliance requirements (e.g., PCI-DSS encryption enforcement).

**Defaults Tier** — Sensible baselines that developers can override. Use for standard recommendations (e.g., secure-by-default values).

The kropath controller pre-merges both tiers and all KropathConfig org-wide settings into a single `status.effectiveConfig` that all ElastiCache resources read.

## Governance Fields

| Field | Purpose | Mandatory | Defaults |
|---|---|---|---|
| `atRestEncryptionEnabled` | Enforce encryption of data at rest using KMS | true = always encrypt, false = not enforced | true = secure by default, false = not enforced |
| `transitEncryptionEnabled` | Enforce TLS encryption for data in transit | true = always use TLS, false = not enforced | true = secure by default, false = not enforced |
| `automaticFailoverEnabled` | Require automatic failover on replication group failure | true = always enable, false = not enforced | true = HA by default, false = optional |
| `multiAZEnabled` | Require Multi-AZ replication | true = always enable, false = not enforced | true = HA by default, false = optional |
| `engine` | Restrict cache engine choice | "" (empty) = not enforced | "valkey" \| "redis" \| "memcached"; default = "valkey" |
| `blockNoPasswordUsers` | Prevent password-less authentication (RBAC for Valkey/Redis 6+) | true = block, false = not enforced | false = allow, true = enforce |
| `snapshotRetentionLimit` | Minimum snapshot retention floor (days) | 0 (zero) = not enforced; N > 0 = minimum floor | N = default retention days |
| `namingTemplate` | Enforce or suggest naming pattern | Sets pattern (template tokens); "" = not enforced | "{namespace}-{name}" by default |
| `tags` | AWS tags for all resources | Merged into all ElastiCache resource tags | Baseline tags for resources to inherit |
| `syncedLabels` | Kubernetes labels and AWS tags | Merged into all resources | Baseline synced labels |
| `syncedAnnotations` | Kubernetes annotations | Merged into all resources | Baseline synced annotations |

## Core Fields

### Governance Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Profile name; selected by resources via `spec.configRef` |
| `namespace` | string | required | Always `kro-system` for org-wide profiles; can be namespaced for local policies |

### Spec Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: production      # Profile name referenced by resources
  namespace: kro-system # Global namespace for org-wide policies
spec:
  mandatory: {}         # Policies that cannot be overridden
  defaults: {}          # Sensible baselines that can be overridden
```

## Status Outputs

After the controller reconciles an `ElastiCacheConfig`, the `status.effectiveConfig` contains the merged governance:

| Field | Type | Purpose |
|---|---|---|
| `status.effectiveConfig.mandatory.*` | object | Merged mandatory policies from `KropathConfig` levels 1–2 and `ElastiCacheConfig` level 3 |
| `status.effectiveConfig.defaults.*` | object | Merged defaults from `KropathConfig` levels 8–9 and `ElastiCacheConfig` levels 6–7 |
| `status.effectiveConfig.aws.region` | string | AWS region from `KropathConfig` |
| `status.effectiveConfig.aws.accountId` | string | AWS account ID from `KropathConfig` |

All ElastiCache RGDs read this single merged view via an `externalRef` lookup.

## Field Validation

`ElastiCacheConfig` enforces mutual exclusivity on scalar fields: a field cannot be set to a non-default value in both `mandatory` and `defaults` simultaneously (maps like `tags` can appear in both and merge additively).

The CRD validates this at admission time via `x-kubernetes-validations`.

## Complete Examples

### General Policy (Secure-by-Default)

A standard profile for most workloads with secure defaults and minimal enforcement:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No enforcement; all fields optional for developers
  defaults:
    atRestEncryptionEnabled: true
    transitEncryptionEnabled: true
    automaticFailoverEnabled: true
    multiAZEnabled: true
    engine: valkey
    blockNoPasswordUsers: false
    snapshotRetentionLimit: 1
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers can override all defaults except when org-wide `KropathConfig` mandatory settings apply.

### PCI-DSS Compliance Profile

A hardened profile for payment processing workloads with mandatory encryption and backup retention:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    atRestEncryptionEnabled: true       # PCI-DSS: encryption at rest
    transitEncryptionEnabled: true      # PCI-DSS: encryption in transit
    automaticFailoverEnabled: true      # Prevent downtime during incidents
    multiAZEnabled: true                # High availability required
    engine: valkey                      # Approved engine only
    snapshotRetentionLimit: 30          # 30-day compliance retention floor
    blockNoPasswordUsers: true          # No anonymous access (OD-4)
    tags:
      compliance-scope: "pci-dss"
      data-classification: "payment-card"
  defaults:
    namingTemplate: "{namespace}-{name}-{tag.environment}"
    syncedLabels:
      audit-required: "true"
```

Resources using `configRef: pci` cannot override mandatory fields. Snapshot retention is clamped to at least 30 days.

### Production Profile (HA Enforced)

A profile that enforces high availability but allows encryption and retention flexibility:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    automaticFailoverEnabled: true
    multiAZEnabled: true
  defaults:
    atRestEncryptionEnabled: true
    transitEncryptionEnabled: true
    snapshotRetentionLimit: 7
    engine: valkey
    namingTemplate: "{namespace}-prod-{name}"
    tags:
      environment: production
      backup-required: "true"
```

Developers must accept Multi-AZ HA but can choose their encryption and retention strategy.

### Development Profile (Permissive)

A profile for non-production workloads with minimal enforcement and lower costs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ElastiCacheConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory: {}  # No enforcement for dev workloads
  defaults:
    atRestEncryptionEnabled: false
    transitEncryptionEnabled: false
    automaticFailoverEnabled: false
    multiAZEnabled: false
    engine: valkey
    snapshotRetentionLimit: 0  # No snapshots by default
    namingTemplate: "{namespace}-dev-{name}"
    tags:
      environment: development
```

Developers have full flexibility; encryption and HA are opt-in rather than default.

## Governance Cascade

The effective configuration for every ElastiCache resource is determined by merging three layers:

**Layer 1 (Org-wide, highest priority):** `KropathConfig.mandatory.elasticache` and `KropathConfig.defaults.elasticache`
- Only encryption fields (`atRestEncryptionEnabled`, `transitEncryptionEnabled`)
- Applies to every cache regardless of profile

**Layer 2 (Profile-specific):** `ElastiCacheConfig.spec.mandatory` and `ElastiCacheConfig.spec.defaults`
- All eleven governance fields
- Selected by resource's `spec.configRef`

**Layer 3 (Developer instance):** `ElastiCacheReplicationGroup.spec.engine`, `.snapshotRetentionLimit`, etc.
- Individual resource overrides
- Can override defaults but not mandatory policies

**Merge order for effective values:**
- Mandatory: KropathConfig org-wide mandatory (levels 1–2) wins over profile mandatory (levels 3–4)
- Defaults: Profile defaults (levels 6–7) override org-wide defaults (levels 8–9)
- Instance spec is evaluated against both mandatory and defaults; mandatory fields cannot be overridden

## Naming Convention

The `namingTemplate` field in `ElastiCacheConfig` defines the naming pattern for all ElastiCache resources that reference this profile. The pattern is resolved at resource creation time.

**Available tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID from `KropathConfig`
- `{region}` — AWS region from `KropathConfig`
- `{tag.KEY}` — Any tag key from the merged tags (e.g., `{tag.environment}` → "production")

**AWS Constraints:** Each resource type applies `.lowerAscii()` post-processing and enforces length/character limits specific to that resource (e.g., replication groups: 1–40 chars, lowercase alphanumeric + hyphens).

**Example:** With template `{namespace}-{tag.environment}-{name}`, a resource `my-cache` in namespace `app-team` with a tag `environment: prod` produces the name `app-team-prod-my-cache`.

## Key Behaviors

### Mutual Exclusivity on Mandatory vs Defaults

Each governance field can be set to a non-default value in either the `mandatory` tier or the `defaults` tier, but not both. The CRD validates this at admission time.

**Valid:**
```yaml
mandatory:
  atRestEncryptionEnabled: true  # Enforcement
defaults:
  atRestEncryptionEnabled: false # Or left empty (default false)
```

**Invalid:**
```yaml
mandatory:
  atRestEncryptionEnabled: true
defaults:
  atRestEncryptionEnabled: true  # Error: must be in only one tier
```

### Map Field Merging

The three tag/label/annotation map fields (`tags`, `syncedLabels`, `syncedAnnotations`) merge additively across both tiers and org-wide settings. Mandatory tags cannot be removed by developers; defaults can be overridden or supplemented.

Example:
- `KropathConfig.mandatory.tags: {cost-centre: infra}`
- `ElastiCacheConfig.mandatory.tags: {cache-tier: shared}`
- Resource `spec.tags: {team: app}`
- **Result:** All three tag sets merged together on the AWS resource

### Label Auto-Injection

The controller label operator automatically adds the label `aws.kropath.run/resource-name: <metadata.name>` to every `ElastiCacheConfig` CR. This label is used by RGDs' `externalRef` lookups to locate the config profile—no manual labeling is required.

## Troubleshooting

### "Must be set in either mandatory or defaults, not both"

An `ElastiCacheConfig` CR was rejected at admission because a governance field is set to a non-default value in both tiers. Choose one tier for that field:
- Use `mandatory` for policies that cannot be overridden
- Use `defaults` for recommendations developers can override

Fix the profile and reapply.

### Cache Resources Won't Find the Config Profile

Check:
1. The `ElastiCacheConfig` CR exists and is in the `kro-system` namespace (or matching namespace if using local policies)
2. The resource's `spec.configRef` matches the profile's `metadata.name` exactly
3. The profile has the label `aws.kropath.run/resource-name: <profile-name>` (auto-injected by the label operator)

If the profile doesn't exist, resources fall back to looking for a `general-policy` profile in the same namespace.

### "Snapshot Retention Must Be Clamped" Error

Your profile has a `mandatory.snapshotRetentionLimit: 7` (for example), but a resource is trying to set `spec.snapshotRetentionLimit: 0` (disable snapshots). The RGD enforces the mandatory floor and rejects zero. Increase the resource's retention or adjust the profile's mandatory floor.

### Tag Conflicts

If a mandatory tag key conflicts with a default or instance tag (different values), the mandatory tag always wins. Developers cannot override or remove mandatory tags. Contact your platform team if a tag needs adjustment.

## Next Steps

- Deploy a default profile: `general-policy` in `kro-system`
- Create governance profiles for your organization's compliance requirements
- Reference profiles in resource instances via `spec.configRef`
- See [ElastiCacheReplicationGroup](elasticachereplicationgroup.md) for production cache examples
