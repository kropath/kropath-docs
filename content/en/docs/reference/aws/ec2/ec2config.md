---
title: AWS EC2 Governance Configuration
description: "The `EC2Config` CRD is the governance configuration for all AWS EC2 resources in kropath."
doc_type: reference
---
# AWS EC2 Governance Configuration

The `EC2Config` CRD is the governance configuration for all AWS EC2 resources in kropath. It enables platform teams to enforce organization-wide policies for networking, compute, and observability across Virtual Private Clouds (VPCs), instances, security groups, and other EC2 resources. Platform teams deploy named configuration profiles (such as `general-policy` and `restricted`) to codify compliance postures for different workload tiers.

## Prerequisites and Setup

EC2 resources are created independently, but all EC2 resources leverage the `EC2Config` CRD for governance. No additional prerequisites are required beyond a Kubernetes cluster with kropath installed.

## Configuration

Kropath's EC2 governance is managed through `EC2Config` custom resource instances in the `kro-system` namespace. Each `EC2Config` CR defines a named profile (e.g., `general-policy`, `restricted`) that EC2 resources reference via the `configRef` field.

### EC2Config Core Structure

An `EC2Config` CR contains two governance tiers: `mandatory` (enforced rules) and `defaults` (baseline configuration). These two tiers follow the kropath governance cascade (ADR-010, ADR-015 §5.3).

*   **`mandatory`** section: Fields set here enforce strict policies that cannot be overridden by EC2 resource instances. Use this tier for compliance requirements that must not be violated.
*   **`defaults`** section: Fields set here provide baseline configurations that EC2 resource instances can override. Use this tier for sensible defaults that operators can customize per-resource.

**Note:** Scalar fields (booleans, strings, integers) cannot be set in both tiers simultaneously. Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are additive and can be set in both tiers.

### EC2Config Governance Fields

EC2Config governs three categories of fields: networking, compute, and naming/metadata.

#### Networking Governance

*   `flowLogsRequired` (boolean, sentinel=false): When set to `true`, EC2 resources should produce VPC Flow Logs. In Phase 1, this is advisory only (does not block resource creation). Future phases will enforce this requirement.
*   `flowLogTrafficType` (string, sentinel="", valid values: "ACCEPT", "REJECT", "ALL"): Specifies which traffic should be captured in Flow Logs. The `mandatory` tier forces a specific type; `defaults` provides a fallback when the resource does not specify one.
*   `flowLogMaxAggregationInterval` (integer, sentinel=0, valid values: 60, 600): Specifies the interval (in seconds) for aggregating flow log records. The `mandatory` tier forces a specific value; `defaults` provides a fallback.
*   `restrictPublicIpOnLaunch` (boolean, sentinel=false): When set to `true`, subnets do not automatically assign public IPs to instances launched within them. This is a Subnet-level setting propagated through EC2Config.

#### Compute Governance

*   `imdsv2Required` (boolean, sentinel=false): When set to `true`, EC2 instances and launch templates must use IMDSv2 (token-based access to instance metadata) instead of IMDSv1. IMDSv2 is more secure and is recommended as a default.
*   `ebsEncryptionRequired` (boolean, sentinel=false): When set to `true`, all EBS volumes must be encrypted at rest.
*   `ebsDefaultKmsKeyId` (string, sentinel=""): Specifies the ARN of a KMS key for EBS encryption. When set in `mandatory`, this key is used for all EBS volumes regardless of instance-level overrides.
*   `publicIpRestricted` (boolean, sentinel=false): When set to `true`, instances should not be assigned public IP addresses. This is advisory in Phase 1.
*   `allowSourceDestCheckDisable` (boolean, sentinel=false): When set to `false` (default), instances cannot disable source/destination checks (a network option used by NAT instances and VPN appliances). When set to `true`, the disable is permitted.

#### Naming and Metadata Governance

*   `namingTemplate` (string, sentinel=""): Specifies a naming template for resources that support naming (SecurityGroup, LaunchTemplate, PrefixList). The template uses tokens like `{namespace}`, `{name}`, `{account_id}`, and `{region}`. When set in `mandatory`, this template is forced; when set in `defaults`, it applies to resources that don't specify a naming template.
*   `tags` (map<string,string>): Cloud tags (AWS resource tags) applied to all EC2 resources. Merged across mandatory and defaults tiers.
*   `syncedLabels` (map<string,string>): Kubernetes labels that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`.
*   `syncedAnnotations` (map<string,string>): Kubernetes annotations that are mirrored as AWS resource tags, prefixed with `aws.kropath.run/`.

### EC2Config Organization-Wide Blanket Governance

Three EC2Config fields are also available in `KropathConfig` for org-wide enforcement:

*   `KropathConfig.spec.mandatory.ec2.flowLogsRequired` (boolean): Org-wide requirement for flow logs across all EC2 resources in all namespaces.
*   `KropathConfig.spec.mandatory.ec2.imdsv2Required` (boolean): Org-wide requirement for IMDSv2 enforcement.
*   `KropathConfig.spec.mandatory.ec2.ebsEncryptionRequired` (boolean): Org-wide requirement for EBS encryption.

When set in `KropathConfig`, these fields override the corresponding `EC2Config` settings, ensuring organization-wide compliance.

### Ten-Tier Governance Cascade

Kropath employs a ten-tier governance cascade to resolve effective configuration for EC2 resources. The `kropath-controller` pre-merges all governance sources (from `KropathConfig` and `EC2Config`) into `status.effectiveConfig` on the namespaced `EC2Config` CR. EC2 resource RGDs read this `status.effectiveConfig` to determine the final, resolved settings.

**When to use `KropathConfig.ec2` vs. `EC2Config`:**

*   **`KropathConfig.ec2`:** Used for blanket, organization-wide governance that applies across *all* EC2 configuration profiles. For example, setting `KropathConfig.mandatory.ec2.imdsv2Required: true` would force all EC2 instances in the organization to use IMDSv2, regardless of the `EC2Config` profile they reference.
*   **`EC2Config`:** Used for per-profile governance. For instance, a `restricted` `EC2Config` profile might mandate a specific governance posture only for resources that explicitly reference that profile, allowing other profiles more flexibility.

## EC2Config Profiles

Kropath ships with two example `EC2Config` profiles. Platform teams can create additional profiles as needed.

### general-policy Profile

The default profile for most workloads. It provides sensible defaults for security and observability:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Config
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}  # No mandatory overrides; allows per-resource customization
  defaults:
    imdsv2Required: true
    ebsEncryptionRequired: true
    flowLogsRequired: false
    flowLogTrafficType: "ALL"
    flowLogMaxAggregationInterval: 600
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

### restricted Profile

A stricter compliance profile for workloads with heightened security requirements (e.g., payment processing, sensitive data):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Config
metadata:
  name: restricted
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: restricted
spec:
  mandatory:
    imdsv2Required: true
    ebsEncryptionRequired: true
    flowLogsRequired: true
  defaults:
    flowLogTrafficType: "ALL"
    flowLogMaxAggregationInterval: 60
    namingTemplate: "{namespace}-{name}"
    tags: {}
    syncedLabels: {}
    syncedAnnotations: {}
```

## Governance Cascade Behavior

### Boolean Governance Semantics

For boolean fields like `imdsv2Required` and `ebsEncryptionRequired`, `false` (or the sentinel empty value) in a `mandatory` or `defaults` tier means "follow the next tier in the cascade" rather than explicitly disabling the control. This allows platform teams to layer governance without forcing all values at every level.

### Map Field Merging

Map fields (`tags`, `syncedLabels`, `syncedAnnotations`) are merged additively across tiers. For example, if `mandatory.tags: {owner: platform-team}` and `defaults.tags: {environment: prod}`, the effective result is both tags. Instance-level tags are also merged into this set.

## Example EC2Config with Tag Governance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2Config
metadata:
  name: prod-compliance
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: prod-compliance
spec:
  mandatory:
    imdsv2Required: true
    ebsEncryptionRequired: true
    ebsDefaultKmsKeyId: "arn:aws:kms:us-east-1:123456789012:key/prod-key-id"
    tags:
      managed-by: kropath
      environment: production
    syncedLabels:
      compliance-tier: high
  defaults:
    flowLogsRequired: false
    flowLogTrafficType: "ALL"
    flowLogMaxAggregationInterval: 600
    restrictPublicIpOnLaunch: false
    publicIpRestricted: false
    allowSourceDestCheckDisable: false
    namingTemplate: "{namespace}-{name}"
    tags:
      cost-center: platform
```

## Cross-Provider Notes

EC2Config consolidates networking and compute governance into a single CRD because AWS uses a single ACK `ec2-controller` service. In GCP and Azure, equivalent configuration may be split across separate CRDs for different services (Compute, VPC, etc.), reflecting how those providers organize their APIs.

---

For EC2 resource documentation, see:

*   [EC2VPC](./networking-core/ec2vpc.md)
*   [EC2Subnet](./networking-core/ec2subnet.md)
*   [EC2SecurityGroup](./networking-core/ec2securitygroup.md)
*   [EC2RouteTable](./networking-core/ec2routetable.md)
*   [EC2InternetGateway](./networking-core/ec2internetgateway.md)
*   [EC2NATGateway](./networking-core/ec2natgateway.md)
*   [EC2FlowLog](./networking-core/ec2flowlog.md)
*   [EC2ElasticIP](./connectivity-compute/ec2elasticip.md)
*   [EC2VPCEndpoint](./connectivity-compute/ec2vpcendpoint.md)
*   [EC2NetworkACL](./connectivity-compute/ec2networkacl.md)
*   [EC2Instance](./connectivity-compute/ec2instance.md)
*   [EC2LaunchTemplate](./connectivity-compute/ec2launchtemplate.md)
*   [EC2TransitGateway](./advanced-networking/ec2transitgateway.md)
*   [EC2TransitGatewayAttachment](./advanced-networking/ec2transitgatewayattachment.md)
*   [EC2VPCPeering](./advanced-networking/ec2vpcpeering.md)
*   [EC2DHCPOptions](./advanced-networking/ec2dhcpoptions.md)
*   [EC2PrefixList](./advanced-networking/ec2prefixlist.md)
