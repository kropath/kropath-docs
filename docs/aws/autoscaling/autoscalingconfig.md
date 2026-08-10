# AutoScalingConfig — Governance Configuration

The `AutoScalingConfig` resource defines governance profiles that control EC2 Auto Scaling group behavior across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each Auto Scaling group.

## Overview

`AutoScalingConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., instance protection that all groups must enforce)
- **Defaults tier** — Baseline values developers can override (e.g., default health check type if not specified on the group)

This two-tier approach lets platform teams enforce critical fleet management policies while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `newInstancesProtectedFromScaleIn` | boolean | Protect new instances from scale-in termination (cannot be overridden) |
| `capacityRebalance` | boolean | Enable proactive Spot rebalancing (cannot be overridden for Spot fleets) |
| `healthCheckType` | string | Required health check type: `EC2`, `ELB`, `EC2,ELB`, etc. (empty = not enforced) |
| `healthCheckGracePeriod` | integer | Required health check grace period in seconds (0 = not enforced) |
| `maxInstanceLifetime` | integer | Required maximum instance age in seconds (0 = disabled by default) |
| `namingTemplate` | string | Template for Auto Scaling group names (cannot be overridden) |
| `tags` | map | Tags applied to all groups (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the group level:

| Field | Type | Purpose |
|---|---|---|
| `newInstancesProtectedFromScaleIn` | boolean | Default scale-in protection |
| `capacityRebalance` | boolean | Default Spot capacity rebalancing |
| `healthCheckType` | string | Default health check type |
| `healthCheckGracePeriod` | integer | Default health check grace period in seconds |
| `maxInstanceLifetime` | integer | Default maximum instance age in seconds |
| `namingTemplate` | string | Default naming template |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `0`, or `""` can appear in both — they indicate "not set".)

## Field Semantics

**`newInstancesProtectedFromScaleIn`:** When set to `true`, new instances launched by the group are protected from scale-in termination. Mandatory `true` enforces protection for all groups; default `true` provides protection unless the group overrides it.

**`capacityRebalance`:** When set to `true`, the group proactively replaces Spot Instances at elevated interruption risk. Mandatory `true` enforces Spot rebalancing; useful for workloads sensitive to Spot interruptions.

**`healthCheckType`:** Specifies which health checks the group uses. Common values: `EC2` (EC2 status checks only), `ELB` (Elastic Load Balancing health checks), or `EC2,ELB` (both). Empty string `""` means not enforced — group can choose.

**`healthCheckGracePeriod`:** Seconds to wait after an instance enters service before checking its health. Mandatory values override group settings; defaults apply when group doesn't specify. Use `0` in mandatory to mean "not enforced".

**`maxInstanceLifetime`:** Maximum age of instances in seconds. When set, instances are rotated out after this age, ensuring fleet freshness. Must be at least 86400 (1 day) when enabled. Use `0` to mean "disabled".

**`namingTemplate`:** Template for generating Auto Scaling group names. Tokens: `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`. Empty string means no template enforcement.

## Example Profiles

### Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    newInstancesProtectedFromScaleIn: false
    capacityRebalance: false
    healthCheckType: "EC2"
    healthCheckGracePeriod: 300
    maxInstanceLifetime: 0
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

This baseline profile:
- Allows developers to choose scale-in protection
- Defaults to EC2 health checks (no load balancer checks required)
- Uses 300-second health check grace period
- Disables automatic instance rotation by default
- Generates group names from namespace and CR name
- Tags all groups with managed-by label

### Production-Hardened (production)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    newInstancesProtectedFromScaleIn: true
    healthCheckType: "EC2,ELB"
    healthCheckGracePeriod: 600
    maxInstanceLifetime: 2592000
    syncedLabels:
      environment: production
      compliance: prod-hardened
  defaults:
    capacityRebalance: true
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      backup-policy: daily
```

This production profile:
- Enforces instance protection from scale-in
- Requires both EC2 and ELB health checks
- Sets 600-second grace period (longer stability window)
- Rotates instances every 30 days
- Enables Spot rebalancing by default
- Adds production environment labels

### Spot Fleet (spot-fleet)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingConfig
metadata:
  name: spot-fleet
  namespace: kro-system
spec:
  mandatory:
    capacityRebalance: true
    healthCheckType: "EC2"
  defaults:
    newInstancesProtectedFromScaleIn: false
    healthCheckGracePeriod: 300
    maxInstanceLifetime: 0
    namingTemplate: "spot-{namespace}-{name}"
    tags:
      capacity-type: spot
      cost-optimized: true
```

This Spot Fleet profile:
- Enforces capacity rebalancing (proactively replaces at-risk Spot instances)
- Allows developers to disable scale-in protection
- Uses basic EC2 health checks
- Applies spot-fleet naming prefix
- Tags for cost tracking

## Using Profiles

Select a profile on any Auto Scaling group:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: AutoScalingGroup
metadata:
  name: web-fleet
  namespace: services-prod
spec:
  configRef: production  # Select the production profile
  minSize: 3
  maxSize: 10
  launchTemplate:
    name: my-app-v1
```

If a named profile does not exist, groups fall back to `general-policy`.

## Organization-Wide Defaults

Set org-wide controls using the root configuration:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    autoscaling:
      newInstancesProtectedFromScaleIn: true
      capacityRebalance: true
  defaults:
    autoscaling:
      newInstancesProtectedFromScaleIn: false
      capacityRebalance: false
```

**Org mandatory** (e.g., `mandatory.autoscaling.newInstancesProtectedFromScaleIn`) applies with **highest priority** — namespace profiles and groups cannot override it.

**Org defaults** (e.g., `defaults.autoscaling.capacityRebalance`) act as fallback values — used only when a namespace profile or group does not specify a value.

## Governance Cascade

The configuration cascade follows a priority system with mandatory controls always winning:

**For mandatory fields:**
- Org mandatory → AutoScalingConfig mandatory → group spec is ignored
- Mandatory controls cannot be overridden by developers

**For defaults and overrideable fields:**
- Group-level spec (if provided) wins
- AutoScalingConfig defaults apply (if group doesn't specify)
- Org-wide defaults apply (if AutoScalingConfig doesn't specify)
- Hardcoded kropath defaults apply (as final fallback)

**For boolean fields** (scale-in protection, capacity rebalance):
- Org mandatory overrides everything; mandatory `true` forces the behavior
- Default `true` provides the behavior unless group explicitly sets `false`

**For string/integer fields** (health check type, grace period):
- Org mandatory overrides completely
- Group spec beats profile defaults
- Profile defaults beat org defaults
- Empty string or `0` means "not enforced" (falls through to next level)

## Monitoring

Verify a profile:

```bash
kubectl get autoscalingconfig general-policy -n kro-system -o yaml
kubectl describe autoscalingconfig production -n kro-system
```

Check what profile a group is using:

```bash
kubectl describe autoscalinggroup web-fleet -n services-prod | grep configRef
```

View governance configuration:

```bash
kubectl get autoscalingconfig production -n kro-system -o yaml
```
