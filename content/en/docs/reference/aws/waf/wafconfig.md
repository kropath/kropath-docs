---
title: WAFConfig — Governance for AWS WAF
description: "The `WAFConfig` resource defines governance policies for AWS WAF resources (web ACLs, rule groups, and IP sets)."
doc_type: reference
---
# WAFConfig — Governance for AWS WAF

The `WAFConfig` resource defines governance policies for AWS WAF resources (web ACLs, rule groups, and IP sets). It establishes organization-wide or environment-specific constraints on scope, default action, visibility configuration, and naming conventions. Platform teams deploy named profiles (`general-policy`, `production`, `strict-security`) to enforce compliance across all WAF resources in a namespace.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `metadata.name` | string | required | Profile name; selected by WAF resources via `spec.configRef` |
| `metadata.namespace` | string | `"kro-system"` | Global profiles are deployed to `kro-system`; local profiles per namespace |

### Mandatory Tier (Policy Enforcement)

Mandatory fields **override** instance specifications — platform requirements that instances cannot bypass.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spec.mandatory.scope` | string | `""` | Force `CLOUDFRONT` or `REGIONAL` scope; `""` = not enforced |
| `spec.mandatory.defaultAction` | string | `""` | Force default action to `allow` or `block`; `""` = not enforced; affects `WAFWebACL` only |
| `spec.mandatory.cloudWatchMetricsEnabled` | boolean | false | Force CloudWatch metrics; false = not enforced |
| `spec.mandatory.sampledRequestsEnabled` | boolean | false | Force sampled request logging; false = not enforced |
| `spec.mandatory.namingTemplate` | string | `""` | Force naming pattern (e.g., `corp-{namespace}-{name}`); `""` = not enforced |
| `spec.mandatory.tags` | map | `{}` | Mandatory cloud tags — instances cannot remove these |
| `spec.mandatory.syncedLabels` | map | `{}` | Labels that sync to both Kubernetes labels AND cloud tags (prefixed `aws.kropath.run/`) |
| `spec.mandatory.syncedAnnotations` | map | `{}` | Annotations for Kubernetes metadata |

### Defaults Tier (Sensible Defaults)

Defaults apply only when an instance specification is empty — providing baseline values without blocking overrides.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `spec.defaults.scope` | string | `"REGIONAL"` | Default scope; overridable by instance |
| `spec.defaults.defaultAction` | string | `"block"` | Default action (`allow` or `block`); overridable by instance |
| `spec.defaults.cloudWatchMetricsEnabled` | boolean | true | Default metric collection; overridable by instance |
| `spec.defaults.sampledRequestsEnabled` | boolean | true | Default sampled request logging; overridable by instance |
| `spec.defaults.namingTemplate` | string | `"{namespace}-{name}"` | Default naming pattern — WAF resource names are account+region scoped |
| `spec.defaults.tags` | map | `{}` | Baseline cloud tags; instances can add tags but cannot remove baseline |
| `spec.defaults.syncedLabels` | map | `{}` | Baseline synced labels |
| `spec.defaults.syncedAnnotations` | map | `{}` | Baseline synced annotations |

## Governance Cascade

WAF resources use a **ten-level cascade** to resolve fields:

```
KropathConfig.mandatory → WAFConfig.mandatory → Instance spec → WAFConfig.defaults → KropathConfig.defaults → RGD built-in default
```

**Example:**

A web ACL in namespace `security-prod` with no `spec.defaultAction` set:

1. Check `KropathConfig.mandatory.waf.defaultAction` — if set, use it (organization requirement)
2. Check `WAFConfig/production.spec.mandatory.defaultAction` — if set, use it (profile requirement)
3. Check `spec.defaultAction` on the web ACL — if set, use it (instance override)
4. Check `WAFConfig/production.spec.defaults.defaultAction` — if set, use it (profile default)
5. Check `KropathConfig.defaults.waf.defaultAction` — if set, use it (organization default)
6. Use the RGD built-in: `"block"` (hardcoded safe default)

**Note:** When mandatory governance overrides the `defaultAction` field, custom request/response handling from the instance specification is dropped — only the bare allow or block action is applied. Custom handling is an instance-only feature and cannot be governed via mandatory tier.

## Scope

The `scope` field determines where the WAF policy applies:

- **`REGIONAL`** — Applied to regional AWS resources (ALB, API Gateway, AppSync, Cognito, etc.)
- **`CLOUDFRONT`** — Applied to CloudFront distributions; must be deployed to `us-east-1` region

Scope is **immutable after creation** — it cannot be changed without deleting and recreating the resource.

## Naming Convention

WAF resource names are AWS account+region scoped — they must be unique within your account but not globally.

**Default template:** `{namespace}-{name}` → e.g., `security-prod-main-acl`

**Available tokens:**
- `{namespace}` — Kubernetes namespace
- `{name}` — Kubernetes resource name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — WAFConfig profile name
- `{tag.<key>}` — Replace with tag value (e.g., `{tag.env}` → `prod` if tags include `env: prod`)

**AWS constraints:** Alphanumeric characters and hyphens only (`[\w\-]+`).

## Complete Examples

### General Policy — Development and Testing

A permissive profile for development environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    scope: REGIONAL
    defaultAction: block
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
    namingTemplate: "{namespace}-{name}"
    tags:
      team: platform
      cost-center: engineering
```

**Result:**
- All resources default to REGIONAL scope
- Resources default to block action
- Developers can override any field
- Baseline tags applied to all resources

### Production — Strict Governance

A production profile with mandatory compliance requirements:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    # Compliance requirements — cannot override
    scope: REGIONAL
    defaultAction: block
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
    tags:
      environment: production
      compliance: sox
      backup-policy: enabled
    syncedLabels:
      critical: "true"
      audit-required: "true"
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
```

**Result:**
- All production web ACLs must use REGIONAL scope
- Default action enforced as block
- CloudWatch logging and sampling mandatory
- Audit tags applied to all resources
- Production naming convention enforced

### Strict Security Profile

A locked-down profile for high-security environments:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFConfig
metadata:
  name: strict-security
  namespace: kro-system
spec:
  mandatory:
    scope: REGIONAL
    defaultAction: block
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
    namingTemplate: "sec-{namespace}-{name}"
    tags:
      environment: production
      compliance: pci
      data-classification: restricted
    syncedLabels:
      pci: "true"
      audit-required: "true"
  defaults:
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
```

**Result:**
- All fields locked — no instance override possible for security fields
- REGIONAL scope enforced
- Block action enforced
- Full logging and sampling required
- PCI compliance tags applied
- Audit trail enabled

## Key Behaviors

- **Mutual exclusivity:** Each scalar field (string or boolean) must appear in **either** the `mandatory` tier **or** the `defaults` tier, not both. Maps (`tags`, `syncedLabels`, `syncedAnnotations`) can appear in both tiers and merge additively.
- **Boolean semantics:** Boolean fields use `false` or `nil` (absent) to mean "not enforced." Only set a boolean to `true` to enforce a value (for `cloudWatchMetricsEnabled` and `sampledRequestsEnabled`).
- **Tag merging:** `mandatory.tags` and `defaults.tags` merge automatically. Mandatory tags take precedence on key conflicts. Instances can add their own tags but cannot remove mandatory tags.
- **Label sync:** `syncedLabels` appear as both Kubernetes labels (with `aws.kropath.run/` prefix) and as AWS cloud tags, enabling consistent metadata across platforms.
- **Profile fallback:** If a WAF resource references a profile that does not exist, it falls back to `general-policy`. Ensure `general-policy` always exists in `kro-system`.
- **String enum constraints:** The `defaultAction` field accepts only `"allow"` or `"block"`. The `scope` field accepts only `"CLOUDFRONT"` or `"REGIONAL"`.

## Accessing Effective Configuration

When the kropath-controller reconciles a WAFConfig CR, it writes the merged governance result to `status.effectiveConfig`, combining the resource's `spec.mandatory` and `spec.defaults` tiers with organization-wide `KropathConfig` settings:

```yaml
status:
  effectiveConfig:
    mandatory:
      scope: REGIONAL
      defaultAction: block
      cloudWatchMetricsEnabled: true
      sampledRequestsEnabled: true
      namingTemplate: prod-{namespace}-{name}
      tags:
        environment: production
        compliance: sox
      syncedLabels:
        critical: "true"
    defaults:
      scope: REGIONAL
      defaultAction: block
      cloudWatchMetricsEnabled: true
      sampledRequestsEnabled: true
      namingTemplate: "{namespace}-{name}"
      tags:
        team: platform
      syncedLabels: {}
    aws:
      accountId: "123456789012"
      region: "us-east-1"
```

WAF resource RGDs (WAFWebACL, WAFRuleGroup, WAFIPSet) read this `status.effectiveConfig` via `externalRef` with `selector.matchLabels` lookup, applying the merged governance directly to child ACK resources.

## Related Resources

- [WAFWebACL](wafwebacl.md) — Create and manage web access control lists
- [WAFRuleGroup](wafrulegroup.md) — Create and manage reusable rule groups
- [WAFIPSet](wafipset.md) — Create and manage IP address sets
- [KropathConfig](../../../concepts/controller/label-operator.md) — Organization-wide configuration
