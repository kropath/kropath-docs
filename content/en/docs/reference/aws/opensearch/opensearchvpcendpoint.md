---
title: OpenSearchVPCEndpoint — Private Domain Access
description: "The `OpenSearchVPCEndpoint` resource provisions VPC endpoints for private connectivity to managed OpenSearch Service domains."
doc_type: reference
---
# OpenSearchVPCEndpoint — Private Domain Access

The `OpenSearchVPCEndpoint` resource provisions VPC endpoints for private connectivity to managed OpenSearch Service domains. Applications in a VPC access the domain without traversing the public internet.

## Purpose

`OpenSearchVPCEndpoint` enables private, low-latency access to OpenSearch domains:

- **Private connectivity** — Access domain from a VPC without public IP or internet gateway
- **Low latency** — Direct VPC-to-VPC communication (no internet routing)
- **Security isolation** — No public endpoint; network access controlled by security groups
- **Multi-VPC access** — Single domain accessible from multiple VPCs via separate endpoints

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `OpenSearchConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` keeps endpoint; `"delete"` removes it |

### Domain Target

Exactly one of `domainARN` or `domainRef` must be set.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `domainARN` | string | `""` | Direct ARN of the target OpenSearch Service domain (mutually exclusive with `domainRef`) |
| `domainRef` | string | `""` | Local `OpenSearchDomain` CR name; resolved to ARN automatically (mutually exclusive with `domainARN`) |

### VPC Configuration

| Field | Type | Required | Purpose |
|---|---|---|---|
| `vpcSubnetIDs` | array | Yes | Subnet IDs where the endpoint ENI will be placed |
| `vpcSecurityGroupIDs` | array | No | Security group IDs; empty = default VPC SG |

### Tags and Governance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | K8s metadata tags (VPC endpoints don't support cloud resource tags) |
| `syncedLabels` | map | `{}` | Labels synced to K8s metadata |
| `syncedAnnotations` | map | `{}` | Annotations synced to K8s metadata |

## Status Fields

After creation, the endpoint reports:

| Field | Type | Purpose |
|---|---|---|
| `conditions` | array | Standard Kubernetes conditions (Ready, Reconciling, etc.) |

Note: VPC endpoints do not have `resourceName`, `predictedArn`, or `namingStatus` fields (no naming templates apply).

## Domain Reference Options

### Direct ARN Reference

Use when accessing domains outside your Kubernetes cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: external-domain-access
  namespace: app-team
spec:
  domainARN: "arn:aws:es:us-east-1:123456789012:domain/shared-domain"
  vpcSubnetIDs:
    - "subnet-app-1"
    - "subnet-app-2"
  vpcSecurityGroupIDs:
    - "sg-app-opensearch"
```

### Local Domain Reference

Use when accessing domains managed via `OpenSearchDomain` CR in the same cluster:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: internal-endpoint
  namespace: app-team
spec:
  domainRef: shared-logs  # References OpenSearchDomain/shared-logs
  vpcSubnetIDs:
    - "subnet-app-1"
    - "subnet-app-2"
  vpcSecurityGroupIDs:
    - "sg-app-opensearch"
```

The endpoint automatically resolves the domain's ARN from `OpenSearchDomain.status.predictedArn`.

## Examples

### Single Subnet Endpoint

Minimal setup with a single subnet:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: simple-endpoint
  namespace: default
spec:
  domainARN: "arn:aws:es:us-east-1:123456789012:domain/my-domain"
  vpcSubnetIDs:
    - "subnet-12345678"
```

### Multi-Subnet HA Setup

High-availability endpoint across multiple subnets and AZs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: ha-endpoint
  namespace: observability
spec:
  domainRef: prod-logs  # Local domain reference
  vpcSubnetIDs:
    - "subnet-app-1a"
    - "subnet-app-1b"
    - "subnet-app-1c"
  vpcSecurityGroupIDs:
    - "sg-opensearch-consumer"
  tags:
    availability: high
```

### Multi-VPC Domain Access

Single domain accessible from multiple VPCs via separate endpoints:

```yaml
# Observability VPC — owns the domain
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: shared-logs
  namespace: observability
spec:
  configRef: production
  instanceType: "m6g.large.search"
  instanceCount: 3
  vpcSubnetIDs:
    - "subnet-obs-1"
    - "subnet-obs-2"
  vpcSecurityGroupIDs:
    - "sg-domain-internal"

---
# App VPC #1 — accesses the domain
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: app1-to-logs
  namespace: app-team-1
spec:
  domainRef: shared-logs
  vpcSubnetIDs:
    - "subnet-app1-1"
    - "subnet-app1-2"
  vpcSecurityGroupIDs:
    - "sg-app1-opensearch"
  tags:
    consumer: app-team-1

---
# App VPC #2 — accesses the same domain
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: app2-to-logs
  namespace: app-team-2
spec:
  domainRef: shared-logs
  vpcSubnetIDs:
    - "subnet-app2-1"
    - "subnet-app2-2"
  vpcSecurityGroupIDs:
    - "sg-app2-opensearch"
  tags:
    consumer: app-team-2
```

### Production Setup with Network ACLs

Complete example with explicit security group management:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchDomain
metadata:
  name: internal-logs
  namespace: platform
spec:
  configRef: production
  instanceType: "r6g.large.search"
  instanceCount: 3
  dedicatedMasterEnabled: true
  dedicatedMasterType: "m6g.large.search"
  dedicatedMasterCount: 3
  ebsVolumeSize: 500
  vpcSubnetIDs:
    - "subnet-domain-az1"
    - "subnet-domain-az2"
    - "subnet-domain-az3"
  vpcSecurityGroupIDs:
    - "sg-opensearch-domain"
  encryptionAtRestKmsKeyID: "arn:aws:kms:us-east-1:123456789012:key/domain-key"
  logPublishingOptions:
    AUDIT_LOGS:
      cloudWatchLogsLogGroupARN: "arn:aws:logs:us-east-1:123:log-group:/aws/opensearch/audit"
      enabled: true

---
# VPC Endpoint for app team access
apiVersion: aws.kropath.run/v1alpha1
kind: OpenSearchVPCEndpoint
metadata:
  name: app-access
  namespace: app-team
spec:
  domainRef: internal-logs
  vpcSubnetIDs:
    - "subnet-app-1a"
    - "subnet-app-1b"
  vpcSecurityGroupIDs:
    - "sg-app-to-opensearch"  # Allows outbound to opensearch-domain SG
  tags:
    team: app-team
    access-type: private
```

## VPC Configuration Details

### Subnets

- Specify 1-3 subnets from the application VPC
- Subnets should be in different AZs for high availability
- Endpoint ENI is placed in each specified subnet
- Route tables for these subnets must have connectivity to the domain VPC (via VPC peering, Transit Gateway, etc.)

### Security Groups

Security groups control network access to the VPC endpoint:

**Inbound rules for endpoint SG** (allow app to connect):
```
Protocol: TCP
Port: 443 (HTTPS)
Source: Application VPC CIDR or app security group
```

**Inbound rules for domain SG** (allow endpoint to connect):
```
Protocol: TCP
Port: 443 (HTTPS)
Source: Endpoint VPC CIDR or endpoint security group
```

### DNS Resolution

After creating the endpoint, query the domain via:

- **Private DNS within same VPC** — Domain DNS name resolves to endpoint (if DNS enabled)
- **Cross-VPC access** — Use the endpoint DNS name (e.g., `aos-abc123.us-east-1.aoss.amazonaws.com`)

## Governance Cascade

VPC endpoints follow the standard governance cascade for tags and labels only. `domainARN`, `domainRef`, and `vpcSubnetIDs` are not governance-enforced.

1. **OpenSearchConfig mandatory tier** (highest priority)
2. **Endpoint spec** (developer choice)
3. **OpenSearchConfig defaults tier** (lowest priority)

## Deletion Behavior

| Policy | Behavior |
|---|---|
| `retain` (default) | AWS VPC endpoint persists; K8s CR deleted |
| `delete` | AWS VPC endpoint deleted when K8s CR deleted |

## Best Practices

### Multi-Region Domains

If the domain is in another region:

1. Ensure network connectivity (VPC peering, Transit Gateway)
2. Endpoint must be in same region as the domain
3. Use direct ARN reference (domainRef works only within cluster)

### Security

- **Restrict security groups** — Only allow necessary ports/protocols
- **Isolate subnets** — Use dedicated subnets for VPC endpoint ENIs
- **Enable CloudTrail** — Monitor endpoint creation and access
- **Encrypt data in transit** — Domain must enforce HTTPS

### Performance

- **Multi-subnet for HA** — Place endpoints in multiple AZs
- **Dedicated subnets** — Avoid endpoint contention with other traffic
- **Monitor endpoint metrics** — CloudWatch provides throughput and packet metrics

### Networking

- **VPC peering** — For simple cross-VPC access
- **Transit Gateway** — For multi-VPC/multi-region complex topologies
- **Private hosted zones** — Consider Route53 private zone for DNS aliasing

## Related Concepts

- **Managed domains** — See [OpenSearchDomain](opensearchdomain.md)
- **Domain governance** — See [OpenSearchConfig](opensearchconfig.md)
- **Public endpoint** — See [OpenSearchDomain: VPC Networking](opensearchdomain.md#vpc-networking)
- **VPC Peering** — AWS VPC Peering documentation
- **Transit Gateway** — AWS Transit Gateway documentation
