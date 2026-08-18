# CloudWatchConfig — Governance Configuration

The `CloudWatchConfig` resource defines governance profiles for CloudWatch resources (alarms, dashboards, metric streams) across your organization and namespaces. Platform teams create named profiles; developers select the profile they need via `spec.configRef` on each resource.

## Overview

`CloudWatchConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., alarm action enforcement, required naming patterns, compliance tags)
- **Defaults tier** — Baseline values developers can override (e.g., default missing data treatment, default output format, default naming pattern)

This two-tier approach lets platform teams enforce critical operational and compliance controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Applies To | Purpose |
|---|---|---|---|
| `actionsEnabled` | boolean | Alarms only | Forces alarm actions on/off; instance `spec.actionsEnabled` cannot override |
| `treatMissingData` | string | Alarms only | Forces missing data handling (breaching/notBreaching/ignore/missing); instance cannot override |
| `outputFormat` | string | Metric Streams only | Forces metric stream output format (json/opentelemetry1.0/opentelemetry0.7); instance cannot override |
| `namingTemplate` | string | All resources | Cloud resource naming pattern (e.g. `{namespace}-{name}`). Empty = not enforced. |
| `tags` | map | Alarms, Metric Streams | Cloud tags applied to resources. Cannot be removed by developers. **Dashboard has no cloud tag support.** |
| `syncedLabels` | map | All resources | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | All resources | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Applies To | Purpose |
|---|---|---|---|
| `actionsEnabled` | boolean | Alarms only | Default alarm action setting when instance doesn't specify. Absent (nil) = use platform default true. |
| `treatMissingData` | string | Alarms only | Default missing data treatment when instance doesn't specify. Default: `"missing"` (AWS default). |
| `outputFormat` | string | Metric Streams only | Default output format when stream doesn't specify. Default: `"json"`. |
| `namingTemplate` | string | All resources | Default naming pattern (e.g. `{namespace}-{name}`). Applied when resource doesn't use `spec.nameOverride`. |
| `tags` | map | Alarms, Metric Streams | Default cloud tags. Can be overridden per-resource. **Dashboard has no cloud tag support.** |
| `syncedLabels` | map | All resources | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | All resources | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

### Allowed Values

**`treatMissingData`:** `"breaching"`, `"notBreaching"`, `"ignore"`, `"missing"` (AWS default)

**`outputFormat`:** `"json"`, `"opentelemetry1.0"`, `"opentelemetry0.7"`

### Naming Tokens

The `namingTemplate` field supports dynamic token substitution:

| Token | Substituted With |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | Resource CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Profile name (e.g. `general-policy`) |
| `{tag.KEY}` | Value of governance tag `KEY`; empty string if absent |

**Example:** `corp-{region}-{name}` on an alarm in namespace `monitoring-prod` named `cpu-high` in region `us-east-1` with profile `general-policy` produces: `corp-us-east-1-cpu-high`.

## How the Cascade Works

When you create a CloudWatch resource, the platform merges organizational governance (KropathConfig), profile settings (CloudWatchConfig), and instance-level overrides:

**For alarm `actionsEnabled`:** Mandatory (if set) → Instance override → Defaults → platform default `true`

**For alarm `treatMissingData`:** Mandatory (if set) → Instance override → Defaults → platform default `"missing"`

**For metric stream `outputFormat`:** Mandatory (if set) → Instance override → Defaults → platform default `"json"`

**For tags/labels:** Additive merge: mandatory + instance + defaults (mandatory keys cannot be removed)

**For naming:** Mandatory template (if set) → Defaults template → `{namespace}-{name}`

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    actionsEnabled:
    treatMissingData: ""
    outputFormat: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    treatMissingData: "missing"
    outputFormat: "json"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### PCI Compliance (pci)

Enforces alarm action enforcement and mandatory naming/tagging for compliance:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: pci
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: pci
spec:
  mandatory:
    actionsEnabled: true
    treatMissingData: "breaching"
    outputFormat: "json"
    namingTemplate: "pci-{namespace}-{name}"
    tags:
      compliance: pci
      data-classification: restricted
    syncedLabels:
      compliance: pci
    syncedAnnotations: {}
  defaults:
    actionsEnabled:
    treatMissingData: ""
    outputFormat: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

Developers using the `pci` profile cannot override:
- Alarm action enablement (all alarms must have actions enabled)
- Alarm missing data treatment (must use `"breaching"`)
- Metric stream output format (must be `"json"`)
- Naming pattern (must use PCI-compliant prefix)
- Compliance tags (mandatory PCI tags applied)

### HIPAA Compliance (hipaa)

Enforces strict controls for protected health information:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: hipaa
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: hipaa
spec:
  mandatory:
    actionsEnabled: true
    treatMissingData: "breaching"
    outputFormat: "json"
    namingTemplate: "hipaa-{namespace}-{name}"
    tags:
      compliance: hipaa
      data-classification: phi
    syncedLabels:
      compliance: hipaa
      audit-required: "true"
    syncedAnnotations: {}
  defaults:
    actionsEnabled:
    treatMissingData: ""
    outputFormat: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## How to Deploy

1. Create the profile CRs in the `kro-system` namespace:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    actionsEnabled:
    treatMissingData: ""
    outputFormat: ""
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    treatMissingData: "missing"
    outputFormat: "json"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Developers create alarms, dashboards, or metric streams that reference the profile:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: CloudWatchAlarm
metadata:
  name: cpu-high
  namespace: app-team
spec:
  configRef: general-policy  # Selects the profile
  metricName: CPUUtilization
  namespace: AWS/EC2
  statistic: Average
  period: 300
  evaluationPeriods: 1
  threshold: 80
  comparisonOperator: GreaterThanThreshold
  alarmActions:
    - arn:aws:sns:us-east-1:123456789012:alerts
EOF
```

## Cluster Setup

Before deploying CloudWatch resources, ensure the `CloudWatchConfig` CRDs are deployed in your cluster. Platform teams typically deploy base profiles (`general-policy`, `pci`, `hipaa`) during cluster initialization in the `kro-system` namespace.

All CloudWatch resources will fall back to `general-policy` if a referenced profile does not exist.

## Dashboard Tag Exception

**Note:** CloudWatchDashboard does not support cloud tags due to a current platform limitation. Governance-mandated tags from `CloudWatchConfig` cannot be applied to Dashboard cloud resources. Governance-mandated `syncedLabels` and `syncedAnnotations` are mirrored to Kubernetes metadata only, not to cloud tags.
