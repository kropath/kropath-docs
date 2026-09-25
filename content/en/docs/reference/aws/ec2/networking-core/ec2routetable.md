---
title: AWS EC2RouteTable
description: EC2RouteTable represents an Amazon Route Table—a set of rules (routes) that determines where network traffic from your subnet or gateway is directed.
doc_type: reference
---
# AWS EC2RouteTable

EC2RouteTable represents an Amazon Route Table—a set of rules (routes) that determines where network traffic from your subnet or gateway is directed. Every subnet must be associated with a route table.

## Configuration

*   `vpcId` (string, required): VPC ID containing the route table.
*   `routes` (array of routes): List of routing rules specifying destinations and targets (IGW, NAT GW, TGW, etc.).
*   `subnetAssociations` (array of subnet IDs, optional): Subnets to explicitly associate with this route table.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance settings.

## Status Outputs

*   `status.routeTableId`: AWS-assigned route table identifier (format: `rtb-*`).

## Example EC2RouteTable

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2RouteTable
metadata:
  name: public-routes
  namespace: default
spec:
  vpcId: vpc-0123456789abcdef0
  routes:
    - destinationCidrBlock: "0.0.0.0/0"
      gatewayId: igw-0123456789abcdef0
    - destinationCidrBlock: "10.1.0.0/16"
      transitGatewayId: tgw-0123456789abcdef0
  subnetAssociations:
    - subnet-0123456789abcdef0
    - subnet-0987654321fedcba0
```

## Naming

Route tables have no user-assigned name. AWS assigns a unique `routeTableId`.

See [EC2 Family](../_index.md) for related resources.
