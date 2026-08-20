# ECRConfig — Setting Up Governance Profiles

The `ECRConfig` resource defines governance profiles that control encryption, tag immutability, naming conventions, and lifecycle policies for all repositories in your organization. Platform teams use these profiles to enforce compliance and establish sensible defaults for developers.

## Core Concepts

Each `ECRConfig` profile has two tiers:

- **Mandatory tier** — Organization-wide enforcement that overrides developer choices
- **Defaults tier** — Fallback values applied when a repository doesn't specify a setting

For example, a `pci` profile might mandate immutable tags and KMS encryption, while a `general-policy` profile provides defaults but lets developers choose their encryption.

## Configuration Fields

### Image Tag Mutability

| Field | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `imageTagMutability` | Mandatory | string | `""` (not enforced) | Force all repositories to `IMMUTABLE` or `MUTABLE` tags. Mandatory tier overrides developer choice. |
| `imageTagMutability` | Defaults | string | `"MUTABLE"` | Default tag mutability when the repository doesn't specify one |

**Values:** `"IMMUTABLE"` or `"MUTABLE"`

### Encryption

| Field | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `encryptionType` | Mandatory | string | `""` (not enforced) | Force all repositories to use `"AES256"` (AWS-managed) or `"KMS"` (customer-managed). Mandatory tier overrides developer choice. |
| `encryptionType` | Defaults | string | `"AES256"` | Default encryption type when the repository doesn't specify one |
| `kmsKeyID` | Mandatory | string | `""` (not set) | ARN of the KMS key to enforce for all repositories. Only applies if `encryptionType` is `"KMS"`. |
| `kmsKeyID` | Defaults | string | `""` | Default KMS key ARN when the repository doesn't specify one and `encryptionType` is `"KMS"` |

**Important:** When `encryptionType` is `"AES256"`, `kmsKeyID` must be empty — AES256 encryption does not use a customer-managed key.

### Lifecycle Policies

| Field | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `lifecyclePolicy` | Mandatory | string | `""` (not enforced) | Force all repositories to use this lifecycle policy JSON document. Overrides developer choice. |
| `lifecyclePolicy` | Defaults | string | `""` | Default lifecycle policy when the repository doesn't specify one |

**Format:** Standard AWS ECR lifecycle policy JSON (see AWS documentation for structure).

### Naming Convention

| Field | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `namingTemplate` | Mandatory | string | `""` (not enforced) | Force all repositories to follow this naming pattern. Overrides developer `spec.nameOverride`. |
| `namingTemplate` | Defaults | string | `"{namespace}/{name}"` | Default naming pattern when the repository doesn't specify one |

**Available tokens:** `{name}`, `{namespace}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.KEY}` (any tag key)

### Tags and Metadata

| Field | Tier | Type | Default | Purpose |
|---|---|---|---|---|
| `tags` | Mandatory | map | `{}` | AWS tags that all repositories inherit (cannot be removed by developers) |
| `tags` | Defaults | map | `{}` | Default AWS tags applied when the repository doesn't specify any |
| `syncedLabels` | Mandatory | map | `{}` | Kubernetes labels synced to AWS tags (prefixed `aws.kropath.run/`) |
| `syncedLabels` | Defaults | map | `{}` | Default synced labels applied when the repository doesn't specify any |
| `syncedAnnotations` | Mandatory | map | `{}` | Kubernetes annotations that repositories inherit |
| `syncedAnnotations` | Defaults | map | `{}` | Default synced annotations applied when the repository doesn't specify any |

## Built-In Profiles

kropath includes three example profiles:

### general-policy (Default)

Minimal enforcement with sensible defaults:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    imageTagMutability: "MUTABLE"
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{name}"
```

**Use when:** You want to provide guidance without enforcing constraints. Developers can override defaults if needed.

### pci (PCI Compliance)

Strict enforcement for PCI-DSS compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/mrk-pci-cmk"
  defaults:
    namingTemplate: "{namespace}/{configRef}/{name}"
```

**Use when:** You need PCI-DSS compliance. All repositories will have immutable tags and customer-managed encryption. The mandatory tier cannot be overridden.

### immutable-only

Enforce immutable tags with default encryption:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: immutable-only
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: immutable-only
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
  defaults:
    encryptionType: "AES256"
    namingTemplate: "{namespace}/{name}"
```

**Use when:** You want to enforce immutable tags for supply chain security but allow developers to choose their encryption approach.

## Creating Custom Profiles

Create new profiles by defining an `ECRConfig` in the `kro-system` namespace:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: production  # Profile name — used by repositories via configRef
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production  # Required for label selector lookup
spec:
  mandatory:
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/mrk-prod"
    tags:
      environment: production
      compliance: required
  defaults:
    imageTagMutability: "IMMUTABLE"
    namingTemplate: "{namespace}/prod/{name}"
    tags:
      team: platform
```

## How Repositories Use Profiles

Repositories select a governance profile using `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ECRRepository
metadata:
  name: my-app
  namespace: app-team
spec:
  configRef: production  # Uses the "production" profile
  tags:
    app: my-app
```

**Resolution order:**
1. If `configRef` is set and the profile exists, use that profile
2. If `configRef` is empty or the profile doesn't exist, fall back to `general-policy`
3. Mandatory tier settings override repository `spec`
4. Repository `spec` overrides defaults tier

## Key Behaviors

### Tier Mutual Exclusivity

For scalar governance fields (imageTagMutability, encryptionType, kmsKeyID, lifecyclePolicy, namingTemplate), either the mandatory tier **or** the defaults tier may be set, but not both. If you try to set the same scalar field in both tiers, kropath rejects the profile.

Map fields (tags, syncedLabels, syncedAnnotations) are exempt from this rule and can appear in both tiers — they merge additively (see Tag Merging below).

### Tag Merging

Tags are merged additively across all tiers:
- Mandatory tags are always present
- Developer-specified tags are added
- Default tags fill in any gaps

Example:
```
Mandatory: {environment: production, compliance: required}
Developer:  {app: my-app}
Defaults:   {team: platform, cost-center: engineering}

Result: {environment: production, compliance: required, app: my-app, team: platform, cost-center: engineering}
```

### Encryption Configuration Validation

kropath validates the combination of `encryptionType` and `kmsKeyID`:
- If `encryptionType: "AES256"` and `kmsKeyID` is set, the profile is rejected (AES256 doesn't use a CMK)
- If `encryptionType: "KMS"` and `kmsKeyID` is empty, AWS uses a default KMS key

## Common Patterns

### Compliance-Driven Governance

Separate profiles by compliance requirement:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/mrk-pci"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    imageTagMutability: "IMMUTABLE"
    encryptionType: "KMS"
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/mrk-hipaa"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    imageTagMutability: "MUTABLE"
    encryptionType: "AES256"
```

Teams select `spec.configRef: pci` for payment systems, `spec.configRef: hipaa` for healthcare, and `spec.configRef: general-policy` for everything else.

### Namespace-Based Naming

Use the naming template to automatically organize repositories by namespace:

```yaml
defaults:
  namingTemplate: "{namespace}/{name}"
```

Repositories in `payments` namespace are named `payments/my-app`, repositories in `analytics` are named `analytics/my-app`.

### Staging and Production Separation

Use profile names in the naming template:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: staging
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: staging
spec:
  defaults:
    namingTemplate: "{namespace}/staging/{name}"
---
apiVersion: aws.kropath.run/v1alpha1
kind: ECRConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    encryptionType: "KMS"
    imageTagMutability: "IMMUTABLE"
  defaults:
    namingTemplate: "{namespace}/prod/{name}"
```

## Troubleshooting

### "Cannot set field in both mandatory and defaults"

Error: The same field is configured in both tiers. Fix: Remove the field from one tier.

### Repositories Not Using Updated Profile

Changes to mandatory and defaults tiers in `ECRConfig` propagate to existing repositories on the next reconciliation cycle, since repositories read the profile's `status.effectiveConfig` at every reconcile loop. However, ECR itself enforces immutability constraints on certain fields: encryption type and repository name cannot be changed after creation. Mutable settings (tag mutability, lifecycle policies, tags, and naming conventions applied at creation time) do propagate on profile updates. For fields locked by ECR's immutability constraints, update the repository's `spec` directly if you need to change them.

### "Invalid encryption configuration"

Error: `encryptionType: "AES256"` is set with a `kmsKeyID`. Fix: Remove the `kmsKeyID` when using AES256, or change to `encryptionType: "KMS"`.
