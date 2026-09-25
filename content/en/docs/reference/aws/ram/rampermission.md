---
title: RAMPermission — Custom Sharing Permissions
description: "`RAMPermission` is a Kubernetes resource that represents a customer-managed AWS RAM permission — a reusable policy template that defines which actions a principal can perform on a shared resource of a specific type."
doc_type: reference
---
# RAMPermission — Custom Sharing Permissions

`RAMPermission` is a Kubernetes resource that represents a customer-managed AWS RAM permission — a reusable policy template that defines which actions a principal can perform on a shared resource of a specific type.

Permissions are attached to resource shares and apply to all resources of the matching type within that share. They allow teams to define precise access controls beyond the AWS-managed defaults.

## Overview

A `RAMPermission` defines:

- **Policy template** — JSON policy document specifying allowed actions (e.g., `ec2:RunInstances`, `ec2:DescribeSubnets`)
- **Resource type** — Which AWS resource type this permission applies to (e.g., `ec2:Subnet`, `ec2:TransitGateway`)
- **Governance** — Profile selection, naming conventions, tags, and deletion behavior (inherited from `RAMConfig`)

Application teams create `RAMPermission` CRs once, then attach them to multiple shares via `RAMResourceShare.spec.permissionRefs` to share resources with controlled access.

## Prerequisites

- A Kubernetes cluster running kropath-aws
- `kropath-controller` deployed in the cluster
- At least one `RAMConfig` profile deployed (defaults to `general-policy`)
- A namespace where permissions will be provisioned

## Basic Structure

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMPermission
metadata:
  name: subnet-readonly
  namespace: production
spec:
  configRef: general-policy            # RAMConfig profile to use
  nameOverride: ""                      # Override naming template (empty = use template)
  deletionPolicy: retain                # retain | delete

  # Permission definition
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSubnets",
        "ec2:DescribeSubnetAttributes"
      ]
    }
  resourceType: "ec2:Subnet"            # Resource type this applies to

  # Metadata and governance
  tags:
    team: platform-network
    purpose: readonly-access
  syncedLabels: {}
  syncedAnnotations: {}

status:
  resourceName: production-subnet-readonly  # Resolved name from template
  namingStatus: "valid"                     # valid | invalid-unresolved-tokens
  permissionArn: arn:aws:ram::123456789012:permission/abcdef-1234567890  # AWS-assigned ARN
  predictedArn: arn:aws:ram::123456789012:permission/abcdef-1234567890   # Same as above
```

## Core Fields

### Policy Template (`policyTemplate`)

A JSON string defining the permission policy. This is a policy template that RAM uses as-is when the permission is attached to shares.

**Important constraints:**
- Must include `"Effect": "Allow"` — only allow statements are supported
- Must include `"Action"` — list the allowed actions
- May include `"Condition"` — optional conditional restrictions
- Must NOT include `"Resource"` — RAM fills this when the permission is attached to a share
- Must NOT include `"Principal"` — RAM fills this based on share principals

**Example — Read-only access to subnets:**
```yaml
policyTemplate: |
  {
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeSubnets",
      "ec2:DescribeSubnetAttributes",
      "ec2:GetSubnetCidrReservationUsage"
    ]
  }
```

**Example — With conditions:**
```yaml
policyTemplate: |
  {
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeTransitGateways",
      "ec2:SearchTransitGatewayRoutes"
    ],
    "Condition": {
      "StringEquals": {
        "aws:RequestedRegion": "us-east-1"
      }
    }
  }
```

### Resource Type (`resourceType`)

The AWS resource type this permission applies to. Format: `<service>:<resourceType>` (case-insensitive).

**Common resource types:**
- `ec2:Subnet` — VPC subnets
- `ec2:TransitGateway` — Transit Gateways
- `ec2:CustomerGateway` — VPN customer gateways
- `license-manager:LicenseConfiguration` — License Manager configurations
- `route53resolver:ResolverRule` — Route 53 Resolver rules
- `kms:Key` — AWS KMS encryption keys
- `glue:Catalog` — AWS Glue data catalogs

**Example:**
```yaml
spec:
  resourceType: "ec2:TransitGateway"
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayAttachments"
      ]
    }
```

### Config Profile Reference (`configRef`)

Selects which `RAMConfig` profile governs this permission's naming, tags, and deletion behavior.

**Behavior:**
- If the named profile doesn't exist, falls back to `general-policy`
- If `general-policy` doesn't exist, the resource is rejected

**Examples:**
```yaml
spec:
  configRef: general-policy    # Use general-policy profile

  configRef: ""                # Empty string: fall through to general-policy
  configRef: prod-strict       # Use custom prod-strict profile
```

## Governance Fields

All governance is inherited from the selected `RAMConfig` profile via `status.effectiveConfig`:

| Field | Source | Meaning |
|---|---|---|
| `namingTemplate` | RAMConfig | Resolved to `status.resourceName` |
| `tags` | RAMConfig (merged with instance `spec.tags`) | Applied to the AWS permission resource |
| `syncedLabels` | RAMConfig (merged with instance) | Kubernetes labels + cloud tags |
| `syncedAnnotations` | RAMConfig (merged with instance) | Kubernetes annotations |
| `deletionPolicy` | Instance `spec.deletionPolicy` | `retain` or `delete` |

### Naming

Resource names follow the naming template from `RAMConfig`. The template is resolved and stored in `status.resourceName`.

**Example:** If `RAMConfig.defaults.namingTemplate: "{namespace}-{name}"` and you create:
```yaml
metadata:
  name: subnet-readonly
  namespace: production
```

Then `status.resourceName: "production-subnet-readonly"`

**Token vocabulary:**
- `{name}` — The resource's `metadata.name`
- `{namespace}` — The resource's Kubernetes namespace
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — The profile name
- `{tag.<key>}` — Merge tag values into the name

If a token can't be resolved (e.g., missing tag), `status.namingStatus: "invalid-unresolved-tokens"` and the resource won't be created.

### Tagging and Metadata

Tags are inherited from `RAMConfig` and merged with instance `spec.tags`. The `RAMConfig` tier hierarchy determines precedence:

1. Global org-wide mandatory tags (`KropathConfig.mandatory.tags`)
2. Profile mandatory tags (`RAMConfig.mandatory.tags`)
3. Instance tags (`spec.tags`)
4. Profile default tags (`RAMConfig.defaults.tags`)
5. Global default tags (`KropathConfig.defaults.tags`)

**Example:**
```yaml
# RAMConfig
spec:
  mandatory:
    tags:
      cost-centre: platform
  defaults:
    tags:
      managed-by: kropath

---
# RAMPermission
spec:
  tags:
    team: networking

# Result: merged tags = {cost-centre: platform, managed-by: kropath, team: networking}
```

## ARN Exposure

After the permission is created, AWS assigns a unique ARN. The ARN is exposed via `status.permissionArn` and `status.predictedArn` (both contain the same value).

**ARN format:**
```
arn:aws:ram:region:account-id:permission/unique-identifier
```

Note: The unique identifier is AWS-assigned, not derived from the `metadata.name`. This ARN can be used to reference the permission in `RAMResourceShare.spec.permissionARNs`.

**Example:**
```yaml
status:
  permissionArn: arn:aws:ram::123456789012:permission/abcdef-1234567890
  predictedArn: arn:aws:ram::123456789012:permission/abcdef-1234567890
```

## Deletion Policy

Controls what happens to the AWS RAM permission when you delete the Kubernetes CR.

**Options:**
- `retain` (default) — Keep the AWS resource; only delete the Kubernetes CR
- `delete` — Delete the AWS resource when the Kubernetes CR is deleted

**Example:**
```yaml
spec:
  deletionPolicy: retain    # Keep AWS permission after CR deletion

  deletionPolicy: delete    # Delete AWS permission when CR deleted
```

## Common Patterns

### Read-Only Access to EC2 Subnets

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMPermission
metadata:
  name: subnet-readonly
  namespace: production
spec:
  configRef: general-policy
  resourceType: "ec2:Subnet"
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSubnets",
        "ec2:DescribeSubnetAttributes",
        "ec2:GetSubnetCidrReservationUsage"
      ]
    }
  tags:
    access-level: readonly
    team: platform-network
```

### Full Access to Transit Gateway

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMPermission
metadata:
  name: tgw-full-access
  namespace: production
spec:
  configRef: general-policy
  resourceType: "ec2:TransitGateway"
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayAttachments",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:DescribeTransitGatewayRouteTableAssociations",
        "ec2:SearchTransitGatewayRoutes",
        "ec2:GetTransitGatewayAttachmentPropagations"
      ]
    }
  tags:
    access-level: full
    team: network-engineering
```

### Conditional License Manager Access

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMPermission
metadata:
  name: license-manager-config-access
  namespace: production
spec:
  configRef: general-policy
  resourceType: "license-manager:LicenseConfiguration"
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "license-manager:GetLicenseConfiguration",
        "license-manager:ListLicenseConfigurations",
        "license-manager:GetLicenseConversionTask"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    }
  tags:
    access-level: readonly
    team: license-compliance
```

## Using Permissions in Resource Shares

Once created, attach the permission to shares via `RAMResourceShare.spec.permissionRefs`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: vpc-share
  namespace: production
spec:
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abcdef"
  principals:
    - "222233334444"  # External AWS account
  permissionRefs:
    - from:
        name: subnet-readonly
        namespace: production
```

Or use the ARN directly:

```yaml
spec:
  permissionARNs:
    - "arn:aws:ram::123456789012:permission/abcdef-1234567890"
```

## Troubleshooting

**"Permission is not being created"**
- Check if the specified `configRef` profile exists
- Verify `policyTemplate` is valid JSON
- Ensure `resourceType` follows the format `<service>:<resourceType>`
- Check the Kubernetes events: `kubectl describe rampermission <name> -n <namespace>`

**"Naming is invalid"**
- Check `status.namingStatus` on the permission
- If it shows `"invalid-unresolved-tokens"`, check your naming template for unresolved `{tag.*}` tokens
- Verify all referenced tags are present in the merged tags from RAMConfig

**"Permission ARN isn't showing in status"**
- The permission may still be creating — ARNs appear after successful creation
- Check the resource's `status.conditions` for any errors
- Verify the AWS RAM service is accessible in your region

**"Permission is not being attached to shares"**
- Check that `RAMResourceShare.spec.permissionRefs` or `spec.permissionARNs` references the correct permission
- Verify the permission's `resourceType` matches the resource types in the share
- Check that the permission was successfully created (look for `status.permissionArn`)

## See Also

- [RAMConfig Reference](./ramconfig.md)
- [RAMResourceShare User Guide](./ramresourceshare.md)
- [RAM Resource Family Overview](./_index.md)
- [AWS RAM Permissions Documentation](https://docs.aws.amazon.com/ram/latest/userguide/permissions.html)
