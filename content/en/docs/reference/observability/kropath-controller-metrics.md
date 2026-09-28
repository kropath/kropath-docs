---
title: kropath-controller metrics and alerts
linkTitle: Controller metrics
description: >
  Reference of all Prometheus metrics and alerting rules exposed by kropath-controller.
weight: 10
doc_type: reference
---

This page documents every metric and alert exposed by kropath-controller on its `/metrics` endpoint
(port `8080` by default). Use this as a reference when setting up Prometheus scraping, configuring
alert routing, or interpreting metric values.

## Metric types

Metrics follow Prometheus conventions:

- **Counter** — Monotonically increasing value (never resets within a pod lifetime). Use
  `rate()` or `increase()` in alert expressions to measure events per second or per interval.
- **Gauge** — Point-in-time value sampled when Prometheus scrapes the endpoint.

## Cardinality and aggregation

kropath-controller runs on every replica in a cluster with leader election. Gauge metrics report
the same cluster-wide value on every replica — use `max by (label)` in alert expressions and
dashboards, never `sum by (label)`, to avoid reading N times too high across N replicas.

Counters are per-replica facts (events this process handled), so `sum by (...) (rate(...))` is
correct for them.

## Configuration resolution

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_placement_resolutions_total` | counter | `reason` | `KropathPlacementResolutionFailing` |
| `kropath_config_profile_resolutions_total` | counter | `family`, `reason` | Dashboard only |

**`kropath_placement_resolutions_total`** increments when a namespace's account and region
annotations are processed. Reasons include:

- `PlacementResolved` — annotations were valid
- `MissingAccountAnnotation`, `InvalidAccountAnnotation` — annotation issues
- `MissingRegionAnnotation` — region annotation missing
- `NamespaceUnreadable` — namespace itself could not be read

**`kropath_config_profile_resolutions_total`** increments when a configuration profile is resolved
for a service. `reason` values:

- `ProfileFound` — matching profile found in `KropathConfig`
- `ProfileFallthrough` — no profile matched; defaults used
- `ProfileUnresolved` — resolution failed

## Policy documents

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_policydocument_documents` | gauge | `reason` | `KropathPolicyDocumentsNotReady` |
| `kropath_policydocument_unresolved_refs` | gauge | `kind`, `field` | Dashboard only |
| `kropath_policydocument_ref_resolutions_total` | counter | `kind`, `field`, `outcome` | `KropathPolicyRefCRDAbsent` |
| `kropath_policydocument_sid_conflicts_total` | counter | — | Dashboard only |

**`kropath_policydocument_documents`** — Count of policy documents by their current status:

- `DocumentResolved` — document ready
- `InvalidDocumentJSON` — JSON parsing failed
- `SidConflict` — statement IDs are duplicated
- `SourceNotReady` — referenced resource ARN could not be resolved
- `SourceMissing` — referenced source document doesn't exist
- `SourcePending` — referenced document is still resolving
- `MergeFromRawNotSupported` — cannot merge with raw JSON document

**`kropath_policydocument_unresolved_refs`** — Count of resource references that could not be
resolved to an ARN. `kind` includes common AWS resource types (e.g. `AWSS3Bucket`, `AWSIAMRole`)
plus `other` for unknown kinds. `field` indicates where the ARN came from:

- `predictedArn` — derived from resource name before creation
- `arn` — read from resource status after creation
- `unsupported` — ARN prediction not supported for this kind

**`kropath_policydocument_ref_resolutions_total`** — Counter of ARN resolution attempts. `outcome`:

- `resolved` — ARN found
- `pending` — resource exists but doesn't yet have an ARN
- `crd_absent` — resource kind is not installed
- `error` — lookup failed

## Configuration cascade

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_cascade_effective_config_withheld` | gauge | `family`, `reason` | `KropathEffectiveConfigWithheld` |
| `kropath_cascade_mapfunc_errors_total` | counter | `family`, `trigger` | `KropathCascadeChangeEventsDropped` |

**`kropath_cascade_effective_config_withheld`** — Count of configurations that could not be
written to `status.effectiveConfig` due to placement failures. The `reason` label indicates which
step failed (matches the `kropath_placement_resolutions_total` reasons above).

High values on this metric indicate that RGDs cannot resolve configurations in your cluster.

**`kropath_cascade_mapfunc_errors_total`** — Counter of change events that were dropped due to
errors while processing configuration updates. `trigger` indicates which kind of change caused
the error: `kropathconfig`, `familyconfig`, or `namespace`.

## Label injection

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_labeloperator_watched_kinds` | gauge | `group` | `KropathLabelInjectionOff` |
| `kropath_labeloperator_group_discovery_total` | counter | `group`, `outcome` | Dashboard only |
| `kropath_labeloperator_patches_total` | counter | `group`, `outcome` | Dashboard only |

**`kropath_labeloperator_watched_kinds`** — Count of resource kinds being watched per provider
group (`aws.kropath.run`, `gcp.kropath.run`, `azure.kropath.run`). A value of `0` means label
injection is not running for that group. The alert fires if this is absent or zero.

**`kropath_labeloperator_group_discovery_total`** — Counter of group discovery attempts per
provider group. `outcome`:

- `discovered` — kinds found and controllers started
- `empty` — group exists but no kinds matched
- `error` — discovery failed

**`kropath_labeloperator_patches_total`** — Counter of label patching attempts. `outcome`:

- `patched` — successfully added or updated labels
- `not_found` — resource was deleted during patching
- `error` — patch failed

## KropathConfig status

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_kropathconfigstatus_configs` | gauge | `reason` | `KropathConfigUnreferenced` |
| `kropath_kropathconfigstatus_family_kinds_unavailable` | gauge | — | `KropathConfigFamilyKindsUnavailable` |

**`kropath_kropathconfigstatus_configs`** — Count of `KropathConfig` CRs by their classification:

- `GlobalTier` — config is used as org-wide settings
- `LocalTier` — config is used as namespace-local overrides
- `GlobalAndLocalTier` — config serves both roles
- `Unreferenced` — no service config reads this `KropathConfig`

Unreferenced configs represent a critical failure: valid configurations that aren't connected
to any service, so no `status.effectiveConfig` is ever written. This is caught by the
`KropathConfigUnreferenced` alert.

**`kropath_kropathconfigstatus_family_kinds_unavailable`** — Count of service configuration kinds
that are not installed. If this is non-zero, `KropathConfigUnreferenced` may be underreported
(a config might not find a reader because the reader's CRD isn't installed yet, not because it's
truly unreferenced).

## Namespace placement

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_namespaceplacement_namespaces` | gauge | `status` | Dashboard only |
| `kropath_namespaceplacement_transitions_total` | counter | `to` | Dashboard only |

**`kropath_namespaceplacement_namespaces`** — Count of namespaces by their placement status:

- `ok` — all required annotations are present and valid
- `MissingAccountAnnotation`, `InvalidAccountAnnotation` — account annotation issues
- `MissingRegionAnnotation` — region annotation missing
- `TeamAnnotationUnsupported` — team annotation present but not supported in your configuration

**`kropath_namespaceplacement_transitions_total`** — Counter of namespace placement status changes.
Track this to see how often namespaces move between healthy and unhealthy states.

## Reconciler health

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_registry_reconciler_pending_since_timestamp_seconds` | gauge | `package` | `KropathReconcilerPendingTooLong` |
| `kropath_registry_crd_watch_events_total` | counter | `outcome` | Dashboard only |
| `kropath_registry_optional_kinds_attached` | gauge | `package` | Dashboard only |

**`kropath_registry_reconciler_pending_since_timestamp_seconds`** — Unix timestamp when a
reconciler's CRD was first detected as missing. If the CRD is later installed and the reconciler
activates, this series disappears (is not zero — it is absent). Use `absent()` or `absent() or ... == 0`
in alert expressions to detect missing reconcilers.

The alert fires when a reconciler has been pending for over an hour.

**`kropath_registry_crd_watch_events_total`** — Counter of CRD watch events that add or modify
reconcilers. `outcome`:

- `activated` — CRD became available and reconciler started
- `not_servable` — CRD is installed but not served
- `store_miss` — CRD data not found in cache
- `already_active` — CRD update for an already-running reconciler
- `cast_failed` — internal type assertion error

## Metrics collector health

| Metric | Type | Labels | Alert |
|---|---|---|---|
| `kropath_metrics_collect_errors_total` | counter | `collector` | `KropathMetricsCollectorFailing` |

**`kropath_metrics_collect_errors_total`** — Counter of errors while collecting metrics. Each
scrape-time collector (those that require a Kubernetes API call, like policy document listing)
has a 2-second timeout. On error, the collector emits no samples for its metric but increments
this counter instead, so you know data is missing.

## Alerting rules

| Alert | Severity | Fires when |
|---|---|---|
| `KropathConfigUnreferenced` | critical | A `KropathConfig` is not being read by any service config — the most common platform-breaking failure |
| `KropathConfigFamilyKindsUnavailable` | warning | A service config CRD is not installed, masking true placement status |
| `KropathEffectiveConfigWithheld` | critical | Placement failed, so `status.effectiveConfig` was not written; RGD CEL will fail |
| `KropathPlacementResolutionFailing` | warning | Namespace placement is rejecting at a sustained rate |
| `KropathPolicyDocumentsNotReady` | warning | A policy document is stuck (not resolved, SID conflict, unresolved refs) |
| `KropathPolicyRefCRDAbsent` | warning | A policy document references a resource kind that is not installed |
| `KropathLabelInjectionOff` | critical | No label-injection controller is registered for a provider group |
| `KropathCascadeChangeEventsDropped` | warning | A service config's watch handler dropped a batch of change events |
| `KropathReconcilerPendingTooLong` | warning | A reconciler's CRD is missing for over an hour |
| `KropathMetricsCollectorFailing` | warning | A metrics collector hit an error; its series are missing |

All alerts carry `component: kropath-controller` so you can route them as a group.

Severity levels:

- **Critical** — Tenant workloads are broken or will break immediately.
- **Warning** — Degraded or missing visibility, transient issues, or future problems.

## Alert routing

Route all kropath-controller alerts to a single receiver:

```yaml
routes:
- match:
    component: kropath-controller
  receiver: platform-team
```

## Interpreting metrics

### High `kropath_cascade_effective_config_withheld`

Effective configurations are not being written. Check:

- Are namespace annotations present and valid? (Review `kropath_placement_resolutions_total`)
- Are service config CRDs installed? (Check `kropath_kopathconfigstatus_family_kinds_unavailable`)
- Is there a `KropathConfigUnreferenced` alert firing?

### High `kropath_policydocument_unresolved_refs`

Policy documents cannot resolve resource ARNs. Check:

- Are the referenced resources created? (Check resource status in your cloud provider)
- Are their CRDs installed? (Check `KropathPolicyRefCRDAbsent` alert)
- Is label injection working? (Check `kropath_labeloperator_watched_kinds`)

### Zero `kropath_labeloperator_watched_kinds`

Label injection is not running. Check:

- Is the operator pod running? (`kubectl get pods`)
- Are the provider group CRDs present? (`kubectl get crd | grep kropath.run`)
- Is `KropathLabelInjectionOff` alert firing?

## See also

- [Monitor kropath-controller](../../tasks/operations/monitor-kropath-controller.md) — Setup guide for Prometheus and Grafana
