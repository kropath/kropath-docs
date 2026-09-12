# QuickSightAnalysis

`QuickSightAnalysis` represents an editable, interactive analysis workspace in AWS QuickSight. Unlike dashboards (published, read-only snapshots), analyses are working spaces where analysts create, experiment with, and refine visualizations before publishing them as dashboards for broader consumption.

## Scope

This resource is AWS-only. QuickSightAnalysis manages QuickSight Analysis resources, handling analysis creation and lifecycle.

## What it solves

Creating QuickSight analyses declaratively enables:

- **Infrastructure-as-code analysis deployment** — define analysis workspaces via Kubernetes CRs instead of manual console creation
- **Template-based setup** — accelerate analysis creation by starting from an organization template
- **Theme consistency** — apply corporate themes to analyses automatically
- **Governance** — apply organizational naming, tagging, and permission policies
- **Reproducibility** — recreate analysis workspaces using version-controlled YAML definitions

`QuickSightAnalysis` provides a way to provision analysis workspaces at scale, useful for:

- Creating team-specific analysis workspaces (sales team analysis, marketing team analysis)
- Onboarding new analysts with pre-configured analysis environments
- Supporting analysis work without requiring direct AWS console access

## Core concepts

### Analysis as authoring workspace

An analysis is an editable, interactive workspace where analysts:

- Create and modify visualizations
- Connect to datasets and explore data
- Experiment with filters, parameters, and calculations
- Collaborate on analysis design

Once satisfied, analysts typically publish the analysis as a dashboard for end-user consumption.

### Analysis vs. Dashboard distinction

| Aspect | Analysis | Dashboard |
|---|---|---|
| **Mutability** | Editable by authorized users | Read-only snapshot |
| **Purpose** | Authoring and exploration | Publishing and sharing |
| **Audience** | Analysts, data professionals | End users, executives |
| **Update frequency** | Ongoing refinement | Published versions |
| **Creation** | Can be standalone or template-based | Created from templates |

### Themes

Analyses can apply a QuickSight theme (custom branding, colors, typography) by ARN. Themes must be pre-created in QuickSight; this resource only references them.

## Configuration fields

### Essential fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `resourceId` | string | required | Immutable unique identifier for this analysis (regex: `[\w\-]+`) |
| `sourceEntity` | object | required | Template reference: `{sourceTemplate: {arn: string, dataSetReferences: [...]}}` |

### Visual customization

| Field | Type | Default | Meaning |
|---|---|---|---|
| `themeARN` | string | `""` | ARN of a QuickSight theme to apply (empty = use QuickSight default theme) |

### Optional parameters

| Field | Type | Default | Meaning |
|---|---|---|---|
| `parameters` | object | nil | Parameter override values for analysis creation |
| `validationStrategy` | object | nil | Relaxes definition validation for minor schema differences |

### Governance and lifecycle

| Field | Type | Default | Meaning |
|---|---|---|---|
| `configRef` | string | `general-policy` | Selects QuickSightConfig governance profile |
| `tags` | map | `{}` | Cloud tags (merged with profile tags) |
| `syncedLabels` | map | `{}` | Labels to sync to Kubernetes and cloud tags |
| `syncedAnnotations` | map | `{}` | Annotations to sync to Kubernetes metadata |
| `nameOverride` | string | `""` | Overrides naming template when set |
| `deletionPolicy` | string | `retain` | `retain` = keep analysis; `delete` = remove on CR deletion |
| `permissions` | []object | `[]` | IAM resource permissions |
| `folderARNs` | []string | `[]` | QuickSight folders to organize analyses |

## Complete example

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightAnalysis
metadata:
  name: sales-exploration
  namespace: analytics
spec:
  configRef: general-policy
  resourceId: sales-exploration-ws
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/analyst-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/sales-metrics-ds
          dataSetPlaceholder: SalesMetrics
  themeARN: arn:aws:quicksight:us-east-1:123456789012:theme/corporate-brand
  tags:
    team: sales
    purpose: ad-hoc-analysis
```

In this example:
- Analysis is created from an analyst template
- Sales metrics dataset is mapped to the template
- Corporate brand theme is applied
- Display name is derived from CR name and namespace (e.g., `analytics-sales-exploration`)

## Themed analysis

Apply a pre-created QuickSight theme to maintain consistent branding:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightAnalysis
metadata:
  name: finance-analysis
  namespace: analytics
spec:
  resourceId: finance-analysis-ws
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/finance-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/financial-data-ds
          dataSetPlaceholder: FinancialData
  themeARN: arn:aws:quicksight:us-east-1:123456789012:theme/finance-branding
```

The `finance-branding` theme (colors, fonts, logos) is automatically applied when the analysis loads.

## Analysis without theme

If no custom theme is needed, omit `themeARN`:

```yaml
spec:
  resourceId: product-analysis-ws
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/product-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/product-data-ds
          dataSetPlaceholder: ProductData
  # No themeARN: uses QuickSight default theme
```

## Governance and naming

`QuickSightAnalysis` respects naming and tagging governance from `QuickSightConfig` profiles:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightAnalysis
metadata:
  name: compliance-analysis
  namespace: regulated
spec:
  configRef: compliance  # Use compliance profile
  resourceId: compliance-analysis-ws
  sourceEntity:
    sourceTemplate:
      arn: arn:aws:quicksight:us-east-1:123456789012:template/audit-template
      dataSetReferences:
        - dataSetARN: arn:aws:quicksight:us-east-1:123456789012:dataset/compliance-data
          dataSetPlaceholder: ComplianceData
```

With the `compliance` profile, this analysis automatically inherits compliance-required tags and naming conventions.

## Permissions and sharing

Control who can edit and view the analysis:

```yaml
spec:
  permissions:
    - actions:
        - quicksight:UpdateAnalysis
        - quicksight:DescribeAnalysis
      principal: arn:aws:quicksight:us-east-1:123456789012:group/default/analysts
    - actions:
        - quicksight:DescribeAnalysis
      principal: arn:aws:quicksight:us-east-1:123456789012:group/default/managers
```

Analysts can edit the analysis; managers can view it.

## Deletion policy

Control cleanup when the Kubernetes resource is deleted:

- **`retain`** (default): Analysis remains in QuickSight (safe, requires manual cleanup)
- **`delete`**: Analysis is automatically removed from QuickSight (use with caution)

## Status outputs

When a QuickSightAnalysis is deployed, its status includes:

- **`status.resourceName`**: The resolved display name in QuickSight
- **`status.analysisStatus`**: Current analysis state (`CREATION_IN_PROGRESS`, `CREATION_SUCCESSFUL`, etc.)
- **`status.predictedArn`**: The ARN of the created analysis

## Best practices

1. **Use templates for consistency.** Create approved templates tailored for different analysis use cases (financial analysis, product analysis, etc.) so analysts start with the right structure.

2. **Apply themes for branding.** Use corporate themes to maintain consistent visual identity across all analyses.

3. **Name analyses for their purpose.** Use names like `sales-pipeline-analysis`, `customer-churn-exploration`, not generic names like `analysis-1`.

4. **Set appropriate permissions.** Restrict editing to the analysts who own the analysis; allow broader read access for stakeholders.

5. **Organize with folders.** Use `folderARNs` to organize analyses by team, domain, or function so analysts can discover related work.

6. **Plan for publication.** When an analysis is ready for broader use, publish it as a dashboard (created from the same template) for end users.

7. **Document analysis purpose in tags.** Use tags to capture intent: `purpose: exploratory`, `use-case: forecasting`, etc.

8. **Version and archive old analyses.** As analyses evolve, archive completed work to keep the workspace organized.

## Related resources

- **QuickSightConfig**: Governance profiles for naming, tagging, and policies
- **QuickSightDataSet**: Datasets that provide data to analysis visualizations
- **QuickSightDashboard**: Published visualizations created from analyses
- **QuickSightDataSource**: Data connections that feed datasets

## API reference

- **Group**: `aws.kropath.run`
- **Version**: `v1alpha1`
- **Kind**: `QuickSightAnalysis`
- **Scope**: Namespaced
