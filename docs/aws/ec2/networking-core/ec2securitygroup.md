# AWS EC2SecurityGroup

EC2SecurityGroup represents an Amazon security group—a stateful firewall that controls inbound and outbound traffic for resources within a VPC. Each security group is bound to a specific VPC and acts as a virtual firewall for instances and network interfaces.

## Prerequisites and Setup

EC2SecurityGroup requires an existing VPC. Create an `EC2VPC` resource first. An `EC2Config` profile must be deployed in `kro-system`. See [EC2Config](../ec2config.md) for setup.

## Configuration

### Core Fields

*   `configRef` (string, default: `"general-policy"`): Reference to the `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `vpcId` (string, required): VPC ID where the security group is created.
*   `description` (string, required): Human-readable description of the security group.
*   `nameOverride` (string, optional): Override the generated security group name.
*   `ingress` (array of rules, optional): Inbound traffic rules allowing specific CIDR blocks, security groups, or prefix lists.
*   `egress` (array of rules, optional): Outbound traffic rules controlling outgoing traffic.

### Metadata and Tags

*   `tags` (map<string,string>): AWS tags merged with governance tags from `EC2Config`.
*   `syncedLabels` and `syncedAnnotations`: Kubernetes metadata mirrored as AWS tags.

### Status Outputs

*   `status.securityGroupId`: AWS-assigned security group identifier (format: `sg-*`).
*   `status.resourceName`: Effective name derived from the naming template or `nameOverride`.
*   `status.namingStatus`: `"valid"` if naming template resolved successfully, `"invalid-unresolved-tokens"` if not.

## Governance

Security groups support naming convention. The `nameOverride` field allows overriding the generated name. Ingress and egress rules reference other security groups by ID or CIDR blocks/prefix lists for specifying allowed traffic sources and destinations.

## Naming

EC2SecurityGroup supports naming via the `namingTemplate` from `EC2Config`. Default template is `{namespace}-{name}`. Use `spec.nameOverride` to override.

## Example EC2SecurityGroup Resource

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2SecurityGroup
metadata:
  name: app-sg
  namespace: default
spec:
  configRef: general-policy
  vpcId: vpc-0123456789abcdef0
  description: "Security group for application servers"
  ingress:
    - ipProtocol: tcp
      fromPort: 80
      toPort: 80
      cidrIp: "0.0.0.0/0"
    - ipProtocol: tcp
      fromPort: 443
      toPort: 443
      cidrIp: "0.0.0.0/0"
    - ipProtocol: tcp
      fromPort: 8080
      toPort: 8080
      referencedGroupInfo:
        groupId: sg-internal-sg  # Internal security group
  egress:
    - ipProtocol: -1  # All traffic
      cidrIp: "0.0.0.0/0"
  tags:
    environment: production
    tier: application
```

After applying:

```yaml
status:
  securityGroupId: sg-0123456789abcdef0
  resourceName: "default-app-sg"
  namingStatus: "valid"
```

## Common Patterns

### Web Server Security Group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2SecurityGroup
metadata:
  name: web-sg
  namespace: default
spec:
  vpcId: vpc-abc123
  description: "Security group for web servers"
  ingress:
    - ipProtocol: tcp
      fromPort: 80
      toPort: 80
      cidrIp: "0.0.0.0/0"
    - ipProtocol: tcp
      fromPort: 443
      toPort: 443
      cidrIp: "0.0.0.0/0"
  egress:
    - ipProtocol: -1
      cidrIp: "0.0.0.0/0"
```

### Database Security Group

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2SecurityGroup
metadata:
  name: db-sg
  namespace: default
spec:
  vpcId: vpc-abc123
  description: "Security group for database servers"
  ingress:
    - ipProtocol: tcp
      fromPort: 5432
      toPort: 5432
      referencedGroupInfo:
        groupId: sg-web-sg  # Allow from web servers
  egress:
    - ipProtocol: -1
      cidrIp: "0.0.0.0/0"
```

## Cross-Provider Notes

*   **GCP Firewall Rules**: GCP uses hierarchical firewall rules at the network level rather than instance-level security groups. Rules are applied via tags or service accounts.
*   **Azure Network Security Groups (NSGs)**: Similar to AWS security groups but scoped to subnets or NICs. Azure NSGs use priority numbers instead of allow/deny ordering.

See [EC2Config](../ec2config.md) for naming governance, [EC2VPC](./ec2vpc.md) for VPC configuration, and [EC2 Family](../ec2.md) for other resources.
