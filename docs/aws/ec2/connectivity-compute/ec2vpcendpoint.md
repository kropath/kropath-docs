# AWS EC2VPCEndpoint

EC2VPCEndpoint represents a VPC Endpoint—a private connection between a VPC and an AWS service or third-party service, eliminating the need for internet gateways, NAT gateways, or direct connections to reach services outside the VPC.

## Configuration

*   `vpcId` (string, required): VPC ID for the endpoint.
*   `serviceType` (string, required): Endpoint type (`"Gateway"` for S3/DynamoDB, `"Interface"` for other services, `"GatewayLoadBalancer"`).
*   `serviceName` (string, required): AWS service name (e.g., `"com.amazonaws.us-east-1.s3"`).
*   `subnetIds` (array of strings, for Interface endpoints): Subnets where ENIs are placed.
*   `securityGroupIds` (array of strings, for Interface endpoints): Security groups for ENIs.
*   `privateHostEnabled` (boolean, for Interface endpoints): Enable private hosted zone for the service name.
*   `policyDocument` (string, optional): VPC endpoint policy for restricting access.
*   `routeTableIds` (array of strings, for Gateway endpoints): Route tables to add S3/DynamoDB routes to.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.vpcEndpointId`: AWS-assigned VPC endpoint identifier (format: `vpce-*`).
*   `status.state`: Current state (`"pending"`, `"available"`, `"deleting"`, `"deleted"`).
*   `status.networkInterfaceIds`: Network interfaces (for Interface endpoints).
*   `status.serviceName`: Resolved service name.

## Example EC2VPCEndpoint

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPCEndpoint
metadata:
  name: s3-endpoint
  namespace: default
spec:
  vpcId: vpc-0123456789abcdef0
  serviceType: "Gateway"
  serviceName: "com.amazonaws.us-east-1.s3"
  routeTableIds:
    - rtb-0123456789abcdef0
  tags:
    environment: production
```

## Naming

VPC endpoints have no user-assigned name. AWS assigns a unique `vpcEndpointId`.

See [EC2 Family](../ec2.md) for related resources.
