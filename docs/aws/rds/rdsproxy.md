# RDSProxy

`RDSProxy` creates an RDS Proxy — a managed connection pooling proxy that sits between your applications and RDS instances or Aurora clusters. A proxy bounds connection churn from high-concurrency or serverless clients and shortens failover impact by pooling and reusing database connections.

## When to use

Use `RDSProxy` when your workload has:

- High concurrency or many short-lived connections (serverless functions, Lambda)
- Connection storms during scaling events
- Need to enforce TLS encryption at the proxy layer
- Desire to centralize authentication via AWS Secrets Manager

## Prerequisites

- One or more RDS instances or Aurora clusters to attach as targets (see Limitations below)
- A VPC with at least two subnets spanning different availability zones
- A Secrets Manager secret containing database credentials with `username` and `password` keys
- An optional IAM role granting the proxy permission to read Secrets Manager secrets

## Configuration

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `spec.engineFamily` | string | Database engine family: `MYSQL` or `POSTGRESQL`. Immutable after creation. |
| `spec.vpcSubnetIDs` | array | List of VPC subnet IDs for the proxy (minimum 1; recommendation: 2+ across AZs). |
| `spec.auth[]` | array | At least one authentication entry (see Auth configuration below). |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `spec.vpcSecurityGroupIDs` | array | `[]` | Security groups controlling proxy network access. |
| `spec.roleARN` | string | `""` | IAM role ARN granting the proxy Secrets Manager read access. Required if using Secrets Manager. |
| `spec.requireTLS` | boolean | `false` | Enforce TLS for client connections to the proxy. |
| `spec.idleClientTimeout` | integer | `1800` | Seconds of inactivity before the proxy closes an idle client connection. |
| `spec.debugLogging` | boolean | `false` | Enable debug logging (verbose; use only for troubleshooting). |
| `spec.nameOverride` | string | `""` | Explicitly set the proxy name instead of using the naming template. |
| `spec.deletionPolicy` | string | `"retain"` | Deletion behavior: `"retain"` keeps the proxy in AWS; `"delete"` removes it when the resource is deleted. |
| `spec.configRef` | string | `"general-policy"` | Reference to an `RDSConfig` profile by name. Falls back to `general-policy` if the profile does not exist. |
| `spec.tags` | map | `{}` | AWS tags to apply to the proxy. Merged with tags from `RDSConfig`. |
| `spec.syncedLabels` | map | `{}` | Labels mirrored to both Kubernetes annotations and AWS tags. |
| `spec.syncedAnnotations` | map | `{}` | Annotations synced from `RDSConfig` and mirrored to AWS tags. |

### Auth configuration

Each entry in `spec.auth[]` must define:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `authScheme` | string | `"SECRETS"` | Authentication type: `"SECRETS"` (Secrets Manager-backed). |
| `secretARN` | string | *required* | AWS Secrets Manager ARN containing database credentials. Required — enforced via `status.validationError` at reconcile time, not rejected at admission. |
| `iamAuth` | string | `"DISABLED"` | IAM database authentication: `"DISABLED"`, `"ENABLED"`, or `"REQUIRED"`. |
| `clientPasswordAuthType` | string | `""` | Password authentication type for specific engines: `MYSQL_NATIVE_PASSWORD`, `POSTGRES_SCRAM_SHA_256`, or `POSTGRES_MD5`. Omit for engine defaults. |

## Status fields

| Field | Type | Description |
|-------|------|-------------|
| `status.resourceName` | string | The effective proxy name in AWS (after applying naming template and lowercase conversion). |
| `status.namingStatus` | string | Naming resolution status: `"valid"` or `"invalid-unresolved-tokens"`. |
| `status.proxyArn` | string | The AWS ARN of the proxy. **Empty until the proxy reaches `proxyStatus: available`.** |
| `status.endpoint` | string | The DNS endpoint clients connect to. **Empty until the proxy reaches `proxyStatus: available`.** |
| `status.proxyStatus` | string | Proxy lifecycle state: `available`, `creating`, `modifying`, `deleting`, `incompatible-network`, etc. |
| `status.vpcID` | string | The VPC the proxy was deployed into. |
| `status.validationError` | string | Error message if the proxy configuration is invalid and cannot be created. Empty if the resource is valid. |
| `status.conditions[]` | array | Standard Kubernetes conditions tracking resource state. |

## Naming convention

Proxy names follow the naming template defined in your `RDSConfig` profile. The default template is `{namespace}-{name}`. Names are converted to lowercase and must use only letters, digits, and hyphens.

**Important:** Proxy names are **account-scoped unique**. Two clusters in different namespaces but the same AWS account using identical naming templates will collide. If you run multi-cluster on one account, use a naming template that includes `{region}` or cluster-specific tag tokens.

Use `spec.nameOverride` to bypass the template and set an explicit name.

## Lifecycle and ARN behavior

A proxy undergoes a creation sequence:

1. State: `creating` — ARN and endpoint are **empty** and unavailable
2. State: `available` — ARN and endpoint populate in status

**Never rely on `status.proxyArn` immediately after creation.** Always wait for `status.proxyStatus: available` before using the proxy endpoint.

The endpoint follows the format: `<proxy-name>.proxy-<id>.<region>.rds.amazonaws.com`.

## Attaching targets

`RDSProxy` currently does not support attaching instances or clusters through Kubernetes resources. Target registration is a manual step:

1. Create the proxy with `RDSProxy`
2. Wait for `status.proxyStatus: available`
3. Use the AWS console or CLI to attach RDS instances or Aurora clusters to the proxy via `DBProxyTargetGroup`

Target attachment is tracked as a future enhancement.

## Secrets Manager setup

The Secrets Manager secret referenced in `spec.auth[].secretARN` must contain:

```json
{
  "username": "admin",
  "password": "your-password"
}
```

Kropath does not create or validate this secret — it must exist before the proxy is created. The proxy will fail to become available if the secret does not exist or the IAM role lacks read access.

## Example: Basic MySQL proxy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSProxy
metadata:
  name: mysql-pool
  namespace: production
spec:
  engineFamily: MYSQL
  vpcSubnetIDs:
    - subnet-1a
    - subnet-1b
  auth:
    - secretARN: arn:aws:secretsmanager:us-east-1:111122223333:secret:db-creds
  tags:
    application: web-api
    environment: production
```

## Example: PostgreSQL proxy with TLS enforcement

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSProxy
metadata:
  name: postgres-secure-pool
  namespace: production
spec:
  engineFamily: POSTGRESQL
  vpcSubnetIDs:
    - subnet-prod-1
    - subnet-prod-2
  vpcSecurityGroupIDs:
    - sg-proxy-allow
  roleARN: arn:aws:iam::111122223333:role/proxy-secrets-role
  auth:
    - secretARN: arn:aws:secretsmanager:us-east-1:111122223333:secret:postgres-prod
      iamAuth: ENABLED
      clientPasswordAuthType: POSTGRES_SCRAM_SHA_256
  requireTLS: true
  debugLogging: false
  idleClientTimeout: 900
  deletionPolicy: retain
```

## Monitoring proxy creation

Check proxy status:

```bash
kubectl get rdsproxy -n production
kubectl describe rdsproxy mysql-pool -n production
```

Wait for the status to show:

```
status.proxyStatus: available
status.endpoint: mysql-pool.proxy-abc123.us-east-1.rds.amazonaws.com
status.proxyArn: arn:aws:rds:us-east-1:111122223333:db-proxy:prx-0abc123
```

## Deletion behavior

- `deletionPolicy: "retain"` (default): The proxy stays in AWS. Useful for long-lived pooling infrastructure.
- `deletionPolicy: "delete"`: The proxy is deleted from AWS when the resource is deleted.

Deletion requires that all attached targets are detached first.

## Limitations and notes

- **No target group support yet**: Use the AWS console or CLI to attach instances/clusters to the proxy.
- **Network requirements**: Subnets must span at least two availability zones for high availability.
- **Slow creation**: Proxy provisioning typically takes several minutes. Networking incompatibilities (subnets in same AZ, security group blocking) may prevent creation.
- **Secrets format**: The Secrets Manager secret must contain `username` and `password` keys in the exact format RDS Proxy expects.

## Cross-provider availability

`RDSProxy` is AWS-only. GCP uses the Cloud SQL Auth Proxy (a client-side sidecar); Azure has no native equivalent and uses PgBouncer or application-layer pooling.

## Related resources

- [`RDSConfig`](./rdsconfig.md) — Defines naming templates and shared tags
- [`RDSInstance`](./rdsinstance.md) — Attach as proxy target (manual step)
- [`RDSCluster`](./rdscluster.md) — Attach as proxy target (manual step)
