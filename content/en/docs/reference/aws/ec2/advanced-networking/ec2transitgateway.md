---
title: AWS EC2TransitGateway
description: EC2TransitGateway represents a Transit Gateway—a highly available AWS service that connects VPCs and on-premises networks through a central hub.
doc_type: reference
---
# AWS EC2TransitGateway

EC2TransitGateway represents a Transit Gateway—a highly available AWS service that connects VPCs and on-premises networks through a central hub. Transit gateways simplify complex multi-VPC architectures by providing a single point of connection.

## Configuration

*   `configRef` (string, default: `"general-policy"`): Reference to `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `amazonSideAsn` (integer, optional): BGP ASN for the transit gateway.
*   `autoAcceptSharedAttachments` (string): Auto-accept attachment requests (`"enable"` or `"disable"`).
*   `defaultRouteTableAssociation` (string): Auto-associate attachments to default route table.
*   `defaultRouteTablePropagation` (string): Auto-propagate routes to default route table.
*   `dnsSupport` (string, default: `"enable"`): Enable DNS support (`"enable"` or `"disable"`).
*   `vpnEcmpSupport` (string, default: `"enable"`): Enable VPN ECMP support (`"enable"` or `"disable"`).
*   `multicastSupport` (string, default: `"disable"`): Enable multicast support.
*   `transitGatewayCidrBlocks` (array of strings, optional): CIDR blocks for the transit gateway.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.transitGatewayId`: AWS-assigned transit gateway identifier (format: `tgw-*`).
*   `status.state`: Current state (`"pending"`, `"available"`, `"modifying"`, `"deleting"`, `"deleted"`).

## Example EC2TransitGateway

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2TransitGateway
metadata:
  name: org-transit-gateway
  namespace: default
spec:
  configRef: general-policy
  amazonSideAsn: 64512
  autoAcceptSharedAttachments: "enable"
  defaultRouteTableAssociation: "enable"
  defaultRouteTablePropagation: "enable"
  dnsSupport: "enable"
  vpnEcmpSupport: "enable"
  multicastSupport: "enable"
  transitGatewayCidrBlocks:
    - "10.0.0.0/8"
  tags:
    environment: production
```

## Naming

Transit gateways have no user-assigned name. AWS assigns a unique `transitGatewayId`.

See [EC2TransitGatewayAttachment](./ec2transitgatewayattachment.md) for attaching VPCs and [EC2 Family](../_index.md) for related resources.
