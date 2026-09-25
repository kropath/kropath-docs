---
title: PipesConfig — Governance Profiles for EventBridge Pipes
description: "`PipesConfig` CRs define per-profile governance policies that platform engineers apply to the EventBridge Pipes family."
doc_type: reference
---
# PipesConfig — Governance Profiles for EventBridge Pipes

`PipesConfig` CRs define per-profile governance policies that platform engineers apply to the EventBridge Pipes family. Teams select a profile via `spec.configRef` when creating pipe resources.

## Governance Structure

Each `PipesConfig` CR has two sections:

- **`spec.mandatory`** — Fields set here enforce policies that instances cannot override
- **`spec.defaults`** — Fields here provide defaults that instances can override

This two-tier structure ensures compliance while preserving operational flexibility.

## Scalar Field Mutual-Exclusion Constraint

For **scalar fields only** (`desiredState` and `namingTemplate`), you must choose **one or the other** — never both:

- **Set in `mandatory`:** The field has a non-empty value in mandatory, and an **empty** string (`""`) in defaults
- **Set in `defaults`:** The field has an **empty** value in mandatory, and a non-empty value in defaults
- **Unset:** The field has empty values in **both** mandatory and defaults (no enforcement, no default)

Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are **additive across tiers** — you can set them in both mandatory and defaults, and they will be merged with mandatory taking precedence on key conflict. The mutual-exclusion constraint applies only to scalar fields.

The admission webhook rejects any `PipesConfig` that violates this constraint by setting non-empty values in both sections for the same scalar field.

## General Policy (Default)

The `general-policy` profile is the built-in fallback and ships with kropath. It provides conservative defaults suitable for most workloads:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory:
    desiredState: ""                          # No enforcement; teams can choose
    namingTemplate: ""
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
  defaults:
    desiredState: "running"                   # Default: pipes run by default
    namingTemplate: "{namespace}-{name}"      # Default naming pattern
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## Production Profile

For production workloads, enforce stricter controls:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    desiredState: "running"                   # Enforce running state (no stopping)
    namingTemplate: "prod-{namespace}-{name}" # Enforce naming convention
    tags:
      environment: production
      managed-by: kropath
    syncedLabels:
      environment: production
  defaults:
    desiredState: ""                          # Governed by mandatory
    namingTemplate: ""                        # Governed by mandatory
    tags: {}                                  # Merged with mandatory tags
    syncedLabels: {}                          # Merged with mandatory labels
```

## Staging Profile with Controlled State

For staging environments, allow stopping pipes to save costs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesConfig
metadata:
  name: staging
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: staging
spec:
  mandatory:
    desiredState: ""                          # Allow teams to control state
    namingTemplate: ""                        # Allow team flexibility
    tags:
      environment: staging
    syncedLabels:
      environment: staging
  defaults:
    desiredState: "running"                   # Default to running
    namingTemplate: "staging-{namespace}-{name}" # Default naming pattern
    tags: {}                                  # Merged with mandatory tags
    syncedLabels: {}                          # Merged with mandatory labels
```

## Development Profile

For dev/test environments, minimize constraints:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}                               # No mandatory enforcements
  defaults:
    desiredState: "stopped"                   # Default to stopped (cost savings)
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development
    syncedLabels:
      environment: development
```

## Creating a Custom Profile

To create a profile for your specific use case:

1. **Choose a name** — e.g., `high-throughput`, `real-time-analytics`, `batch-processing`
2. **Define mandatory policies** — Enforcement at org level (compliance, cost limits, SLAs)
3. **Define defaults** — Fallbacks when teams don't specify
4. **Apply tags and labels** — For cost allocation, audit trails, and metadata

Example: High-Throughput Real-Time Processing Profile

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: PipesConfig
metadata:
  name: high-throughput
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-throughput
spec:
  mandatory:
    desiredState: "running"                    # Always running
    namingTemplate: "realtime-{namespace}-{name}" # Enforce naming
    tags:
      workload-type: real-time
      sla: critical
    syncedLabels:
      workload-type: real-time
  defaults:
    desiredState: ""                           # Governed by mandatory
    namingTemplate: ""                         # Governed by mandatory
    tags: {}                                   # Merged with mandatory tags
    syncedLabels: {}                           # Merged with mandatory labels
```

## Governance Cascade

When a pipe instance is created, the resolution order is:

1. **Check mandatory** — If `PipesConfig.mandatory.<field>` is set, use it (no override)
2. **Check instance** — If `spec.<field>` is explicitly set on the CR, use it
3. **Check defaults** — If `spec.<field>` is unset, use `PipesConfig.defaults.<field>`

**Example Cascade:**

```
PipesPipe.spec:
  configRef: production       # Use production profile
  desiredState: ""            # Not specified (empty)

Resolution:
  desiredState → production.mandatory.desiredState = "running"
                (mandatory wins; instance cannot override)
```

## Naming Template Tokens

The `namingTemplate` field supports several tokens that are automatically replaced:

| Token | Value |
|---|---|
| `{name}` | The CR's metadata.name |
| `{namespace}` | The CR's metadata.namespace |
| `{account_id}` | The AWS account ID from configuration |
| `{region}` | The AWS region from configuration |
| `{configRef}` | The selected config profile name |
| `{tag.<key>}` | A tag value (e.g., `{tag.environment}` for the `environment` tag) |

Example templates:

```
{namespace}-{name}           # e.g., events-prod-order-processor
{tag.environment}-{name}     # e.g., production-order-processor
corp-{region}-{name}         # e.g., corp-us-east-1-order-processor
```

**AWS Constraints:** Pipe names are 1–64 characters, `A-Za-z0-9._-` only, and case-sensitive.

## Desired State Governance

The `desiredState` field controls whether pipes are running or stopped:

| Value | Behavior |
|---|---|
| `"running"` | Pipe actively processes events from source to target |
| `"stopped"` | Pipe is stopped and does not process events |
| `""` (empty) | Not enforced or not specified |

**Enforcement Rules:**

- **Mandatory `"running"`** — Pipe always runs; instance cannot stop it
- **Mandatory `"stopped"`** — Pipe always stopped; instance cannot run it
- **Mandatory `""`** — No enforcement; instance can choose
- **Default `"running"`** — Pipe runs by default if instance doesn't specify
- **Default `""`** — Falls through to RGD built-in default (running)

Use mandatory `desiredState` for production pipes (always running) and defaults for development/staging (provide a sensible default but allow override).

## Tag and Label Merging

Tags, syncedLabels, and syncedAnnotations are **merged** across tiers:

1. **`mandatory` tags** — Merged first (take precedence on key conflict)
2. **`spec` tags** — Merged second
3. **`defaults` tags** — Merged last

Final tags = `mandatory.tags` + `spec.tags` + `defaults.tags` (with mandatory winning on conflict)

**Example:**

```yaml
spec:
  configRef: production
  tags:
    application: order-service
```

Production profile has:
- `mandatory.tags: {environment: production, managed-by: kropath}`
- `defaults.tags: {cost-centre: platform}`

Result:
- `tags: {environment: production, managed-by: kropath, application: order-service, cost-centre: platform}`

**SyncedLabels** and **SyncedAnnotations** work the same way — they are merged across tiers and applied as both Kubernetes labels/annotations (prefixed with `aws.kropath.run/`) and cloud tags.

## Platform Engineering Best Practices

1. **Start with general-policy** — Use the built-in profile as a baseline; create custom profiles only when needed.

2. **Use mandatory for compliance** — Enforce fields via `mandatory` when your organization has non-negotiable requirements (e.g., production pipes must run, naming conventions).

3. **Use defaults for convenience** — Provide sensible defaults via `defaults` to reduce boilerplate without enforcing policies.

4. **Name profiles clearly** — Use descriptive names (`production`, `staging`, `development`, `high-throughput`) so teams understand what governance applies.

5. **Document per-profile rules** — Maintain a runbook describing what each profile enforces and when to use it.

6. **Monitor usage** — Check which profiles are being used; if a profile is never selected, consider removing it.

7. **Test profile changes** — Before rolling out new mandatory rules, test them in staging clusters first.

## Cross-Provider Notes

`PipesConfig` is AWS-specific. Other providers will have their own config CRDs with different governance fields appropriate to each provider's feature set.

The two-tier structure (mandatory/defaults) and governance cascade pattern are consistent across all providers.

## Related Topics

- [PipesPipe](pipespipe.md) — Creating and managing individual pipes with configRef
