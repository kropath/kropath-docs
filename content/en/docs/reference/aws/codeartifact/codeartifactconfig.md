---
title: CodeArtifactConfig
description: "`CodeArtifactConfig` is a governance resource that defines organizational policies for CodeArtifact domains and package groups."
doc_type: reference
---
# CodeArtifactConfig

`CodeArtifactConfig` is a governance resource that defines organizational policies for CodeArtifact domains and package groups. Platform teams create named profiles (`general-policy`, `production`, etc.) in the `kro-system` namespace; developers select a profile via `spec.configRef` on each domain and package group to inherit encryption, naming, and tagging policies.

## Scope

`CodeArtifactConfig` is AWS-only. GCP Artifact Registry and Azure Artifacts do not have equivalent governance resources.

## What it solves

Creating CodeArtifact domains at scale introduces policy decisions:

- **Encryption** — Should domains use AWS-managed or customer-managed KMS keys?
- **Naming** — How should domain names be generated to avoid collisions and reflect organizational structure?
- **Tagging** — What tags are mandatory or recommended for cost tracking and compliance?

`CodeArtifactConfig` solves this by providing:

- **Centralized encryption governance** — Enforce customer-managed KMS keys for compliance domains, allow AWS-managed keys for development
- **Consistent naming** — Generate domain names from templates (e.g., `{namespace}-{name}`, `corp-{namespace}-{name}`)
- **Organized tagging** — Set mandatory and default tags that flow to all domains using this profile
- **Organization-wide defaults** — Inherit defaults from `KropathConfig` (org-wide) plus profile-specific overrides

## Core Concepts

### Governance Tiers

Each profile has two tiers of governance:

**Mandatory tier** — Platform enforcements that override developer choices:
- Encryption key enforcement (all domains must use a specific KMS key)
- Naming template enforcement (all domain names must match a pattern)
- Mandatory tags (cannot be removed)

**Defaults tier** — Sensible defaults developers can override:
- Default encryption key (applied when domain spec is empty)
- Default naming template (applied when domain spec is empty)
- Default tags (applied when domain spec does not set them)

### Encryption Key Governance

```yaml
spec:
  mandatory:
    encryptionKey: ""          # Empty: no encryption enforcement
    encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/abc-123"  # Enforce this key
  defaults:
    encryptionKey: ""          # Empty: use AWS-managed key as default
    encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/xyz-789"  # Suggest this key as default
```

If both mandatory and defaults are set for the same field, the mandatory tier takes precedence for any domain using this profile.

**Important:** Encryption keys cannot be set in both mandatory and defaults at the same time. Use one or the other.

### Naming Templates

Domain names are generated from templates using tokens:

| Token | Value |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Selected profile name |
| `{tag.<key>}` | Tag value |

**Example template**: `{namespace}-{name}` generates `app-team-shared-domain` for a CR named `shared-domain` in namespace `app-team`.

**AWS constraints**: Domain names must be 2–50 characters, lowercase alphanumeric and hyphens only, starting and ending with alphanumeric characters.

### Synced Labels and Annotations

Labels and annotations can be synced to both Kubernetes metadata and AWS cloud tags:

```yaml
spec:
  defaults:
    syncedLabels:
      data-class: internal
      environment: production
    syncedAnnotations:
      team: platform-engineering
```

These are applied as:
- Kubernetes labels: `aws.kropath.run/data-class: internal`
- AWS tags: `data-class: internal`

## Complete Example

```yaml
---
# General governance profile for development domains
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  # No mandatory enforcements
  mandatory: {}
  
  # Sensible defaults
  defaults:
    encryptionKey: ""  # Use AWS-managed key
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
      environment: development
    syncedLabels:
      environment: development
    syncedAnnotations:
      maintained-by: platform-team

---
# Strict governance profile for production domains
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  # Mandatory enforcement
  mandatory:
    encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/prod-cmk"  # Customer-managed key required
    namingTemplate: "prod-{namespace}-{name}"  # All prod domains get prod- prefix
    tags:
      environment: production
      compliance-reviewed: "true"
  
  # Defaults for fields not in mandatory tier
  defaults:
    tags:
      managed-by: kropath
      cost-center: infrastructure
    syncedLabels:
      environment: production
    syncedAnnotations:
      owner: platform-team@example.com
```

After creating these profiles, developers select them via `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: shared-domain
  namespace: app-team
spec:
  configRef: general-policy  # Use general-policy defaults
  # encryptionKey inherits empty from profile (AWS-managed)
  # naming inherits {namespace}-{name} from profile
```

Or for production:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactDomain
metadata:
  name: prod-domain
  namespace: platform-services
spec:
  configRef: production  # Use production governance
  # encryptionKey is enforced to prod-cmk (developer cannot override)
  # naming is enforced to prod-{namespace}-{name}
  # tags and labels are merged with mandatory values
```

## Reference Specification

### Spec Fields

| Field | Type | Required? | Default | Notes |
|---|---|---|---|---|
| `mandatory.encryptionKey` | string | No | empty | KMS key ARN to enforce for all domains using this profile. Cannot be set together with `defaults.encryptionKey`. |
| `mandatory.namingTemplate` | string | No | empty | Naming template to enforce for all domain names using this profile. Cannot be set together with `defaults.namingTemplate`. |
| `mandatory.tags` | map[string]string | No | `{}` | Tags that cannot be removed by developers. Merged with domain-level tags. |
| `mandatory.syncedLabels` | map[string]string | No | `{}` | Labels to sync to K8s and cloud tags. Cannot be removed by developers. |
| `mandatory.syncedAnnotations` | map[string]string | No | `{}` | Annotations to sync to K8s. Cannot be removed by developers. |
| `defaults.encryptionKey` | string | No | empty | Default KMS key ARN when domain spec is empty. Cannot be set together with `mandatory.encryptionKey`. |
| `defaults.namingTemplate` | string | No | `"{namespace}-{name}"` | Default naming template when domain spec is empty. Cannot be set together with `mandatory.namingTemplate`. |
| `defaults.tags` | map[string]string | No | `{}` | Default tags applied when domain does not set them. |
| `defaults.syncedLabels` | map[string]string | No | `{}` | Default labels to sync when domain does not set them. |
| `defaults.syncedAnnotations` | map[string]string | No | `{}` | Default annotations to sync when domain does not set them. |

### Status Fields

| Field | Type | Meaning |
|---|---|---|
| `effectiveConfig` | object | Resolved configuration after merging with `KropathConfig` org-wide settings. |
| `effectiveConfig.mandatory.encryptionKey` | string | Final mandatory encryption key (from mandatory tier or `KropathConfig`). |
| `effectiveConfig.mandatory.namingTemplate` | string | Final mandatory naming template. |
| `effectiveConfig.mandatory.tags` | map | Merged mandatory tags from profile and `KropathConfig`. |
| `effectiveConfig.mandatory.syncedLabels` | map | Merged mandatory labels to sync to K8s and cloud tags. |
| `effectiveConfig.mandatory.syncedAnnotations` | map | Merged mandatory annotations to sync to K8s. |
| `effectiveConfig.defaults.encryptionKey` | string | Final default encryption key. |
| `effectiveConfig.defaults.namingTemplate` | string | Final default naming template. |
| `effectiveConfig.defaults.tags` | map | Merged default tags from profile and `KropathConfig`. |
| `effectiveConfig.defaults.syncedLabels` | map | Default labels to sync when domain does not set them. |
| `effectiveConfig.defaults.syncedAnnotations` | map | Default annotations to sync when domain does not set them. |
| `effectiveConfig.aws.region` | string | AWS region for this cluster. |
| `effectiveConfig.aws.accountId` | string | AWS account ID for this cluster. |

## Organization-Wide Defaults

Organization-wide encryption and tagging policies flow from `KropathConfig` in the `kro-system` namespace. Profile-specific `CodeArtifactConfig` overrides org-wide settings:

```yaml
# Organization-wide settings (kro-system namespace)
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: kro-system-config
  namespace: kro-system
spec:
  mandatory:
    codeartifact:
      encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/org-cmk"
  defaults:
    tags:
      organization: acme-corp
      billing-entity: infrastructure

---
# Profile can override org-wide defaults
apiVersion: aws.kropath.run/v1alpha1
kind: CodeArtifactConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    encryptionKey: "arn:aws:kms:us-west-2:123456789012:key/prod-cmk"  # Override org CMK
  defaults:
    tags:
      environment: production  # Override org defaults
```

The domain's `status.effectiveConfig` reflects the final merged configuration.

## Encryption Key Options

### AWS-Managed Key

```yaml
defaults:
  encryptionKey: ""  # Empty: use AWS-managed key
```

Simplest option: AWS manages the key for you. No additional cost. Suitable for development and non-compliance workloads.

### Customer-Managed KMS Key

```yaml
defaults:
  encryptionKey: "arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

You control the key. Required for compliance audits where you must demonstrate key control and rotation. Additional AWS KMS costs.

## Best Practices

1. **Start with general-policy** — Create a `general-policy` profile with sensible defaults and no mandatory enforcements. Let it be the default choice for most workloads.

2. **Create compliance profiles** — For regulated workloads (PCI, HIPAA, SOC2), create separate `production` or `compliance` profiles with mandatory encryption and naming enforcements.

3. **Encode organizational standards in profiles** — Don't let developers choose encryption modes or naming schemes individually; put your standards in the profile so consistency is automatic.

4. **Use naming templates to prevent collisions** — Default template `{namespace}-{name}` provides namespace-scoping. Add `{account_id}` if domains must be globally unique across multiple AWS accounts.

5. **Set contact information at the domain level** — Use tags or `syncedAnnotations` to track domain ownership and support contacts.

6. **Document profile purpose** — Use descriptive names (`general-policy`, `production`, `compliance`) and document each profile's governance model in your internal wiki.

7. **Never set both mandatory and defaults for the same field** — Choose enforcement (mandatory) or flexibility (defaults), not both.

## Validation Rules

CodeArtifactConfig enforces these validation rules:

- `encryptionKey` cannot be set in both `mandatory` and `defaults` at the same time
- `namingTemplate` cannot be set in both `mandatory` and `defaults` at the same time
- Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) use additive merge semantics; no conflict validation needed

## Troubleshooting

### Encryption key conflict

```
Error: encryptionKey cannot be set in both mandatory and defaults
```

You specified the same field in both tiers. Remove it from one tier (typically keep it in mandatory for enforcement or defaults for flexibility).

### Naming template conflict

```
Error: namingTemplate cannot be set in both mandatory and defaults
```

Same issue: remove the field from one tier.

### Profile not found

When a domain uses `spec.configRef: my-profile` but the profile doesn't exist, the domain falls back to `general-policy` if it exists, or fails to reconcile if neither profile exists. Ensure the referenced profile exists in `kro-system` namespace.

## API Reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `CodeArtifactConfig`
- **Scope**: Namespaced (usually `kro-system`)
