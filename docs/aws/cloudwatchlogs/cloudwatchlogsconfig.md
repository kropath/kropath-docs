# CloudWatchLogsConfig — Governance Configuration

The `CloudWatchLogsConfig` resource defines governance profiles that control how log groups are created and configured across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each log group.

## Overview

`CloudWatchLogsConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., encryption keys that all log groups must use, required retention periods)
- **Defaults tier** — Baseline values developers can override (e.g., default encryption key, default retention period, default naming pattern)

This two-tier approach lets platform teams enforce critical compliance and security controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `kmsKeyId` | string | Encryption key enforcement: full KMS key ARN. CloudWatch Logs requires the complete ARN, not key IDs or aliases. Empty = not enforced. |
| `retentionDays` | integer | Log retention period that cannot be overridden. Must be one of the allowed values or 0 (not enforced). Empty (`0`) = no mandatory retention. |
| `namingTemplate` | string | Naming pattern for log group names (e.g. `{namespace}-{name}`). Empty = no mandatory template. |
| `tags` | map | Cloud tags applied to all log groups. Cannot be removed by developers. |
| `syncedLabels` | map | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the log group level:

| Field | Type | Purpose |
|---|---|---|
| `kmsKeyId` | string | Default encryption key when log group doesn't specify one. Empty = no KMS encryption (uses CloudWatch Logs default encryption). |
| `retentionDays` | integer | Default retention period when log group doesn't specify one. Must be one of the allowed values. Empty (`0`) = indefinite retention (not recommended for production). Default is `90` days. |
| `namingTemplate` | string | Default naming pattern (e.g. `{namespace}-{name}`). Applied when log group doesn't use `spec.nameOverride`. |
| `tags` | map | Default cloud tags for log groups. Can be overridden per-log-group. |
| `syncedLabels` | map | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

### Allowed Retention Values

CloudWatch Logs supports only specific retention periods. Valid values are:

`1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653`

Any other value will be rejected. The value `0` means "not set" (indefinite retention or uses the next tier in the cascade).

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    kmsKeyId: ""
    retentionDays: 0
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    kmsKeyId: ""  # No KMS encryption by default
    retentionDays: 90  # 90-day default retention
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### PCI Compliance (pci)

Enforces encryption with a customer-managed key and mandatory 1-year retention:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/mrk-pci-compliance"
    retentionDays: 365
    namingTemplate: ""
    tags:
      compliance: pci
      data-classification: restricted
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
  defaults:
    kmsKeyId: ""
    retentionDays: 0
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `pci` profile cannot override:
- The encryption key (must use the org's PCI-compliant key)
- The retention period (must retain logs for 1 year)
- Tag classification (mandatory PCI tags applied)

### HIPAA Compliance (hipaa)

Enforces long-term encryption and retention for protected health information:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    kmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/mrk-hipaa-compliance"
    retentionDays: 2557  # 7 years (AWS maximum)
    namingTemplate: ""
    tags:
      compliance: hipaa
      data-classification: phi
    syncedLabels:
      compliance: hipaa
    syncedAnnotations: {}
  defaults:
    kmsKeyId: ""
    retentionDays: 0
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Deploy

1. Create the profile CRs in the `kro-system` namespace (reserved for system-wide configuration):

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    kmsKeyId: ""
    retentionDays: 0
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    kmsKeyId: ""
    retentionDays: 90
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers create log groups that reference the profile:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchLogsLogGroup
metadata:
  name: app-logs
  namespace: app-team
spec:
  configRef: general-policy  # Selects the profile
EOF
```

## Effective Configuration

When a log group is created, kropath-controller reads the selected `CloudWatchLogsConfig` and merges mandatory and defaults tiers along with org-wide settings from `KropathConfig`. The final merged configuration is written to `status.effectiveConfig` on the config CR.

Developers and platform teams can inspect the effective configuration:

```bash
kubectl get cloudwatchlogsconfig general-policy -n kro-system -o yaml
```

The `status.effectiveConfig` shows:
- All mandatory fields (platform enforcement)
- All default fields (developer overrides possible)
- AWS account and region information

This single config CR ensures consistent, auditable governance across all log groups that reference it.

## Cluster Setup

Before deploying log groups, ensure the `CloudWatchLogsConfig` CRDs are deployed in your cluster. Platform teams typically deploy base profiles (`general-policy`, `pci`, `hipaa`) during cluster initialization in the `kro-system` namespace.

All log group instances will fall back to `general-policy` if a referenced profile does not exist.
