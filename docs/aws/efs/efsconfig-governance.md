# EFSConfig — Governance Profiles for EFS

`EFSConfig` CRs define per-profile governance policies that platform engineers apply to the EFS family. Teams select a profile via `spec.configRef` when creating file systems, access points, and mount targets.

## Governance Structure

Each `EFSConfig` CR has two sections:

- **`spec.mandatory`** — Fields set here enforce policies that instances cannot override
- **`spec.defaults`** — Fields here provide defaults that instances can override

This two-tier structure ensures compliance while preserving operational flexibility.

## General Policy (Default)

The `general-policy` profile is the built-in fallback and ships with kropath. It provides conservative defaults suitable for most workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    encrypted: false              # No enforcement; teams can choose
    kmsKeyId: ""
    performanceMode: ""
    throughputMode: ""
    backupEnabled: false          # No enforcement
    transitionToIA: ""
    transitionToArchive: ""
    transitionToPrimaryStorage: ""
    replicationOverwriteProtection: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    encrypted: true               # Default: encrypted
    kmsKeyId: ""                  # Default: AWS-managed key
    performanceMode: generalPurpose
    throughputMode: elastic
    backupEnabled: true           # Default: backups enabled
    transitionToIA: ""            # No lifecycle transition by default
    transitionToArchive: ""
    transitionToPrimaryStorage: ""
    replicationOverwriteProtection: ENABLED
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## PCI Compliance Profile

For regulated workloads (payment systems, financial data), enforce strict controls:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    encrypted: true                                           # Enforce encryption
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/pci-key # Enforce specific key
    performanceMode: generalPurpose                          # Restrict to general purpose
    throughputMode: elastic                                  # Elastic only (predictable)
    backupEnabled: true                                      # Enforce backups
    transitionToIA: AFTER_30_DAYS                            # Enforce lifecycle
    transitionToArchive: AFTER_90_DAYS
    transitionToPrimaryStorage: AFTER_1_ACCESS
    replicationOverwriteProtection: ENABLED                  # Protect replicas
    tags:
      compliance: pci
      audit: required
    syncedLabels:
      pci-scope: "true"
  defaults:
    encrypted: false                                          # Zero value; mandatory governs
    kmsKeyId: ""                                              # Zero value; mandatory governs
    performanceMode: ""                                       # Zero value; mandatory governs
    throughputMode: ""                                        # Zero value; mandatory governs
    backupEnabled: false                                      # Zero value; mandatory governs
    transitionToIA: ""                                        # Zero value; mandatory governs
    transitionToArchive: ""                                   # Zero value; mandatory governs
    transitionToPrimaryStorage: ""                            # Zero value; mandatory governs
    replicationOverwriteProtection: ""                        # Zero value; mandatory governs
    tags: {}                                                  # Zero value; mandatory governs
    syncedLabels: {}                                          # Zero value; mandatory governs
```

## HIPAA Compliance Profile

For healthcare data, enforce even stricter controls:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    encrypted: true
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/hipaa-key  # HIPAA-specific key
    performanceMode: generalPurpose
    throughputMode: elastic
    backupEnabled: true
    transitionToIA: AFTER_60_DAYS                            # Longer retention
    transitionToArchive: AFTER_180_DAYS
    transitionToPrimaryStorage: AFTER_1_ACCESS
    replicationOverwriteProtection: ENABLED
    tags:
      compliance: hipaa
      pii: "yes"
    syncedLabels:
      hipaa-scope: "true"
      pii-data: "yes"
  defaults:
    encrypted: false                                          # Zero value; mandatory governs
    kmsKeyId: ""                                              # Zero value; mandatory governs
    performanceMode: ""                                       # Zero value; mandatory governs
    throughputMode: ""                                        # Zero value; mandatory governs
    backupEnabled: false                                      # Zero value; mandatory governs
    transitionToIA: ""                                        # Zero value; mandatory governs
    transitionToArchive: ""                                   # Zero value; mandatory governs
    transitionToPrimaryStorage: ""                            # Zero value; mandatory governs
    replicationOverwriteProtection: ""                        # Zero value; mandatory governs
    tags: {}                                                  # Zero value; mandatory governs
    syncedLabels: {}                                          # Zero value; mandatory governs
```

## Development/Test Profile

For non-production workloads, allow cost optimization:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}                                               # No mandatory enforcements
  defaults:
    encrypted: true                                          # Encrypted by default
    kmsKeyId: ""                                            # Use AWS-managed key
    performanceMode: generalPurpose
    throughputMode: bursting                               # Bursting for cost savings
    backupEnabled: false                                   # No backups (dev data is expendable)
    transitionToIA: AFTER_7_DAYS                           # Aggressive IA transition
    transitionToArchive: ""
    transitionToPrimaryStorage: ""
    replicationOverwriteProtection: DISABLED               # Allow overwrites in dev
    tags:
      environment: development
```

## Creating a Custom Profile

To create a profile for your specific use case:

1. **Choose a name** — e.g., `analytics`, `ml-training`, `internal-tools`
2. **Define mandatory policies** — Enforcement at org level (security, compliance, cost limits)
3. **Define defaults** — Fallbacks when teams don't specify (convenience + safety)
4. **Apply tags and labels** — For cost allocation, audit trails, and metadata

Example: Analytics Platform Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EFSConfig
metadata:
  name: analytics
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: analytics
spec:
  mandatory:
    encrypted: true
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/analytics-key
    backupEnabled: true                                    # Backups mandatory
    replicationOverwriteProtection: ENABLED
    tags:
      cost-centre: analytics
      data-classification: internal
    syncedLabels:
      workload-type: analytics
  defaults:
    encrypted: true
    kmsKeyId: arn:aws:kms:us-east-1:123456789012:key/analytics-key
    performanceMode: maxIO                                 # Optimized for throughput (big data)
    throughputMode: provisioned
    backupEnabled: true
    transitionToIA: AFTER_90_DAYS                          # Cold data → IA after 90 days
    transitionToArchive: AFTER_180_DAYS                    # Then → Archive after 6 months
    transitionToPrimaryStorage: ""
    replicationOverwriteProtection: ENABLED
    tags:
      cost-centre: analytics
      data-classification: internal
    syncedLabels:
      workload-type: analytics
```

## Governance Cascade

When an instance is created, the resolution order is:

1. **Check mandatory** — If `EFSConfig.mandatory.<field>` is set, use it (no override)
2. **Check instance** — If `spec.<field>` is explicitly set on the CR, use it
3. **Check defaults** — If `spec.<field>` is unset (nil), use `EFSConfig.defaults.<field>`

**Example Cascade:**

```
EFSFileSystem.spec:
  configRef: pci            # Use PCI profile
  encrypted: null           # Not specified (null)
  performanceMode: maxIO    # Explicitly set

Resolution:
  encrypted:         → pci.mandatory.encrypted (mandatory wins)
                       = true
  
  performanceMode:   → REJECTED by PCI mandatory validation
                       (pci.mandatory.performanceMode = "generalPurpose", not "maxIO")
```

## Boolean Field Semantics

Boolean fields like `encrypted` and `backupEnabled` use pointer semantics to distinguish "not set" from "explicitly false":

- **`nil` (unset)** — Defer to governance cascade (check next tier)
- **`false` (explicit)** — Opt-out; this value takes precedence
- **`true` (explicit)** — Opt-in; this value takes precedence

Only when nil does the governance cascade apply.

**Example:**

```yaml
spec:
  configRef: development
  backupEnabled: false        # Explicit false (opt-out)
```

Even if `development.defaults.backupEnabled: true`, the explicit `false` takes precedence.

## Tag and Label Merging

Tags, syncedLabels, and syncedAnnotations are **merged** across tiers:

1. **`mandatory` tags** — Merged first (take precedence on key conflict)
2. **`spec` tags** — Merged second
3. **`defaults` tags** — Merged last

Final tags = `mandatory.tags` + `spec.tags` + `defaults.tags` (with mandatory winning on conflict)

**Example:**

```yaml
spec:
  configRef: pci
  tags:
    application: my-app
```

PCI profile has:
- `mandatory.tags: {compliance: pci, audit: required}`
- `defaults.tags: {cost-centre: security}`

Result:
- `tags: {compliance: pci, audit: required, application: my-app, cost-centre: security}`

## Platform Engineering Best Practices

1. **Start with general-policy** — Use the built-in profile as a baseline; create custom profiles only when needed.

2. **Use mandatory for compliance** — Enforce fields via `mandatory` when your organization has non-negotiable requirements (e.g., encryption, backups).

3. **Use defaults for convenience** — Provide sensible defaults via `defaults` to reduce boilerplate without enforcing policies.

4. **Name profiles clearly** — Use descriptive names (`pci`, `hipaa`, `development`) so teams understand what governance applies.

5. **Document per-profile rules** — Maintain a runbook describing what each profile enforces and when to use it.

6. **Monitor usage** — Check which profiles are being used; if a profile is never selected, consider removing it.

7. **Test profile changes** — Before rolling out new mandatory rules, test them in development/staging clusters first.

## Cross-Provider Notes

`EFSConfig` is AWS-specific. Other providers (GCP, Azure) have their own config CRDs with different governance fields appropriate to each provider's feature set.

The two-tier structure (mandatory/defaults) and governance cascade pattern are consistent across all providers.

## Related Topics

- [EFS Overview](index.md) — Architecture and governance structure
- [EFSFileSystem](efsfilesystem.md) — Creating resources with configRef
- [ADR-010 Governance Cascade](../../adrs/010-consolidated-governance-cascade.md) — Detailed specification
