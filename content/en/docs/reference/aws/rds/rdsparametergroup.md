---
title: RDSParameterGroup
description: "`RDSParameterGroup` creates a named database parameter group for RDS instances."
doc_type: reference
---
# RDSParameterGroup

`RDSParameterGroup` creates a named database parameter group for RDS instances. A parameter group defines engine-level settings — such as `max_connections`, `innodb_buffer_pool_size`, and `rds.force_ssl` — that apply to all instances using that group.

## When to use

Use `RDSParameterGroup` when you need to configure engine settings for one or more RDS instances. This is the standard way to enforce connection limits, tune buffer pools, and manage per-connection behaviors like TLS enforcement.

## Prerequisites

- An `RDSConfig` profile must exist in the same namespace (or `general-policy` will be used as a fallback)
- The parameter group family must match your database engine version (e.g., `mysql8.0`, `postgres15`)

## Configuration

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `spec.family` | string | Database engine family (e.g., `mysql8.0`, `postgres15`, `mariadb10.6`, `oracle-ee-19`, `sqlserver-ex-15.0`). Immutable after creation. |
| `spec.description` | string | Human-readable description of the parameter group's purpose. |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `spec.parameterOverrides` | map | `{}` | Named engine parameters to customize (e.g., `max_connections: 500`). Parameter names are family-specific; invalid keys are rejected by the database engine. |
| `spec.nameOverride` | string | `""` | Explicitly set the parameter group name instead of using the naming template. |
| `spec.deletionPolicy` | string | `"retain"` | Deletion behavior: `"retain"` keeps the parameter group in AWS; `"delete"` removes it when the resource is deleted. |
| `spec.configRef` | string | `"general-policy"` | Reference to an `RDSConfig` profile by name. Falls back to `general-policy` if the profile does not exist. |
| `spec.tags` | map | `{}` | AWS tags to apply to the parameter group. Merged with tags from `RDSConfig`. |
| `spec.syncedLabels` | map | `{}` | Labels mirrored to both Kubernetes annotations and AWS tags. |
| `spec.syncedAnnotations` | map | `{}` | Annotations synced from `RDSConfig` and mirrored to AWS tags. |

## Status fields

| Field | Type | Description |
|-------|------|-------------|
| `status.resourceName` | string | The effective parameter group name in AWS (after applying naming template and lowercase conversion). |
| `status.namingStatus` | string | Naming resolution status: `"valid"` or `"invalid-unresolved-tokens"` if template tokens cannot be resolved. |
| `status.predictedArn` | string | The AWS ARN of the parameter group in the format `arn:aws:rds:<region>:<account>:pg:<resourceName>`. |
| `status.parameterOverrideStatuses` | array | Status of each parameter override, including `parameterName`, `parameterValue`, `applyStatus` (e.g., `pending-reboot`), and `applyMethod`. |
| `status.validationError` | string | Error message if the parameter group configuration is invalid and cannot be created. Empty if the resource is valid. |
| `status.conditions[]` | array | Standard Kubernetes conditions tracking resource state. |

## Naming convention

Parameter group names follow the naming template defined in your `RDSConfig` profile. The default template is `{namespace}-{name}`, which expands to namespace and resource name. Names are converted to lowercase and must use only letters, digits, and hyphens (1–255 characters).

Use `spec.nameOverride` to bypass the template and set an explicit name.

## Parameter override behavior

When you specify `spec.parameterOverrides`:

- Parameter names and values are family-specific — supplying an invalid key is accepted by the API but rejected by the database engine.
- Some parameters require a reboot to take effect. The `status.parameterOverrideStatuses` field shows which parameters have `applyStatus: pending-reboot`. Kropath does not trigger reboots; you must do this manually.
- If a parameter override is omitted, the database engine uses its default value for that family.

## Attaching parameter groups to instances

To use a parameter group, set its name in an `RDSInstance`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: web-db
  namespace: production
spec:
  family: mysql8.0
  engine: mysql8.0.39
  dbParameterGroupName: my-db-params  # Reference by name
  # ... other RDSInstance fields
```

## Example: Basic parameter group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSParameterGroup
metadata:
  name: orders-pg
  namespace: production
spec:
  family: postgres15
  description: Tuned parameter group for orders service
  parameterOverrides:
    max_connections: "200"
    shared_preload_libraries: "pg_stat_statements"
  tags:
    application: orders
    environment: production
```

## Example: Parameter group with pending-reboot parameters

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSParameterGroup
metadata:
  name: mysql-pool-tuning
  namespace: default
spec:
  family: mysql8.0
  description: MySQL connection pool tuning
  parameterOverrides:
    max_connections: "500"
    innodb_buffer_pool_size: "1073741824"  # 1 GB
    rds.force_ssl: "1"
  deletionPolicy: retain
```

To monitor which parameters require a reboot:

```bash
kubectl describe rdsparametergroup orders-pg -n production
```

Look for parameters with `applyStatus: pending-reboot` in the status output.

## Deletion behavior

- `deletionPolicy: "retain"` (default): The parameter group stays in AWS. Useful when the group may be reused or shared.
- `deletionPolicy: "delete"`: The parameter group is deleted from AWS when the resource is deleted.

Deletion requires that no instances or clusters are actively using the group.

## Cross-provider availability

`RDSParameterGroup` is AWS-only. GCP Cloud SQL and Azure Database do not have standalone parameter group resources; instead, database parameters are configured directly on the instance.

## Related resources

- [`RDSClusterParameterGroup`](./rdsclusterparametergroup.md) — For Aurora cluster-wide settings
- [`RDSInstance`](./rdsinstance.md) — Attaches a parameter group via `spec.dbParameterGroupName`
- [`RDSConfig`](./rdsconfig.md) — Defines naming templates and shared tags
