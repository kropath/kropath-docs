# SecretsManagerConfig — Governance Configuration

The `SecretsManagerConfig` resource defines governance profiles that control how secrets are created and replicated across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each secret.

## Overview

`SecretsManagerConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., encryption keys that all secrets must use, required replication to DR regions)
- **Defaults tier** — Baseline values developers can override (e.g., default encryption key, default naming pattern)

This two-tier approach lets platform teams enforce critical compliance and security controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `kmsKeyID` | string | Encryption key enforcement: KMS key ARN, ID, or alias. Empty = not enforced. |
| `replicaRegions` | array | Cross-region replication targets that cannot be overridden (list of regions with optional per-region KMS key). Empty = no replication mandate. |
| `forceOverwriteReplicaSecret` | boolean | Forces overwrite behavior when replicating to a region that already has a secret with the same name. `false` = not enforced. |
| `namingTemplate` | string | Naming pattern for secret names (e.g. `{namespace}-{configRef}-{name}`). Empty = no mandatory template. |
| `tags` | map | Cloud tags applied to all secrets. Cannot be removed by developers. |
| `syncedLabels` | map | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the secret level:

| Field | Type | Purpose |
|---|---|---|
| `kmsKeyID` | string | Default encryption key when secret doesn't specify one. Empty = use AWS managed key (`aws/secretsmanager`). |
| `replicaRegions` | array | Default replication targets when secret doesn't specify any. Empty = no replication by default. |
| `forceOverwriteReplicaSecret` | boolean | Default overwrite behavior. `false` = don't overwrite by default. |
| `namingTemplate` | string | Default naming pattern (e.g. `{namespace}-{name}`). Applied when secret doesn't use `spec.nameOverride`. |
| `tags` | map | Default cloud tags for secrets. Can be overridden per-secret. |
| `syncedLabels` | map | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    kmsKeyID: ""
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    kmsKeyID: ""  # Uses AWS managed key aws/secretsmanager
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### PCI Compliance (pci)

Enforces encryption with a customer-managed key and mandatory DR replication:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    kmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/mrk-pci-compliance"
    replicaRegions:
      - region: "us-west-2"
        kmsKeyID: "arn:aws:kms:us-west-2:123456789012:key/mrk-pci-dr"
    forceOverwriteReplicaSecret: true
    namingTemplate: ""
    tags:
      compliance: pci
      data-classification: restricted
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
  defaults:
    kmsKeyID: ""
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `pci` profile cannot override:
- The encryption key (must use the org's PCI-compliant key)
- Replication targets (must replicate to the DR region)
- Tag classification (mandatory PCI tags applied)

### Disaster Recovery (dr-required)

Mandates replication to a specific DR region but allows encryption key selection:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerConfig
metadata:
  name: dr-required
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: dr-required
spec:
  mandatory:
    kmsKeyID: ""  # Not enforced; use default or specify per-secret
    replicaRegions:
      - region: "us-west-2"
    forceOverwriteReplicaSecret: false
    namingTemplate: ""
    tags:
      environment: production
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    kmsKeyID: ""
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Deploy

1. Create the profile CRs in `kro-system` namespace (reserved for system-wide configuration):

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    kmsKeyID: ""
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    kmsKeyID: ""
    replicaRegions: []
    forceOverwriteReplicaSecret: false
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers create secrets that reference the profile:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: SecretsManagerSecret
metadata:
  name: db-password
  namespace: app-team
spec:
  configRef: general-policy  # Selects the profile
  description: "Production database password"
  secretRef:
    name: db-secret
    key: password
EOF
```

## Effective Configuration

When a secret is created, kropath-controller reads the selected `SecretsManagerConfig` and merges mandatory and defaults tiers along with org-wide settings from `KropathConfig`. The final merged configuration is written to `status.effectiveConfig` on the config CR.

Developers and platform teams can inspect the effective configuration:

```bash
kubectl get secretsmanagerconfig general-policy -n kro-system -o yaml
```

The `status.effectiveConfig` shows:
- All mandatory fields (platform enforcement)
- All default fields (developer overrides possible)
- AWS account and region information

This single config CR ensures consistent, auditable governance across all secrets that reference it.
