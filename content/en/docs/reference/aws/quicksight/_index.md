---
title: AWS QuickSight Resources
description: AWS QuickSight is a cloud-based business intelligence (BI) service that makes it easy to build visualizations, conduct ad hoc analyses, and get business insights.
doc_type: reference
weight: 410
---
# AWS QuickSight Resources

AWS QuickSight is a cloud-based business intelligence (BI) service that makes it easy to build visualizations, conduct ad hoc analyses, and get business insights. kropath provides Kubernetes native resources for managing QuickSight configurations, data sources, datasets, dashboards, and analyses.

## Resource overview

QuickSight resources in kropath are organized into two categories:

### Governance

**[QuickSightConfig](quicksightconfig.md)** — Governance profiles for QuickSight resources

Define mandatory and default policies for naming, tagging, import modes, and synced labels. Create named profiles (`general-policy`, `compliance`, `high-performance`) that apply consistent governance across all QuickSight resources in your cluster.

### Data and visualization resources

**[QuickSightDataSource](quicksightdatasource.md)** — Connections to external data systems

Define connections to databases (Redshift, Athena, RDS, S3, Snowflake, etc.) with credentials, VPC networking, and SSL configuration.

**[QuickSightDataSet](quicksightdataset.md)** — Structured data models

Build data models from physical tables (relational, custom SQL, S3, SaaS) with import mode governance (SPICE vs. DIRECT_QUERY), column-level security, and row-level security support.

**[QuickSightDashboard](quicksightdashboard.md)** — Published visualizations

Create read-only dashboards from templates for end-user consumption. Control 13 feature toggles (export, drill-down, Q&A, etc.) and manage permissions and versioning.

**[QuickSightAnalysis](quicksightanalysis.md)** — Editable analysis workspaces

Provision interactive analysis workspaces for data exploration and visualization authoring. Apply themes and governance before publishing as dashboards.

## Typical workflow

1. **Set up governance** — Deploy QuickSightConfig profiles (`general-policy`, `high-performance`, `compliance`) to define organizational policies
2. **Connect data sources** — Create QuickSightDataSource resources for your databases
3. **Build datasets** — Create QuickSightDataSet resources that model your data with import modes and security rules
4. **Create analysis workspaces** — Deploy QuickSightAnalysis resources for teams to explore and build visualizations
5. **Publish dashboards** — Once analyses are finalized, create QuickSightDashboard resources to publish read-only views for end users

## Core concepts

### Import modes

QuickSight supports two data loading strategies:

- **SPICE** (Super-fast, Parallel, In-memory Calculation Engine): Cached, high-performance, cost-predictable. Default for dashboards and published analyses.
- **DIRECT_QUERY**: Real-time queries against source databases. Best for ad-hoc analysis and real-time data.

Import mode can be governed via QuickSightConfig profiles so your organization can enforce consistent strategies.

### Governance cascade

QuickSightConfig provides a two-tier governance model:

1. **Mandatory fields** override instance specifications (useful for compliance)
2. **Defaults fields** apply when instances don't specify a value (useful for convenience)

Mandatory wins over defaults. Both merge with organization-wide KropathConfig settings.

### Naming and resource identity

QuickSight resources have two identifiers:

- **Display name** (`effectiveName`): Mutable, user-facing name shown in the QuickSight console
- **Resource ID** (`resourceId`): Immutable unique identifier used in ARNs and cannot be changed after creation

### Tagging and synced labels

Tags and synced labels flow through the governance cascade:

1. Organization-wide tags (KropathConfig)
2. Profile-level mandatory and default tags (QuickSightConfig)
3. Instance-level tags (individual resource specs)

Tags at all levels are merged, with mandatory taking precedence on key conflict.

## Getting started

Create a simple multi-resource example:

```yaml
---
# Governance profile
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

---
# Data source
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSource
metadata:
  name: sales-db
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-db-ds
  type: REDSHIFT
  parameters:
    redshiftParameters:
      clusterID: my-cluster
      database: sales
      port: 5439

---
# Dataset
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: sales-metrics
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-metrics-ds
  physicalTableMap:
    orders:
      relationalTable:
        dataSourceARN: arn:aws:quicksight:us-east-1:123456789012:datasource/sales-db
        name: orders
        schema: public

---
# Dashboard
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDashboard
metadata:
  name: sales-kpis
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-kpis-dash
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/kpi-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/sales-metrics-ds
          dataSetPlaceholder: SalesMetrics
```

## Best practices

1. **Create governance profiles for organizational postures.** Use `general-policy` as the sensible default; create specialized profiles (`compliance`, `high-performance`) only when needed.

2. **Default to SPICE unless you need real-time.** SPICE is cost-predictable and performant. Use DIRECT_QUERY for specific use cases.

3. **Use templates for consistency.** Create organization-approved templates for common dashboard and analysis patterns to ensure consistency.

4. **Apply governance from the start.** Define QuickSightConfig profiles before creating resources so governance is automatic.

5. **Document naming conventions.** Use clear, consistent resource IDs (e.g., `sales-warehouse-ds`, `customer-360-dataset`) so resources are discoverable.

6. **Monitor SPICE usage.** Track SPICE capacity consumption to avoid hitting account limits unexpectedly.

7. **Test permission and security rules.** Column-level and row-level security rules should be validated with representative users before production.

## Related documentation

- [AWS QuickSight documentation](https://docs.aws.amazon.com/quicksight/)
- Governance: See [QuickSightConfig](quicksightconfig.md) for governance profiles
- Data connections: See [QuickSightDataSource](quicksightdatasource.md) for credential and connectivity options
