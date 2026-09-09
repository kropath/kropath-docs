# Amazon QuickSight Resources

QuickSight is AWS's managed business intelligence (BI) service. kropath provides Kubernetes-native management of QuickSight resources including data sources, datasets, dashboards, and analyses.

## Resource Family Overview

The QuickSight resource family includes:

- **QuickSightDataSource** — Connect to data sources (S3, RDS, Redshift, etc.)
- **QuickSightDataSet** — Define and import data (SPICE or DIRECT_QUERY mode)
- **QuickSightDashboard** — Create interactive dashboards
- **QuickSightAnalysis** — Create interactive analyses for individual users

## Governance

The **QuickSightConfig** CRD provides governance across all QuickSight resources:

- Control import mode (SPICE vs DIRECT_QUERY) to manage costs
- Enforce naming conventions
- Apply mandatory and default tags, labels, and annotations
- Support multiple governance profiles per namespace

See [QuickSightConfig Reference](./quicksightconfig.md) for full documentation.

## Getting Started

1. Ensure your cluster has `kropath-aws` and `kropath-controller` deployed
2. Create a `QuickSightConfig` profile in your namespace (or use `general-policy`)
3. Create QuickSight resources with `spec.configRef` pointing to your profile

Example:

```yaml
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
      managed-by: kropath
```

Then create a dataset:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: QuickSightDataSet
metadata:
  name: my-dataset
spec:
  configRef: general-policy
  # ... rest of spec
```

## Documentation

- [QuickSightConfig Governance Reference](./quicksightconfig.md) — Governance fields, tier system, cascade rules
