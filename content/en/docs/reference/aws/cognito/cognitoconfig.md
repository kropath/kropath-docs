---
title: CognitoConfig — Governance Configuration
description: "The `CognitoConfig` resource defines governance profiles that control how Cognito user pools are created and configured across your organization and namespaces."
doc_type: reference
---
# CognitoConfig — Governance Configuration

The `CognitoConfig` resource defines governance profiles that control how Cognito user pools are created and configured across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each user pool.

## Overview

`CognitoConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., MFA enforcement, mandatory deletion protection, required password policies)
- **Defaults tier** — Baseline values developers can override (e.g., default MFA level, default password length)

This two-tier approach lets platform teams enforce critical security and compliance controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `mfaConfiguration` | string | MFA enforcement: `OFF`, `OPTIONAL`, or `ON`. Empty = not enforced. |
| `deletionProtection` | string | Deletion protection: `ACTIVE` or `INACTIVE`. Empty = not enforced. |
| `advancedSecurityMode` | string | Advanced security mode: `OFF`, `AUDIT`, or `ENFORCED`. Empty = not enforced. |
| `passwordPolicy.minimumLength` | integer | Minimum password length (6–99). 0 = not enforced. |
| `passwordPolicy.requireLowercase` | boolean | Require lowercase characters. Omit to inherit governance default. |
| `passwordPolicy.requireNumbers` | boolean | Require numeric characters. Omit to inherit governance default. |
| `passwordPolicy.requireSymbols` | boolean | Require special characters. Omit to inherit governance default. |
| `passwordPolicy.requireUppercase` | boolean | Require uppercase characters. Omit to inherit governance default. |
| `passwordPolicy.temporaryPasswordValidityDays` | integer | Temp password expiry (1–365 days). 0 = not enforced. |
| `namingTemplate` | string | Naming pattern for pool names (e.g. `{namespace}-{name}`). Empty = no mandatory template. |
| `tags` | map | Cloud tags applied to all pools. Cannot be removed by developers. |
| `syncedLabels` | map | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the pool level:

| Field | Type | Purpose |
|---|---|---|
| `mfaConfiguration` | string | Default MFA level when pool doesn't specify one. Defaults to `OFF`. |
| `deletionProtection` | string | Default protection state. Defaults to `INACTIVE`. |
| `advancedSecurityMode` | string | Default advanced security mode. Empty = no advanced security by default. |
| `passwordPolicy.minimumLength` | integer | Default minimum password length. Defaults to 8. |
| `passwordPolicy.requireLowercase` | boolean | Default lowercase requirement. Defaults to `true`. |
| `passwordPolicy.requireNumbers` | boolean | Default numeric requirement. Defaults to `true`. |
| `passwordPolicy.requireSymbols` | boolean | Default special character requirement. Defaults to `true`. |
| `passwordPolicy.requireUppercase` | boolean | Default uppercase requirement. Defaults to `true`. |
| `passwordPolicy.temporaryPasswordValidityDays` | integer | Default temp password expiry. Defaults to 7 days. |
| `namingTemplate` | string | Default naming pattern (e.g. `{namespace}-{name}`). |
| `tags` | map | Default cloud tags. Can be overridden per-pool. |
| `syncedLabels` | map | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. Empty values like `{}`, `[]`, or `""` indicate "not set" and can appear in both tiers.

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    mfaConfiguration: "OFF"
    deletionProtection: "INACTIVE"
    advancedSecurityMode: ""
    passwordPolicy:
      minimumLength: 8
      requireLowercase: true
      requireNumbers: true
      requireSymbols: true
      requireUppercase: true
      temporaryPasswordValidityDays: 7
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

### High Security (high-security)

Enforces MFA, deletion protection, and stronger password policies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoConfig
metadata:
  name: high-security
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-security
spec:
  mandatory:
    mfaConfiguration: "ON"
    deletionProtection: "ACTIVE"
    advancedSecurityMode: "ENFORCED"
    passwordPolicy:
      minimumLength: 12
  defaults:
    passwordPolicy:
      requireLowercase: true
      requireNumbers: true
      requireSymbols: true
      requireUppercase: true
      temporaryPasswordValidityDays: 7
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using this profile cannot override:
- MFA enforcement (must be ON)
- Deletion protection (must be ACTIVE)
- Advanced security (must be ENFORCED)
- Minimum password length (must be at least 12)

### PCI Compliance (pci)

Enforces PCI-DSS compliance with mandatory encryption and security controls:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    mfaConfiguration: "ON"
    deletionProtection: "ACTIVE"
    advancedSecurityMode: "ENFORCED"
    passwordPolicy:
      minimumLength: 14
      requireLowercase: true
      requireNumbers: true
      requireSymbols: true
      requireUppercase: true
    tags:
      compliance: pci-dss
  defaults:
    passwordPolicy:
      temporaryPasswordValidityDays: 1
    namingTemplate: "pci-{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Deploy

1. Create the profile CRs in `kro-system` namespace (reserved for system-wide configuration):

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    mfaConfiguration: "OFF"
    deletionProtection: "INACTIVE"
    advancedSecurityMode: ""
    passwordPolicy:
      minimumLength: 8
      requireLowercase: true
      requireNumbers: true
      requireSymbols: true
      requireUppercase: true
      temporaryPasswordValidityDays: 7
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers create user pools that reference the profile:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CognitoUserPool
metadata:
  name: auth-pool
  namespace: app-team
spec:
  configRef: general-policy
  mfaConfiguration: "OPTIONAL"
EOF
```

## How Governance Is Resolved

When you create a user pool, the selected `CognitoConfig` profile merges with any org-wide settings to determine the final governance configuration. Platform teams set mandatory fields that developers cannot override, and defaults that apply when developers don't specify a value.

To audit which governance settings apply to a profile:

```bash
kubectl describe cognitoconfig general-policy -n kro-system
```

This shows you the complete merged governance: all mandatory fields (platform enforcement), all defaults (developer overrides possible), and AWS account/region information.

This single config CR ensures consistent, auditable governance across all user pools that reference it.

## Governance Cascade

All governance fields follow a three-tier resolution:

1. **Mandatory tier** (from selected CognitoConfig and org-wide KropathConfig) — takes precedence
2. **Instance spec** (developer choice) — overrides defaults but loses to mandatory
3. **Defaults tier** (fallback) — applies only when neither mandatory nor instance spec is set

### Naming Template Tokens

Pool names use a configurable template. Available tokens:

- `{name}` — The pool's Kubernetes resource name
- `{namespace}` — The pool's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Any tag key from merged tags (e.g., `{tag.environment}`)

Example: A profile with `namingTemplate: "{namespace}-{configRef}-{tag.environment}-{name}"` produces names like `auth-team-high-security-production-main-pool`.

**Important:** Pool names cannot be changed after creation. Renaming the template or profile on an existing pool does not rename the AWS pool — it remains registered under its original name.
