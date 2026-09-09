# RAMConfig — Resource Sharing Governance

`RAMConfig` is a Kubernetes CRD that platform teams use to enforce policies across all AWS Resource Access Manager (RAM) resource shares and permissions in a namespace or cluster.

## Overview

Platform teams create named `RAMConfig` profiles (for example: `general-policy`, `cross-account`, `restricted`) that specify:

- **External principal control** — whether shares may include principals outside the AWS Organization
- **Resource type restrictions** — which AWS resource types are permitted to be shared
- **Naming conventions** — required naming templates for shares and permissions
- **Tag and label policies** — mandatory and default tags applied to all shares and permissions
- **Deletion policies** — whether resources are retained or deleted when the Kubernetes CR is removed

Application teams select a profile via `spec.configRef` on their `RAMPermission` and `RAMResourceShare` resources. If the named profile doesn't exist, the system falls back to `general-policy`.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster (provides the governance cascade logic)
- AWS IAM permissions to create and manage RAM resources in the target account
- A namespace where resources will be provisioned

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    # These fields are enforced — application teams cannot override them
    allowExternalPrincipals: false        # nil | false | true (nil = not enforced)
    allowedResourceTypes: []              # [] | ["ec2:Subnet", ...] (empty = no restriction)
    namingTemplate: ""                    # "" | "{namespace}-{name}" pattern (empty = not enforced)
    tags:
      cost-centre: platform
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}

  defaults:
    # These fields are applied when not overridden by application teams
    allowExternalPrincipals: false
    allowedResourceTypes: []
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Fields

### External Principal Control (`allowExternalPrincipals`)

Controls whether resource shares may include principals outside your AWS Organization.

**Levels:**
- `nil` (omitted) — Not enforced; application teams decide
- `false` — Mandated: shares may only include principals within your AWS Organization
- `true` — Mandated: shares may include external principals (cross-account, cross-org)

**Mandatory tier** — Enforces this rule on all shares created with this profile
**Defaults tier** — Applied when application teams don't specify a value

**Examples:**
```yaml
spec:
  mandatory:
    # Strict: block all external principals (org-wide compliance)
    allowExternalPrincipals: false

  defaults:
    # Permissive default: allow external principals unless mandatory says otherwise
    allowExternalPrincipals: true
```

### Resource Type Restrictions (`allowedResourceTypes`)

Restricts which AWS resource types may be shared via this profile.

**Format:** List of resource type identifiers — `<service>:<resourceType>` (case-insensitive)

**Examples:**
- `ec2:Subnet` — VPC subnets
- `ec2:TransitGateway` — Transit Gateways
- `route53resolver:ResolverRule` — Route 53 Resolver rules
- `license-manager:LicenseConfiguration` — License Manager configurations

**Empty list behavior:**
- Empty `[]` = all resource types permitted (no restriction)
- Non-empty list = only these resource types may be shared

**Examples:**
```yaml
spec:
  mandatory:
    # Strict: only subnets and transit gateways may be shared
    allowedResourceTypes:
      - "ec2:Subnet"
      - "ec2:TransitGateway"

  defaults:
    # No restriction — any resource type permitted
    allowedResourceTypes: []
```

### Naming Template (`namingTemplate`)

Enforces a naming convention for all resource shares and permissions. Templates use token substitution:

- `{name}` — The resource's `metadata.name`
- `{namespace}` — The resource's Kubernetes namespace
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — The profile name (e.g., `general-policy`)
- `{tag.<key>}` — Merge tag values into the name

**Examples:**
```yaml
spec:
  defaults:
    # Simple namespace-based naming
    namingTemplate: "{namespace}-{name}"

    # Environment-aware naming
    namingTemplate: "{tag.env}-{namespace}-{name}"

    # Account and region aware
    namingTemplate: "{account_id}-{region}-{name}"
```

AWS doesn't specify strict naming constraints for RAM resources — names should follow organizational conventions. If a template resolves to an invalid name (unresolved tokens, invalid characters), the resource will be rejected and marked with `status.namingStatus: "invalid-unresolved-tokens"`.

### Tags, Labels, and Annotations

Policies control which tags, labels, and Kubernetes annotations are applied to all resource shares and permissions.

**Mandatory entries** (`spec.mandatory.tags`, `spec.mandatory.syncedLabels`, `spec.mandatory.syncedAnnotations`) are enforced — application teams cannot override or remove them.

**Default entries** (`spec.defaults.tags`, `spec.defaults.syncedLabels`, `spec.defaults.syncedAnnotations`) are applied unless the application team specifies their own values.

**Tags** are applied to both Kubernetes labels (via `syncedLabels` merge) and used for naming token resolution (`{tag.<key>}`). Tags are forwarded to AWS cloud resources (shares and permissions).

**Synced labels** appear in Kubernetes resource labels (prefixed with `aws.kropath.run/`).

**Annotations** are mirrored to Kubernetes resource metadata (prefixed with `aws.kropath.run/`).

**Example — Multi-tier tagging policy:**
```yaml
spec:
  mandatory:
    tags:
      cost-centre: platform
      compliance: required
    syncedLabels:
      team: platform-network
  defaults:
    tags:
      managed-by: kropath
    syncedLabels:
      data-class: internal
    syncedAnnotations:
      provisioner: kropath
```

## Profile-Based Governance

Create multiple profiles for different organizational requirements:

```yaml
---
# General governance profile — permissive defaults
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    allowExternalPrincipals: false
    allowedResourceTypes: []
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath

---
# Cross-account sharing profile
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: cross-account
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: cross-account
spec:
  mandatory: {}
  defaults:
    allowExternalPrincipals: true
    allowedResourceTypes: []
    namingTemplate: "{namespace}-{name}"
    tags:
      sharing-model: cross-account
      managed-by: kropath

---
# Restricted sharing profile — compliance-focused
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: restricted
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: restricted
spec:
  mandatory:
    allowExternalPrincipals: false
    allowedResourceTypes:
      - "ec2:Subnet"
      - "ec2:TransitGateway"
  defaults:
    namingTemplate: "restricted-{namespace}-{name}"
    tags:
      sharing-model: restricted
      compliance: required
      audit-trail: "yes"
      managed-by: kropath
```

Application teams select a profile when creating shares:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: vpc-share
  namespace: production
spec:
  configRef: cross-account  # Use the cross-account profile
  # ... rest of spec
```

## Fallthrough Behavior

If an application team references a profile that doesn't exist, the system falls back to `general-policy` automatically. Always ensure `general-policy` exists in the cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    allowExternalPrincipals: false
    allowedResourceTypes: []
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade

When you apply a `RAMResourceShare` or `RAMPermission`, the effective configuration is resolved from ten levels of governance (ADR-015 §5.3):

1. Global KropathConfig mandatory (`KropathConfig.spec.mandatory.ram`)
2. Namespace KropathConfig mandatory
3. Profile mandatory (this RAMConfig)
4. Namespace profile mandatory
5. Instance override (`spec.allowExternalPrincipals`, `spec.tags`, `spec.syncedLabels`, `spec.syncedAnnotations`)
6. Namespace profile defaults
7. Profile defaults
8. Namespace KropathConfig defaults
9. Global KropathConfig defaults
10. RGD built-in default (e.g., `false` for `allowExternalPrincipals`, `retain` for deletion policy)

Priority runs top to bottom — level 1 (Global KropathConfig mandatory) always wins; each subsequent level applies only when the levels above it are unset. The `kropath-controller` pre-merges these into `status.effectiveConfig` on each `RAMConfig` CR, and resource RGDs read a single `effectiveConfig` value.

### Example Cascade Resolution

Given:
- Global KropathConfig `mandatory.ram.allowExternalPrincipals: false`
- Profile mandatory `allowExternalPrincipals: nil` (not set)
- Instance `spec.allowExternalPrincipals: true`

**Result:** KropathConfig mandatory wins — the share will NOT allow external principals, even though the instance and profile prefer it. The application team's request is overridden by org-wide policy.

## Org-Wide Governance via KropathConfig

For requirements that apply to all profiles and all shares (for example, "all shares must have a cost-centre tag"), use `KropathConfig`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global-governance
  namespace: kro-system
spec:
  mandatory:
    ram:
      allowExternalPrincipals: false  # Org-wide: no external principals
      allowedResourceTypes: []        # No org-wide resource type restriction
    tags:
      cost-centre: shared-platform    # Org-wide mandatory tag
  defaults:
    ram:
      allowExternalPrincipals: false
    tags:
      managed-by: kropath
  # ... other family sections
```

This mandatory tier (level 1) overrides all `RAMConfig` mandatory tiers (levels 3–4).

## Deployment

Deploy `RAMConfig` CRs to your cluster:

```bash
kubectl apply -f ramconfig.yaml
```

Then application teams reference the profile:

```bash
kubectl apply -f my-share.yaml
```

The `spec.configRef: cross-account` selects the cross-account profile; if it doesn't exist, `general-policy` is used.

## Common Patterns

### Strict Compliance Environment
```yaml
spec:
  mandatory:
    allowExternalPrincipals: false
    allowedResourceTypes:
      - "ec2:Subnet"
    tags:
      compliance: required
      audit-trail: "yes"
    syncedLabels:
      data-class: sensitive
```

### Multi-Environment with Profiles

Create `dev`, `staging`, `prod` profiles in the same namespace, each with different external principal policies and resource type restrictions. Application teams select the appropriate profile for their workload environment.

```yaml
# Dev: permissive
spec:
  mandatory: {}
  defaults:
    allowExternalPrincipals: true
    namingTemplate: "dev-{namespace}-{name}"

---
# Prod: strict
spec:
  mandatory:
    allowExternalPrincipals: false
    allowedResourceTypes:
      - "ec2:Subnet"
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
```

### Org-Wide with Profiles

Use `KropathConfig` for org-wide mandatory rules, then use profiles for team-specific defaults:

```yaml
# KropathConfig: org-wide mandatory
spec:
  mandatory:
    ram:
      allowExternalPrincipals: false
    tags:
      cost-centre: shared-platform

---
# Profile: team-specific defaults
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: networking-team
spec:
  mandatory: {}
  defaults:
    namingTemplate: "networking-{namespace}-{name}"
    tags:
      team: networking
```

## Troubleshooting

**"My resource is using the wrong naming template"**
- Check the `configRef` you specified
- Verify the named profile exists in the cluster (check `status.effectiveConfig.mandatory.namingTemplate` on the RAMConfig)
- If the profile doesn't exist, `general-policy` is used
- Inspect `status.namingStatus` on your resource — it will show `"invalid-unresolved-tokens"` if tokens couldn't be resolved

**"My external principal restriction isn't being enforced"**
- Ensure the `RAMConfig` CR has `status.effectiveConfig` populated (the controller writes this)
- Check `mandatory.allowExternalPrincipals` — it must be explicitly set to `false` (not `nil`) to enforce
- Verify the profile was selected (check `spec.configRef` on your share)
- Check both `KropathConfig` and `RAMConfig` mandatory tiers — both are merged

**"Resource types are allowed when they should be restricted"**
- Check `mandatory.allowedResourceTypes` is non-empty (empty list = no restriction)
- Verify the resource ARN in your share matches the format (e.g., `arn:aws:ec2:region:account:resourceType/resourceId`)
- Inspect the controller logs for CEL validation errors

**"Tags aren't being applied to shares"**
- Check both `KropathConfig` and `RAMConfig` tags (both are merged)
- Verify `metadata.labels` on the Kubernetes resource have the `aws.kropath.run/` prefix
- Check cloud resource tags in AWS RAM console — they may be visible there even if Kubernetes labels differ

## See Also

- [RAMPermission User Guide](./rampermission.md)
- [RAMResourceShare User Guide](./ramresourceshare.md)
- [RAM Resource Family Overview](./README.md)
- [AWS RAM Documentation](https://docs.aws.amazon.com/ram/latest/userguide/what-is.html)
- [ADR-015: Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md)
- [ADR-010: Kropath Controller Effective Config](https://github.com/kropath/kropath-core/blob/main/docs/adrs/010-kropath-controller-effective-config.md)
