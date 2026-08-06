# RDSSubnetGroup — Managing VPC Subnet Groups

The `RDSSubnetGroup` resource creates and manages an AWS RDS DB Subnet Group, which determines which VPC subnets (and Availability Zones) your RDS instances and Aurora clusters can be deployed into. A subnet group is a prerequisite for all RDS deployments.

## What It Does

A subnet group:
- Defines a collection of subnets where RDS resources can be placed
- Spans **multiple Availability Zones** for high-availability deployments
- Associates your databases with a specific VPC and routing context
- Is shared — multiple RDS instances and clusters can reference the same subnet group

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `RDSConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the subnet group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (safe) or `"delete"` |

### Subnet Group Properties

| Field | Type | Required | Purpose |
|---|---|---|---|
| `description` | string | ✓ | Human-readable description of the subnet group's purpose |
| `subnetIDs` | array of strings | ✓ | List of VPC subnet IDs to include (at least 2, in different AZs) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** Subnet group names must be 1–255 characters with lowercase letters, digits, hyphens, spaces, and periods
- **Predictable ARN:** `arn:aws:rds:<region>:<account-id>:subgrp:<subnet-group-name>`

Use `nameOverride` to set a custom name if the default template doesn't fit your naming scheme.

## Complete Example: Multi-AZ Subnet Group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSSubnetGroup
metadata:
  name: app-subnet-group
  namespace: database-prod
spec:
  configRef: general-policy
  deletionPolicy: retain
  description: "Production database subnet group spanning us-east-1a and us-east-1b"
  subnetIDs:
    - subnet-0a1b2c3d4e5f6g7h8  # us-east-1a
    - subnet-1f2g3h4i5j6k7l8m9  # us-east-1b
  tags:
    environment: production
    team: data-platform
    purpose: rds-deployments
  syncedLabels:
    tier: database
    backup-policy: daily
```

Result:
- Subnet group named (by default): `database-prod-app-subnet-group`
- Subnets span two AZs for Multi-AZ failover
- Tags synced to AWS
- Ready for RDS instances and clusters to reference via `spec.dbSubnetGroupName`

## Multiple Subnet Groups

If your RDS deployments need different subnets for different workloads (e.g., production vs. staging, different VPCs, different AZs), create multiple subnet groups:

```yaml
---
# Production: multi-AZ in us-east-1
apiVersion: aws.kropath.run/v1alpha1
kind: RDSSubnetGroup
metadata:
  name: prod-multi-az
  namespace: database-prod
spec:
  description: "Production multi-AZ database subnets"
  subnetIDs:
    - subnet-prod-1a
    - subnet-prod-1b

---
# Staging: single-AZ in us-west-2 (cost saving)
apiVersion: aws.kropath.run/v1alpha1
kind: RDSSubnetGroup
metadata:
  name: staging-single-az
  namespace: database-staging
spec:
  description: "Staging single-AZ database subnets"
  subnetIDs:
    - subnet-staging-2a
```

## Referencing from RDS Instances and Clusters

Once created, RDS instances and clusters reference the subnet group by name:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSInstance
metadata:
  name: main-db
  namespace: database-prod
spec:
  configRef: production
  dbSubnetGroupName: database-prod-app-subnet-group  # Reference by name
  engine: postgres
  engineVersion: "15.4"
  dbInstanceClass: db.m5.large
  allocatedStorage: 100
```

## Best Practices

1. **Plan for AZ distribution.** Include subnets from at least 2 (ideally 3+) Availability Zones for failover resilience.
2. **One group per VPC.** Create separate subnet groups for separate VPCs; do not mix VPCs in a single group.
3. **Use descriptive names.** Include environment and purpose in the description (`"Production multi-AZ for analytics workloads"`).
4. **Retention policy.** Set `deletionPolicy: retain` so deleting the Kubernetes resource doesn't accidentally delete the subnet group.
5. **Pre-create shared groups.** If multiple teams or services use the same subnets, create the subnet group in a shared namespace and let developers reference it by name.

## Governance

Subnet groups honor `RDSConfig` governance for tags, labels, and annotations. They have no special governance controls (e.g., no mandatory encryption or deletion protection — those apply to instances/clusters, not subnet infrastructure).

If your organization requires all subnets to be tagged with specific compliance labels, ensure they are set in the `RDSConfig` defaults or mandatory tier:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RDSConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    tags:
      compliance: pci
      data-classification: confidential
```
