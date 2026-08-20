# AWS EC2InternetGateway

EC2InternetGateway represents an Internet Gateway—an AWS resource that enables communication between resources in a VPC and the internet. An IGW serves two purposes: it provides a target for internet-routable traffic in your route tables and performs NAT for instances that have been assigned public IPv4 addresses.

## Configuration

*   `vpcId` (string, required): VPC ID to attach the IGW to.
*   `routeTableIds` (array of strings, optional): Route tables to add internet routes to.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance settings.

## Status Outputs

*   `status.internetGatewayId`: AWS-assigned IGW identifier (format: `igw-*`).
*   `status.attachmentState`: Current state of VPC attachment (`"attaching"`, `"attached"`, `"detaching"`, `"detached"`).

## Example EC2InternetGateway

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2InternetGateway
metadata:
  name: prod-igw
  namespace: default
spec:
  vpcId: vpc-0123456789abcdef0
  routeTableIds:
    - rtb-0123456789abcdef0  # Public route table
  tags:
    environment: production
```

## Naming

Internet gateways have no user-assigned name. AWS assigns a unique `internetGatewayId`.

See [EC2 Family](../ec2.md) for related resources.
