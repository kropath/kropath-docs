# AWS EC2TransitGatewayAttachment

EC2TransitGatewayAttachment represents an attachment between a VPC and a Transit Gateway. Attachments enable traffic to flow from a VPC through the transit gateway to other VPCs and on-premises networks.

## Configuration

*   `transitGatewayId` (string, required): Transit gateway ID to attach to.
*   `vpcId` (string, required): VPC ID to attach.
*   `subnetIds` (array of strings, required): Subnets in which to place the attachment's ENIs.
*   `applianceModeSupport` (string, optional): Enable appliance mode (`"enable"` or `"disable"`).
*   `ipv6Support` (string, optional): Enable IPv6 support (`"enable"` or `"disable"`).
*   `dnsSupport` (string, optional): Enable DNS support (`"enable"` or `"disable"`).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.transitGatewayAttachmentId`: AWS-assigned attachment identifier (format: `tgw-attach-*`).
*   `status.state`: Current state (`"associating"`, `"associated"`, `"disassociating"`, `"disassociated"`, `"failed"`, `"failing"`, `"pending"`, `"pendingAcceptance"`, `"rollingBack"`, `"rejected"`, `"rejecting"`).

## Example EC2TransitGatewayAttachment

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2TransitGatewayAttachment
metadata:
  name: prod-vpc-attachment
  namespace: default
spec:
  transitGatewayId: tgw-0123456789abcdef0
  vpcId: vpc-0123456789abcdef0
  subnetIds:
    - subnet-0123456789abcdef0
    - subnet-0987654321fedcba0
  dnsSupport: "enable"
  ipv6Support: "enable"
  tags:
    environment: production
    vpc: prod
```

## Naming

Attachments have no user-assigned name. AWS assigns `transitGatewayAttachmentId`.

See [EC2TransitGateway](./ec2transitgateway.md) for transit gateway configuration and [EC2 Family](../ec2.md) for related resources.
