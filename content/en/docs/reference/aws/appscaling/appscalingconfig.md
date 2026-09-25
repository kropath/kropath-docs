---
title: AppScalingConfig — Governance Model for Application Auto Scaling
description: "The `AppScalingConfig` resource defines per-profile governance settings for Application Auto Scaling."
doc_type: reference
---
# AppScalingConfig — Governance Model for Application Auto Scaling

The `AppScalingConfig` resource defines per-profile governance settings for Application Auto Scaling. Platform teams deploy named profiles (e.g., `general-policy`, `production`, `cost-optimized`) to codify scaling compliance postures and enforce organization-wide scaling policies.

## Core Fields

### Profile Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `AppScalingConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when the scaling resource is deleted: `"retain"` (safe, keep AWS resource) or `"delete"` |

### Governance Fields — Mandatory Tier

The `mandatory` tier enforces organizational policies — these settings override instance-level specifications for all resources using this profile.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mandatory.minCapacity` | integer | `0` | `0` = not enforced; `> 0` = minimum capacity floor required |
| `mandatory.maxCapacity` | integer | `0` | `0` = not enforced; `> 0` = maximum capacity ceiling required |
| `mandatory.disableScaleIn` | boolean | `false` | `false` = not enforced; `true` = scale-in protection required |
| `mandatory.scaleInCooldown` | integer | `0` | `0` = not enforced; `> 0` = minimum scale-in cooldown (seconds) required |
| `mandatory.scaleOutCooldown` | integer | `0` | `0` = not enforced; `> 0` = minimum scale-out cooldown (seconds) required |
| `mandatory.tags` | map | `{}` | Mandatory AWS cloud tags (applied to all resources using this profile) |
| `mandatory.syncedLabels` | map | `{}` | Mandatory Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `mandatory.syncedAnnotations` | map | `{}` | Mandatory Kubernetes annotations (prefixed `aws.kropath.run/`) |

### Governance Fields — Defaults Tier

The `defaults` tier provides sensible defaults when the instance spec is empty.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaults.minCapacity` | integer | `1` | Safe default: at least 1 instance when no other tier sets it |
| `defaults.maxCapacity` | integer | `10` | Safe default: cap at 10 when no other tier sets it |
| `defaults.disableScaleIn` | boolean | `false` | Safe default: scale-in allowed when no other tier sets it |
| `defaults.scaleInCooldown` | integer | `300` | Safe default: 5 minutes between scale-in events |
| `defaults.scaleOutCooldown` | integer | `60` | Safe default: 1 minute between scale-out events |
| `defaults.tags` | map | `{}` | Default AWS cloud tags |
| `defaults.syncedLabels` | map | `{}` | Default Kubernetes labels and AWS tags |
| `defaults.syncedAnnotations` | map | `{}` | Default Kubernetes annotations |

## Tier Semantics

### Integer Cascades — `minCapacity`, `maxCapacity`, `scaleInCooldown`, `scaleOutCooldown`

Integer governance fields use `0` as the zero-value sentinel:

- `mandatory.minCapacity: 0` means **"do not enforce a minimum capacity"** (not set)
- `mandatory.minCapacity: 2` means **"minimum capacity of 2 required"** (enforcement active)
- `defaults.minCapacity: 1` means **"use 1 as minimum when no other tier sets it"** (safe default)

The `0` value signals "not set / not enforced," not a literal zero. Instance-level `spec.minCapacity: 0` is valid and will be used when no mandatory tier enforces a higher value.

### Boolean Cascades — `disableScaleIn`

Boolean governance fields use `false` as the zero-value sentinel:

- `mandatory.disableScaleIn: false` means **"do not enforce scale-in protection"** (not set)
- `mandatory.disableScaleIn: true` means **"scale-in protection is required"** (enforcement active)
- `defaults.disableScaleIn: false` means **"scale-in is allowed when no other tier sets it"** (default behavior)

The `false` value signals "not set / not enforced," not an explicit "allow scale-in."

### Maps — `tags`, `syncedLabels`, `syncedAnnotations`

All map fields use **additive merge semantics** — no conflict prevention needed. All values from all tiers are combined.

## Example Profiles

### General Policy Profile

A conservative profile suitable for most workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    minCapacity: 0                    # Not enforced
    maxCapacity: 0                    # Not enforced
    disableScaleIn: false             # Not enforced
    scaleInCooldown: 0                # Not enforced
    scaleOutCooldown: 0               # Not enforced
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    minCapacity: 1                    # Safe default: at least 1 instance
    maxCapacity: 10                   # Safe default: cap at 10
    disableScaleIn: false             # Safe default: scale-in allowed
    scaleInCooldown: 300              # Safe default: 5 min between scale-in
    scaleOutCooldown: 60              # Safe default: 1 min between scale-out
    tags:
      managed-by: kropath
      lifecycle: general
    syncedLabels: {}
    syncedAnnotations: {}
```

**Behavior:**
- Resources default to 1–10 capacity range
- Scale-in allowed (no protection)
- Standard cooldown periods (5 min scale-in, 1 min scale-out)
- Default tags applied to all resources using this profile

### Production Profile

A hardened profile for production workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    minCapacity: 2                    # Minimum 2 instances (HA requirement)
    maxCapacity: 100                  # Maximum 100 (cost control)
    disableScaleIn: true              # Scale-in protection required
    scaleInCooldown: 600              # Minimum 10 min between scale-in
    scaleOutCooldown: 0               # Not enforced; scale-out can be faster
    tags:
      environment: production
      compliance: required
      cost-center: operations
    syncedLabels:
      environment: production
      tier: critical
    syncedAnnotations:
      sla-level: business-critical
  defaults:
    minCapacity: 1
    maxCapacity: 10
    disableScaleIn: false
    scaleInCooldown: 300
    scaleOutCooldown: 60
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

**Behavior:**
- ALL resources: minimum 2 instances (HA enforced)
- ALL resources: scale-in protection required (cost safety)
- ALL resources: maximum 100 capacity (cost control)
- Production tags and labels applied automatically
- Resources cannot opt out of minimum capacity or scale-in protection

### Cost-Optimized Profile

A profile that allows scale-to-zero and aggressive cooldowns:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: cost-optimized
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: cost-optimized
spec:
  mandatory:
    minCapacity: 0                    # Not enforced; scale-to-zero allowed
    maxCapacity: 0                    # Not enforced
    disableScaleIn: false             # Not enforced; scale-in allowed
    scaleInCooldown: 0                # Not enforced
    scaleOutCooldown: 0               # Not enforced
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    minCapacity: 0                    # Default: scale-to-zero allowed
    maxCapacity: 5                    # Default: small capacity
    disableScaleIn: false             # Default: aggressive scale-in
    scaleInCooldown: 60               # Default: 1 min (aggressive)
    scaleOutCooldown: 30              # Default: 30 sec (responsive)
    tags:
      environment: staging
      cost-optimization: enabled
    syncedLabels:
      cost-sensitive: "true"
    syncedAnnotations:
      scaling-mode: aggressive
```

**Behavior:**
- Resources scale to zero (minimum 0 instances)
- Aggressive cooldown periods enable rapid scaling
- Cost optimization tags applied
- Ideal for non-critical, bursty workloads

## Organization-Wide Governance

In addition to per-profile `AppScalingConfig` settings, the `KropathConfig` CRD provides organization-wide governance for Application Auto Scaling:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: kro
  namespace: kro-system
spec:
  mandatory:
    appScaling:
      minCapacity: 1                  # Org-wide: all resources minimum 1
      maxCapacity: 50                 # Org-wide: all resources max 50
      disableScaleIn: true            # Org-wide: all resources cannot scale in
  defaults:
    appScaling:
      minCapacity: 1
      maxCapacity: 10
      scaleInCooldown: 300
      scaleOutCooldown: 60
```

**Cascade Priority:**
1. `KropathConfig.mandatory.appScaling` (org-wide mandatory)
2. `AppScalingConfig/<profile>.mandatory` (profile-specific mandatory)
3. Instance spec (resource-specific override)
4. `AppScalingConfig/<profile>.defaults` (profile-specific default)
5. `KropathConfig.defaults.appScaling` (org-wide default)

Higher priority sources override lower ones. Example:
- If org-wide `KropathConfig.mandatory.appScaling.minCapacity: 2`, ALL resources must have minimum capacity 2, even if a profile's mandatory tier is `0`
- If a profile mandatory tier has `maxCapacity: 50`, the instance-level `spec.maxCapacity: 100` is overridden to `50`

## Tier Conflict Prevention

Kropath validates that conflicting settings are not applied simultaneously. The following rules prevent logical conflicts:

### Integer Conflict Rule

You cannot set the same integer field to non-zero values in both `mandatory` and `defaults`:

```yaml
spec:
  mandatory:
    minCapacity: 2                    # Enforce: minimum 2
  defaults:
    minCapacity: 1                    # Default: minimum 1
```

This is rejected by `x-kubernetes-validations` with the error:
```
minCapacity cannot be set (non-zero) in both mandatory and defaults
```

**Rationale:** If mandatory tier specifies a value, defaults are never consulted. Setting both signals confusion about intent.

### Boolean Conflict Rule

You cannot set the same boolean field to `true` in both `mandatory` and `defaults`:

```yaml
spec:
  mandatory:
    disableScaleIn: true              # Enforce: scale-in protection required
  defaults:
    disableScaleIn: true              # Default: protection on
```

This is rejected with the error:
```
disableScaleIn cannot be set to true in both mandatory and defaults
```

**Rationale:** Setting both to `true` is redundant and signals a misconfiguration.

## Complete Example: Three-Profile Organization

A typical organization deploying three profiles:

```yaml
---
# General policy: flexible, sensible defaults
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    minCapacity: 1
    maxCapacity: 10
    scaleInCooldown: 300
    scaleOutCooldown: 60
---
# Production: hardened, strict governance
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    minCapacity: 2
    maxCapacity: 100
    disableScaleIn: true
    scaleInCooldown: 600
    tags:
      environment: production
      soc2: required
    syncedLabels:
      tier: critical
  defaults:
    minCapacity: 1
    maxCapacity: 10
---
# Cost-optimized: permissive, aggressive scaling
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingConfig
metadata:
  name: cost-optimized
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: cost-optimized
spec:
  mandatory: {}
  defaults:
    minCapacity: 0
    maxCapacity: 5
    scaleInCooldown: 60
    scaleOutCooldown: 30
    tags:
      environment: staging
      cost-sensitive: "true"
```

## Resource Usage

Resources reference profiles via `spec.configRef`:

```yaml
# Uses the 'production' profile — mandatory min 2, max 100, scale-in protection
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: prod-api-target
  namespace: services
spec:
  configRef: production
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/prod-cluster/api-service
  minCapacity: 1                      # Will be overridden to 2 (mandatory min)
  maxCapacity: 50                     # Will be overridden to 100 (mandatory max)

---
# Uses the 'cost-optimized' profile — permissive defaults
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: staging-worker-target
  namespace: batch
spec:
  configRef: cost-optimized
  serviceNamespace: ecs
  scalableDimension: ecs:service:DesiredCount
  resourceID: service/staging-cluster/worker-service
  # Defaults to: min 0, max 5, scale-in cooldown 60s (aggressive)
```

## Default Fallback

If a resource references a profile that does not exist, kropath falls through to `general-policy`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AppScalingTarget
metadata:
  name: my-target
  namespace: default
spec:
  configRef: nonexistent-profile      # Profile does not exist
  # Falls through to: configRef = "general-policy"
```

This ensures resources always have some governance applied, even if a profile is misconfigured.

## Status Fields

After deployment, the `AppScalingConfig` CR exposes the controller-computed `status.effectiveConfig` — the pre-merged result of org-wide (`KropathConfig`) + profile-specific (`AppScalingConfig`) cascade:

```yaml
status:
  effectiveConfig:
    mandatory:
      minCapacity: 2
      maxCapacity: 100
      disableScaleIn: true
      scaleInCooldown: 600
      tags:
        environment: production
        cost-center: platform
      syncedLabels:
        environment: production
        tier: critical
      syncedAnnotations: {}
    defaults:
      minCapacity: 1
      maxCapacity: 10
      scaleInCooldown: 300
      scaleOutCooldown: 60
      tags: {...}
      syncedLabels: {}
      syncedAnnotations: {}
    aws:
      region: us-east-1
      accountId: "123456789012"
```

Resources read `effectiveConfig` from the referenced profile to determine final governance values.

## Next Steps

- [AppScalingTarget](./appscalingtarget.md) — Register your first scalable resource
- [AppScalingPolicy](./appscalingpolicy.md) — Attach scaling policies to targets
- [Application Auto Scaling Overview](./index.md) — Family concepts and quick start
