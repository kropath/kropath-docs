---
title: NetworkFirewallConfig — Governance Configuration
description: "The `NetworkFirewallConfig` resource defines governance profiles that control Network Firewall behavior across your organization and namespaces."
doc_type: reference
---
# NetworkFirewallConfig — Governance Configuration

The `NetworkFirewallConfig` resource defines governance profiles that control Network Firewall behavior across your organization and namespaces. Platform teams create named profiles; developers and operators select the profile they need via `spec.configRef` on each firewall, policy, and rule group.

## Overview

`NetworkFirewallConfig` establishes two tiers of governance:

- **Mandatory tier** — Controls that cannot be overridden by developers (e.g., all firewalls must use CUSTOMER_KMS encryption, all stateful rules must use STRICT_ORDER evaluation)
- **Defaults tier** — Baseline values developers can override (e.g., default encryption type if not specified, default log destinations)

This two-tier approach lets platform teams enforce critical compliance and operational controls while preserving developer flexibility.

## Configuration Fields

### Mandatory Tier

Mandatory values **always apply** and override developer choices:

| Field | Type | Purpose |
|---|---|---|
| `deleteProtection` | boolean | If `true`, all firewalls have deletion protection enabled |
| `firewallPolicyChangeProtection` | boolean | If `true`, all firewalls cannot change their firewall policy |
| `subnetChangeProtection` | boolean | If `true`, all firewalls cannot change their subnet mappings |
| `encryptionType` | string | Forces encryption type: `AWS_OWNED_KMS_KEY` or `CUSTOMER_KMS` |
| `statefulRuleOrder` | string | Enforces rule evaluation order: `STRICT_ORDER` or `DEFAULT_ACTION_ORDER` |
| `statefulDefaultActions` | array | Enforces default stateful actions: `aws:drop_strict`, `aws:drop_established`, `aws:alert_strict`, `aws:alert_established` |
| `streamExceptionPolicy` | string | Enforces stream exception policy: `DROP`, `CONTINUE`, or `REJECT` |
| `loggingDestination` | object | Enforces logging destinations for alert, flow, and TLS logs |
| `namingTemplate` | string | Template for resource names (e.g., `"corp-{namespace}-{name}"`) |
| `tags` | map | Tags applied to all resources (cannot be removed) |
| `syncedLabels` | map | Labels on Kubernetes and cloud resources |
| `syncedAnnotations` | map | Annotations on Kubernetes and cloud resources |

### Defaults Tier

Default values apply only when **not specified** at the resource level:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `deleteProtection` | boolean | `true` | Default deletion protection (true = protected) |
| `firewallPolicyChangeProtection` | boolean | `true` | Default policy change protection |
| `subnetChangeProtection` | boolean | `true` | Default subnet change protection |
| `encryptionType` | string | `"AWS_OWNED_KMS_KEY"` | Default encryption type |
| `statefulRuleOrder` | string | `"STRICT_ORDER"` | Default rule evaluation order |
| `statefulDefaultActions` | array | `["aws:drop_strict"]` | Default stateful actions |
| `streamExceptionPolicy` | string | `"DROP"` | Default stream exception policy |
| `loggingDestination` | object | `{}` | Default logging (empty = no logging) |
| `namingTemplate` | string | `"{namespace}-{name}"` | Default naming template |
| `tags` | map | `{}` | Default tags for resources |
| `syncedLabels` | map | `{}` | Default labels |
| `syncedAnnotations` | map | `{}` | Default annotations |

**Key rule:** A field cannot be set in both mandatory and defaults tiers simultaneously (with non-empty values). Empty values (`""`, `false`, `[]`, `{}`) can appear in both tiers — they indicate "not set" and don't trigger the mutual-exclusion check.

## Example Profiles

### Conservative Baseline (general-policy)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallConfig
metadata:
  name: general-policy
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: general-policy
spec:
  mandatory: {}
  defaults:
    deleteProtection: true
    firewallPolicyChangeProtection: true
    subnetChangeProtection: true
    encryptionType: "AWS_OWNED_KMS_KEY"
    statefulRuleOrder: "STRICT_ORDER"
    statefulDefaultActions:
      - "aws:drop_strict"
    streamExceptionPolicy: "DROP"
    namingTemplate: "{namespace}-{name}"
    tags:
      managed-by: kropath
      team: platform
```

This profile uses sensible defaults: all protections enabled, strict rule evaluation, AWS-managed encryption. Developers can override most fields unless the mandatory tier restricts them.

### Production Hardened (production)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallConfig
metadata:
  name: production
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: production
spec:
  mandatory:
    deleteProtection: true                    # All production firewalls are protected
    firewallPolicyChangeProtection: true      # All firewalls are policy-locked
    subnetChangeProtection: true              # Prevent subnet changes
    encryptionType: "CUSTOMER_KMS"            # Force customer-managed encryption
    statefulRuleOrder: "STRICT_ORDER"         # Force strict rule order
    statefulDefaultActions:
      - "aws:drop_strict"
    streamExceptionPolicy: "DROP"
    loggingDestination:
      alertLogDestination:
        type: "CloudWatchLogs"
        destination:
          logGroup: "/aws/nfw/prod/alerts"
      flowLogDestination:
        type: "S3"
        destination:
          bucketName: "prod-nfw-logs"
          prefix: "flow/"
    tags:
      environment: production
      compliance: required
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
    tags:
      cost-center: prod-security
```

This hardened profile enforces strict controls for production workloads: customer encryption is mandatory, all protections are enabled, logging destinations are enforced. Developers cannot override these controls.

### Development (development)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallConfig
metadata:
  name: development
  namespace: kro-system
  labels:
    aws.kropath.run/resource-name: development
spec:
  mandatory: {}
  defaults:
    deleteProtection: false                   # Dev firewalls can be deleted
    firewallPolicyChangeProtection: false     # Flexible for experimentation
    subnetChangeProtection: false
    encryptionType: "AWS_OWNED_KMS_KEY"       # AWS-managed encryption is fine
    statefulRuleOrder: "DEFAULT_ACTION_ORDER" # More flexible rule order
    namingTemplate: "dev-{namespace}-{name}"
    tags:
      environment: development
```

This development profile minimizes overhead with optional protections and flexible configurations. No mandatory controls.

## Profile Selection

Resources select which `NetworkFirewallConfig` profile to use via `spec.configRef`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallFirewall
metadata:
  name: perimeter-fw
  namespace: security-prod
spec:
  configRef: production          # Uses the 'production' NetworkFirewallConfig profile
  vpcId: vpc-12345678
  subnetMappings:
    - subnetId: subnet-az1a
    - subnetId: subnet-az1b
  firewallPolicyArn: arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/prod-policy
```

If `configRef` is omitted or empty, the default `"general-policy"` profile is used.

All resources in the Network Firewall family support `configRef`:
- `NetworkFirewallRuleGroup`
- `NetworkFirewallPolicy`
- `NetworkFirewallFirewall`

## Cascade Semantics

When resolving firewall configuration, kropath merges settings from three sources in this order (lowest to highest priority):

1. **NetworkFirewallConfig defaults tier** — Platform baseline values
2. **Resource `spec` fields** — Developer overrides
3. **NetworkFirewallConfig mandatory tier** — Non-negotiable platform controls

The mandatory tier always wins. For example:

- If `NetworkFirewallConfig.mandatory.encryptionType = "CUSTOMER_KMS"`, all rule groups use CUSTOMER_KMS encryption regardless of their `spec.encryptionType`
- If `NetworkFirewallConfig.defaults.namingTemplate = "{namespace}-{name}"` and `spec.nameOverride = ""`, the resource uses the template
- If `NetworkFirewallConfig.mandatory.deleteProtection = true` and `spec.deleteProtection = false`, the firewall has deletion protection enabled (mandatory wins)

## Logging Destinations

The `loggingDestination` field in both mandatory and defaults tiers has three sub-objects:

- `alertLogDestination` — Logs of dropped/alerted packets
- `flowLogDestination` — Logs of all traffic (high volume)
- `tlsLogDestination` — TLS inspection logs (if TLS inspection is enabled)

Each destination is an object with:

| Field | Type | Purpose |
|---|---|---|
| `type` | string | Destination type: `S3`, `CloudWatchLogs`, or `KinesisDataFirehose` |
| `destination` | map | Destination-specific parameters |

**Destination parameters by type:**

| Type | Parameters |
|---|---|
| `S3` | `bucketName` (required), `prefix` (optional) |
| `CloudWatchLogs` | `logGroup` (required, e.g., `/aws/nfw/alerts`) |
| `KinesisDataFirehose` | `deliveryStream` (required, stream name) |

Example:
```yaml
loggingDestination:
  alertLogDestination:
    type: "CloudWatchLogs"
    destination:
      logGroup: "/aws/nfw/alerts"
  flowLogDestination:
    type: "S3"
    destination:
      bucketName: "nfw-flow-logs"
      prefix: "prod/"
```

## Best Practices

1. **Use mandatory tier sparingly.** Reserve it for compliance-critical controls (encryption, deletion protection, logging).
2. **Provide sensible defaults.** The defaults tier should reflect your organization's standard practices without blocking flexibility.
3. **Version your profiles.** Consider naming profiles by compliance/environment level rather than team names (profiles can outlive team reorganizations).
4. **Set logging destinations.** Production firewalls should always have logging enabled via governance to detect and respond to threats.
5. **Enforce encryption in sensitive environments.** Use mandatory `encryptionType: "CUSTOMER_KMS"` for production profiles.

## Status Fields

After creation, the config CR exposes status fields:

| Field | Type | Meaning |
|---|---|---|
| `status.effectiveConfig` | object | The computed result of merging KropathConfig + NetworkFirewallConfig tiers; used by RGDs |
| `status.effectiveConfig.aws.region` | string | AWS region (written by kropath-controller) |
| `status.effectiveConfig.aws.accountId` | string | AWS account ID (written by kropath-controller) |
