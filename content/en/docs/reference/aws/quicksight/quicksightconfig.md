---
title: QuickSightConfig
description: "`QuickSightConfig` is a governance configuration resource that lets you define mandatory and default settings for AWS QuickSight resources across your cluster."
doc_type: reference
---
# QuickSightConfig

`QuickSightConfig` is a governance configuration resource that lets you define mandatory and default settings for AWS QuickSight resources across your cluster. Instead of requiring every QuickSight dashboard, dataset, and analysis to specify naming, tags, and import modes independently, you can create named configuration profiles and let kropath apply them consistently.

## Scope

This resource is AWS-only. QuickSightConfig governs AWS QuickSight resources (via `QuickSightDataSource`, `QuickSightDataSet`, `QuickSightDashboard`, and `QuickSightAnalysis` RGDs). There is no GCP or Azure equivalent yet.

## What it solves

Managing QuickSight resources at scale creates several operational challenges:

- **Inconsistent governance** — different teams use different data import modes (SPICE vs DIRECT_QUERY), naming conventions, and tagging strategies, making compliance audits difficult
- **Compliance drift** — once resources are created, enforcing new compliance requirements (e.g., "all datasets must use SPICE for performance") requires manual updates
- **Manual defaults** — every resource spec must list sensible defaults for optional fields, creating noise and inconsistency
- **No central policy** — when a new compliance requirement arrives, you must update every resource individually

`QuickSightConfig` solves this by providing:

- **Governance profiles** — define reusable profiles like `general-policy`, `compliance`, or `high-performance` that encode your organization's requirements
- **Mandatory enforcement** — platform teams set fields that override user input (e.g., "all datasets must use SPICE import mode for cost predictability")
- **Sensible defaults** — declare defaults for optional fields so user specs are cleaner and every resource has a consistent baseline
- **Scalable compliance** — update one profile to enforce a new requirement across all resources using that profile

## Core concepts

### Mandatory vs. defaults tiers

`QuickSightConfig` has two independent tiers of settings:

**Mandatory fields** (enforced):
- Override any user specification for that field
- Useful for compliance: "all datasets must import via SPICE"
- If mandatory is empty, it is not enforced (user can override)

**Defaults fields** (applied when user doesn't specify):
- Provide sensible fallback values
- Applied only when the user leaves the field empty
- Useful for convenience: "SPICE import by default, but let power users choose DIRECT_QUERY"

Mandatory and defaults interaction:
- **Scalar fields** (`importMode`, `namingTemplate`): The resource rejects the CR with a validation error if both mandatory and instance-level values are set (mutual-exclusion rule); this ensures no ambiguity.
- **Map fields** (`tags`, `syncedLabels`, `syncedAnnotations`): Mandatory values merge with defaults and instance values, with mandatory winning on key conflict.

### Governance cascade

The kropath controller pre-merges settings from two sources and writes them to the resource's status:

1. **Organization-wide** (KropathConfig settings) — applies to all QuickSight resources across the cluster
2. **Per-profile** (QuickSightConfig settings) — applies to resources using this profile

Resources read the merged result, ensuring a single source of truth.

### Profile patterns

Common profiles codify organizational postures:

**general-policy** — the default, sensible baseline:
- Data import mode: SPICE (default, can be overridden)
- Standard naming template: `{namespace}-{name}`
- Standard cloud tags and synced labels applied to all resources

**high-performance** — optimized for query speed:
- Data import mode: DIRECT_QUERY (required, bypasses SPICE caching)
- Standard naming template includes performance tier
- Performance-related tags applied automatically

**compliance** — stricter, suitable for regulated workloads:
- Data import mode: SPICE (required, for cost and audit predictability)
- Naming templates enforce namespace context
- Compliance tags and data classification labels applied automatically

## Configuration fields

### Mandatory tier

Fields in this tier override any instance `spec` setting:

| Field | Type | Meaning |
|---|---|---|
| `importMode` | `SPICE` \| `DIRECT_QUERY` | Dataset data import mode (SPICE = cached, DIRECT_QUERY = real-time). Empty = not enforced. |
| `namingTemplate` | string | Cloud resource name template (e.g., `"corp-{namespace}-{name}"`). Empty = not enforced. |
| `tags` | map | Cloud resource tags. Merged with defaults and instance tags. |
| `syncedLabels` | map | Labels to sync to both Kubernetes and cloud tags. |
| `syncedAnnotations` | map | Annotations to sync to Kubernetes metadata. |

### Defaults tier

Fields here apply when an instance leaves the field empty:

| Field | Type | Default value | Meaning |
|---|---|---|---|
| `importMode` | string | `"SPICE"` | Fallback data import mode (SPICE = cached, for cost control). |
| `namingTemplate` | string | `"{namespace}-{name}"` | Default cloud resource naming template. |
| `tags` | map | `{}` | Merged with mandatory and instance tags. |
| `syncedLabels` | map | `{}` | Merged with mandatory and instance labels. |
| `syncedAnnotations` | map | `{}` | Merged with mandatory and instance annotations. |

## Complete example

Here's a multi-profile setup:

```yaml
---
# Default profile: sensible baseline
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    importMode: "SPICE"
    namingTemplate: "{namespace}-{name}"
    tags:
      environment: production
      cost-center: analytics

---
# High-performance profile: prioritize query speed
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: high-performance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-performance
spec:
  mandatory:
    importMode: "DIRECT_QUERY"
    tags:
      performance-tier: critical
  defaults:
    namingTemplate: "{namespace}-realtime-{name}"
    tags:
      environment: production

---
# Compliance profile: enforce cost-predictable import mode
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    importMode: "SPICE"
    tags:
      compliance-tier: pci
      data-classification: internal
  defaults:
    namingTemplate: "{namespace}-compliant-{name}"
    tags:
      environment: production
```

## Using profiles with instances

Once your profiles are deployed, QuickSight resources select them via `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: sales-metrics
  namespace: analytics
spec:
  configRef: high-performance
  resourceId: sales-metrics-ds
  importMode: ""  # Empty: let the config decide (forced to DIRECT_QUERY)
  physicalTableMap:
    sales:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/sales-db
        name: orders
        schema: public
```

In this example:
- Import mode is forced to `DIRECT_QUERY` (mandatory from high-performance profile)
- Developer cannot override import mode
- Naming automatically includes performance tier context
- Performance-related tags are automatically applied

## Profile selection rules

- **Default fallthrough** — if you omit `spec.configRef` or reference a profile that doesn't exist, kropath automatically uses the `general-policy` profile
- **Profiles in kro-system** — all profiles are deployed to the `kro-system` namespace. Instances in any application namespace can reference them via `spec.configRef`
- **Profile lookup by label** — profiles are found via the `aws.kropath.run/resource-name` label, not by `metadata.name`, so you can rename the CR safely without breaking references

## Import mode guidance

QuickSight supports two data import modes:

- **SPICE** (Super-fast, Parallel, In-memory Calculation Engine): QuickSight caches data in its high-performance store. Queries are fast, predictable. Best for dashboards, pre-defined analyses, cost-predictable BI.
- **DIRECT_QUERY**: Queries execute against the source database in real-time. Lower latency for updates, higher database load. Best for ad-hoc analysis, live data feeds, databases that can handle the query volume.

Most organizations default to SPICE and allow exceptions for high-performance or real-time use cases.

## Best practices

1. **Create profiles for organizational postures, not per-resource.** One `compliance` profile serves all regulated workloads; don't create individual profiles for each resource.

2. **Use mandatory fields sparingly.** Reserve mandatory for hard requirements (import mode for cost control, tags for compliance). Use defaults for convenience.

3. **Document why mandatory fields exist.** Add annotations to profiles explaining why certain settings are enforced.

4. **Tag at the profile level.** Add environment and cost-center tags to profiles so every resource inheriting that profile carries the tags automatically, reducing manual overhead.

5. **Test profile changes in non-production first.** Profile updates apply to all resources using that profile; validate in a staging namespace before production.

6. **Use consistent naming templates.** The `{namespace}-{name}` template is recommended. It ensures cloud resource names include namespace context, reducing confusion in production.

7. **Plan for profile evolution.** When operational requirements change, update the profile rather than updating every resource individually — that's the power of centralized governance.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `QuickSightConfig`
- **Scope**: Namespaced
