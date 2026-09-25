---
title: DSQLConfig — Governance Model for Aurora DSQL
description: "The `DSQLConfig` resource defines per-profile governance settings for Aurora DSQL clusters."
doc_type: reference
---
# DSQLConfig — Governance Model for Aurora DSQL

The `DSQLConfig` resource defines per-profile governance settings for Aurora DSQL clusters. Platform teams deploy named profiles (e.g., `general-policy`, `production`, `dev`) to codify compliance postures and enforce organization-wide security policies.

## Core Fields

### Profile Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `DSQLConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the DSQL cluster resource is deleted: `"retain"` (safe) or `"delete"` |

### Governance Fields — Mandatory Tier

The `mandatory` tier enforces organizational policies — these settings override instance-level specifications.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mandatory.deletionProtectionEnabled` | boolean | `false` | `true` = deletion protection required; `false` = not enforced |
| `mandatory.kmsEncryptionKey` | string | `""` | `""` = not enforced; non-empty = specific KMS key ARN required |
| `mandatory.tags` | map | `{}` | Mandatory AWS cloud tags (applied to all clusters using this profile) |
| `mandatory.syncedLabels` | map | `{}` | Mandatory Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `mandatory.syncedAnnotations` | map | `{}` | Mandatory Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Governance Fields — Defaults Tier

The `defaults` tier provides sensible defaults when the instance spec is empty.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaults.deletionProtectionEnabled` | boolean | `true` | Safe default when instance spec is empty: `true` = protection on |
| `defaults.kmsEncryptionKey` | string | `""` | `""` = AWS-owned key (provider default); non-empty = fallback KMS key ARN |
| `defaults.tags` | map | `{}` | Default AWS cloud tags |
| `defaults.syncedLabels` | map | `{}` | Default Kubernetes labels and AWS tags |
| `defaults.syncedAnnotations` | map | `{}` | Default Kubernetes annotations |

## Tier Semantics

### Boolean Cascades — `deletionProtectionEnabled`

Boolean governance fields use `false` as the zero-value sentinel:

- `mandatory.deletionProtectionEnabled: false` means **"do not enforce deletion protection"** (not set)
- `mandatory.deletionProtectionEnabled: true` means **"deletion protection is required"** (enforcement active)
- `defaults.deletionProtectionEnabled: true` means **"enable deletion protection when no other tier sets it"** (safe default)

The `false` value is the zero-value sentinel and does NOT force deletion protection off — it signals "not set / not enforced."

### String Cascades — `kmsEncryptionKey`

String governance fields use empty string as the zero-value sentinel:

- `mandatory.kmsEncryptionKey: ""` means **"do not enforce a specific KMS key"** (not set)
- `mandatory.kmsEncryptionKey: "arn:aws:kms:..."` means **"this specific KMS key is required"** (enforcement active)
- `defaults.kmsEncryptionKey: ""` means **"use AWS-owned KMS key when no other tier sets it"** (provider default)

## Example Profiles

### General Policy Profile

A conservative profile suitable for most clusters:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    deletionProtectionEnabled: false      # Not enforced (zero-value)
    kmsEncryptionKey: ""                  # Not enforced; AWS-owned key allowed
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    deletionProtectionEnabled: true       # Safe default: protection on
    kmsEncryptionKey: ""                  # Safe default: AWS-owned key
    tags:
      managed-by: kropath
      lifecycle: production
    syncedLabels: {}
    syncedAnnotations: {}
```

**Behavior:**
- Clusters default to deletion protection ON
- AWS-owned KMS keys allowed (clusters default to AWS-managed encryption)
- Default tags applied to all clusters using this profile

### Production Profile

A hardened profile for production workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    deletionProtectionEnabled: true       # Deletion protection required
    kmsEncryptionKey: "arn:aws:kms:us-east-1:111122223333:key/mrk-prod"
    tags:
      environment: production
      compliance: required
    syncedLabels:
      environment: production
    syncedAnnotations:
      tier: production-critical
  defaults:
    deletionProtectionEnabled: false      # Overridden by mandatory tier
    kmsEncryptionKey: ""                  # Overridden by mandatory tier
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

**Behavior:**
- Deletion protection REQUIRED (mandatory tier)
- Customer-managed KMS key REQUIRED (mandatory tier overrides instance choice)
- Production tags and labels applied to all clusters
- No cluster using this profile can disable deletion protection or use a different KMS key

### Development Profile

A permissive profile for development and testing:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory:
    deletionProtectionEnabled: false      # Not enforced
    kmsEncryptionKey: ""                  # Not enforced
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    deletionProtectionEnabled: false      # Dev default: protection off
    kmsEncryptionKey: ""                  # Dev default: AWS-owned key
    tags:
      environment: dev
      lifecycle: temporary
    syncedLabels:
      environment: dev
    syncedAnnotations: {}
```

**Behavior:**
- Deletion protection OFF by default (development convenience)
- AWS-owned keys allowed (simplicity for non-production)
- Dev tags applied for cost tracking

## Organization-Wide Governance

In addition to per-profile `DSQLConfig` settings, the `KropathConfig` CRD provides organization-wide governance for DSQL:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: kro
  namespace: kro-system
spec:
  mandatory:
    dsql:
      deletionProtectionEnabled: true     # All clusters: deletion protection required
  defaults:
    dsql:
      deletionProtectionEnabled: true     # All clusters: protection on if no profile sets it
```

**Cascade Priority:**
1. `KropathConfig.mandatory.dsql` (org-wide mandatory)
2. `DSQLConfig/<profile>.mandatory` (profile-specific mandatory)
3. Instance spec (cluster-specific override)
4. `DSQLConfig/<profile>.defaults` (profile-specific default)
5. `KropathConfig.defaults.dsql` (org-wide default)

Higher priority sources override lower ones. Example:
- If org-wide `KropathConfig.mandatory.dsql.deletionProtectionEnabled: true`, ALL clusters must have deletion protection, even if a profile's mandatory tier has `false`
- If a profile mandatory tier has `deletionProtectionEnabled: true`, the instance-level `spec.deletionProtectionEnabled: false` is overridden

## Tier Conflict Prevention

Kropath validates that conflicting settings are not applied simultaneously. The following rules prevent logical conflicts:

### Boolean Conflict Rule

You cannot set the same boolean field to `true` in both `mandatory` and `defaults`:

```yaml
spec:
  mandatory:
    deletionProtectionEnabled: true   # Enforce: deletion protection required
  defaults:
    deletionProtectionEnabled: true   # Default: deletion protection on
```

This is rejected by `x-kubernetes-validations` with the error:
```
deletionProtectionEnabled cannot be set to true in both mandatory and defaults
```

**Rationale:** Setting both to `true` is redundant and signals a misconfiguration. Use:
- Mandatory tier only: enforcement, optional fallback to AWS default
- Defaults tier only: soft guidance when instance spec is empty

### String Conflict Rule

You cannot set the same string field to non-empty values in both `mandatory` and `defaults`:

```yaml
spec:
  mandatory:
    kmsEncryptionKey: "arn:aws:kms:us-east-1:111122223333:key/mrk-prod"
  defaults:
    kmsEncryptionKey: "arn:aws:kms:us-east-1:111122223333:key/mrk-default"
```

This is rejected with the error:
```
kmsEncryptionKey cannot be set in both mandatory and defaults
```

**Rationale:** If mandatory tier specifies a key, defaults are never consulted. Setting both signals confusion about intent.

## Complete Example: Three-Tier Profile System

A typical organization deploying three profiles:

```yaml
---
# General policy: conservative defaults, flexible
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    deletionProtectionEnabled: false
    kmsEncryptionKey: ""
  defaults:
    deletionProtectionEnabled: true
    kmsEncryptionKey: ""
---
# Production: hardened, strict governance
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    deletionProtectionEnabled: true
    kmsEncryptionKey: "arn:aws:kms:us-east-1:111122223333:key/mrk-prod"
    tags:
      environment: production
      soc2: required
    syncedLabels:
      tier: critical
  defaults:
    deletionProtectionEnabled: false
    kmsEncryptionKey: ""
---
# Development: permissive, test-friendly
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLConfig
metadata:
  name: dev
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dev
spec:
  mandatory:
    deletionProtectionEnabled: false
    kmsEncryptionKey: ""
  defaults:
    deletionProtectionEnabled: false
    kmsEncryptionKey: ""
    tags:
      environment: dev
```

## Cluster Usage

Clusters reference profiles via `spec.configRef`:

```yaml
# Uses the 'production' profile — mandatory deletion protection and KMS key enforced
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: prod-db
  namespace: payments
spec:
  configRef: production
  # deletionProtectionEnabled omitted → mandatory tier enforces true
  # kmsKeyArn omitted → mandatory tier enforces production key ARN

---
# Uses the 'dev' profile — permissive defaults
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: test-db
  namespace: sandbox
spec:
  configRef: dev
  # Defaults allow deletion protection OFF and AWS-owned keys
```

## Default Fallback

If a `DSQLCluster` references a profile that does not exist, kropath falls through to `general-policy`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: DSQLCluster
metadata:
  name: my-cluster
  namespace: production
spec:
  configRef: nonexistent-profile  # Profile does not exist
  # Falls through to: configRef = "general-policy"
```

This ensures clusters always have some governance applied, even if a profile is misconfigured.

## Status Fields

After deployment, the `DSQLConfig` CR exposes the controller-computed `status.effectiveConfig` — the pre-merged result of org-wide (`KropathConfig`) + profile-specific (`DSQLConfig`) + instance cascade:

```yaml
status:
  effectiveConfig:
    mandatory:
      deletionProtectionEnabled: true       # Final mandatory value
      kmsEncryptionKey: "arn:aws:kms:..."   # Final mandatory key
      tags:
        environment: production
        cost-center: platform
      syncedLabels:
        environment: production
      syncedAnnotations: {}
    defaults:
      deletionProtectionEnabled: true
      kmsEncryptionKey: ""
      tags: {...}
      syncedLabels: {}
      syncedAnnotations: {}
```

Clusters read `effectiveConfig` from the referenced profile to determine final governance values.

## Next Steps

- [DSQLCluster Usage Guide](./dsqlcluster.md) — How to create and manage clusters within governance profiles
- [Aurora DSQL Family Overview](./index.md) — High-level concepts and quick start
