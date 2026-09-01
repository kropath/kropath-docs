# SSMConfig — Governance and Profiles

`SSMConfig` is a CRD that defines organization-wide governance policies for the SSM family. Platform teams deploy one or more `SSMConfig` resources (called "profiles") to enforce mandatory settings and provide sensible defaults across all SSM instances in their organization.

## Overview

Each `SSMConfig` resource is a named governance profile that applies to SSM instances selecting it via `spec.configRef`. The profile contains two tiers of configuration:

- **`mandatory`:** Settings that cannot be overridden by instances (enforced policy)
- **`defaults`:** Settings applied when instances don't specify a value (fallback recommendation)

All fields in both tiers are optional—platform teams only set what they need to enforce.

## Core Fields

### Governance Tier Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SSMConfig` profile to apply |

Every SSM instance (Document, Parameter, PatchBaseline, ResourceDataSync) uses `spec.configRef` to select its governance profile. If not specified, defaults to `general-policy`.

### Mandatory Tier (Enforced)

The `mandatory` tier defines non-negotiable organizational requirements:

```yaml
spec:
  mandatory:
    type: SecureString                    # All parameters must be SecureString
    tier: Advanced                        # All parameters must be Advanced tier
    keyID: "arn:aws:kms:..."             # All SecureString parameters must use this KMS key
    documentType: Automation             # All documents must be Automation type
    allowedDocumentTypes:                # Restrict which document types can be created
      - Command
      - Automation
    operatingSystem: AMAZON_LINUX_2      # All patch baselines target this OS
    approvedPatchesComplianceLevel: HIGH # All baselines enforce HIGH compliance
    approvedPatchesEnableNonSecurity: true # All baselines must include non-security patches
    rejectedPatchesAction: BLOCK          # All baselines block rejected patches
    tags:                                 # Tags always applied; cannot be overridden
      Environment: Production
      Compliance: Required
    syncedLabels:                        # Kubernetes labels synchronized to AWS tags
      team: platform
    syncedAnnotations:                   # Kubernetes annotations synchronized to AWS tags
      owner: ops-team
    namingTemplate: "{namespace}-{name}-prod"  # Enforce naming pattern
```

**Behavior:**
- Platform teams set `mandatory` fields to enforce compliance
- SSM instances cannot override `mandatory` fields
- If an instance tries to override a mandatory field, the controller validation fails

### Defaults Tier (Recommended)

The `defaults` tier provides sensible fallback values when instances don't specify:

```yaml
spec:
  defaults:
    type: String                         # Default parameter type
    tier: Standard                       # Default parameter tier (Standard is cheaper)
    keyID: ""                            # No default KMS key enforcement
    documentType: Command                # Default document type
    allowedDocumentTypes: []             # No restriction (all types allowed)
    operatingSystem: WINDOWS             # Default OS for patch baselines
    approvedPatchesComplianceLevel: MEDIUM
    approvedPatchesEnableNonSecurity: false
    rejectedPatchesAction: ALLOW_AS_DEPENDENCY
    tags:
      Environment: Development
      Owner: TeamName
    syncedLabels: {}
    syncedAnnotations: {}
    namingTemplate: "{namespace}-{name}"
```

**Behavior:**
- SSM instances use defaults when they don't specify a value
- Instances can override defaults (no enforcement)
- If both mandatory and defaults are set for the same field, validation fails

## Profile Examples

### Profile: `general-policy` (Balanced)

Suitable for most use cases—reasonable security without heavy restrictions:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    allowedDocumentTypes:
      - Command
      - Automation
      - Policy
  defaults:
    type: String
    tier: Standard
    documentType: Command
    operatingSystem: WINDOWS
    approvedPatchesComplianceLevel: MEDIUM
    tags:
      ManagedBy: kropath
      Profile: general-policy
```

### Profile: `secure` (Hardened)

For sensitive workloads—enforces encryption, advanced tier, and specific key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: secure
  namespace: kro-system
spec:
  mandatory:
    type: SecureString                  # All parameters must be encrypted
    tier: Advanced                      # All parameters must use Advanced tier
    keyID: "arn:aws:kms:us-east-1:123456789012:key/12345678-..."
    allowedDocumentTypes:
      - Command
      - Automation
    approvedPatchesEnableNonSecurity: false
  defaults:
    documentType: Automation
    operatingSystem: AMAZON_LINUX_2
    approvedPatchesComplianceLevel: HIGH
    rejectedPatchesAction: BLOCK
    tags:
      SecurityProfile: Hardened
```

### Profile: `patching` (Compliance)

Focused on fleet patch compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: patching
  namespace: kro-system
spec:
  mandatory:
    operatingSystem: AMAZON_LINUX_2
    approvedPatchesComplianceLevel: HIGH
    rejectedPatchesAction: BLOCK
  defaults:
    approvedPatchesEnableNonSecurity: false
    tags:
      Purpose: Patching
      Compliance: Required
```

### Profile: `dev` (Permissive)

For development/testing—minimal restrictions:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: dev
  namespace: kro-system
spec:
  defaults:
    type: String
    tier: Standard
    documentType: Command
    tags:
      Environment: Development
```

## Governance Cascade

When an SSM instance doesn't specify a field, kropath resolves it using this cascade (ADR-015 §5.3):

1. **Global KropathConfig mandatory** — Org-wide enforcement for all profiles
2. **Local KropathConfig mandatory** — Namespace-level enforcement for all profiles
3. **Global SSMConfig mandatory** — Per-profile enforcement (org-wide)
4. **Local SSMConfig mandatory** — Per-profile enforcement (namespace)
5. **Instance spec value** — The instance's explicit choice
6. **Local SSMConfig defaults** — Per-profile default (namespace)
7. **Global SSMConfig defaults** — Per-profile default (org-wide)
8. **Local KropathConfig defaults** — All-profile default (namespace)
9. **Global KropathConfig defaults** — All-profile default (org-wide)
10. **RGD built-in** — Hard-coded fallback (e.g., `String` for parameter type)

Example: SSMParameter type resolution:

```
Result = mandatory.type from KropathConfig (global)
      OR mandatory.type from KropathConfig (local)
      OR mandatory.type from SSMConfig (global, profile-specific)
      OR mandatory.type from SSMConfig (local, profile-specific)
      OR instance.spec.type
      OR defaults.type from SSMConfig (local, profile-specific)
      OR defaults.type from SSMConfig (global, profile-specific)
      OR defaults.type from KropathConfig (local)
      OR defaults.type from KropathConfig (global)
      OR "String"  (RGD built-in)
```

## Special Cases and Constraints

### Parameter Type Immutability

`type` is immutable after parameter creation. If a mandatory tier forces `SecureString`, all new parameters will be SecureString, but existing parameters with a different type remain unchanged.

### Tier One-Way Upgrade

Standard → Advanced tier promotion is **irreversible**. Reverting requires deleting and recreating the parameter (data loss). Use `defaults.tier` for non-binding recommendations, not `mandatory.tier`, unless you intend to enforce Advanced tier organization-wide.

### Document Type + Allowed Types Validation

If both `documentType` and `allowedDocumentTypes` are set in the mandatory tier, the controller validates that `documentType` is a member of `allowedDocumentTypes`. A misconfiguration (e.g., `documentType: Automation` with `allowedDocumentTypes: [Command, Policy]`) causes:

```yaml
status:
  conditions:
    - type: Valid
      status: "False"
      reason: InvalidDocumentTypeNotInAllowedList
      message: "documentType 'Automation' not in allowedDocumentTypes [Command, Policy]"
```

The controller does not write `status.effectiveConfig` until resolved.

### Patch Compliance Levels

Valid compliance levels for `approvedPatchesComplianceLevel`:
- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INFORMATIONAL`
- `UNSPECIFIED` (default)

### Global Filters in Patch Baselines

The `globalFilters` field on patch baselines is CLI/SDK-only and not available in the AWS Patch Manager console. Document this limitation to your users when governance includes patch filtering.

## Validation

`SSMConfig` includes `x-kubernetes-validations` rules preventing fields from being set in both `mandatory` and `defaults` simultaneously. Invalid configurations are rejected at creation time.

## Deploying Profiles

Platform teams typically deploy 2-4 governance profiles to `kro-system` namespace at cluster setup:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  mandatory:
    allowedDocumentTypes: [Command, Automation]
  defaults:
    type: String
    tier: Standard
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: secure
  namespace: kro-system
spec:
  mandatory:
    type: SecureString
    tier: Advanced
    keyID: "arn:aws:kms:us-east-1:123456789012:key/..."
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMConfig
metadata:
  name: patching
  namespace: kro-system
spec:
  mandatory:
    operatingSystem: AMAZON_LINUX_2
    approvedPatchesComplianceLevel: HIGH
```

Applications then reference profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMParameter
metadata:
  name: api-key
  namespace: production
spec:
  configRef: secure  # Use the secure profile for encryption
  type: SecureString
  valueFrom:
    secretKeyRef:
      name: api-credentials
      key: key
```

## Best Practices

1. **Create 2-4 profiles, not one-per-team.** Limit profile explosion; use a few well-defined policies instead.
2. **Use `defaults` liberally, `mandatory` sparingly.** Enforcement should be minimal; recommendations should be generous.
3. **Document profile purposes.** Add labels or descriptions so teams know which profile fits their use case.
4. **Validate tier upgrades.** Be cautious with `mandatory.tier: Advanced`—it's irreversible.
5. **Reference governance docs.** Link to ADR-010 and ADR-015 when explaining cascade to teams.
6. **Test profile changes.** Deploying a new mandatory constraint affects all existing instances using that profile.

## Next Steps

- [SSMParameter Guide](./ssmparameter.md) — Using parameter governance
- [SSMDocument Guide](./ssmdocument.md) — Document type governance
- [SSMPatchBaseline Guide](./ssmpatchbaseline.md) — Patch compliance governance
- [ADR-010](../../adrs/010-governance-cascade.md) — Governance cascade design
- [ADR-015 §3 & §5](../../adrs/015-consolidated-platform-decisions.md) — Consolidated governance decisions
