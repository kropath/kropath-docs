---
title: NetworkFirewallFirewall — Deploying Network Firewalls
description: "The `NetworkFirewallFirewall` resource creates and manages AWS Network Firewall instances."
doc_type: reference
---
# NetworkFirewallFirewall — Deploying Network Firewalls

The `NetworkFirewallFirewall` resource creates and manages AWS Network Firewall instances. A firewall is deployed at VPC subnet boundaries for inline traffic inspection.

## What It Does

A `NetworkFirewallFirewall`:
- Deploys a firewall instance in one or more VPC subnets
- Associates with a firewall policy
- Creates firewall endpoints in specified subnets (one per Availability Zone)
- Encrypts traffic and data at rest
- Logs traffic via CloudWatch, S3, or Kinesis Data Firehose
- Enforces protection settings (deletion, policy changes, subnet changes)

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `NetworkFirewallConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses the naming template |
| `deletionPolicy` | string | `"retain"` | Safe delete: `"retain"` or `"delete"` |

### Firewall Properties

| Field | Type | Required | Purpose |
|---|---|---|---|
| `description` | string | no | Human-readable description |

### VPC Attachment (Immutable)

| Field | Type | Required | Purpose |
|---|---|---|---|
| `vpcId` | string | no* | VPC ID (mutually exclusive with `vpcRef`) |
| `vpcRef` | string | no* | Reference to a local VPC CR (mutually exclusive with `vpcId`) |

*One of `vpcId` or `vpcRef` is required.

### Subnet Mappings (Required)

| Field | Type | Purpose |
|---|---|---|
| `subnetMappings` | array | One subnet per Availability Zone |
| `.subnetId` | string | Subnet ID for the firewall endpoint |
| `.ipAddressType` | string | Address type: `IPV4` (default) or `DUALSTACK` |

### Firewall Policy Association

| Field | Type | Purpose |
|---|---|---|
| `firewallPolicyArn` | string | ARN of the firewall policy (mutually exclusive with `firewallPolicyRef`) |
| `firewallPolicyRef` | string | Reference to a local NetworkFirewallPolicy CR (mutually exclusive with `firewallPolicyArn`) |

### Protection Settings (Governance-Driven)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deleteProtection` | boolean | `true` | Prevent accidental deletion |
| `firewallPolicyChangeProtection` | boolean | `true` | Prevent policy changes |
| `subnetChangeProtection` | boolean | `true` | Prevent subnet mapping changes |

### Encryption (Governance-Driven)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionType` | string | `""` | Encryption type: `AWS_OWNED_KMS_KEY` or `CUSTOMER_KMS` |
| `kmsKeyId` | string | `""` | KMS key ARN/ID for CUSTOMER_KMS |
| `kmsKeyRef` | string | `""` | Reference to a local KMSKey CR |

### Logging (Governance-Driven)

| Field | Type | Purpose |
|---|---|---|
| `loggingConfiguration` | object | Log destinations for alert, flow, and TLS logs |
| `.alertLogDestination` | object | Where to send alert logs |
| `.flowLogDestination` | object | Where to send flow logs |
| `.tlsLogDestination` | object | Where to send TLS inspection logs |

Each log destination has:

| Field | Type | Purpose |
|---|---|---|
| `type` | string | Destination type: `S3`, `CloudWatchLogs`, or `KinesisDataFirehose` |
| `destination` | map | Destination-specific parameters |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** 1–128 characters, alphanumeric and hyphens only
- **Predicted ARN:** `arn:aws:network-firewall:<region>:<account>:firewall/<name>`

## Example: Production Multi-AZ Firewall

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallFirewall
metadata:
  name: perimeter-fw
  namespace: security-prod
spec:
  configRef: production
  description: "Production perimeter firewall — multi-AZ deployment"
  deletionPolicy: retain
  
  # VPC attachment
  vpcId: vpc-12345678
  
  # Subnets — one per AZ
  subnetMappings:
    - subnetId: subnet-us-east-1a
      ipAddressType: IPV4
    - subnetId: subnet-us-east-1b
      ipAddressType: IPV4
  
  # Firewall policy
  firewallPolicyRef: production-policy     # Reference by name (same namespace)
  
  # Protection settings (defaults from production profile)
  deleteProtection: true
  firewallPolicyChangeProtection: true
  subnetChangeProtection: true
  
  # Logging (from production profile)
  loggingConfiguration:
    alertLogDestination:
      type: CloudWatchLogs
      destination:
        logGroup: /aws/network-firewall/prod/alerts
    flowLogDestination:
      type: S3
      destination:
        bucketName: prod-nfw-flow-logs
        prefix: prod/flow/
  
  tags:
    environment: production
    firewall-role: perimeter
    high-availability: true
```

Result:
- Firewall named `security-prod-perimeter-fw`
- Deployed in VPC `vpc-12345678` across two subnets (us-east-1a and us-east-1b)
- Multi-AZ setup with automatic failover
- Deletion protected via governance
- Alert and flow logs exported to CloudWatch and S3
- All governance from `production` profile applies

## Example: Development Firewall (Single AZ)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallFirewall
metadata:
  name: dev-fw
  namespace: security-dev
spec:
  configRef: development
  description: "Development firewall — single AZ"
  deletionPolicy: delete              # Development firewalls can be deleted
  
  # VPC attachment
  vpcId: vpc-dev-12345678
  
  # Single subnet (dev only)
  subnetMappings:
    - subnetId: subnet-dev-us-east-1a
  
  # Policy
  firewallPolicyRef: dev-policy
  
  # Logging optional in dev
  loggingConfiguration:
    alertLogDestination:
      type: CloudWatchLogs
      destination:
        logGroup: /aws/network-firewall/dev/alerts
```

Result:
- Firewall named `security-dev-dev-fw`
- Single-AZ deployment for cost savings
- Can be deleted freely (dev only)
- Alert logs only (flow logs not needed for dev)

## Example: Policy Reference by ARN

For firewalls that use policies in different namespaces:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallFirewall
metadata:
  name: shared-fw
  namespace: security-prod
spec:
  configRef: production
  vpcId: vpc-shared
  subnetMappings:
    - subnetId: subnet-shared-1a
    - subnetId: subnet-shared-1b
  
  # Direct ARN reference
  firewallPolicyArn: "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/org-wide-policy"
```

Use direct ARN references for policies:
- In different AWS accounts
- Managed outside of Kubernetes
- Shared across many firewalls

## Status Fields

After creation, the firewall exposes status fields:

| Field | Type | Meaning |
|---|---|---|
| `status.resourceName` | string | The resolved firewall name |
| `status.namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `status.predictedArn` | string | The predicted AWS ARN |

## Governance Fields

The following fields are governance-driven via `NetworkFirewallConfig`:

| Field | Governance Behavior |
|---|---|
| `deleteProtection` | Falls through: mandatory → spec → defaults |
| `firewallPolicyChangeProtection` | Falls through: mandatory → spec → defaults |
| `subnetChangeProtection` | Falls through: mandatory → spec → defaults |
| `encryptionType` | Falls through: mandatory → spec → defaults |
| `loggingConfiguration` | Per-destination fallthrough: mandatory → spec → defaults |
| `tags`, `syncedLabels`, `syncedAnnotations` | Merges governance + spec values |

If `deleteProtection` is set to `true` in the mandatory tier of `NetworkFirewallConfig`, all firewalls have deletion protection enabled regardless of their `spec.deleteProtection`.

## Immutable Fields

After creation, this field cannot be changed:

| Field | Reason |
|---|---|
| `vpcId` | AWS does not allow moving a firewall to a different VPC |

To change the VPC, delete and recreate the resource (if not deletion-protected).

## Logging Destinations

Each log type (alert, flow, TLS) can be sent independently to different destinations:

### Destination: CloudWatch Logs

```yaml
alertLogDestination:
  type: CloudWatchLogs
  destination:
    logGroup: /aws/nfw/alerts
```

Logs appear in `/aws/nfw/alerts` log group.

### Destination: S3

```yaml
flowLogDestination:
  type: S3
  destination:
    bucketName: my-nfw-logs
    prefix: prod/flow/        # Optional prefix
```

Flow logs are stored in `s3://my-nfw-logs/prod/flow/`.

### Destination: Kinesis Data Firehose

```yaml
tlsLogDestination:
  type: KinesisDataFirehose
  destination:
    deliveryStream: nfw-tls-stream
```

TLS logs are delivered to `nfw-tls-stream` stream.

## Best Practices

1. **Use Multi-AZ for production.** Deploy firewalls across at least two subnets for high availability.
2. **Enable deletion protection.** Set `deletionPolicy: retain` for all production firewalls.
3. **Lock down policy changes.** Use governance to enforce `firewallPolicyChangeProtection: true`.
4. **Enable comprehensive logging.** Log alert, flow, and TLS traffic to analyze threats.
5. **Use custom encryption for sensitive workloads.** Enforce `CUSTOMER_KMS` encryption via governance.
6. **Monitor firewall health.** Set up CloudWatch alarms on firewall metrics and log volumes.
7. **Test policies before production.** Use development policies to validate rule behavior.

## Cross-References

- Firewalls reference [`NetworkFirewallPolicy`](networkfirewallpolicy.md) resources
- Policies reference [`NetworkFirewallRuleGroup`](networkfirewallrulegroup.md) resources
- All resources are governed by [`NetworkFirewallConfig`](networkfirewallconfig.md) profiles
