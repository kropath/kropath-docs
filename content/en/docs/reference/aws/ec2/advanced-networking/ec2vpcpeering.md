---
title: AWS EC2VPCPeering
description: EC2VPCPeering represents a VPC Peering Connection—a networking connection between two VPCs that enables resources in each VPC to communicate using private IP addresses as if they were on the same network.
doc_type: reference
---
# AWS EC2VPCPeering

EC2VPCPeering represents a VPC Peering Connection—a networking connection between two VPCs that enables resources in each VPC to communicate using private IP addresses as if they were on the same network. Peering can connect VPCs within the same region or across regions, and in the same AWS account or different accounts.

## Configuration

*   `vpcId` (string, required): The requesting VPC ID.
*   `peerVpcId` (string, required): The VPC ID to peer with.
*   `peerOwnerId` (string, optional): AWS account ID of the peer VPC (required for cross-account peering).
*   `peerRegion` (string, optional): AWS region of the peer VPC (required for cross-region peering).
*   `acceptRequest` (boolean, default: false): Auto-accept peering request for same-account peerings.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.vpcPeeringConnectionId`: AWS-assigned peering connection identifier (format: `pcx-*`).
*   `status.state`: Current state (`"initiating-request"`, `"pending-acceptance"`, `"active"`, `"inactive"`, `"rejected"`, `"failed"`, `"expired"`, `"provisioning"`, `"deleting"`, `"deleted"`).
*   `status.accepterVpcInfo`: Information about the peer VPC (CIDR, owner ID, region).
*   `status.requesterVpcInfo`: Information about the requesting VPC.

## Example EC2VPCPeering

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPCPeering
metadata:
  name: prod-to-dev-peering
  namespace: default
spec:
  vpcId: vpc-prod-abc123
  peerVpcId: vpc-dev-xyz789
  acceptRequest: true
  tags:
    environment: production
    peering-name: prod-dev-link
```

### Cross-Account Peering

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPCPeering
metadata:
  name: cross-account-peering
  namespace: default
spec:
  vpcId: vpc-account-a
  peerVpcId: vpc-account-b
  peerOwnerId: "123456789012"
  acceptRequest: false  # Peer account must accept
```

## Naming

VPC peering connections have no user-assigned name. AWS assigns `vpcPeeringConnectionId`.

See [EC2TransitGateway](./ec2transitgateway.md) for multi-VPC connectivity and [EC2 Family](../_index.md) for related resources.
