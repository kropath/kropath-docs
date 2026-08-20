# AWS EC2Subnet

EC2Subnet represents an Amazon EC2 subnet—a logical subdivision of a VPC bound to a single availability zone (AZ). Subnets are the fundamental placement unit for EC2 instances, RDS databases, load balancers, EKS node groups, and nearly all other AWS resources that run inside a VPC.

## Prerequisites and Setup

EC2Subnet requires an existing VPC. Create an `EC2VPC` resource first. An `EC2Config` profile must also be deployed in the `kro-system` namespace. See [EC2Config](../ec2config.md) for setup details.

## Configuration

### Core Fields

An `EC2Subnet` instance defines a network segment within a VPC:

*   `configRef` (string, default: `"general-policy"`): Reference to the `EC2Config` profile for governance policies.
*   `deletionPolicy` (string, default: `"retain"`): Behavior when the `EC2Subnet` CR is deleted.
*   `vpcId` (string, required): ID of the VPC in which to create the subnet (format: `vpc-*`).
*   `cidrBlock` (string, required): IPv4 CIDR block for the subnet (e.g., `"10.0.1.0/24"`). Must be within the VPC's CIDR range.
*   `availabilityZone` (string, required): AWS availability zone name (e.g., `"us-east-1a"`). Subnet is bound to this AZ.
*   `restrictPublicIpOnLaunch` (boolean, default: false): When `true`, instances launched in this subnet do not automatically receive a public IP address. Governed by `EC2Config.restrictPublicIpOnLaunch` if present.
*   `ipv6CidrBlock` (string, optional): IPv6 CIDR block for the subnet. Only valid if the VPC has an IPv6 CIDR association.
*   `routeTableIds` (array of strings, optional): Route table IDs to associate with this subnet.

### Metadata and Tags

*   `tags` (map<string,string>): AWS tags applied to the subnet. Merged with governance tags from `EC2Config`.
*   `syncedLabels` (map<string,string>): Kubernetes labels mirrored as AWS tags (prefixed with `aws.kropath.run/`).
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations mirrored as AWS tags.

### Status Outputs

*   `status.subnetID`: AWS-assigned subnet identifier (format: `subnet-0123456789abcdef0`).
*   `status.state`: Current state (`"pending"` or `"available"`).
*   `status.availableIpAddressCount`: Number of IP addresses available for assignment in the subnet.

## Governance

EC2Subnet respects the `restrictPublicIpOnLaunch` governance field from `EC2Config`. When `EC2Config.mandatory.restrictPublicIpOnLaunch: true`, instances launched in the subnet do not receive public IPs, overriding the instance-level setting.

## Naming

Subnets have no user-assigned name field. AWS-assigned `subnetID` uniquely identifies the subnet. The naming convention does not apply.

## Example EC2Subnet Resource

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Subnet
metadata:
  name: prod-subnet-1a
  namespace: default
spec:
  configRef: general-policy
  deletionPolicy: retain
  vpcId: vpc-0123456789abcdef0
  cidrBlock: "10.0.1.0/24"
  availabilityZone: "us-east-1a"
  restrictPublicIpOnLaunch: false
  routeTableIds:
    - rtb-0123456789abcdef0
  tags:
    environment: production
    tier: application
```

After applying:

```yaml
status:
  subnetID: subnet-0123456789abcdef0
  state: available
  availableIpAddressCount: 251
```

## Common Patterns

### Private Subnet (No Public IPs)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Subnet
metadata:
  name: private-subnet
  namespace: default
spec:
  vpcId: vpc-abc123
  cidrBlock: "10.0.10.0/24"
  availabilityZone: "us-east-1a"
  restrictPublicIpOnLaunch: true
```

### Public Subnet (With Auto-Assigned Public IPs)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Subnet
metadata:
  name: public-subnet
  namespace: default
spec:
  vpcId: vpc-abc123
  cidrBlock: "10.0.1.0/24"
  availabilityZone: "us-east-1a"
  restrictPublicIpOnLaunch: false
  routeTableIds:
    - rtb-igw-route-table  # Route table with IGW route
```

### Dual-Stack Subnet (IPv4 + IPv6)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Subnet
metadata:
  name: dual-stack-subnet
  namespace: default
spec:
  vpcId: vpc-abc123
  cidrBlock: "10.0.1.0/24"
  availabilityZone: "us-east-1a"
  ipv6CidrBlock: "2600:1f16::/64"
```

## Cross-Provider Notes

*   **GCP Compute Subnetworks**: GCP subnets can span all zones within a region, whereas AWS subnets are bound to a single AZ. This means you may need fewer GCP subnets for the same architecture.
*   **Azure Subnets**: Azure subnets are not AZ-bound by default; zonal affinity is achieved through resource placement and NSG rules rather than subnet configuration.
*   **Public IP Assignment**: AWS provides a subnet-level toggle (`MapPublicIpOnLaunch`). GCP and Azure control public IP assignment at the instance or NIC level, not at the subnet level.

See [EC2Config](../ec2config.md) for governance policies, [EC2VPC](./ec2vpc.md) for VPC configuration, and [EC2 Family](../ec2.md) for other networking resources.
