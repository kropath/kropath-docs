---
title: ELBLoadBalancer — Application, Network, and Gateway Load Balancers
description: "The `ELBLoadBalancer` resource represents a single load balancer in AWS."
doc_type: reference
---
# ELBLoadBalancer — Application, Network, and Gateway Load Balancers

The `ELBLoadBalancer` resource represents a single load balancer in AWS. It supports all three ELBv2 types: Application Load Balancer (ALB), Network Load Balancer (NLB), and Gateway Load Balancer (GWLB).

## Load Balancer Types

| Type | Use Case | Protocol | Scheme | Security Groups |
|---|---|---|---|---|
| **application** (ALB) | Web and API applications | HTTP, HTTPS | internet-facing or internal | Required |
| **network** (NLB) | Ultra-high performance, low latency | TCP, TLS, UDP, TCP_UDP | internet-facing or internal | Optional |
| **gateway** (GWLB) | Inline appliance integration | GENEVE | Always internal | Not used |

**Important:** The load balancer type is immutable after creation. Choose the correct type when creating the resource.

## Core Fields

### Load Balancer Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ELBConfig` governance profile to apply |
| `type` | string | required | `"application"`, `"network"`, or `"gateway"` |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the load balancer name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when the resource is deleted: `"retain"` (keeps AWS LB) or `"delete"` (deletes AWS LB) |

### Network Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scheme` | string | `"internet-facing"` | `"internet-facing"` (public IP) or `"internal"` (private IP). Not applicable to GWLB. Governable by `ELBConfig`. |
| `subnets` | array | optional | Subnet IDs for the load balancer (mutually exclusive with `subnetMappings`) |
| `subnetMappings` | array | optional | Subnet IDs with optional Elastic IP (NLB) or private IP (NLB internal). Mutually exclusive with `subnets`. |
| `subnetMappings[].subnetId` | string | required | Subnet ID |
| `subnetMappings[].allocationId` | string | optional | Elastic IP allocation ID (NLB internet-facing only) |
| `subnetMappings[].privateIPv4Address` | string | optional | Private IPv4 (NLB internal only) |
| `subnetMappings[].ipv6Address` | string | optional | IPv6 address (NLB internet-facing only) |
| `ipAddressType` | string | `"ipv4"` | `"ipv4"`, `"dualstack"`, or `"dualstack-without-public-ipv4"`. Internal LBs must use `ipv4`. |
| `securityGroups` | array | optional | Security group IDs (ALB and NLB only, not GWLB). Omit for GWLB. |

### Load Balancer Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deletionProtection` | boolean | `false` | Prevent accidental deletion. Governable by `ELBConfig`. |
| `accessLogging.enabled` | boolean | `false` | Enable access logs to S3. Governable by `ELBConfig`. |
| `accessLogging.s3Bucket` | string | `""` | S3 bucket for access logs. Governable by `ELBConfig`. |
| `accessLogging.s3Prefix` | string | `""` | Optional S3 key prefix for access logs. |
| `crossZoneLoadBalancing` | boolean | `false` (NLB/GWLB) | Enable cross-zone load balancing. ALB is always cross-zone. Governable by `ELBConfig`. |
| `idleTimeoutSeconds` | integer | `60` (ALB) | Idle timeout in seconds (1–4000). ALB only; ignored for NLB/GWLB. Governable by `ELBConfig`. |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |
| `additionalAttributes` | array | `[]` | Additional key-value LB attributes beyond typed fields |

## Status Outputs

After reconciliation, the load balancer's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective load balancer name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions` | array | Status conditions (ready, error, etc.) |

**Note:** There is no `status.predictedArn` because ELBv2 ARNs include a hash suffix assigned by AWS at creation time. Use `status.ackResourceMetadata.arn` to get the actual ARN after creation.

## Naming Convention

Load balancers are named using a configurable template. The default template is `{namespace}-{name}`, which produces names like `api-team-api-lb`.

**Available naming tokens:**
- `{name}` — The resource's Kubernetes name
- `{namespace}` — The resource's Kubernetes namespace
- `{configRef}` — The selected governance profile name
- `{account_id}` — AWS account ID (from governance)
- `{region}` — AWS region (from governance)
- `{tag.KEY}` — Any tag key from the merged tags (e.g. `{tag.environment}`)

**AWS constraints:**
- Max 32 characters
- Alphanumeric and hyphens only
- No leading/trailing hyphens
- No `internal-` prefix

**Important:** The load balancer name is immutable after creation in AWS. Changing `spec.nameOverride` or the governance naming template on an existing load balancer does not rename the AWS LB.

## Complete Examples

### Application Load Balancer (ALB)

Internet-facing ALB for web applications:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: web-alb
  namespace: web-team
spec:
  configRef: general-policy
  type: application
  scheme: internet-facing
  subnets:
    - subnet-0a1b2c3d4e5f6g7h8
    - subnet-0b2c3d4e5f6g7h8i9
  securityGroups:
    - sg-12345678
  deletionProtection: true
  tags:
    team: web
    environment: production
  syncedLabels:
    tier: frontend
```

### Network Load Balancer (NLB) with Static IPs

NLB for high-performance workloads with static Elastic IPs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: api-nlb
  namespace: api-team
spec:
  configRef: general-policy
  type: network
  scheme: internet-facing
  ipAddressType: ipv4
  subnetMappings:
    - subnetId: subnet-0a1b2c3d4e5f6g7h8
      allocationId: eipalloc-12345678
    - subnetId: subnet-0b2c3d4e5f6g7h8i9
      allocationId: eipalloc-87654321
  deletionProtection: false
  crossZoneLoadBalancing: true
  tags:
    team: infrastructure
```

### Internal Network Load Balancer (NLB)

NLB for internal traffic with private IPs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: internal-nlb
  namespace: backend-team
spec:
  configRef: internal
  type: network
  scheme: internal
  subnets:
    - subnet-0a1b2c3d4e5f6g7h8
    - subnet-0b2c3d4e5f6g7h8i9
  crossZoneLoadBalancing: true
  tags:
    scope: internal
```

### Gateway Load Balancer (GWLB)

GWLB for inline security appliances:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: security-gwlb
  namespace: security-team
spec:
  configRef: general-policy
  type: gateway
  subnets:
    - subnet-0a1b2c3d4e5f6g7h8
    - subnet-0b2c3d4e5f6g7h8i9
  deletionProtection: false
  tags:
    team: security
    function: inline-appliance
```

## Governance Examples

### Enforced Deletion Protection

If your `ELBConfig` has `mandatory.deletionProtection: true`, all load balancers will have deletion protection enabled regardless of your `spec.deletionProtection` value:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: prod-lb
  namespace: prod-team
spec:
  configRef: prod-strict
  type: application
  scheme: internet-facing
  subnets:
    - subnet-123
    - subnet-456
  deletionProtection: false  # ← Will be overridden to true by prod-strict config
```

Result: The load balancer will have deletion protection enabled.

### Default Naming Template

If your `ELBConfig.defaults.namingTemplate: "{namespace}-{name}"`, the load balancer will be named `prod-team-prod-lb`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: prod-lb
  namespace: prod-team
spec:
  configRef: general-policy
  type: application
  subnets:
    - subnet-123
    - subnet-456
```

Result: `resourceName: "prod-team-prod-lb"`

### Custom Naming Override

Use `nameOverride` to bypass the template:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: prod-lb
  namespace: prod-team
spec:
  configRef: general-policy
  type: application
  nameOverride: my-custom-alb  # ← Bypasses template
  subnets:
    - subnet-123
    - subnet-456
```

Result: `resourceName: "my-custom-alb"`

## Cross-Zone Load Balancing

- **ALB:** Always enabled; cannot be disabled
- **NLB/GWLB:** Defaults to `false` (disabled); set to `true` to enable. Can be enforced by `ELBConfig.mandatory.crossZoneEnabled`.

## Access Logging

Enable access logging to track and analyze traffic:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: api-lb
  namespace: api-team
spec:
  configRef: general-policy
  type: application
  scheme: internet-facing
  subnets:
    - subnet-123
    - subnet-456
  accessLogging:
    enabled: true
    s3Bucket: my-org-lb-logs
    s3Prefix: alb/api-team/
```

Access logs are delivered to `s3://my-org-lb-logs/alb/api-team/` with timestamps as keys.

## Tag Propagation

Tags from `ELBConfig` governance and developer-specified tags are automatically merged and applied to the AWS load balancer:

```yaml
# In ELBConfig:
spec:
  defaults:
    tags:
      managed-by: kropath
      cost-center: platform

# In ELBLoadBalancer:
spec:
  tags:
    team: api

# Result on AWS: managed-by=kropath, cost-center=platform, team=api
```

## Deletion Policy

Control what happens when you delete the Kubernetes resource:

- `deletionPolicy: "retain"` (default) — Keeps the AWS load balancer intact
- `deletionPolicy: "delete"` — Deletes the AWS load balancer when the Kubernetes resource is deleted

Use `"retain"` for production to prevent accidental deletion.
