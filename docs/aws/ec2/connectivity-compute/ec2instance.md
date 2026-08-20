# AWS EC2Instance

EC2Instance represents an Amazon EC2 instance—a virtual machine running on AWS infrastructure. Instances are the core compute resource for running applications within a VPC.

## Configuration

*   `configRef` (string, default: `"general-policy"`): Reference to `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `imageId` (string, required): AMI ID for the instance.
*   `instanceType` (string, required): Instance type (e.g., `"t3.medium"`, `"m5.large"`).
*   `subnetId` (string, required): Subnet ID where the instance is launched.
*   `securityGroupIds` (array of strings): Security groups for the instance.
*   `keyName` (string, optional): EC2 key pair name for SSH access.
*   `userData` (string, optional): User data script executed at instance launch.
*   `monitoring` (boolean, default: false): Enable detailed CloudWatch monitoring.
*   `metadataOptions` (object): IMDS configuration (respects `imdsv2Required` from `EC2Config`).
*   `blockDeviceMappings` (array): EBS volume configuration (respects `ebsEncryptionRequired` from `EC2Config`).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.instanceId`: AWS-assigned instance identifier (format: `i-*`).
*   `status.state`: Current state (`"pending"`, `"running"`, `"stopping"`, `"stopped"`, `"terminating"`, `"terminated"`).
*   `status.publicIp`: Public IP address (if assigned).
*   `status.privateIp`: Private IP address.
*   `status.securityGroups`: Associated security groups.

## Governance

Instances respect governance from `EC2Config`:
- `imdsv2Required`: Enforces IMDSv2 for instance metadata
- `ebsEncryptionRequired`: Forces EBS encryption
- `ebsDefaultKmsKeyId`: Specifies KMS key for encryption

## Example EC2Instance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Instance
metadata:
  name: web-server
  namespace: default
spec:
  configRef: general-policy
  imageId: ami-0c55b159cbfafe1f0
  instanceType: "t3.medium"
  subnetId: subnet-0123456789abcdef0
  securityGroupIds:
    - sg-0123456789abcdef0
  keyName: my-keypair
  monitoring: true
  userData: |
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
  blockDeviceMappings:
    - deviceName: "/dev/xvda"
      ebs:
        volumeSize: 30
        encrypted: true
  tags:
    environment: production
    tier: web
```

## Naming

Instances have no user-assigned name. AWS assigns `instanceId`.

See [EC2Config](../ec2config.md) for governance, [EC2LaunchTemplate](./ec2launchtemplate.md) for template-based launch, and [EC2 Family](../ec2.md) for related resources.
