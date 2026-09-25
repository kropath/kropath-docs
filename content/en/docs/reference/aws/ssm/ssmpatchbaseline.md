---
title: SSMPatchBaseline — Fleet Patch Compliance
description: "The `SSMPatchBaseline` resource defines patch approval rules and compliance levels for AWS Systems Manager Patch Manager."
doc_type: reference
---
# SSMPatchBaseline — Fleet Patch Compliance

The `SSMPatchBaseline` resource defines patch approval rules and compliance levels for AWS Systems Manager Patch Manager. It enables platform teams to enforce fleet-wide patching policies while letting teams configure OS-specific requirements.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `SSMConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the baseline name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Baseline Properties

| Field | Type | Default | Purpose |
|---|---|---|---|
| `description` | string | `""` | Description of the patch baseline |
| `operatingSystem` | string | `"WINDOWS"` | Target OS: WINDOWS, AMAZON_LINUX, AMAZON_LINUX_2, UBUNTU, RHEL, SUSE, CENTOS, ORACLE_LINUX, DEBIAN, MACOS, RASPBIAN, ROCKY_LINUX, ALMA_LINUX |
| `approvedPatchesComplianceLevel` | string | `"UNSPECIFIED"` | Compliance level: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL, UNSPECIFIED |
| `approvedPatchesEnableNonSecurity` | boolean | `false` | Include non-security updates (Linux only) |
| `rejectedPatchesAction` | string | `"ALLOW_AS_DEPENDENCY"` | Action for rejected patches: ALLOW_AS_DEPENDENCY or BLOCK |

### Approval Rules

| Field | Type | Default | Purpose |
|---|---|---|---|
| `approvalRules` | object | `{}` | Auto-approval rules with patch filters and compliance settings |
| `approvedPatches` | []string | `[]` | Explicitly approved patch list |
| `rejectedPatches` | []string | `[]` | Explicitly rejected patch list |

### Advanced Filtering (CLI/SDK Only)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `globalFilters` | object | `{}` | Global filters applied before approval rules; **not available in AWS console** |
| `sources` | []object | `[]` | Custom patch source repositories (Linux only) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels synchronized to AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations synchronized to AWS tags |

## Operating Systems

Supported OS values:

- `WINDOWS` — Windows Server
- `AMAZON_LINUX` — Amazon Linux (older)
- `AMAZON_LINUX_2` — Amazon Linux 2
- `UBUNTU` — Ubuntu Linux
- `RHEL` — Red Hat Enterprise Linux
- `SUSE` — SUSE Linux
- `CENTOS` — CentOS
- `ORACLE_LINUX` — Oracle Linux
- `DEBIAN` — Debian
- `MACOS` — macOS
- `RASPBIAN` — Raspbian
- `ROCKY_LINUX` — Rocky Linux
- `ALMA_LINUX` — AlmaLinux

## Compliance Levels

| Level | Meaning |
|---|---|
| `CRITICAL` | Critical security patches (highest priority) |
| `HIGH` | High-severity patches |
| `MEDIUM` | Medium-severity patches |
| `LOW` | Low-severity patches |
| `INFORMATIONAL` | Informational updates (e.g., documentation) |
| `UNSPECIFIED` | No specific compliance level (default) |

## Complete Examples

### Example 1: Amazon Linux 2 Baseline (Production)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: amazon-linux-2-prod
  namespace: ops
spec:
  configRef: patching
  deletionPolicy: retain
  description: "Production patch baseline for Amazon Linux 2"
  operatingSystem: AMAZON_LINUX_2
  approvedPatchesComplianceLevel: HIGH
  approvedPatchesEnableNonSecurity: false
  rejectedPatchesAction: BLOCK
  approvalRules:
    patchRules:
      - approveAfterDays: 7
        complianceLevel: CRITICAL
      - approveAfterDays: 14
        complianceLevel: HIGH
      - approveAfterDays: 30
        complianceLevel: MEDIUM
  tags:
    Environment: Production
    OS: AmazonLinux2
    Team: Operations
```

Result:
- Critical patches auto-approve after 7 days
- High patches auto-approve after 14 days
- Medium patches auto-approve after 30 days
- Non-security patches excluded
- Rejected patches are blocked (not installed)

### Example 2: Windows Server Baseline

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: windows-server
  namespace: ops
spec:
  configRef: general-policy
  description: "Windows Server patch baseline"
  operatingSystem: WINDOWS
  approvedPatchesComplianceLevel: HIGH
  approvedPatchesEnableNonSecurity: true  # Windows includes non-security updates by default
  rejectedPatchesAction: ALLOW_AS_DEPENDENCY
  approvalRules:
    patchRules:
      - approveAfterDays: 0
        complianceLevel: CRITICAL
      - approveAfterDays: 7
        complianceLevel: HIGH
      - approveUntilDate: "2026-12-31"
        complianceLevel: MEDIUM
  rejectedPatches:
    - "KB12345"  # Specific patch to never install
  tags:
    Environment: Mixed
    OS: Windows
```

Result:
- Critical patches install immediately
- High patches install after 7 days
- Medium patches approved until year-end
- Non-security updates included (Windows-specific)
- Specific KB patches are rejected

### Example 3: Development Baseline (Permissive)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: dev-baseline
  namespace: development
spec:
  configRef: general-policy
  description: "Development environment — permissive patching"
  operatingSystem: UBUNTU
  approvedPatchesComplianceLevel: LOW
  approvedPatchesEnableNonSecurity: true
  rejectedPatchesAction: ALLOW_AS_DEPENDENCY
  approvalRules:
    patchRules:
      - approveAfterDays: 0
        complianceLevel: UNSPECIFIED
```

Result:
- All patches (UNSPECIFIED level) auto-approve immediately
- Non-security updates included
- Rejected patches can still install as dependencies

## Approval Rules Details

### Rule Structure

Each rule in `approvalRules.patchRules` specifies:

```yaml
approvalRules:
  patchRules:
    - approveAfterDays: 7          # Days before auto-approval (integer)
      approveUntilDate: "2026-12-31"  # OR specific date (YYYY-MM-DD)
      complianceLevel: HIGH        # CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL | UNSPECIFIED
      enableNonSecurity: false     # Override baseline default for this rule (optional)
      patchFilterGroup:
        patchFilters:
          - key: PRODUCT
            values: ["*"]           # Patch filter selector
          - key: CLASSIFICATION
            values: ["Security"]
          - key: SEVERITY
            values: ["Critical", "Important"]
```

### Rule Evaluation

- **First matching rule applies** — If multiple rules match a patch, the first one determines approval
- **`approveAfterDays`** — Number of days since patch release before auto-approval
- **`approveUntilDate`** — Approve patches released before this date
- **`complianceLevel`** — Severity level for this rule
- **`enableNonSecurity`** — Override baseline's `approvedPatchesEnableNonSecurity` for this rule

### Patch Filters

Filter patches by:
- `PRODUCT` — Affected product (e.g., `"*"` for all)
- `CLASSIFICATION` — Patch type (e.g., "Security", "Updates", "Bugfix")
- `SEVERITY` — Severity level (e.g., "Critical", "Important")
- `PRIORITY` — Priority level (provider-specific)
- `SECTION` — Package section (Linux)
- `BUGZILLA_ID` — Bug tracker ID

## Explicit Patch Lists

### Approved Patches

Whitelist specific patches to always install:

```yaml
spec:
  approvedPatches:
    - "KB12345"      # Specific Windows patch
    - "openssl-1.1.1" # Specific Linux package
    - "RHSA-2026:1234" # Red Hat security advisory
```

### Rejected Patches

Blacklist specific patches to never install:

```yaml
spec:
  rejectedPatches:
    - "KB99999"      # Known problematic patch
    - "glibc-2.3.4"  # Problematic Linux package
    - "RHSA-2026:5678"
  rejectedPatchesAction: BLOCK  # BLOCK or ALLOW_AS_DEPENDENCY
```

**`rejectedPatchesAction`:**
- `BLOCK` — Rejected patches are never installed
- `ALLOW_AS_DEPENDENCY` — Rejected patches can install if required by other patches

## Global Filters

**Console Limitation:** `globalFilters` is only configurable via CLI/SDK, not in the AWS Patch Manager console.

```yaml
spec:
  globalFilters:
    patchFilters:
      - key: PRODUCT
        values: ["kernel"]
      - key: SEVERITY
        values: ["Critical"]
```

Applied before approval rules—filters out patches before rule evaluation.

## Naming and ARN

Patch baseline names follow standard naming conventions:

- Max 128 characters
- `a-zA-Z0-9_\-.` only
- Default template: `{namespace}-{name}`

**Important:** Patch baseline ARNs use AWS-assigned `baselineID`, not the baseline name:

```yaml
status:
  predictedArn: "arn:aws:ssm:us-east-1:123456789012:patchbaseline/pb-1234567890abcdef0"
  # Note: uses pb-xxxxx, not the resource name
```

The ARN is only available **after the baseline is created** and the ACK controller populates `status.baselineID`.

## Governance Cascade

When fields aren't specified, they resolve via governance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: my-baseline
  namespace: ops
spec:
  configRef: patching
  # operatingSystem, approvedPatchesComplianceLevel not specified — resolved by cascade
```

Cascade for `operatingSystem`:
1. Check `patching` SSMConfig mandatory tier → `AMAZON_LINUX_2`
2. Result: baseline gets `operatingSystem=AMAZON_LINUX_2`

Platform teams can enforce OS-specific requirements:

```yaml
# In SSMConfig (patching profile)
spec:
  mandatory:
    operatingSystem: AMAZON_LINUX_2  # Force Linux 2 across all baselines
    approvedPatchesComplianceLevel: HIGH  # Enforce high compliance
```

## Status Fields

After creation:

```yaml
status:
  resourceName: "ops-amazon-linux-2-prod"  # effectiveName
  namingStatus: "valid"
  predictedArn: "arn:aws:ssm:us-east-1:123456789012:patchbaseline/pb-1234567890abcdef0"
  baselineID: "pb-1234567890abcdef0"  # AWS-assigned baseline ID
  ackResourceMetadata:
    arn: "arn:aws:ssm:us-east-1:123456789012:patchbaseline/pb-1234567890abcdef0"
```

## Multiple Baselines in One Manifest

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: amazon-linux-2
  namespace: ops
spec:
  operatingSystem: AMAZON_LINUX_2
  approvedPatchesComplianceLevel: HIGH
  approvalRules:
    patchRules:
      - approveAfterDays: 7
        complianceLevel: CRITICAL
---
apiVersion: aws.kropath.run/v1alpha1
kind: SSMPatchBaseline
metadata:
  name: windows-server
  namespace: ops
spec:
  operatingSystem: WINDOWS
  approvedPatchesComplianceLevel: HIGH
  approvalRules:
    patchRules:
      - approveAfterDays: 0
        complianceLevel: CRITICAL
```

## Non-Security Updates

### Linux Behavior

On Linux, `approvedPatchesEnableNonSecurity` controls whether non-security updates (e.g., bugfixes, performance updates) are installed:

- `true` — Include bugfix and performance updates
- `false` — Security patches only (default)

```yaml
spec:
  operatingSystem: AMAZON_LINUX_2
  approvedPatchesEnableNonSecurity: true  # Include non-security
```

### Windows Behavior

Windows treats non-security updates as part of the normal patch stream; this setting applies differently based on classification.

### Boolean Sentinel Note

`approvedPatchesEnableNonSecurity` as a boolean `false`:
- `false` (explicit) — Do not include non-security patches
- `nil` / omitted — Not enforced in governance (instance choice)

Platform teams should use governance to enforce or recommend:

```yaml
spec:
  mandatory:
    approvedPatchesEnableNonSecurity: false  # Enforce: security only
```

## Best Practices

1. **Use OS-specific baselines** — Create separate baselines for each OS (Windows, AMAZON_LINUX_2, UBUNTU, etc.)
2. **Set compliance levels by severity** — CRITICAL → 0 days, HIGH → 7 days, MEDIUM → 30 days
3. **Use governance profiles** — Let `SSMConfig` enforce OS and compliance requirements
4. **Test in development first** — Approve baselines in dev before production
5. **Block known problematic patches** — Use `rejectedPatches` for known issues
6. **Document approval rules** — Add descriptions explaining your patching strategy
7. **Review global filters** — Remember they're CLI-only in the console
8. **Use `retain` deletion policy** — Default; prevents accidental baseline deletion
9. **Tag by environment** — Environment, OS, compliance level metadata
10. **Assign to patch groups** — Baselines must be registered with Patch Manager patch groups (operational step, not Kubernetes)

## Troubleshooting

**Baseline not applying to instances**
- Baselines must be assigned to Patch Manager patch groups
- This is an operational step outside Kubernetes—use AWS console or CLI
- Verify instances are in the target patch group

**Patches not installing as expected**
- Check approval rules and filters
- Verify `rejectedPatches` isn't blocking them
- Review compliance level thresholds
- Check instance permissions for Systems Manager

**Global filters not working**
- `globalFilters` only work via CLI/SDK
- Console doesn't surface or apply them
- Test via AWS CLI: `aws ssm get-patch-baseline --baseline-id pb-xxxxx`

**Non-security updates not installing on Linux**
- Ensure `approvedPatchesEnableNonSecurity: true`
- Verify approval rules allow non-security classifications

## Next Steps

- [SSMConfig Governance](./ssmconfig.md) — Understanding patch governance
- [AWS Patch Manager Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager.html) — AWS documentation
- [AWS Patch Compliance](https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance.html) — Patch compliance reporting
