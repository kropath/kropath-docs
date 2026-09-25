---
title: AWS RAM Resource Family
description: AWS Resource Access Manager (RAM) enables secure sharing of AWS resources across accounts and within an AWS Organization.
doc_type: reference
weight: 420
---
# AWS RAM Resource Family

AWS Resource Access Manager (RAM) enables secure sharing of AWS resources across accounts and within an AWS Organization.

## What is AWS RAM?

AWS RAM allows organizations to share resources (VPC subnets, Transit Gateways, License Manager configurations, Route 53 Resolver rules, and others) with external AWS accounts or with principals within the AWS Organization. The kropath RAM family provides governance, policy enforcement, and declarative configuration for:

- **Application teams** — Create and manage resource shares that distribute resources to other accounts with controlled access
- **Platform teams** — Define org-wide sharing policies, enforce naming conventions, control external principal access, and manage resource type restrictions

## The kropath RAM Family

The kropath RAM family consists of three resources:

### RAMConfig — Governance Configuration

`RAMConfig` is the governance layer that platform teams use to enforce sharing policies. Platform teams create named profiles (`general-policy`, `cross-account`, `restricted`, etc.) that define:

- Whether shares may include principals outside the AWS Organization
- Which resource types are permitted to be shared
- Mandatory and default naming conventions
- Mandatory and default tags for all shares and permissions

**[Read RAMConfig Reference →](./ramconfig.md)**

### RAMPermission — Custom Sharing Permissions

`RAMPermission` represents a customer-managed AWS RAM permission — a reusable policy template that defines which actions principals can perform on a specific resource type.

Application teams create permissions once, then attach them to multiple shares. Permissions allow fine-grained access control beyond AWS-managed defaults.

**[Read RAMPermission Guide →](./rampermission.md)**

### RAMResourceShare — Resource Sharing Bundles

`RAMResourceShare` represents an AWS RAM resource share — a bundle of resources, principals, and permissions that enables cross-account access.

Application teams use shares to distribute AWS resources to other accounts with controlled permissions and compliance enforcement.

**[Read RAMResourceShare Guide →](./ramresourceshare.md)**

## Quick Start

### 1. Deploy a governance profile (platform team)

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: RAMConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    allowExternalPrincipals: false
    allowedResourceTypes: []
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
EOF
```

### 2. Create a custom permission (application team)

```bash
kubectl apply -f - <<EOF
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
        "ec2:DescribeSubnetAttributes"
      ]
    }
EOF
```

### 3. Create a resource share (application team)

```bash
kubectl apply -f - <<EOF
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: vpc-share
  namespace: production
spec:
  configRef: general-policy
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abcdef"
  principals:
    - "222233334444"
  permissionRefs:
    - from:
        name: subnet-readonly
        namespace: production
EOF
```

## Key Concepts

### Governance Cascade

All resources follow a ten-level governance cascade:

1. Global org-wide mandatory (`KropathConfig.mandatory`)
2. Profile mandatory (`RAMConfig.mandatory`)
3. Instance override (`spec.*`)
4. Profile defaults (`RAMConfig.defaults`)
5. Global defaults (`KropathConfig.defaults`)

Higher levels override lower ones. This allows platform teams to enforce org-wide policies while still enabling application flexibility.

**Example:** If `RAMConfig.mandatory.allowExternalPrincipals: false`, then `spec.allowExternalPrincipals: true` is ignored — external principals are blocked by policy.

### Permissions and Shares

- **RAMPermission** defines WHAT principals can do (actions on a resource type)
- **RAMResourceShare** defines WHICH resources are shared and TO WHOM (resources and principals)
- Permissions attach to shares to specify the level of access

### Profile Fallthrough

If an application team references a profile that doesn't exist (e.g., `spec.configRef: nonexistent-profile`), the system automatically falls back to `general-policy`. Always ensure `general-policy` exists in the cluster.

## Common Use Cases

### Secure Resource Sharing Across Accounts

```yaml
# RAMConfig: strict compliance
metadata:
  name: restricted
spec:
  mandatory:
    allowExternalPrincipals: false  # Block external principals
    allowedResourceTypes:
      - "ec2:Subnet"                # Only subnets may be shared

---
# RAMPermission: read-only access
metadata:
  name: subnet-readonly
spec:
  policyTemplate: |
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSubnets",
        "ec2:DescribeSubnetAttributes"
      ]
    }

---
# RAMResourceShare: distribute subnets to internal account
metadata:
  name: vpc-share
spec:
  configRef: restricted
  resourceARNs: [...]
  principals: ["222233334444"]  # Internal AWS account
  permissionRefs:
    - from: { name: subnet-readonly }
```

### Multi-Account Transit Gateway Sharing

Share a Transit Gateway with multiple accounts for network connectivity:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: RAMResourceShare
metadata:
  name: tgw-share
  namespace: network-prod
spec:
  allowExternalPrincipals: false
  resourceARNs:
    - "arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-12345678"
  principals:
    - "222233334444"
    - "333344445555"
    - "arn:aws:organizations::123456789012:ou/o-a1b2c3d4e5/ou-12345678"
  permissionARNs:
    - "arn:aws:ram::aws:permission/AWSRAMDefaultResourceAccessRolePolicy"
```

### Org-Wide Governance

Use `KropathConfig` to enforce org-wide rules:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: KropathConfig
metadata:
  name: global-governance
  namespace: kro-system
spec:
  mandatory:
    ram:
      allowExternalPrincipals: false  # All accounts: no external principal access
      allowedResourceTypes: []        # All resource types allowed
    tags:
      cost-centre: shared-platform    # All shares/permissions must have this tag
```

## Learning Path

1. **Start with governance:** [RAMConfig Reference](./ramconfig.md) — Understand profiles and enforcement
2. **Create permissions:** [RAMPermission Guide](./rampermission.md) — Define custom access policies
3. **Share resources:** [RAMResourceShare Guide](./ramresourceshare.md) — Distribute resources to principals

## Troubleshooting

- **Resources not created?** Check that your `RAMConfig` profile exists; missing profiles fall back to `general-policy`
- **Policy not enforced?** Verify the setting is in `mandatory` tier, not `defaults` (mandatory overrides instance values)
- **External principals blocked?** Check `RAMConfig.mandatory.allowExternalPrincipals: false` — mandatory policies override instance requests
- **Naming errors?** Check `status.namingStatus` for unresolved tokens (missing tags, etc.)

## AWS-Specific Notes

- **AWS RAM is AWS-only** — GCP and Azure have different resource-sharing services (Shared VPC, Azure Lighthouse, etc.) with different models
- **No managed permissions in kropath** — AWS provides built-in managed permissions that can be used in `permissionARNs`, but `RAMPermission` only creates customer-managed permissions
- **Share invitations are asymmetric** — The share creator (producer) deploys the share; recipients (consumers) accept invitations in their own accounts (outside the scope of kropath)
- **Service-specific restrictions** — Some AWS services limit which principals can receive access (e.g., subnets work with account IDs and Organization ARNs; other services may have different restrictions)

## Resources

- [AWS RAM Documentation](https://docs.aws.amazon.com/ram/latest/userguide/what-is.html)
- [AWS RAM Permissions Reference](https://docs.aws.amazon.com/ram/latest/userguide/permissions.html)
- [Kropath ADR-015: Consolidated Platform Decisions](https://github.com/kropath/kropath-core/blob/main/docs/adrs/015-consolidated-platform-decisions.md)
- [Kropath ADR-010: Effective Config Cascade](https://github.com/kropath/kropath-core/blob/main/docs/adrs/010-kropath-controller-effective-config.md)
