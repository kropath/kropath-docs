---
title: QuickSightDashboard
description: "`QuickSightDashboard` represents a published, read-only collection of visualizations in AWS QuickSight."
doc_type: reference
---
# QuickSightDashboard

`QuickSightDashboard` represents a published, read-only collection of visualizations in AWS QuickSight. Dashboards are created from templates and are intended to be shared with end users for interactive analysis. Unlike analyses (which are editable authoring workspaces), dashboards are snapshot views that teams create once and share widely.

## Scope

This resource is AWS-only. QuickSightDashboard manages QuickSight Dashboard resources, handling dashboard creation and lifecycle.

## What it solves

Creating QuickSight dashboards declaratively enables:

- **Template-based creation** — define dashboards from existing templates with dataset mappings
- **Consistency** — apply organizational naming, tagging, and feature policies across dashboards
- **Feature control** — manage 13 dashboard feature toggles (export, drill-down, tooltips, etc.)
- **Sharing and permissions** — control dashboard access and link-sharing at the resource level
- **Versioning** — track dashboard versions and descriptions for audit trails

`QuickSightDashboard` provides infrastructure-as-code deployment of dashboards, eliminating manual console creation.

## Core concepts

### Template-based creation

Dashboards are created from existing QuickSight templates that define the visual structure. You map your datasets to template placeholders, and QuickSight creates the dashboard with those datasets connected.

### Publishing options

Dashboards support 13 feature toggles controlling end-user capabilities:

| Toggle | Controls |
|---|---|
| `adHocFilteringOption` | Filter pane visibility and usability |
| `exportToCSVOption` | Export data to CSV |
| `dataPointDrillUpDownOption` | Drill up/down on data points |
| `dataPointTooltipOption` | Hover tooltips on data points |
| `dataPointMenuLabelOption` | Context menu on data points |
| `sheetControlsOption` | Sheet-level controls (filters, parameters) |
| `sheetLayoutElementMaximizationOption` | Maximize/minimize chart sizes |
| `visualAxisSortOption` | Sort axes in visualizations |
| `exportWithHiddenFieldsOption` | Include hidden columns in CSV export |
| `dataQAEnabledOption` | Enable Q&A/natural language queries |
| `dataStoriesSharingOption` | Share data stories / narratives |
| `executiveSummaryOption` | Executive summary building |
| `quickSuiteActionsOption` | Quick Suite automation actions |

### Dashboard vs. Analysis

- **Dashboard**: Published, read-only snapshot shared with end users. Created once from a template, viewed and filtered but not edited by most users.
- **Analysis**: Editable authoring workspace where analysts create and refine visualizations before publishing to a dashboard.

## Configuration fields

### Essential fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `resourceId` | string | required | Immutable unique identifier for this dashboard (regex: `[\w\-]+`) |
| `sourceEntity` | object | required | Template reference: `{sourceTemplate: {arn: string, dataSetReferences: [...]}}` |

### Publishing options

| Field | Type | Default | Meaning |
|---|---|---|---|
| `publishOptions` | object | nil | Feature toggles (13 optional sub-fields, each with `availabilityStatus: ENABLED\|DISABLED`) |

### Optional customization

| Field | Type | Default | Meaning |
|---|---|---|---|
| `versionDescription` | string | `""` | Description for this dashboard version |
| `parameters` | object | nil | Parameter overrides for dashboard creation |
| `linkEntities` | []string | `[]` | Analysis ARNs to link to dashboard |
| `linkSharingConfiguration` | object | nil | Shareable link permissions |
| `validationStrategy` | object | nil | Relaxes definition validation for minor schema differences |

### Governance and lifecycle

| Field | Type | Default | Meaning |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects QuickSightConfig governance profile |
| `tags` | map | `{}` | Cloud tags (merged with profile tags) |
| `syncedLabels` | map | `{}` | Labels to sync to Kubernetes and cloud tags |
| `syncedAnnotations` | map | `{}` | Annotations to sync to Kubernetes metadata |
| `nameOverride` | string | `""` | Overrides naming template when set |
| `deletionPolicy` | string | `retain` | `retain` = keep dashboard; `delete` = remove on CR deletion |
| `permissions` | []object | `[]` | IAM resource permissions |
| `folderARNs` | []string | `[]` | QuickSight folders to organize dashboards. **Immutable after dashboard creation.** |

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDashboard
metadata:
  name: sales-executive-dashboard
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-exec-dash
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/executive-sales-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/sales-metrics-ds
          dataSetPlaceholder: SalesMetricsDataSet
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/forecast-ds
          dataSetPlaceholder: ForecastDataSet
  publishOptions:
    exportToCSVOption:
      availabilityStatus: ENABLED
    adHocFilteringOption:
      availabilityStatus: ENABLED
    dataPointTooltipOption:
      availabilityStatus: ENABLED
  versionDescription: "Q4 sales metrics dashboard - Initial release"
  tags:
    team: sales
    audience: executives
```

In this example:
- Dashboard is created from an executive sales template
- Two datasets are mapped to template placeholders
- CSV export and ad-hoc filtering are enabled
- Other features default to their QuickSight defaults (typically enabled)

## Feature toggle examples

### All features disabled (read-only dashboard)

```yaml
spec:
  publishOptions:
    adHocFilteringOption:
      availabilityStatus: DISABLED
    exportToCSVOption:
      availabilityStatus: DISABLED
    dataPointDrillUpDownOption:
      availabilityStatus: DISABLED
    dataPointTooltipOption:
      availabilityStatus: DISABLED
    sheetControlsOption:
      availabilityStatus: DISABLED
```

This creates a completely read-only dashboard where users can only view visualizations.

### Partial feature set

```yaml
spec:
  publishOptions:
    exportToCSVOption:
      availabilityStatus: ENABLED
    adHocFilteringOption:
      availabilityStatus: ENABLED
    dataQAEnabledOption:
      availabilityStatus: ENABLED
```

Only CSV export, filtering, and Q&A are enabled; other features default to QuickSight's defaults.

### Feature not specified

If you omit a toggle from `publishOptions`, QuickSight uses its default (typically `ENABLED`). To guarantee a feature is disabled, explicitly set `availabilityStatus: DISABLED`.

## Governance and naming

`QuickSightDashboard` respects naming and tagging governance from `QuickSightConfig` profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDashboard
metadata:
  name: compliance-dashboard
  namespace: regulated
spec:
  configRef: compliance  # Use compliance profile
  resourceId: compliance-dash
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/compliance-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/compliance-data
          dataSetPlaceholder: ComplianceData
```

With the `compliance` profile, this dashboard automatically inherits compliance-required tags and naming conventions.

## Deletion policy

Control cleanup when the Kubernetes resource is deleted:

- **`retain`** (default): Dashboard remains in QuickSight (safe, requires manual cleanup)
- **`delete`**: Dashboard is automatically removed from QuickSight (use with caution)

## Status outputs

When a QuickSightDashboard is deployed, its status includes:

- **`status.resourceName`**: The resolved display name in QuickSight
- **`status.creationStatus`**: Dashboard creation state
- **`status.versionNumber`**: Current version number
- **`status.versionStatus`**: Version status (`CREATION_IN_PROGRESS`, `CREATION_SUCCESSFUL`, etc.)
- **`status.predictedArn`**: The ARN of the created dashboard

## Best practices

1. **Use templates for consistency.** Create organization-approved templates and reference them across dashboards to ensure consistent look and feel.

2. **Restrict features based on audience.** For executive dashboards, consider disabling drill-down and other advanced features to keep focus on KPIs.

3. **Enable CSV export selectively.** Allow power users to export but disable for read-only dashboards to control data distribution.

4. **Document feature policies in governance profiles.** Set default `publishOptions` in QuickSightConfig so teams don't have to repeat feature configuration.

5. **Version your dashboards.** Use `versionDescription` to track changes and improvements over time.

6. **Name dashboards for their primary audience.** Use names like `executive-kpis`, `sales-pipeline`, `support-metrics` instead of generic names.

7. **Test with end users.** Before production, validate that your feature toggle choices and dataset mappings work for the intended audience.

8. **Use folderARNs to organize dashboards.** Organize dashboards into logical folders so teams can find related dashboards easily.

## Related resources

- **QuickSightConfig**: Governance profiles for naming, tagging, and feature policies
- **QuickSightDataSet**: Datasets that provide data to dashboard visualizations
- **QuickSightAnalysis**: Editable workspace for creating dashboards
- **QuickSightDataSource**: Data connections that feed datasets

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `QuickSightDashboard`
- **Scope**: Namespaced
