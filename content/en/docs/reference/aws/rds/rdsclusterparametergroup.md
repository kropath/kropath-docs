---
title: RDSClusterParameterGroup
description: "`RDSClusterParameterGroup` creates a parameter group for Aurora clusters."
doc_type: reference
---
# RDSClusterParameterGroup

`RDSClusterParameterGroup` creates a parameter group for Aurora clusters. Unlike instance-level parameter groups, cluster parameter groups apply engine settings cluster-wide to every instance in an Aurora cluster — settings like `rds.force_ssl`, `aurora_parallel_query`, and logical replication flags.

## When to use

Use `RDSClusterParameterGroup` when you need to enforce cluster-wide engine settings on Aurora. This is the standard way to configure features like parallel query, manage replication, and enforce security settings like SSL across all instances in a cluster.

## Prerequisites

- An `RDSConfig` profile must exist in the same namespace (or `general-policy` will be used as a fallback)
- The parameter group family must be an **Aurora family** (e.g., `aurora-mysql8.0`, `aurora-postgresql15`)
- The cluster must be created before attaching the parameter group

## Configuration

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `spec.family` | string | Aurora database engine family (e.g., `aurora-mysql8.0`, `aurora-postgresql15`, `aurora-postgresql16`). Immutable after creation. Must be an Aurora family. |
| `spec.description` | string | Human-readable description of the cluster parameter group. |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `spec.parameterOverrides` | map | `{}` | Named engine parameters to customize cluster-wide (e.g., `rds.force_ssl: "1"`). Parameter names are family-specific and Aurora-specific; invalid keys are rejected by the database engine. |
| `spec.nameOverride` | string | `""` | Explicitly set the cluster parameter group name instead of using the naming template. |
| `spec.deletionPolicy` | string | `"retain"` | Deletion behavior: `"retain"` keeps the group in AWS; `"delete"` removes it when the resource is deleted. |
| `spec.configRef` | string | `"general-policy"` | Reference to an `RDSConfig` profile by name. Falls back to `general-policy` if the profile does not exist. |
| `spec.tags` | map | `{}` | AWS tags to apply to the cluster parameter group. Merged with tags from `RDSConfig`. |
| `spec.syncedLabels` | map | `{}` | Labels mirrored to both Kubernetes annotations and AWS tags. |
| `spec.syncedAnnotations` | map | `{}` | Annotations synced from `RDSConfig` and mirrored to AWS tags. |

## Status fields

| Field | Type | Description |
|-------|------|-------------|
| `status.resourceName` | string | The effective cluster parameter group name in AWS (after applying naming template and lowercase conversion). |
| `status.namingStatus` | string | Naming resolution status: `"valid"` or `"invalid-unresolved-tokens"` if template tokens cannot be resolved. |
| `status.predictedArn` | string | The AWS ARN of the cluster parameter group in the format `arn:aws:rds:<region>:<account>:cluster-pg:<resourceName>`. Note: `cluster-pg`, not `pg` — this differs from instance parameter groups. |
| `status.parameterOverrideStatuses` | array | Status of each parameter override, including `parameterName`, `parameterValue`, `applyStatus`, and `applyMethod`. |
| `status.validationError` | string | Error message if the cluster parameter group configuration is invalid and cannot be created. Empty if the resource is valid. |
| `status.conditions[]` | array | Standard Kubernetes conditions tracking resource state. |

## Naming convention

Cluster parameter group names follow the naming template defined in your `RDSConfig` profile. The default template is `{namespace}-{name}`, which expands to namespace and resource name. Names are converted to lowercase and must use only letters, digits, and hyphens (1–255 characters).

Use `spec.nameOverride` to bypass the template and set an explicit name.

## Parameter override behavior

When you specify `spec.parameterOverrides`:

- Parameter names and values are **Aurora-family-specific** — supplying an invalid key is accepted by the API but rejected by the database engine.
- Some parameters require the cluster's writer instance to reboot before taking effect. The `status.parameterOverrideStatuses` field shows which parameters have `applyStatus: pending-reboot`. Kropath does not trigger reboots; you must do this manually.
- If a parameter override is omitted, the cluster uses the database engine's default value for that family.
- Common Aurora parameters: `rds.force_ssl`, `binlog_format` (MySQL), `rds.logical_replication` (PostgreSQL), `aurora_parallel_query`.

## Note on underlying API deprecation

**Note:** The underlying AWS RDS API (via ACK's `DBClusterParameterGroup`) has a deprecated `parameters` field for inline parameter definitions. `RDSClusterParameterGroup` never exposes this field to users — always use `spec.parameterOverrides`, which is the only supported path.

## Attaching cluster parameter groups to clusters

To use a cluster parameter group, set its name in an `RDSCluster`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSCluster
metadata:
  name: prod-cluster
  namespace: production
spec:
  family: aurora-mysql8.0
  engine: aurora-mysql8.0
  dbClusterParameterGroupName: my-cluster-params  # Reference by name
  # ... other RDSCluster fields
```

## Example: Basic cluster parameter group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSClusterParameterGroup
metadata:
  name: aurora-cluster-pg
  namespace: production
spec:
  family: aurora-postgresql15
  description: Aurora PostgreSQL cluster settings
  parameterOverrides:
    rds.force_ssl: "1"
    rds.logical_replication: "1"
  tags:
    application: reporting
    environment: production
```

## Example: Aurora MySQL with parallel query

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSClusterParameterGroup
metadata:
  name: aurora-mysql-pq
  namespace: default
spec:
  family: aurora-mysql8.0
  description: Aurora MySQL with parallel query enabled
  parameterOverrides:
    aurora_parallel_query: "ON"
    binlog_format: "ROW"
    rds.force_ssl: "1"
  deletionPolicy: retain
```

To check parameter application status:

```bash
kubectl describe rdsclusterparametergroup aurora-mysql-pq -n default
```

## Deletion behavior

- `deletionPolicy: "retain"` (default): The cluster parameter group stays in AWS. Useful when the group may be reused or shared across clusters.
- `deletionPolicy: "delete"`: The cluster parameter group is deleted from AWS when the resource is deleted.

Deletion requires that no Aurora clusters are actively using the group.

## Key differences from instance parameter groups

| Aspect | Instance (`RDSParameterGroup`) | Cluster (`RDSClusterParameterGroup`) |
|--------|--------|------------|
| Family | Single-instance engines (mysql8.0, postgres15) | Aurora families only (aurora-mysql8.0, aurora-postgresql15) |
| Scope | Applies to one instance | Applies cluster-wide to all instances |
| ARN segment | `pg` | `cluster-pg` |
| Attachment | `RDSInstance.spec.dbParameterGroupName` | `RDSCluster.spec.dbClusterParameterGroupName` |

## Cross-provider availability

`RDSClusterParameterGroup` is AWS Aurora-only. GCP Cloud SQL and Azure Database do not have cluster-wide parameter groups; parameters are configured per-instance or per-server.

## Related resources

- [`RDSParameterGroup`](./rdsparametergroup.md) — For instance-level settings
- [`RDSCluster`](./rdscluster.md) — Attaches a cluster parameter group via `spec.dbClusterParameterGroupName`
- [`RDSConfig`](./rdsconfig.md) — Defines naming templates and shared tags
