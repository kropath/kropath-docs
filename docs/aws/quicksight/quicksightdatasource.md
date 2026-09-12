# QuickSightDataSource

`QuickSightDataSource` represents a connection to an external data system for AWS QuickSight. A data source defines how QuickSight connects to your data (Redshift, Athena, S3, RDS, or other supported databases), providing credentials, connection parameters, and VPC networking configuration.

## Scope

This resource is AWS-only. QuickSightDataSource wraps the AWS Cassandra Controller (ACK) QuickSight DataSource resource, managing connection details and lifecycle.

## What it solves

Creating QuickSight data sources requires managing:

- **Connection credentials** — storing database connection secrets securely
- **Connection types** — specifying which data system QuickSight connects to (Redshift, Athena, S3, etc.)
- **VPC connectivity** — routing QuickSight to databases in private VPCs
- **Consistency** — applying naming conventions, tags, and policy settings across data sources
- **Lifecycle** — controlling whether deleted data sources are retained or removed

`QuickSightDataSource` provides a declarative way to define data connections, with built-in support for governance profiles, standard naming, tagging, and deletion policies.

## Core concepts

### Data source types

QuickSight supports connections to various data sources:

- **Redshift**: AWS managed data warehouse
- **Athena**: SQL queries on S3 data
- **S3**: Direct S3 bucket access
- **RDS**: MySQL, PostgreSQL, or other RDS databases
- **And others**: Snowflake, DataBrew, Salesforce, ServiceNow, etc.

Each type requires specific parameters (database name, table schema, S3 bucket path, etc.).

### Credentials and secrets

QuickSight data sources can use several credential types:

- **Secret ARN**: Reference an AWS Secrets Manager secret directly
- **Credential pair**: Username and password (stored in the secret referenced by the DataSource)
- **VPC connection**: For private database access, pair with a VPC Connection resource

### Naming and resource identity

QuickSight resources have two identifiers:

- **Display name** (`effectiveName`): Mutable, user-facing name in the QuickSight console
- **Resource ID** (`spec.resourceId`): Immutable unique identifier used in ARNs, cannot be changed after creation

## Configuration fields

### Essential fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `resourceId` | string | required | Immutable unique identifier for this data source (regex: `[\w\-]+`) |
| `type` | string | required | Data source type: `REDSHIFT`, `S3`, `ATHENA`, `MYSQL`, `POSTGRESQL`, etc. |
| `parameters` | object | required | Connection parameters specific to the source type (e.g., cluster ID for Redshift, bucket name for S3) |

### Optional connectivity

| Field | Type | Default | Meaning |
|---|---|---|---|
| `credentials` | object | nil | Connection credentials: secret ARN, credential pair, or key pair credentials |
| `vpcConnectionProperties` | object | nil | VPC Connection ARN for private database access |
| `sslProperties` | object | nil | SSL/TLS configuration (e.g., `{disableSSL: false}`) |

### Governance and lifecycle

| Field | Type | Default | Meaning |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects QuickSightConfig governance profile |
| `tags` | map | `{}` | Cloud tags (merged with config profile tags) |
| `syncedLabels` | map | `{}` | Labels to sync to Kubernetes and cloud tags |
| `syncedAnnotations` | map | `{}` | Annotations to sync to Kubernetes metadata |
| `nameOverride` | string | `""` | Overrides naming template when set |
| `deletionPolicy` | string | `retain` | `retain` = keep data source in QuickSight; `delete` = remove on CR deletion |
| `permissions` | []object | `[]` | IAM resource permissions (instance-level, not governed) |
| `folderARNs` | []string | `[]` | Folder ARNs to assign resource to |

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSource
metadata:
  name: sales-redshift
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-redshift-ds
  type: REDSHIFT
  parameters:
    redshiftParameters:
      clusterID: my-redshift-cluster
      database: analytics
      port: 5439
  credentials:
    secretARN: arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift-creds
  tags:
    team: analytics
    data-type: warehouse
```

In this example:
- Data source ID is `sales-redshift-ds` (immutable)
- Display name is derived from the CR name and namespace (e.g., `analytics-sales-redshift`)
- Connects to a Redshift cluster with credentials stored in Secrets Manager
- Uses the `general-policy` governance profile for naming and tagging
- Applies additional team-specific tags

## Parameter examples

### Redshift

```yaml
spec:
  type: REDSHIFT
  parameters:
    redshiftParameters:
      clusterID: my-cluster
      database: analytics
      port: 5439
```

### Athena

```yaml
spec:
  type: ATHENA
  parameters:
    athenaParameters:
      workGroup: primary
```

### S3

```yaml
spec:
  type: S3
  parameters:
    s3Parameters:
      manifestFileLocation:
        bucket: my-bucket
        key: manifest.json
```

### RDS (PostgreSQL)

```yaml
spec:
  type: POSTGRESQL
  parameters:
    postgresqlParameters:
      host: my-database.c123456.us-east-1.rds.amazonaws.com
      port: 5432
      database: mydb
```

## Governance and profiles

QuickSightDataSource resources use `QuickSightConfig` governance profiles for:

- **Naming**: Automatic naming via `namingTemplate` (default: `{namespace}-{name}`)
- **Tags**: Merging mandatory, default, and instance-level tags
- **Synced labels**: Propagating tags to both Kubernetes and QuickSight
- **Synced annotations**: Propagating annotations to Kubernetes metadata

Example with profile override:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSource
metadata:
  name: compliance-warehouse
  namespace: regulated
spec:
  configRef: compliance  # Use compliance profile
  resourceId: compliance-warehouse-ds
  type: REDSHIFT
  parameters:
    redshiftParameters:
      clusterID: compliance-cluster
      database: compliant_data
      port: 5439
```

With the `compliance` profile enforcing specific tags and naming templates, this data source automatically inherits compliance-required settings.

## VPC connectivity

For databases in private VPCs, create a VPC Connection in QuickSight first, then reference it:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSource
metadata:
  name: private-database
  namespace: analytics
spec:
  resourceId: private-db-ds
  type: POSTGRESQL
  parameters:
    postgresqlParameters:
      host: internal-postgres.example.com
      port: 5432
      database: private_data
  vpcConnectionProperties:
    vpcConnectionARN: arn:aws:quicksight:us-east-1:123456789012:vpcConnection/vpc-conn-1
  credentials:
    secretARN: arn:aws:secretsmanager:us-east-1:123456789012:secret:postgres-creds
```

## Deletion policy

The `deletionPolicy` field controls cleanup when the Kubernetes resource is deleted:

- **`retain`** (default): The QuickSight data source remains in your account (safe default, manual cleanup)
- **`delete`**: The QuickSight data source is automatically deleted (use with caution)

```yaml
spec:
  deletionPolicy: delete  # Automatically delete from QuickSight
```

## Status outputs

When a QuickSightDataSource is deployed, its status includes:

- **`status.resourceName`**: The resolved display name in QuickSight
- **`status.connectionStatus`**: Current connection state (`CREATION_IN_PROGRESS`, `CREATION_SUCCESSFUL`, etc.)
- **`status.predictedArn`**: The ARN of the created data source

## Best practices

1. **Use Secrets Manager for credentials.** Store database credentials in AWS Secrets Manager and reference them via `secretARN` rather than embedding credentials.

2. **Validate connection parameters** before deploying. Use your cloud provider's CLI to verify connection details (e.g., `psql` for PostgreSQL, `redshift-cli` for Redshift).

3. **Name data sources for their purpose.** Use resource IDs like `sales-warehouse`, `analytics-s3-export`, not generic names like `ds-1`.

4. **Test connectivity in non-production first.** Deploy data sources to a staging QuickSight account before production to validate parameter and permission configuration.

5. **Document parameter differences.** Each data source type has unique parameters; document your organization's standard parameters in your governance profile or runbooks.

6. **Use VPC connections for private databases.** For databases in private VPCs, always set up and test VPC Connections before creating data sources.

7. **Restrict data source permissions.** Use the `permissions` field to limit which users can modify or analyze data from this source.

## Related resources

- **QuickSightConfig**: Governance profiles for naming, tagging, and policy
- **QuickSightDataSet**: Models built on data sources (used by dashboards and analyses)
- **QuickSightDashboard**: Published visualizations consuming datasets
- **QuickSightAnalysis**: Interactive authoring workspace

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `QuickSightDataSource`
- **Scope**: Namespaced
