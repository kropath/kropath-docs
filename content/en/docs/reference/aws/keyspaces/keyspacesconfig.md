---
title: KeyspacesConfig
description: "`KeyspacesConfig` is a governance configuration resource that lets you define mandatory and default settings for Amazon Keyspaces keyspaces and tables."
doc_type: reference
---
# KeyspacesConfig

`KeyspacesConfig` is a governance configuration resource that lets you define mandatory and default settings for Amazon Keyspaces keyspaces and tables. Instead of requiring every keyspace and table to specify encryption, throughput, backup policy, and naming independently, you can create named configuration profiles and let the kropath controller apply them consistently across your cluster.

## Scope

This resource is AWS-only. KeyspacesConfig governs AWS Keyspaces resources (via `KeyspacesKeyspace` and `KeyspacesTable` RGDs). There is no GCP or Azure equivalent yet.

## What it solves

Managing Keyspaces resources at scale creates several operational challenges:

- **Inconsistent governance** — different teams set different encryption types, throughput modes, and PITR settings, making compliance audits difficult
- **Compliance drift** — once resources are created, enforcing new compliance requirements (e.g., "all tables must use customer-managed KMS keys") requires manual updates
- **Manual defaults** — every resource spec must list sensible defaults (on-demand throughput, AWS-managed encryption), creating noise and inconsistency
- **No central policy** — when a new compliance requirement arrives, you must update every resource individually

`KeyspacesConfig` solves this by providing:

- **Governance profiles** — define reusable profiles like `compliance`, `high-availability`, or `general-policy` that encode your organization's requirements
- **Mandatory enforcement** — platform teams set fields that override user input (e.g., "all tables must use customer-managed encryption for compliance")
- **Sensible defaults** — declare defaults for optional fields so user specs are cleaner and every resource has a consistent baseline
- **Scalable compliance** — update one profile to enforce a new requirement across all resources using that profile

## Core concepts

### Mandatory vs. defaults tiers

`KeyspacesConfig` has two independent tiers of settings:

**Mandatory fields** (enforced):
- Override any user specification for that field
- Useful for compliance: "all keyspaces must use multi-region replication"
- If mandatory is empty, it is not enforced (user can override)

**Defaults fields** (applied when user doesn't specify):
- Provide sensible fallback values
- Applied only when the user leaves the field empty
- Useful for convenience: "on-demand throughput by default, but let power users choose provisioned"

Mandatory wins over defaults: if both are set for the same field, the default is ignored.

### Governance cascade

The kropath controller pre-merges settings from three sources and writes them to `status.effectiveConfig`:

1. **Org-wide** (`KropathConfig.spec.keyspaces.*`) — applies to all keyspaces and tables across the cluster
2. **Per-type** (`KeyspacesConfig.spec.mandatory/defaults.*`) — applies to keyspaces or tables using this profile
3. **Instance** (`KeyspacesKeyspace/KeyspacesTable.spec.*`) — developer override for a specific resource

RGDs read the merged result from `status.effectiveConfig`, ensuring a single source of truth.

### Profile patterns

Common profiles codify organizational postures:

**general-policy** — the default, sensible baseline:
- On-demand throughput (`PAY_PER_REQUEST`)
- AWS-managed encryption
- PITR disabled (cost-conscious default)
- TTL disabled
- Single-region replication

**compliance** — stricter, suitable for regulated workloads:
- Customer-managed encryption (required)
- PITR enabled (required, for audit trail)
- Throughput defaults to on-demand
- Naming templates can be tightened

**high-availability** — multi-region failover:
- Multi-region replication (required)
- PITR enabled (required, for data recovery)
- On-demand throughput (reduce operational burden)
- Encryption defaults to AWS-managed (developers can override to CMEK)

## Configuration fields

### Mandatory tier

Fields in this tier override any instance `spec` setting:

| Field | Type | Meaning |
|---|---|---|
| `replicationStrategy` | `SINGLE_REGION` \| `MULTI_REGION` | Keyspace replication (immutable). Empty = not enforced. |
| `throughputMode` | `PAY_PER_REQUEST` \| `PROVISIONED` | Table capacity mode. Empty = not enforced. |
| `encryptionType` | `AWS_OWNED_KMS_KEY` \| `CUSTOMER_MANAGED_KMS_KEY` | Table encryption. Empty = not enforced. |
| `pointInTimeRecovery` | boolean | Enable PITR for tables. Empty = not enforced. |
| `ttlEnabled` | boolean | Enable row-level TTL for tables. Empty = not enforced. |
| `namingTemplate` | string | Cloud resource name template (e.g., `"corp_{namespace}_{name}"`). Empty = use defaults tier. |
| `tags` | map | Cloud resource tags. Merged with defaults and instance tags. |
| `syncedLabels` | map | Labels to sync to both K8s and cloud tags. |
| `syncedAnnotations` | map | Annotations to sync to both K8s metadata and cloud tags. |

### Defaults tier

Fields here apply when an instance leaves the field empty:

| Field | Type | Default value | Meaning |
|---|---|---|---|
| `replicationStrategy` | string | `"SINGLE_REGION"` | Fallback replication strategy. |
| `throughputMode` | string | `"PAY_PER_REQUEST"` | Fallback capacity mode. |
| `encryptionType` | string | `"AWS_OWNED_KMS_KEY"` | Fallback encryption. |
| `pointInTimeRecovery` | boolean | `false` | Fallback: PITR disabled. |
| `ttlEnabled` | boolean | `false` | Fallback: TTL disabled. |
| `namingTemplate` | string | `"{namespace}_{name}"` | Default cloud resource naming. |
| `tags` | map | `{}` | Merged with mandatory and instance tags. |
| `syncedLabels` | map | `{}` | Merged with mandatory and instance labels. |
| `syncedAnnotations` | map | `{}` | Merged with mandatory and instance annotations. |

## Complete example

Here's a complete multi-profile setup:

```yaml
---
# Org-wide settings (applied to all keyspaces and tables)
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global
  namespace: kro-system
spec:
  mandatory:
    keyspaces:
      # (empty — no org-wide mandatory overrides)
  defaults:
    keyspaces:
      # (can add org-wide defaults if desired)

---
# Default profile: sensible, cost-conscious baseline
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    replicationStrategy: "SINGLE_REGION"
    throughputMode: "PAY_PER_REQUEST"
    encryptionType: "AWS_OWNED_KMS_KEY"
    pointInTimeRecovery: false
    ttlEnabled: false
    namingTemplate: "{namespace}_{name}"
    tags:
      environment: development

---
# Compliance profile: stricter, for regulated workloads
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesConfig
metadata:
  name: compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: compliance
spec:
  mandatory:
    encryptionType: "CUSTOMER_MANAGED_KMS_KEY"
    pointInTimeRecovery: true
    tags:
      compliance-tier: pci
  defaults:
    replicationStrategy: "SINGLE_REGION"
    throughputMode: "PAY_PER_REQUEST"
    ttlEnabled: false
    namingTemplate: "{namespace}_{name}"

---
# High-availability profile: multi-region failover
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesConfig
metadata:
  name: high-availability
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: high-availability
spec:
  mandatory:
    replicationStrategy: "MULTI_REGION"
    pointInTimeRecovery: true
  defaults:
    throughputMode: "PAY_PER_REQUEST"
    encryptionType: "AWS_OWNED_KMS_KEY"
    ttlEnabled: false
    namingTemplate: "{namespace}_{name}"
    tags:
      environment: production
      tier: mission-critical
```

When a keyspace or table references one of these profiles via `spec.configRef`, the controller writes the merged settings to the profile's `status.effectiveConfig`.

## Using profiles with instances

Once your profiles are deployed, keyspaces and tables select them via `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesKeyspace
metadata:
  name: my-keyspace
  namespace: payments
spec:
  configRef: compliance  # Use the compliance profile
  replicationStrategy: ""  # Empty: let the config decide
```

In this example:
- Encryption type is forced to `CUSTOMER_MANAGED_KMS_KEY` (mandatory)
- PITR is forced to enabled (mandatory)
- Replication defaults to `SINGLE_REGION` (from defaults tier)
- Developer can override replication, but cannot override encryption or PITR

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KeyspacesTable
metadata:
  name: user-events
  namespace: payments
spec:
  configRef: high-availability  # Use the HA profile
  keyspaceName: my-keyspace
  columns:
    - name: user_id
      type: uuid
    - name: event_time
      type: timestamp
  partitionKeys:
    - name: user_id
  throughputMode: ""  # Empty: defaults to PAY_PER_REQUEST
```

Here:
- Replication is forced to `MULTI_REGION` (mandatory, applies to the containing keyspace)
- PITR is forced to enabled (mandatory)
- Throughput defaults to on-demand (from defaults tier)

## Profile selection rules

- **Default fallthrough** — if you omit `spec.configRef` or reference a profile that doesn't exist, kropath automatically uses the `general-policy` profile
- **Profiles in kro-system** — all profiles are deployed to the `kro-system` namespace. Instances in any application namespace can reference them via `spec.configRef`
- **Profile lookup by label** — profiles are found via the `aws.kropath.run/resource-name` label, not by `metadata.name`, so you can rename the CR safely without breaking references

## Best practices

1. **Create profiles for organizational postures, not per-resource.** One `compliance` profile serves all regulated workloads; don't create `compliance-table-1`, `compliance-table-2`, etc.

2. **Use mandatory fields sparingly.** Reserve mandatory for hard compliance requirements (encryption, PITR for audit). Use defaults for convenience.

3. **Document why mandatory fields exist.** Add annotations or comments to profiles explaining compliance drivers or operational requirements.

4. **Tag at the profile level.** Add environment and cost-center tags to profiles so every resource inheriting that profile carries the tags automatically.

5. **Test profile changes in non-production first.** Profile updates apply to all resources using that profile; validate in a staging namespace before production.

6. **Use consistent naming templates.** The `{namespace}_{name}` template is recommended. It ensures cloud resource names include the namespace context, reducing confusion in production.

7. **Plan for profile evolution.** When compliance requirements change, update the profile rather than updating every resource individually — that's the power of centralized governance.

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `KeyspacesConfig`
- **Scope**: Namespaced
