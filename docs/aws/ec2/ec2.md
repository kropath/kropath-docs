# AWS EC2 Family

The AWS EC2 family in kropath provides abstractions for managing Amazon Elastic Compute Cloud (EC2) resources and related networking infrastructure. It enables platform engineers to enforce organization-wide controls such as IMDSv2 enforcement, EBS encryption, flow log collection, and security policies, while allowing application teams to provision and configure VPCs, instances, security groups, and other EC2 resources for their specific needs.

The EC2 family is organized into three categories: **Networking Core** (foundational VPC resources), **Connectivity and Compute** (networking endpoints and compute instances), and **Advanced Networking** (inter-VPC and advanced routing).

## Overview

The EC2 family consists of 18 resource types plus one configuration CRD:

### Configuration

*   **[EC2Config](./ec2config.md)** — Governance configuration for all EC2 resources. Defines mandatory and default policies for networking, compute, and observability.

### Networking Core (7 resources)

These resources form the foundation of EC2 networking and should be created first:

*   **[EC2VPC](./networking-core/ec2vpc.md)** — Virtual Private Cloud (VPC) for isolating network resources.
*   **[EC2Subnet](./networking-core/ec2subnet.md)** — Subnet within a VPC for grouping resources into logical networks.
*   **[EC2SecurityGroup](./networking-core/ec2securitygroup.md)** — Security group for managing inbound and outbound traffic rules.
*   **[EC2RouteTable](./networking-core/ec2routetable.md)** — Route table for controlling traffic routing within and outside a VPC.
*   **[EC2InternetGateway](./networking-core/ec2internetgateway.md)** — Internet gateway for enabling communication between VPC and the internet.
*   **[EC2NATGateway](./networking-core/ec2natgateway.md)** — NAT gateway for outbound internet access from private subnets.
*   **[EC2FlowLog](./networking-core/ec2flowlog.md)** — VPC Flow Logs for capturing network traffic for observability and troubleshooting.

### Connectivity and Compute (5 resources)

These resources extend basic networking and provide compute capabilities:

*   **[EC2ElasticIP](./connectivity-compute/ec2elasticip.md)** — Static public IP address for instances or network interfaces.
*   **[EC2VPCEndpoint](./connectivity-compute/ec2vpcendpoint.md)** — VPC endpoint for accessing AWS services privately without internet gateway.
*   **[EC2NetworkACL](./connectivity-compute/ec2networkacl.md)** — Network ACL for subnet-level stateless traffic filtering.
*   **[EC2Instance](./connectivity-compute/ec2instance.md)** — EC2 instance (virtual machine) for running applications.
*   **[EC2LaunchTemplate](./connectivity-compute/ec2launchtemplate.md)** — Launch template for configuring EC2 instances with reusable specifications.

### Advanced Networking (5 resources)

These resources enable complex networking topologies and multi-VPC architectures:

*   **[EC2TransitGateway](./advanced-networking/ec2transitgateway.md)** — Transit gateway for connecting multiple VPCs and on-premises networks.
*   **[EC2TransitGatewayAttachment](./advanced-networking/ec2transitgatewayattachment.md)** — Attachment of a VPC to a transit gateway.
*   **[EC2VPCPeering](./advanced-networking/ec2vpcpeering.md)** — VPC peering for direct communication between two VPCs.
*   **[EC2DHCPOptions](./advanced-networking/ec2dhcpoptions.md)** — DHCP options set for customizing DNS and NTP settings.
*   **[EC2PrefixList](./advanced-networking/ec2prefixlist.md)** — Prefix list for managing groups of IP address ranges.

## Prerequisites and Setup

EC2 resources require:

*   A Kubernetes cluster with kropath installed
*   AWS credentials configured for the cluster (typically via IRSA or IAM roles)
*   An `EC2Config` profile deployed in the `kro-system` namespace (see [EC2Config](./ec2config.md))

## Getting Started

To provision a complete VPC environment:

1. **Create an EC2Config profile** in `kro-system` namespace to define governance policies
2. **Create an EC2VPC** with your desired CIDR block
3. **Create EC2Subnets** within the VPC for grouping resources
4. **Create EC2SecurityGroups** for managing traffic rules
5. **Create EC2RouteTables** to define traffic routing
6. **Create EC2InternetGateway** if internet access is needed
7. **Create EC2Instances** or use **EC2LaunchTemplate** for compute workloads

For multi-VPC architectures:

1. Create multiple VPCs
2. Create **EC2TransitGateway** to connect them
3. Create **EC2TransitGatewayAttachment** for each VPC
4. Create **EC2VPCPeering** or routing rules as needed

## Governance and Compliance

All EC2 resources leverage the `EC2Config` governance model to enforce organization-wide policies:

*   **Network governance**: Flow log enforcement, public IP restrictions, DNS settings
*   **Compute governance**: IMDSv2 enforcement, EBS encryption requirements, KMS key policies
*   **Metadata governance**: Tag and label propagation, naming conventions

Platform teams can create multiple `EC2Config` profiles (e.g., `general-policy` for standard workloads, `restricted` for compliance-sensitive workloads) and have EC2 resources reference the appropriate profile via `spec.configRef`.

## Naming Conventions

EC2 resource naming varies by resource type:

*   **Named resources** (EC2SecurityGroup, EC2LaunchTemplate, EC2PrefixList): Use a naming template to generate unique names (e.g., `{namespace}-{name}`). Override with `spec.nameOverride` when needed.
*   **Unnamed resources** (EC2VPC, EC2Subnet, EC2Instance, etc.): Use system-assigned identifiers (e.g., `vpc-*`, `subnet-*`, `i-*`). No naming convention applies.

For details, see the **Naming Conventions** section on each resource's documentation page.

## Deletion Policies

All EC2 resources support a `spec.deletionPolicy` field to control behavior when the Kubernetes resource is deleted:

*   `"retain"` (default): AWS resource is preserved when the Kubernetes CR is deleted
*   `"delete"`: AWS resource is deleted when the Kubernetes CR is deleted

Choose `"retain"` for production resources to prevent accidental deletion; use `"delete"` for ephemeral or test environments.

## Cross-Provider Notes

The EC2 family is AWS-specific. GCP and Azure equivalents are being developed as part of future kropath phases. While the conceptual model (VPCs, subnets, security groups, instances) is similar across cloud providers, the specific field names, constraints, and governance mechanisms differ.

## Next Steps

*   Review [EC2Config](./ec2config.md) for governance policies
*   Choose your deployment pattern (single VPC or multi-VPC with transit gateway)
*   Reference individual resource documentation for detailed field descriptions and examples
*   See ADR-010 and ADR-015 in kropath-core for detailed governance and architecture patterns
