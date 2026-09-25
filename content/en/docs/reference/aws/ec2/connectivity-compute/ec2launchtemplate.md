---
title: AWS EC2LaunchTemplate
description: EC2LaunchTemplate represents an EC2 Launch Template—a reusable configuration for launching EC2 instances.
doc_type: reference
---
# AWS EC2LaunchTemplate

EC2LaunchTemplate represents an EC2 Launch Template—a reusable configuration for launching EC2 instances. Launch templates simplify instance provisioning by storing common configuration details (AMI ID, instance type, security groups, etc.) and allowing override at launch time.

## Configuration

*   `configRef` (string, default: `"general-policy"`): Reference to `EC2Config` profile.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when deleted.
*   `nameOverride` (string, optional): Override the generated template name.
*   `imageId` (string, required): AMI ID for instances launched from this template.
*   `instanceType` (string, required): Default instance type.
*   `keyName` (string, optional): EC2 key pair name.
*   `securityGroupIds` (array of strings): Security groups.
*   `networkInterfaces` (array): Network interface configuration.
*   `metadataOptions` (object): IMDS configuration (respects `imdsv2Required`).
*   `blockDeviceMappings` (array): EBS volume configuration (respects `ebsEncryptionRequired`).
*   `monitoring` (boolean): Enable detailed CloudWatch monitoring.
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.launchTemplateId`: AWS-assigned launch template identifier (format: `lt-*`).
*   `status.resourceName`: Effective name from naming template.
*   `status.namingStatus`: `"valid"` or `"invalid-unresolved-tokens"`.

## Governance

Launch templates respect governance from `EC2Config`:
- `imdsv2Required`: Enforces IMDSv2
- `ebsEncryptionRequired`: Forces EBS encryption  
- `namingTemplate`: Controls template naming (supports naming convention)

## Naming

EC2LaunchTemplate supports naming via the `namingTemplate` from `EC2Config`. Default: `{namespace}-{name}`. Use `spec.nameOverride` to override.

## Example EC2LaunchTemplate

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2LaunchTemplate
metadata:
  name: web-app-template
  namespace: default
spec:
  configRef: general-policy
  imageId: ami-0c55b159cbfafe1f0
  instanceType: "t3.medium"
  keyName: my-keypair
  securityGroupIds:
    - sg-0123456789abcdef0
  monitoring: true
  blockDeviceMappings:
    - deviceName: "/dev/xvda"
      ebs:
        volumeSize: 30
        encrypted: true
  tags:
    environment: production
    application: web-app
```

After applying:

```yaml
status:
  launchTemplateId: lt-0123456789abcdef0
  resourceName: "default-web-app-template"
  namingStatus: "valid"
```

## Common Patterns

### Basic Template for Web Servers

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2LaunchTemplate
metadata:
  name: web-server-lt
  namespace: default
spec:
  imageId: ami-web-server
  instanceType: "t3.small"
  monitoring: true
```

### Advanced Template with IAM Role and Custom Network

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2LaunchTemplate
metadata:
  name: app-server-lt
  namespace: default
spec:
  imageId: ami-app-server
  instanceType: "m5.large"
  iamInstanceProfile:
    name: app-server-role
  networkInterfaces:
    - deviceIndex: 0
      deleteOnTermination: true
      associatePublicIpAddress: false
```

## Naming

EC2LaunchTemplate supports naming via `namingTemplate`. Use `spec.nameOverride` for custom names.

See [EC2Config](../ec2config.md) for governance, [EC2Instance](./ec2instance.md) for launching instances, and [EC2 Family](../_index.md) for related resources.
