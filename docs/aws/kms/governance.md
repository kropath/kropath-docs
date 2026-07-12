# AWSKMSConfig — Governance Configuration

The `AWSKMSConfig` resource defines governance profiles that control KMS key behavior across your organization and namespaces. Platform teams create named profiles; developers and operators select the profile they need via `spec.configRef` on each KMS key.

## Overview

`AWSKMSConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., all keys must be rotated, only allow symmetric encryption)
- **Defaults tier** — Baseline values developers can override (e.g., default key type if not specified)

This two-tier approach lets platform teams enforce critical compliance controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `enableKeyRotation` | boolean | If `true`, all symmetric keys must have automatic rotation enabled |
| `keySpec` | string | Forces a specific key type (e.g., `SYMMETRIC_DEFAULT`, `RSA_4096`) |
| `keyUsage` | string | Forces a specific key usage (e.g., `ENCRYPT_DECRYPT`, `SIGN_VERIFY`) |
| `allowedKeySpecs` | list | Restricts allowed key types (e.g., only `SYMMETRIC_DEFAULT` and `RSA_4096` allowed) |
| `namingTemplate` | string | Template for key alias names (e.g., `{namespace}-{name}`) |
| `tags` | map | Tags applied to all keys (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Purpose |
|---|---|---|
| `enableKeyRotation` | boolean | Default rotation behavior (applied if not specified on key instance) |
| `keySpec` | string | Default key type (applied if not specified) |
| `keyUsage` | string | Default key usage (applied if not specified) |
| `allowedKeySpecs` | list | Default allowlist of key types (can be overridden per profile) |
| `namingTemplate` | string | Default naming template |
| `tags` | map | Default tags for resources |
| `syncedLabels` | map | Default labels |
| `syncedAnnotations` | map | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. Empty values like `{}`, `[]`, `""`, or `false` can appear in both tiers — they indicate "not set" and don't trigger the mutual-exclusion check.

## Example Profiles

### Conservative Baseline (general-policy)

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    enableKeyRotation: true
    keySpec: "SYMMETRIC_DEFAULT"
    keyUsage: "ENCRYPT_DECRYPT"
    allowedKeySpecs: []  # No restriction — any key type allowed
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
      team: platform
```

This profile uses sensible defaults: symmetric keys with rotation enabled, but allows developers to create other key types if needed.

### Hardened (pci)

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSConfig
metadata:
  name: pci
  namespace: kro-system
spec:
  mandatory:
    enableKeyRotation: true  # All keys must have rotation
    allowedKeySpecs:         # Only these key types allowed
      - SYMMETRIC_DEFAULT
      - RSA_4096
    tags:
      compliance: pci
      retention-days: "365"
  defaults:
    keySpec: "SYMMETRIC_DEFAULT"
    keyUsage: "ENCRYPT_DECRYPT"
    namingTemplate: "pci-{namespace}-{name}"
```

This hardened profile enforces strict controls for PCI compliance: rotation is mandatory, only symmetric keys and RSA-4096 are allowed, and all keys are tagged for compliance tracking.

### Development (dev)

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSConfig
metadata:
  name: dev
  namespace: kro-system
spec:
  mandatory: {}  # No mandatory controls
  defaults:
    enableKeyRotation: false  # Rotation optional
    keySpec: "SYMMETRIC_DEFAULT"
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development
```

This development profile is permissive: no mandatory controls, rotation is optional, developers can create any key type.

## Using Profiles

Select a profile on any KMS key:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSKey
metadata:
  name: database-encryption-key
  namespace: data-team
spec:
  configRef: general-policy  # Select the profile
  description: "Key for encrypting database backups"
```

If the named profile does not exist, kropath automatically falls back to `general-policy`. This ensures every key has a governance profile, even if the specific one requested isn't deployed.

## Governance Cascade

Kropath employs a ten-tier governance cascade to resolve effective configuration for KMS keys. This ensures organizational-level policies take precedence while allowing per-profile and per-instance flexibility.

### The Ten-Tier Cascade

| Tier | Layer | Scope |
|---|---|---|
| 1–2 | `AWSKropathConfig.mandatory.kms.*` | Organization-wide, all profiles |
| 3–4 | `AWSKMSConfig.mandatory.*` | Per-profile, all namespaces |
| 5 | `AWSKMSKey.spec.*` | Instance-level (developer choice) |
| 6–7 | `AWSKMSConfig.defaults.*` | Per-profile defaults |
| 8–9 | `AWSKropathConfig.defaults.kms.*` | Organization-wide defaults |

**How it works:** For each field, the cascade evaluates from tier 1 down to tier 9. The first tier with a value wins. This means:
- Org-wide mandatory controls (tier 1–2) override everything
- Per-profile governance (tier 3–4) is more specific than org-wide
- Instance-level choices (tier 5) are the most flexible
- Defaults (tier 6–9) apply only when nothing more specific is set

### Example Cascade Resolution

Scenario: Alice creates a KMS key with no `keySpec` specified:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSKey
metadata:
  name: my-key
  namespace: payments
spec:
  configRef: pci
  # keySpec is empty — will be resolved by the cascade
```

The cascade resolves as:
1. **Tier 1–2** (org-wide mandatory KMS): No `keySpec` set
2. **Tier 3** (global PCI profile mandatory): `keySpec` is not in mandatory (empty)
3. **Tier 4** (namespace PCI profile mandatory): Not applicable; only global exists
4. **Tier 5** (instance spec): Not set by Alice
5. **Tier 6–7** (profile defaults): `pci` defaults has `keySpec: "SYMMETRIC_DEFAULT"` → **Use this value**

Result: Alice's key gets `SYMMETRIC_DEFAULT`, enforcing the security posture of the `pci` profile.

### Key Rotation Semantics

`enableKeyRotation` only applies to symmetric encryption keys (`keySpec: SYMMETRIC_DEFAULT`). For asymmetric and HMAC keys, the AWS API silently ignores this field. Kropath passes the value through without filtering — AWS KMS handles the constraint.

**To disable rotation on a profile that defaults to enabled:** Create a dedicated `AWSKMSConfig` profile with `mandatory.enableKeyRotation: false` and select it via `spec.configRef`.

### Key Spec and Allowed Key Specs

If your `AWSKMSConfig` sets both `mandatory.keySpec` (e.g., `SYMMETRIC_DEFAULT`) and `mandatory.allowedKeySpecs` (e.g., `[RSA_4096]`), the configuration is invalid — the controller will flag this as an error and no keys will be created until it's fixed.

**Best practice:** Use `allowedKeySpecs` to restrict options, not `keySpec`. Reserve `keySpec` only when you want to force a single key type.

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKMSConfig
metadata:
  name: hybrid
  namespace: kro-system
spec:
  mandatory:
    # Don't do this (conflicting signals):
    # keySpec: "SYMMETRIC_DEFAULT"
    # allowedKeySpecs: ["RSA_4096"]
    
    # Do this instead:
    allowedKeySpecs:
      - SYMMETRIC_DEFAULT
      - RSA_4096
  defaults:
    keySpec: "SYMMETRIC_DEFAULT"  # Default to symmetric, but allow RSA via mandatory allowlist
```

## Boolean Governance Semantics

For boolean fields like `enableKeyRotation`, `false` in a `mandatory` or `defaults` tier means "follow the next tier in the cascade" rather than explicitly disabling the control. This is the zero-value sentinel.

**Example:** If `AWSKMSConfig.mandatory.enableKeyRotation = false` and `AWSKMSConfig.defaults.enableKeyRotation = true`, the default tier wins and keys get rotation enabled.

To explicitly disable a control (e.g., no rotation), create a dedicated profile with `mandatory.enableKeyRotation: false`.

## Naming Templates

Each `AWSKMSConfig` profile can define a naming template for automatic alias generation. The template supports these tokens:

- `{namespace}` — Kubernetes namespace
- `{name}` — KMS key resource name
- `{tag.NAME}` — Custom tag value (e.g., `{tag.environment}`)

**Default template:** `{namespace}-{name}`

**Example templates:**
```yaml
namingTemplate: "{namespace}-{name}"          # Namespace + resource name
namingTemplate: "{tag.team}-{namespace}-{name}" # Team tag + namespace + resource name
namingTemplate: "prod-{name}"                  # Hardcoded prefix + resource name
```

If a template references a missing tag (e.g., `{tag.environment}` but the key has no `environment` tag), the naming fails and the key is not created.

## Tags and Labels

Tags and labels are inherited from the `AWSKMSConfig` governance profile, merged with instance-level tags/labels, and then synced to AWS and Kubernetes:

- **`tags`:** Applied to the AWS KMS key; mandatory tags cannot be removed
- **`syncedLabels`:** Mirrored as both Kubernetes labels (prefixed `kropath.run/`) and AWS tags
- **`syncedAnnotations`:** Mirrored as Kubernetes annotations (prefixed `kropath.run/`)

**Example:**

`AWSKMSConfig` with mandatory tags:
```yaml
spec:
  mandatory:
    tags:
      cost-center: security
      compliance: pci
```

Instance with custom tags:
```yaml
spec:
  tags:
    app: payment-processor
```

Result: The KMS key gets all three tags (`cost-center`, `compliance`, `app`), and mandatory tags cannot be removed.

## Organization-Wide Governance (AWSKropathConfig)

For blanket governance across all KMS keys and profiles, use the `kms` section of `AWSKropathConfig`:

```yaml
apiVersion: kropath.run/v1alpha1
kind: AWSKropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    kms:
      enableKeyRotation: true       # All symmetric keys must have rotation
      allowedKeySpecs:              # Organization-wide key type restriction
        - SYMMETRIC_DEFAULT
        - RSA_4096
  defaults:
    kms:
      enableKeyRotation: true
      allowedKeySpecs: []           # Defaults to no restriction
```

This ensures that:
1. Every symmetric key in the organization has rotation enabled (level 1 of cascade)
2. Only specific key types are allowed (level 1 of cascade)
3. Per-profile configurations cannot override org-wide mandates

## Next Steps

- [AWSKMSKey Usage Guide](./awskmskey.md) — Complete field reference and examples
- [Cross-Family Integration](./cross-family-integration.md) — How to use KMS keys in S3, EBS, RDS, Lambda, and EKS
