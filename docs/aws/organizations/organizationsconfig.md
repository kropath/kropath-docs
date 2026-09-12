# OrganizationsConfig — Organizations Governance

The `OrganizationsConfig` resource defines governance policies for the Organizations resource family. Platform teams deploy named profiles to enforce organization-wide policies for billing access, cross-account role names, OU placement, naming conventions, and metadata.

## Overview

Organizations governance spans multiple tiers:

1. **KropathConfig** (`spec.organizations` section) — Org-wide defaults for all Organizations resources
2. **OrganizationsConfig** (named profiles) — per-resource-type governance for specific policy families
3. **Resource instance** (`spec` fields) — developer-specified overrides

The `kropath-controller` watches both `KropathConfig` and `OrganizationsConfig` CRs and writes the merged result to `status.effectiveConfig` on the `OrganizationsConfig` CR. The `OrganizationsAccount` and `OrganizationsOU` RGDs read this merged config via a `configRef` label selector.

## Governance Tiers

### Mandatory Tier (`spec.mandatory`)

Mandatory policies override all other levels. Use for strict compliance requirements that cannot be overridden.

Fields:

- **`iamUserAccessToBilling`** — `"allow"` | `"deny"` | `""` (not enforced)
- **`roleName`** — Cross-account IAM role name (e.g., `"SecureAccessRole"`) | `""` (not enforced)
- **`parentID`** — Root or OU ID for OU placement (e.g., `"r-ab12"` or `"ou-ab12-cd345678"`) | `""` (not enforced)
- **`namingTemplate`** — Template for auto-generated resource names (e.g., `"corp-{name}"`) | `""` (not enforced)
- **`tags`** — Org-wide cloud tags (map); cannot be removed by instances
- **`syncedLabels`** — Labels synced to both K8s and cloud tags
- **`syncedAnnotations`** — Annotations synced to K8s metadata

### Defaults Tier (`spec.defaults`)

Default policies apply when instances do not override them. Instances can override defaults unless a mandatory policy prevents it.

Same fields as the mandatory tier.

## Creating Governance Profiles

### Basic Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    iamUserAccessToBilling: "allow"
    roleName: "OrganizationAccountAccessRole"
    parentID: "r-abc12def"
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-centre: platform
    syncedLabels:
      team: infrastructure
    syncedAnnotations:
      owner: platform-team
```

### Security Baseline Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: security-baseline
  namespace: kro-system
spec:
  mandatory:
    iamUserAccessToBilling: "deny"
    roleName: "SecureAccessRole"
    parentID: "ou-sec1-secure1234"
    tags:
      compliance: sox
      audit-required: "true"
  defaults:
    namingTemplate: "sec-{namespace}-{name}"
    syncedLabels:
      security-zone: restricted
```

## Profile Selection and Fallthrough

Instances reference a governance profile via `spec.configRef`:

```yaml
spec:
  configRef: "security-baseline"  # Use the security-baseline profile
```

If the named profile doesn't exist, the RGD automatically falls through to the `general-policy` profile.

## Naming Convention

The Organizations resource family uses the default naming template `{namespace}-{name}` unless overridden:

- `{namespace}` — The Kubernetes namespace of the instance CR
- `{name}` — The CR name
- `{tag.X}` — Value of a merged tag with key `X` (e.g., `{tag.env}`)
- `nameOverride` — Instances can bypass the template with this field

For example, if the namespace is `workloads-prod`, the CR name is `api-account`, and the template is `{namespace}-{name}`, the effective name is `workloads-prod-api-account`.

## Immutable Fields and Drift

Three fields are immutable after resource creation due to AWS API limitations:

- **`iamUserAccessToBilling`** — Set once at account creation; cannot be updated
- **`roleName`** — Set once at account creation; cannot be updated
- **`parentID`** — Set once at OU creation; cannot be updated

If a governance policy changes after resource creation, the RGD surfaces the drift via status conditions but cannot automatically remediate it. You must delete and recreate the resource to apply the new policy.

## Configuration Schema

```yaml
spec:
  mandatory:
    iamUserAccessToBilling: string | default=""       # "allow" | "deny" | ""
    roleName: string | default=""                     # IAM role name | ""
    parentID: string | default=""                     # Root/OU ID | ""
    namingTemplate: string | default=""               # Naming template | ""
    tags: map<string,string> | default={}
    syncedLabels: map<string,string> | default={}
    syncedAnnotations: map<string,string> | default={}
  defaults:
    iamUserAccessToBilling: string | default=""
    roleName: string | default=""
    parentID: string | default=""
    namingTemplate: string | default="{namespace}-{name}"
    tags: map<string,string> | default={}
    syncedLabels: map<string,string> | default={}
    syncedAnnotations: map<string,string> | default={}
status:
  effectiveConfig:
    mandatory:
      iamUserAccessToBilling: string
      roleName: string
      parentID: string
      namingTemplate: string
      tags: map<string,string>
      syncedLabels: map<string,string>
      syncedAnnotations: map<string,string>
    defaults:
      iamUserAccessToBilling: string
      roleName: string
      parentID: string
      namingTemplate: string
      tags: map<string,string>
      syncedLabels: map<string,string>
      syncedAnnotations: map<string,string>
    aws:
      region: string
      accountId: string
```

## Validation

Scalar governance fields (`iamUserAccessToBilling`, `roleName`, `parentID`, `namingTemplate`) cannot be set in both the mandatory and defaults tiers simultaneously. If you attempt this, the resource is rejected with a clear error message.

Field format validation:

- **`iamUserAccessToBilling`** — Must be `"allow"`, `"deny"`, or empty
- **`roleName`** — Must match the AWS IAM role name pattern: `^[\w+=,.@-]{1,64}$`
- **`parentID`** — Must be a valid root ID (`r-xxxx`) or OU ID (`ou-xxxx-xxxxxxxx`)

## Tag Merging

Tags from both `KropathConfig` and `OrganizationsConfig` are merged using additive union semantics:

- Mandatory tags cannot be removed by instances
- Default tags can be overridden per-instance
- Keys in both tiers: mandatory tags win on conflict

Example:

```yaml
KropathConfig.mandatory.tags: {cost-centre: infra}
OrganizationsConfig.mandatory.tags: {compliance: sox}
OrganizationsConfig.defaults.tags: {team: platform}
Instance.spec.tags: {project: alpha}

Result: {cost-centre: infra, compliance: sox, team: platform, project: alpha}
```

## Deployment

1. Create the `OrganizationsConfig` CR in the `kro-system` namespace:

```bash
kubectl apply -f organizationsconfig.yaml -n kro-system
```

2. Create an optional `KropathConfig` in `kro-system` to set org-wide defaults:

```bash
kubectl apply -f krothconfig.yaml -n kro-system
```

3. The `kropath-controller` automatically writes `status.effectiveConfig` with the merged configuration.

4. Instances in workload namespaces reference the profile via `spec.configRef`:

```yaml
spec:
  configRef: "general-policy"
```

## Account-Only vs OU-Only Fields

- **`iamUserAccessToBilling`** — Account-only; OUs ignore this field
- **`roleName`** — Account-only; OUs ignore this field
- **`parentID`** — OU-only; Accounts ignore this field for placement (accounts are placed via `email` uniqueness)

Both account and OU resources use the same `tags`, `syncedLabels`, `syncedAnnotations`, and `namingTemplate` fields.

## Best Practices

### 1. Use Named Profiles for Different Risk Levels

```yaml
---
# For general-purpose workloads
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    iamUserAccessToBilling: "allow"
---
# For security-sensitive workloads
apiVersion: aws.kropath.run/v1alpha1
kind: OrganizationsConfig
metadata:
  name: security-baseline
  namespace: kro-system
spec:
  mandatory:
    iamUserAccessToBilling: "deny"
```

### 2. Leverage Mandatory Policies for Compliance

Use the mandatory tier to enforce policies that must never be overridden:

```yaml
spec:
  mandatory:
    tags:
      audit-required: "true"
      cost-centre: platform
```

### 3. Plan for Immutable Field Changes

Since account and OU placement fields are immutable, decide your governance policies before creating resources. If a policy must change, delete and recreate the resource.

### 4. Use Naming Templates to Avoid Collisions

The default template `{namespace}-{name}` naturally distributes names across namespaces. For global uniqueness, add a tag reference:

```yaml
defaults:
  namingTemplate: "{namespace}-{name}-{tag.env}"
```
