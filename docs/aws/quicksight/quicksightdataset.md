# QuickSightDataSet

`QuickSightDataSet` represents a structured data model in AWS QuickSight. A dataset is built on top of data sources, combining physical tables (from relational databases, custom SQL, S3, or SaaS platforms) with optional transformations and security rules. Datasets determine how data is imported (via SPICE caching or DIRECT_QUERY) and are consumed by dashboards and analyses.

## Scope

This resource is AWS-only. QuickSightDataSet wraps the AWS Cassandra Controller (ACK) QuickSight DataSet resource, managing data models and lifecycle.

## What it solves

Creating QuickSight datasets requires managing:

- **Data import modes** — choosing between SPICE (cached, cost-predictable) and DIRECT_QUERY (real-time, database-intensive)
- **Physical table definitions** — mapping database tables, custom SQL, or S3 data to the dataset
- **Column-level security** — restricting access to sensitive columns per user
- **Data transformations** — organizing and preparing data for analysis
- **Governance** — applying organizational naming, tagging, and import mode policies
- **SPICE capacity** — understanding and tracking cached data consumption

`QuickSightDataSet` provides a declarative way to define data models with built-in governance profiles and security controls.

## Core concepts

### Import modes

QuickSight supports two data loading strategies:

- **SPICE** (Spire Powered In-Cloud Engine): QuickSight imports and caches data in its high-performance store. Queries are fast, SPICE capacity is consumed, costs are predictable. Best for dashboards, published analyses, and most BI use cases.
- **DIRECT_QUERY**: Queries execute directly against the source database. No caching, lower latency for data updates, higher database load. Best for ad-hoc analysis, datasets accessed infrequently, or when real-time data is essential.

Most organizations default to SPICE and allow exceptions for specific use cases.

### Physical tables

A dataset combines one or more physical tables:

- **Relational tables**: Columns and data from a database table via QuickSightDataSource
- **Custom SQL**: Results of a SQL query (SELECT statement) against a data source
- **S3 source**: Direct CSV, JSON, or Parquet data from S3
- **SaaS tables**: Pre-configured connections (Salesforce, ServiceNow, etc.)

### Column-level security

Restrict access to sensitive columns (salary, SSN, email) per user via column-level permissions rules. Users see only the columns they're authorized for.

### Row-level security (RLS)

Create datasets marked with `useAs: "RLS_RULES"` to define row-level access policies. These datasets aren't analyzed directly; they're referenced by other datasets to filter rows based on user identity.

## Configuration fields

### Essential fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `resourceId` | string | required | Immutable unique identifier for this dataset (regex: `[\w\-]+`) |
| `physicalTableMap` | object | required | Map of physical tables (relational, customSQL, s3Source, or saaSTable) |

### Import mode and governance

| Field | Type | Default | Meaning |
|---|---|---|---|
| `importMode` | string | `""` (falls through to profile default) | `SPICE` or `DIRECT_QUERY`; empty = governed by QuickSightConfig profile |
| `configRef` | string | `general-policy` | Selects QuickSightConfig governance profile |

### Security

| Field | Type | Default | Meaning |
|---|---|---|---|
| `columnLevelPermissionRules` | []object | `[]` | Column access restrictions: `{columnNames: [list], principals: [list]}` |
| `useAs` | string | `""` | Set to `RLS_RULES` for row-level security datasets; omit for regular datasets |
| `permissions` | []object | `[]` | IAM resource permissions |

### Optional organization

| Field | Type | Default | Meaning |
|---|---|---|---|
| `columnGroups` | []object | `[]` | Geospatial or other column groupings |
| `fieldFolders` | map | `{}` | Organize columns into folders for UI display |
| `parameters` | []object | `[]` | Dataset parameters for dynamic queries |
| `performanceConfiguration` | object | nil | Performance hints (e.g., unique keys for optimization) |
| `usageConfiguration` | object | nil | Control usage as import/direct-query source |
| `folderARNs` | []string | `[]` | QuickSight folders to organize datasets |

### Governance and lifecycle

| Field | Type | Default | Meaning |
|---|---|---|---|
| `tags` | map | `{}` | Cloud tags (merged with profile tags) |
| `syncedLabels` | map | `{}` | Labels to sync to Kubernetes and cloud tags |
| `syncedAnnotations` | map | `{}` | Annotations to sync to Kubernetes metadata |
| `nameOverride` | string | `""` | Overrides naming template when set |
| `deletionPolicy` | string | `retain` | `retain` = keep dataset; `delete` = remove on CR deletion |

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: sales-metrics
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-metrics-ds
  importMode: ""  # Uses SPICE from general-policy profile
  physicalTableMap:
    orders:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/sales-db
        name: orders
        schema: public
        inputColumns:
          - name: order_id
            type: INTEGER
          - name: amount
            type: DECIMAL
          - name: customer_id
            type: INTEGER
  tags:
    team: analytics
    data-domain: sales
```

## Physical table examples

### Relational table from database

```yaml
spec:
  physicalTableMap:
    customers:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/postgres-db
        name: customers
        schema: public
        inputColumns:
          - name: customer_id
            type: INTEGER
          - name: name
            type: STRING
          - name: email
            type: STRING
```

### Custom SQL query

```yaml
spec:
  physicalTableMap:
    monthly_revenue:
      customSQL:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/redshift-db
        name: monthly_revenue_query
        sqlQuery: "SELECT DATE_TRUNC('month', order_date) AS month, SUM(amount) as revenue FROM orders GROUP BY DATE_TRUNC('month', order_date)"
        columns:
          - name: month
            type: DATETIME
          - name: revenue
            type: DECIMAL
```

### S3 data

```yaml
spec:
  physicalTableMap:
    events:
      s3Source:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/s3-analytics
        inputColumns:
          - name: event_id
            type: STRING
          - name: event_time
            type: DATETIME
          - name: user_id
            type: STRING
        uploadSettings:
          format: CSV
          containsHeader: true
```

## Import mode governance

QuickSightDataSet respects import mode governance from QuickSightConfig profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: realtime-dashboard-data
  namespace: analytics
spec:
  configRef: high-performance  # Profile enforces DIRECT_QUERY
  resourceId: realtime-data-ds
  importMode: ""  # Empty: governed by profile (forced to DIRECT_QUERY)
  physicalTableMap:
    live_orders:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/prod-db
        name: orders_live
        schema: public
```

With `high-performance` profile mandating `DIRECT_QUERY`, this dataset bypasses SPICE caching for real-time analysis.

## Column-level security

Restrict sensitive columns to authorized users:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: employee-data
  namespace: hr
spec:
  resourceId: employee-data-ds
  physicalTableMap:
    employees:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/hr-db
        name: employees
        schema: hr
  columnLevelPermissionRules:
    - columnNames:
        - salary
        - ssn
        - phone_number
      principals:
        - arn:aws:quicksight:us-east-1:123456789012:user/default/hr-manager
```

Employees outside the `hr-manager` group cannot see salary, SSN, or phone columns.

## Row-level security datasets

Create a dataset marked for RLS, used by other datasets to enforce row-level access:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: sales-rls-rules
  namespace: analytics
spec:
  resourceId: sales-rls-rules-ds
  useAs: "RLS_RULES"  # Mark for row-level security
  importMode: SPICE
  physicalTableMap:
    user_territory_map:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/sales-db
        name: user_sales_territory
        schema: security
```

Other datasets can reference this RLS dataset to filter rows per user's assigned territory.

## SPICE capacity

When using SPICE import mode, datasets consume SPICE storage. Monitor `status.consumedSpiceCapacityInBytes` to track usage. QuickSight accounts have a SPICE capacity limit; optimize large datasets with:

- Filtering irrelevant rows in custom SQL
- Selecting only required columns
- Using DIRECT_QUERY for very large, infrequently-accessed datasets

## Status outputs

When a QuickSightDataSet is deployed, its status includes:

- **`status.resourceName`**: The resolved display name in QuickSight
- **`status.consumedSpiceCapacityInBytes`**: SPICE storage used (0 if DIRECT_QUERY)
- **`status.predictedArn`**: The ARN of the created dataset

## Best practices

1. **Default to SPICE unless you need real-time.** SPICE is cost-predictable and performant. Use DIRECT_QUERY only when real-time updates are essential.

2. **Optimize physical tables for performance.** Use custom SQL to filter and pre-aggregate data rather than loading the full table.

3. **Apply column-level security from the start.** If sensitive columns exist, define access rules immediately — retrofitting is harder.

4. **Monitor SPICE usage.** Track `status.consumedSpiceCapacityInBytes` and alert when approaching account limits.

5. **Document physical table lineage.** Comment on the purpose of each physical table so analysts understand data provenance.

6. **Use consistent naming.** Name datasets for their primary use case (e.g., `sales-kpis`, `customer-360`, not `dataset-1`).

7. **Test with representative data.** Validate performance and SPICE consumption with realistic data volumes before production.

## Related resources

- **QuickSightConfig**: Governance profiles for import mode, naming, and tagging
- **QuickSightDataSource**: Data connections that feed datasets
- **QuickSightDashboard**: Published visualizations consuming datasets
- **QuickSightAnalysis**: Interactive authoring workspace consuming datasets

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `QuickSightDataSet`
- **Scope**: Namespaced
