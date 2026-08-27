# ACMConfig — Certificate Manager Governance

The `ACMConfig` resource defines governance policies for the Certificate Manager family. Platform teams use `ACMConfig` to enforce compliance requirements, security standards, and operational defaults across all certificate resources.

## Core Fields

### Governance Tiers

`ACMConfig` uses a two-tier governance model:

| Tier | Priority | Purpose |
|---|---|---|
| `spec.mandatory` | Highest | Platform-enforced requirements — cannot be overridden by developers |
| `spec.defaults` | Lowest | Sensible fallbacks applied when a resource does not specify a value |

Developer choices in the resource `spec` override the defaults tier but cannot override mandatory tier settings.

## Mandatory Tier

The `spec.mandatory` section enforces non-negotiable requirements:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `keyAlgorithm` | string | `""` (not enforced) | Enforce a specific key algorithm (RSA_2048, EC_prime256v1, EC_secp384r1). Empty string means no enforcement. |
| `certificateTransparencyLogging` | string | `""` (not enforced) | Enforce CT logging for public certificates (ENABLED or DISABLED). Empty string means no enforcement. |
| `usageMode` | string | `""` (not enforced) | For private CAs: enforce GENERAL_PURPOSE or SHORT_LIVED_CERTIFICATE mode. |
| `keyStorageSecurityStandard` | string | `""` (not enforced) | Enforce FIPS level for private CAs (FIPS_140_2_LEVEL_2_OR_HIGHER or FIPS_140_2_LEVEL_3_OR_HIGHER). |
| `tags` | map | `{}` | AWS tags applied to all resources; cannot be removed by developers. |
| `syncedLabels` | map | `{}` | Kubernetes labels (prefixed `aws.kropath.run/`) applied to all resources. |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) applied to all resources. |

## Defaults Tier

The `spec.defaults` section provides fallback values applied when a resource does not specify a value:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `keyAlgorithm` | string | `"RSA_2048"` | Default key algorithm for certificates and CAs |
| `certificateTransparencyLogging` | string | `"ENABLED"` | Default CT logging setting for public certificates |
| `usageMode` | string | `"GENERAL_PURPOSE"` | Default usage mode for private CAs |
| `keyStorageSecurityStandard` | string | `"FIPS_140_2_LEVEL_3_OR_HIGHER"` | Default FIPS level for private CA key storage |
| `tags` | map | `{}` | Tags merged into resources (lower priority than developer tags) |
| `syncedLabels` | map | `{}` | Labels merged into resources (lower priority than developer labels) |
| `syncedAnnotations` | map | `{}` | Annotations merged into resources (lower priority than developer annotations) |

## Governance Cascade

Effective configuration for each resource is determined by a three-layer cascade:

```
Developer spec (highest priority)
    ↓ overrides defaults, cannot override mandatory
Governance defaults tier
    ↓ fallback values
Governance mandatory tier (enforced)
    ↑ cannot be overridden
```

**Example:** If the PCI profile has `mandatory.keyAlgorithm: "EC_prime256v1"`, all certificates in that profile use EC_prime256v1 regardless of what the certificate's `spec.keyAlgorithm` specifies. If the profile has no mandatory key algorithm but specifies `defaults.keyAlgorithm: "RSA_2048"`, that becomes the default unless the certificate specifies a different value.

## Profile Examples

### general-policy (Default)

Suitable for most workloads with sensible security defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory: {}
  defaults:
    keyAlgorithm: "RSA_2048"
    certificateTransparencyLogging: "ENABLED"
    usageMode: "GENERAL_PURPOSE"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
    tags:
      managed-by: "kropath"
```

### pci (PCI Compliance)

Enforces strong cryptography and CT logging for PCI-DSS compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    keyAlgorithm: "EC_prime256v1"
    certificateTransparencyLogging: "ENABLED"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
    tags:
      compliance: "pci-dss"
      encryption: "mandatory"
  defaults:
    keyAlgorithm: "EC_prime256v1"
    certificateTransparencyLogging: "ENABLED"
    usageMode: "GENERAL_PURPOSE"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
```

### internal-services (Internal mTLS)

Optimized for ephemeral internal service-to-service certificates:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMConfig
metadata:
  name: internal-services
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: internal-services
spec:
  mandatory: {}
  defaults:
    keyAlgorithm: "EC_prime256v1"
    certificateTransparencyLogging: "DISABLED"
    usageMode: "SHORT_LIVED_CERTIFICATE"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
    tags:
      scope: "internal"
      rotation: "frequent"
```

## Resource Selection

Each Certificate Manager resource selects a governance profile via `spec.configRef`. If the referenced profile does not exist, the resource falls through to the `general-policy` profile.

**Example:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMCertificate
metadata:
  name: payment-cert
  namespace: payments
spec:
  configRef: pci
  domainName: "payment.example.com"
```

If the `pci` profile exists, governance from that profile applies. If it doesn't exist, the resource uses `general-policy` instead.

## KropathConfig Org-Wide Cascade

`KropathConfig` defines org-wide defaults that apply to all profiles. `ACMConfig` profiles can override org-wide settings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: default
  namespace: kro-system
spec:
  mandatory:
    certificateManager:
      certificateTransparencyLogging: "ENABLED"
  defaults:
    certificateManager:
      keyAlgorithm: "RSA_2048"
```

This makes CT logging mandatory across the entire org, unless an `ACMConfig` profile explicitly sets a different value.

## Creating Custom Profiles

To create a custom governance profile for your organization:

1. Define the `ACMConfig` CR in your cluster
2. Set the `metadata.labels.aws.kropath.run/resource-name` to match the profile name
3. Configure `spec.mandatory` for non-negotiable requirements
4. Configure `spec.defaults` for sensible fallbacks
5. Reference the profile in resource specs via `configRef`

**Example: High-Security Profile**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ACMConfig
metadata:
  name: high-security
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-security
spec:
  mandatory:
    keyAlgorithm: "EC_secp384r1"
    certificateTransparencyLogging: "ENABLED"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
    tags:
      security-level: "high"
      encryption: "secp384r1"
      compliance: "enhanced"
  defaults:
    keyAlgorithm: "EC_secp384r1"
    certificateTransparencyLogging: "ENABLED"
    usageMode: "GENERAL_PURPOSE"
    keyStorageSecurityStandard: "FIPS_140_2_LEVEL_3_OR_HIGHER"
```

## Validation Rules

`ACMConfig` uses Kubernetes validation rules (`x-kubernetes-validations`) to prevent invalid configurations:

- A field cannot be set in both `mandatory` and `defaults` tiers simultaneously (choose one tier per field)
- `keyAlgorithm` must be one of: `""`, `RSA_2048`, `RSA_4096`, `EC_prime256v1`, `EC_secp384r1`
- `certificateTransparencyLogging` must be one of: `""`, `ENABLED`, `DISABLED`
- `usageMode` must be one of: `""`, `GENERAL_PURPOSE`, `SHORT_LIVED_CERTIFICATE`
- `keyStorageSecurityStandard` must be one of: `""`, `FIPS_140_2_LEVEL_2_OR_HIGHER`, `FIPS_140_2_LEVEL_3_OR_HIGHER`

## Tag Merging

Tags from multiple sources are merged in order of precedence:

1. Mandatory tier tags (highest priority — cannot be removed)
2. Developer `spec.tags` (can be added to, but not removed if in mandatory)
3. Defaults tier tags (lowest priority — overridden by developer tags)

**Example:**

```
Mandatory: {security: "required", managed-by: "kropath"}
Developer: {environment: "prod", security: "enhanced"}
Defaults: {team: "platform", environment: "default"}

Result: {
  security: "enhanced",        # Developer overrides mandatory default
  managed-by: "kropath",       # Mandatory tier
  environment: "prod",         # Developer overrides default
  team: "platform"             # From defaults
}
```

## Troubleshooting

### Governance Enforcement Issues

Check `status.conditions` on the affected certificate resource:

- If a mandatory setting is not being applied, verify the profile name in `spec.configRef` matches the profile's `metadata.labels.aws.kropath.run/resource-name`
- If the resource falls back to `general-policy`, check that the referenced profile exists

### FIPS Level Conflicts

Some AWS regions (e.g., `ap-northeast-3`, `ap-southeast-3`) support only FIPS Level 2. If you get an AWS error about FIPS level, update your `ACMConfig.defaults.keyStorageSecurityStandard` to `FIPS_140_2_LEVEL_2_OR_HIGHER` for those regions.

## Further Reading

- [Certificate Manager Family Spec](https://github.com/kropath/kropath-core/blob/main/docs/families/aws/certificate-manager.md) — complete governance design
- [ADR-015: Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md) — governance cascade framework
