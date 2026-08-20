# AWS EC2NATGateway

EC2NATGateway represents a NAT Gateway—a managed AWS service that enables instances in a private subnet to initiate outbound IPv4 traffic to the internet while preventing inbound traffic from reaching those instances. NAT gateways use Elastic IPs for outbound traffic.

## Configuration

*   `subnetId` (string, required): Subnet ID where the NAT gateway is placed (typically a public subnet).
*   `allocationId` (string, required for public): Elastic IP allocation ID for outbound traffic.
*   `connectivityType` (string, default: `"public"`): Type of connectivity (`"public"` for internet-bound, `"private"` for VPC endpoint access).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance settings.

## Status Outputs

*   `status.natGatewayId`: AWS-assigned NAT gateway identifier (format: `natgw-*`).
*   `status.natGatewayAddress`: Elastic IP address used for outbound traffic.
*   `status.state`: Current state (`"pending"`, `"available"`, `"deleting"`, `"deleted"`).

## Example EC2NATGateway

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2NATGateway
metadata:
  name: prod-natgw
  namespace: default
spec:
  subnetId: subnet-0123456789abcdef0  # Public subnet
  allocationId: eipalloc-0123456789abcdef0
  connectivityType: "public"
  tags:
    environment: production
```

## Naming

NAT gateways have no user-assigned name. AWS assigns a unique `natGatewayId`.

See [EC2 Family](../ec2.md) for related resources.
