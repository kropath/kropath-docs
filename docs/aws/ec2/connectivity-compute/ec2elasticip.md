# AWS EC2ElasticIP

EC2ElasticIP represents an Elastic IP (EIP)—a static public IPv4 address that you can allocate to your AWS account and associate with an instance or network interface. Unlike public IPs assigned at instance launch, Elastic IPs persist across stop/start cycles.

## Configuration

*   `configRef` (string, default: `"general-policy"`): Reference to `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `domain` (string, default: `"vpc"`): Address domain (`"vpc"` for VPC instances, `"standard"` for EC2-Classic, deprecated).
*   `networkBorderGroup` (string, optional): AWS network border group (for localized IP allocation).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance settings.

## Status Outputs

*   `status.allocationId`: AWS-assigned Elastic IP allocation identifier (format: `eipalloc-*`).
*   `status.publicIp`: The actual public IP address.
*   `status.associationId`: If associated with an instance/ENI, the association ID (format: `eipassoc-*`).
*   `status.instanceId`: Associated instance ID (if applicable).

## Example EC2ElasticIP

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2ElasticIP
metadata:
  name: natgw-eip
  namespace: default
spec:
  configRef: general-policy
  deletionPolicy: retain
  domain: "vpc"
  tags:
    environment: production
    purpose: nat-gateway
```

After applying:

```yaml
status:
  allocationId: eipalloc-0123456789abcdef0
  publicIp: "203.0.113.42"
```

## Common Patterns

### EIP for NAT Gateway

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2ElasticIP
metadata:
  name: natgw-eip
  namespace: default
spec:
  domain: "vpc"
  tags:
    purpose: nat-gateway
```

### EIP for Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2ElasticIP
metadata:
  name: web-server-eip
  namespace: default
spec:
  domain: "vpc"
  networkBorderGroup: "us-east-1"
  tags:
    purpose: web-server
```

## Naming

Elastic IPs have no user-assigned name. AWS assigns `allocationId` and the public IP address.

See [EC2 Family](../ec2.md) for related resources.
