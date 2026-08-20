# AWS EC2VPC

EC2VPC represents an Amazon Virtual Private Cloud (VPC)—an isolated network environment where you can launch AWS resources. Every EC2 networking resource (subnets, security groups, route tables, gateways) and most dependent AWS services (ELB, RDS, EKS) require a VPC.

## Prerequisites and Setup

EC2VPC is a foundational resource; no other EC2 resources are required before creating a VPC. However, an `EC2Config` profile must be deployed in the `kro-system` namespace. See [EC2Config](../ec2config.md) for setup details.

## Configuration

### Core Fields

An `EC2VPC` instance defines the virtual network infrastructure:

*   `configRef` (string, default: `"general-policy"`): Reference to the `EC2Config` profile to use for governance policies.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when the `EC2VPC` CR is deleted—`"retain"` keeps the AWS VPC, `"delete"` removes it.
*   `cidrBlock` (string, required): Primary IPv4 CIDR block for the VPC (e.g., `"10.0.0.0/16"`).
*   `secondaryCidrBlocks` (array of strings, optional): Additional IPv4 CIDR blocks to associate with the VPC.
*   `enableDnsSupport` (boolean, default: `true`): Enables DNS support within the VPC (enables Route 53 DNS resolution).
*   `enableDnsHostnames` (boolean, default: `true`): Enables DNS hostnames for instances launched in the VPC.
*   `instanceTenancy` (string, default: `"default"`): Tenancy attribute for instances (`"default"` for shared hardware, `"dedicated"` for dedicated hardware).

### Metadata and Tags

*   `tags` (map<string,string>): AWS tags applied to the VPC. Merged with mandatory and default tags from `EC2Config`.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS tags (prefixed with `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored as AWS tags (prefixed with `aws.kropath.run/`).

### Status Outputs

*   `status.vpcID`: AWS-assigned VPC identifier (format: `vpc-0123456789abcdef0`).
*   `status.state`: Current state of the VPC (`"pending"` or `"available"`).
*   `status.flowLogStatus`: Advisory status indicating whether flow logs are configured. Values: `"compliant"` (flow logs exist), `"missing-flow-log"` (required but missing), or empty (not required).

## Governance

EC2VPC respects the `EC2Config` governance cascade. The `flowLogsRequired` field in `EC2Config` controls the advisory `flowLogStatus`:

*   When `flowLogsRequired: true`: VPC should have an associated `EC2FlowLog`. In Phase 1, this is advisory only (does not block VPC creation). A companion `EC2FlowLog` CR targeting this VPC will set `status.flowLogStatus: "compliant"`.
*   When `flowLogsRequired: false`: No flow log requirement. `status.flowLogStatus` is not set.

## Naming

VPCs have no user-assigned name field. The AWS-assigned `vpcID` uniquely identifies the VPC. The naming convention does not apply.

## Example EC2VPC Resource

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPC
metadata:
  name: prod-vpc
  namespace: default
spec:
  configRef: general-policy
  deletionPolicy: retain
  cidrBlock: "10.0.0.0/16"
  secondaryCidrBlocks:
    - "10.1.0.0/16"
  enableDnsSupport: true
  enableDnsHostnames: true
  instanceTenancy: "default"
  tags:
    environment: production
    team: platform
  syncedLabels:
    compliance-level: high
```

After applying this resource:

```yaml
status:
  vpcID: vpc-0123456789abcdef0
  state: available
  flowLogStatus: "missing-flow-log"  # If flowLogsRequired: true in EC2Config
```

## Common Patterns

### Basic VPC with Single CIDR

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPC
metadata:
  name: simple-vpc
  namespace: default
spec:
  cidrBlock: "10.0.0.0/16"
```

### VPC with Multiple CIDR Blocks

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPC
metadata:
  name: multi-cidr-vpc
  namespace: default
spec:
  cidrBlock: "10.0.0.0/16"
  secondaryCidrBlocks:
    - "10.1.0.0/16"
    - "10.2.0.0/16"
```

### VPC with Dedicated Tenancy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2VPC
metadata:
  name: dedicated-vpc
  namespace: default
spec:
  cidrBlock: "10.0.0.0/16"
  instanceTenancy: "dedicated"
  tags:
    tenancy-type: dedicated
```

## Cross-Provider Notes

*   **GCP Compute Network**: GCP does not have a separate network-level CIDR; instead, CIDRs are defined at the subnet level. Secondary address ranges are also subnet-specific.
*   **Azure Virtual Network**: Azure VNets have address spaces (similar to AWS with secondary CIDRs). DNS is always enabled implicitly and cannot be toggled.
*   **Tenancy**: AWS-specific concept. GCP uses sole-tenant nodes; Azure uses dedicated hosts. The `instanceTenancy` field has no equivalent.

See [EC2Config](../ec2config.md) for governance policies and [EC2 Family](../ec2.md) for other networking resources.
