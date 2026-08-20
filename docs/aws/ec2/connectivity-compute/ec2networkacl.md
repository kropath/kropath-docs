# AWS EC2NetworkACL

EC2NetworkACL represents a Network Access Control List (NACL)—a stateless firewall that controls inbound and outbound traffic at the subnet level. Unlike security groups, NACLs apply to the subnet and all resources within it.

## Configuration

*   `vpcId` (string, required): VPC ID for the NACL.
*   `entries` (array of rules): Network ACL entries with rule numbers, direction (ingress/egress via `egress: boolean`), and allow/deny actions.
*   `subnetIds` (array of subnet IDs, optional): Subnets to associate with this NACL.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.networkAclId`: AWS-assigned NACL identifier (format: `acl-*`).
*   `status.isDefault`: Boolean indicating if this is the default NACL for the VPC.

## Example EC2NetworkACL

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2NetworkACL
metadata:
  name: app-nacl
  namespace: default
spec:
  vpcId: vpc-0123456789abcdef0
  entries:
    - ruleNumber: 100
      protocol: "6"  # TCP
      portRange:
        from: 80
        to: 80
      cidrBlocks:
        - "0.0.0.0/0"
      egress: false
      ruleAction: "allow"
    - ruleNumber: 110
      protocol: "6"  # TCP
      portRange:
        from: 443
        to: 443
      cidrBlocks:
        - "0.0.0.0/0"
      egress: false
      ruleAction: "allow"
    - ruleNumber: 100
      protocol: "-1"  # All protocols
      cidrBlocks:
        - "0.0.0.0/0"
      egress: true
      ruleAction: "allow"
  subnetIds:
    - subnet-0123456789abcdef0
```

## Naming

NACLs have no user-assigned name. AWS assigns a unique `networkAclId`.

See [EC2 Family](../ec2.md) for related resources.
