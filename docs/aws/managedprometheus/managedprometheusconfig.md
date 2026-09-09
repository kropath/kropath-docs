# ManagedPrometheusConfig — Governance Configuration

The `ManagedPrometheusConfig` resource defines governance profiles for Managed Prometheus resources across your organization and namespaces. Platform teams create named profiles; developers select a profile via `spec.configRef` on each resource.

## Overview

`ManagedPrometheusConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., workspace alias enforcement, logging destination standards, naming patterns, compliance tags)
- **Defaults tier** — Baseline values developers can override (e.g., default naming pattern, default logging destination, default tags)

This two-tier approach lets platform teams enforce critical operational and compliance controls while preserving developer flexibility for non-critical fields.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Applies To | Purpose |
|---|---|---|---|
| `alias` | string | Workspace only | Forces workspace alias; instance `spec.alias` cannot override when set |
| `logGroupARN` | string | LoggingConfiguration only | Forces CloudWatch log destination; instance cannot override when set |
| `namingTemplate` | string | RuleGroupsNamespace only | Forces naming pattern (e.g. `{namespace}-{name}`). Empty = not enforced. |
| `tags` | map | Workspace, RuleGroupsNamespace | Cloud tags applied to resources. Cannot be removed by developers. |
| `syncedLabels` | map | All resources | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`). Merged with developer labels. |
| `syncedAnnotations` | map | All resources | Kubernetes annotations (prefixed `aws.kropath.run/`). Merged with developer annotations. |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Applies To | Purpose |
|---|---|---|---|
| `alias` | string | Workspace only | Default workspace alias when instance doesn't specify. Empty string (`""`) = no default. |
| `logGroupARN` | string | LoggingConfiguration only | Default CloudWatch log destination. Empty = no default. |
| `namingTemplate` | string | RuleGroupsNamespace only | Default naming pattern (e.g. `{namespace}-{name}`). Applied when resource doesn't use `spec.nameOverride`. Default: `{namespace}-{name}`. |
| `tags` | map | Workspace, RuleGroupsNamespace | Default cloud tags. Can be overridden per-resource. |
| `syncedLabels` | map | All resources | Default labels to sync to Kubernetes and cloud tags. |
| `syncedAnnotations` | map | All resources | Default annotations to sync to Kubernetes. |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously. (Empty values like `{}`, `[]`, or `""` can appear in both — they indicate "not set".)

## How the Cascade Works

When you create a Managed Prometheus resource, the platform merges organizational governance (KropathConfig), profile settings (ManagedPrometheusConfig), and instance-level overrides:

**For workspace `alias`:** Mandatory (if set) → Instance override → Defaults → RGD built-in `""` (no alias)

**For LoggingConfiguration `logGroupARN`:** Mandatory (if set) → Instance override → Defaults (required if no tier provides a value)

**For RuleGroupsNamespace `namingTemplate`:** Mandatory (if set) → Instance `nameOverride` → Defaults → RGD built-in `{namespace}-{name}`

**For tags/labels:** Additive merge: mandatory + instance + defaults (mandatory keys cannot be removed)

**For naming:** Mandatory template (if set) → Defaults template → `{namespace}-{name}`

## Naming Tokens

The `namingTemplate` field (RuleGroupsNamespace only) supports dynamic token substitution:

| Token | Substituted With |
|---|---|
| `{namespace}` | Kubernetes namespace |
| `{name}` | Resource CR name |
| `{account_id}` | AWS account ID |
| `{region}` | AWS region |
| `{configRef}` | Profile name (e.g. `general-policy`) |
| `{tag.KEY}` | Value of governance tag `KEY`; empty string if absent |

**Example:** `amp-{region}-{name}` on a rule group in namespace `monitoring` named `app-rules` in region `us-east-1` produces: `amp-us-east-1-app-rules`.

## Example Profiles

### Baseline (general-policy)

Permissive defaults; no mandatory enforcement. Suitable for development and general use:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    alias: ""
    logGroupARN: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
```

### Production (production-monitoring)

Enforces naming patterns and mandatory compliance tags:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: production-monitoring
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production-monitoring
spec:
  mandatory:
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      environment: production
      compliance: required
    syncedLabels:
      environment: production
  defaults:
    alias: ""
    logGroupARN: ""
```

Developers using the `production-monitoring` profile cannot override:
- Naming pattern (must use `prod-` prefix)
- Environment tag (always `production`)
- Synced labels (environment is mandatory on Kubernetes metadata)

### Centralized Logging

Enforce all workspaces to log to a central location:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: logging-enforced
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: logging-enforced
spec:
  mandatory:
    logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/central:*"
  defaults:
    alias: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      logging: enabled
```

All `ManagedPrometheusLoggingConfiguration` resources using this profile must route to the enforced log group.

## How to Deploy

1. Create profile CRs in the `kro-system` namespace:

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    alias: ""
    logGroupARN: ""
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
    syncedLabels: {}
    syncedAnnotations: {}
EOF
```

2. Verify the profile is created:

```bash
kubectl get managedprometheusconfigs -n kro-system
```

3. Developers reference profiles in their resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ManagedPrometheusWorkspace
metadata:
  name: app-metrics
  namespace: myapp
spec:
  configRef: general-policy  # ← References the profile
```

## Resource Requirements

- **Namespace:** `kro-system` (recommended for org-wide profiles) or developer namespace (for local overrides)
- **Labels:** Must include `aws.kropath.run/resource-name: <profile-name>` for resource lookup
- **Unique name:** Profile `metadata.name` must be unique within the namespace

## Status Fields

`ManagedPrometheusConfig` has a `status.effectiveConfig` field (read-only, populated by the kropath-controller):

```yaml
status:
  effectiveConfig:
    mandatory:
      alias: <effective mandatory value>
      logGroupARN: <effective mandatory value>
      namingTemplate: <effective mandatory value>
      tags: <merged mandatory tags>
      syncedLabels: <merged mandatory labels>
      syncedAnnotations: <merged mandatory annotations>
    defaults:
      alias: <effective default value>
      logGroupARN: <effective default value>
      namingTemplate: <effective default value>
      tags: <merged default tags>
      syncedLabels: <merged default labels>
      syncedAnnotations: <merged default annotations>
    aws:
      region: <AWS region from KropathConfig>
      accountId: <AWS account ID from KropathConfig>
```

The `status.effectiveConfig` is the pre-merged governance state that resources use. It combines `spec.mandatory` / `spec.defaults` with organizational-level settings from `KropathConfig`.

## Common Tasks

### Enforce Workspace Naming

```yaml
spec:
  mandatory:
    namingTemplate: "corp-{region}-{name}"
```

### Set Org-Wide Logging

```yaml
spec:
  mandatory:
    logGroupARN: "arn:aws:logs:us-east-1:123456789012:log-group:/aws/amp/org:*"
```

### Apply Compliance Tags

```yaml
spec:
  mandatory:
    tags:
      compliance: pci
      audit-required: "true"
```

### Provide Defaults Without Mandates

```yaml
spec:
  mandatory: {}
  defaults:
    tags:
      managed-by: kropath
    syncedLabels:
      team: platform
```

## Related Resources

- [ManagedPrometheusWorkspace](./managedprometheusworkspace.md) — Root resource that selects a profile
- [ManagedPrometheusRuleGroupsNamespace](./managedprometheusrulegroupsnamespace.md) — Uses naming governance
- [ManagedPrometheusLoggingConfiguration](./managedprometheusloggingconfiguration.md) — Uses logging governance
