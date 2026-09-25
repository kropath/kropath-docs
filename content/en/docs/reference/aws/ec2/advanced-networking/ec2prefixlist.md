---
title: AWS EC2PrefixList
description: EC2PrefixList represents a Managed Prefix List—a reusable list of IP address ranges that can be used in security group rules, route tables, and other AWS services.
doc_type: reference
---
# AWS EC2PrefixList

EC2PrefixList represents a Managed Prefix List—a reusable list of IP address ranges that can be used in security group rules, route tables, and other AWS services. Customer-managed prefix lists simplify management of large sets of CIDR blocks.

## Configuration

*   `configRef` (string, default: `"general-policy"`): Reference to `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `addressFamily` (string, default: `"IPv4"`): Address family (`"IPv4"` or `"IPv6"`).
*   `maxEntries` (integer, required): Maximum number of entries in the prefix list.
*   `nameOverride` (string, optional): Override the generated prefix list name.
*   `entries` (array of entries): List of IP address ranges with optional descriptions.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.prefixListId`: AWS-assigned prefix list identifier (format: `pl-*`).
*   `status.resourceName`: Effective name from naming template.
*   `status.namingStatus`: `"valid"` or `"invalid-unresolved-tokens"`.
*   `status.version`: Current version of the prefix list.
*   `status.arn`: AWS ARN for the prefix list.

## Governance

Prefix lists support naming via the `namingTemplate` from `EC2Config`. Default template: `{namespace}-{name}`. Use `spec.nameOverride` to override.

## Naming

EC2PrefixList supports naming via the `namingTemplate` from `EC2Config`. Default: `{namespace}-{name}`. Use `spec.nameOverride` for custom names.

## Example EC2PrefixList

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2PrefixList
metadata:
  name: corporate-cidr-list
  namespace: default
spec:
  configRef: general-policy
  addressFamily: "IPv4"
  maxEntries: 50
  entries:
    - cidr: "10.0.0.0/8"
      description: "Corporate network"
    - cidr: "172.16.0.0/12"
      description: "VPN network"
    - cidr: "203.0.113.0/24"
      description: "Partner network"
  tags:
    environment: production
    purpose: corporate-cidrs
```

After applying:

```yaml
status:
  prefixListId: pl-0123456789abcdef0
  resourceName: "default-corporate-cidr-list"
  namingStatus: "valid"
  version: 1
```

### IPv6 Prefix List

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2PrefixList
metadata:
  name: ipv6-partner-list
  namespace: default
spec:
  addressFamily: "IPv6"
  maxEntries: 20
  entries:
    - cidr: "2600:1f16::/32"
      description: "Partner IPv6 network"
```

## Common Patterns

### Security Group Ingress Rules

```yaml
# Use in a security group ingress rule
ingress:
  - ipProtocol: tcp
    fromPort: 443
    toPort: 443
    prefixListId: pl-corporate-cidrs
```

### Route Table Routes

```yaml
# Use in a route table for routing
routes:
  - destinationPrefixListId: pl-partner-cidrs
    gatewayId: igw-site-to-site
```

See [EC2Config](../ec2config.md) for naming governance, [EC2SecurityGroup](../networking-core/ec2securitygroup.md) for using prefix lists in rules, and [EC2 Family](../_index.md) for related resources.
