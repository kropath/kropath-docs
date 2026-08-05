# ELBConfig — Load Balancing Governance

The `ELBConfig` resource defines governance profiles that control how load balancers, target groups, and listeners are created across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each load balancer.

## Overview

`ELBConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., deletion protection for production load balancers, required TLS policies, required cross-zone load balancing)
- **Defaults tier** — Baseline values developers can override (e.g., default idle timeout for ALBs, default naming pattern, default tags)

This two-tier approach lets platform teams enforce critical compliance and operational controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `deletionProtection` | boolean | Enforce deletion protection on all load balancers. `true` = all LBs must have deletion protection; `false` = not enforced. |
| `accessLogsEnabled` | boolean | Enforce access logging on all load balancers. `true` = all LBs must log access; `false` = not enforced. |
| `accessLogsS3Bucket` | string | S3 bucket for access logs when enforced. Empty = not enforced. Paired with `accessLogsEnabled: true`. |
| `crossZoneEnabled` | boolean | Enforce cross-zone load balancing. `true` = NLBs and GWLBs must span zones; `false` = not enforced. (ALBs are always cross-zone.) |
| `internalOnly` | boolean | Restrict load balancers to internal scheme only. `true` = all LBs must be internal; `false` = not enforced. |
| `idleTimeoutSeconds` | integer | Enforce idle timeout for ALBs (range 1–4000). `0` = not enforced; ignored for NLBs and GWLBs. |
| `sslPolicy` | string | Enforce TLS security policy for HTTPS/TLS listeners. Example: `ELBSecurityPolicy-TLS13-1-2-2021-06`. Empty = not enforced. |
| `namingTemplate` | string | Naming pattern for resource names. Empty = not enforced. Available tokens: `{name}`, `{namespace}`, `{configRef}`, `{account_id}`, `{region}`, `{tag.KEY}`. |
| `tags` | map | Cloud tags applied to all resources. Cannot be removed by developers. |
| `syncedLabels` | map | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Purpose |
|---|---|---|
| `deletionProtection` | boolean | Default deletion protection state. `false` = no protection by default. |
| `accessLogsEnabled` | boolean | Default access logging state. `false` = no access logging by default. |
| `accessLogsS3Bucket` | string | Default S3 bucket for access logs. Empty = no bucket configured by default. |
| `crossZoneEnabled` | boolean | Default cross-zone load balancing for NLBs and GWLBs. `true` = enabled by default; `false` = disabled. |
| `internalOnly` | boolean | Default scheme for load balancers. `false` = internet-facing by default; `true` = internal by default. |
| `idleTimeoutSeconds` | integer | Default idle timeout for ALBs. `60` = 60-second timeout by default; `0` = use AWS default. |
| `sslPolicy` | string | Default TLS policy for HTTPS/TLS listeners. Empty = use AWS default policy. |
| `namingTemplate` | string | Default naming pattern. Example: `{namespace}-{name}`. |
| `tags` | map | Default cloud tags for resources. Can be overridden per-resource. |
| `syncedLabels` | map | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: false
    internalOnly: false
    idleTimeoutSeconds: 0
    sslPolicy: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: true
    internalOnly: false
    idleTimeoutSeconds: 60
    sslPolicy: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### Production (prod-strict)

Enforces deletion protection and TLS requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: prod-strict
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod-strict
spec:
  mandatory:
    deletionProtection: true
    accessLogsEnabled: true
    accessLogsS3Bucket: "org-lb-logs"
    crossZoneEnabled: true
    internalOnly: false
    idleTimeoutSeconds: 60
    sslPolicy: "ELBSecurityPolicy-TLS13-1-2-2021-06"
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      compliance: required
    syncedLabels:
      environment: production
    syncedAnnotations: {}
  defaults:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: true
    internalOnly: false
    idleTimeoutSeconds: 60
    sslPolicy: ""
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `prod-strict` profile cannot override:
- Deletion protection (must be enabled)
- Access logging (must be enabled to the org bucket)
- Cross-zone load balancing for NLBs/GWLBs (must be enabled)
- TLS policy for HTTPS/TLS listeners (must use the required policy)
- Naming pattern (must follow `prod-{namespace}-{name}`)
- Environment tags

### Internal-Only (internal)

Restricts load balancers to internal-only scheme:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: internal
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: internal
spec:
  mandatory:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: false
    internalOnly: true
    idleTimeoutSeconds: 0
    sslPolicy: ""
    namingTemplate: ""
    tags:
      scope: internal
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: true
    internalOnly: false
    idleTimeoutSeconds: 60
    sslPolicy: ""
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `internal` profile must create internal load balancers only. The `spec.scheme` field is forced to `"internal"` regardless of any developer choice.

## Governance Cascade

When a load balancer, target group, or listener is created, the governance cascade determines the final value for each field:

1. **Mandatory tier wins** — If the field is set in mandatory, that value is used unconditionally
2. **Developer spec is next** — If not mandatory, the developer's `spec` value is used if present
3. **Defaults tier is last** — If neither mandatory nor developer spec is set, the defaults tier value is used

Example:

```
spec.deletionProtection resolution:
  ├─ If ELBConfig.mandatory.deletionProtection = true → true (enforced)
  ├─ Else if ELBLoadBalancer.spec.deletionProtection = true → true (developer chose)
  └─ Else → ELBConfig.defaults.deletionProtection (e.g., false)
```

## How to Deploy

1. Create governance profiles in `kro-system` namespace (reserved for system-wide configuration):

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: false
    internalOnly: false
    idleTimeoutSeconds: 0
    sslPolicy: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    deletionProtection: false
    accessLogsEnabled: false
    accessLogsS3Bucket: ""
    crossZoneEnabled: true
    internalOnly: false
    idleTimeoutSeconds: 60
    sslPolicy: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers reference the profile when creating resources:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: api-lb
  namespace: api-team
spec:
  configRef: general-policy  # Selects the profile
  type: application
  scheme: internet-facing
  subnets:
    - subnet-12345
    - subnet-67890
EOF
```

## Effective Configuration

When a load balancer is created, kropath-controller reads the selected `ELBConfig` and merges mandatory and defaults tiers along with org-wide settings from `KropathConfig`. The final merged configuration is written to `status.effectiveConfig` on the config CR.

Developers and platform teams can inspect the effective configuration:

```bash
kubectl get elbconfig general-policy -n kro-system -o yaml
```

The `status.effectiveConfig` shows:
- All mandatory fields (platform enforcement)
- All default fields (developer overrides possible)
- AWS account and region information

This single config CR ensures consistent, auditable governance across all load balancers that reference it.
