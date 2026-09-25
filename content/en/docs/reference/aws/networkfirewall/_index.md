---
title: AWS Network Firewall Family
description: Deploy and manage AWS Network Firewall — the managed, stateful network firewall service for VPC protection.
doc_type: reference
weight: 370
---
# AWS Network Firewall Family

Deploy and manage AWS Network Firewall — the managed, stateful network firewall service for VPC protection.

## What It Is

AWS Network Firewall is a managed firewall that inspects traffic at VPC subnet boundaries using stateless and stateful rule evaluation. A typical deployment consists of:

- **Rule Groups** — Collections of stateless or stateful inspection rules (created once, reused across policies)
- **Firewall Policy** — A policy that references rule groups and defines default actions for unmatched traffic
- **Firewall** — The actual firewall instance deployed in VPC subnets, associated with a policy

## Resources in This Family

| Resource | Purpose |
|---|---|
| [`NetworkFirewallConfig`](networkfirewallconfig.md) | Governance CRD defining mandatory and default controls across all firewalls |
| [`NetworkFirewallRuleGroup`](networkfirewallrulegroup.md) | Creates stateless or stateful rule groups (foundation for policies) |
| [`NetworkFirewallPolicy`](networkfirewallpolicy.md) | Bundles rule groups and defines rule evaluation order and defaults |
| [`NetworkFirewallFirewall`](networkfirewallfirewall.md) | Deploys the firewall at VPC subnet boundaries |

## Typical Architecture

```
NetworkFirewallConfig (governance profile)
  ↓
  ├→ NetworkFirewallRuleGroup (block-ssh)
  ├→ NetworkFirewallRuleGroup (allow-https)
  │
  └→ NetworkFirewallPolicy (production-policy)
       ↓
       └→ NetworkFirewallFirewall (perimeter-fw)
```

1. Platform teams define governance policies via `NetworkFirewallConfig` profiles (e.g., `production`, `development`)
2. Teams create rule groups (stateless for basic L3/L4 inspection, stateful for protocol inspection)
3. Teams bundle rule groups into a policy
4. The firewall instance references the policy and deploys in VPC subnets

## Governance Model

All four resources support the two-tier governance cascade via `NetworkFirewallConfig`:

- **Mandatory tier** — Controls that cannot be overridden (e.g., all firewalls must use CUSTOMER_KMS encryption)
- **Defaults tier** — Sensible baselines that developers can override

Example mandatory controls:
- Encryption type (AWS_OWNED_KMS_KEY or CUSTOMER_KMS)
- Deletion and policy-change protection
- Stateful rule evaluation order and default actions
- Logging destinations (S3, CloudWatch Logs, Kinesis Data Firehose)

Resources select which governance profile to apply via `spec.configRef`:

```yaml
spec:
  configRef: production  # Selects NetworkFirewallConfig/production
```

If omitted, `general-policy` is used by default.

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** 1–128 characters, alphanumeric and hyphens only
- **Predicted ARN format:**
  - Rule Group (stateful): `arn:aws:network-firewall:<region>:<account>:stateful-rulegroup/<name>`
  - Rule Group (stateless): `arn:aws:network-firewall:<region>:<account>:stateless-rulegroup/<name>`
  - Policy: `arn:aws:network-firewall:<region>:<account>:firewall-policy/<name>`
  - Firewall: `arn:aws:network-firewall:<region>:<account>:firewall/<name>`

Use `spec.nameOverride` to bypass the template and set a custom name.

## Getting Started

1. **Define a governance profile** — Create a `NetworkFirewallConfig` with sensible defaults and any mandatory controls your organization requires.
2. **Create rule groups** — Define rule groups for your inspection logic (e.g., block SSH, allow HTTPS).
3. **Create a policy** — Reference the rule groups in a `NetworkFirewallPolicy` and define default actions.
4. **Deploy the firewall** — Create a `NetworkFirewallFirewall` that references the policy and subnets.

## Complete Example

See [`example-complete-deployment.md`](example-complete-deployment.md) for a production-ready deployment with:
- Governance profile (general-policy)
- Stateless rule group (allow-https)
- Stateful rule group (block-ssh)
- Firewall policy (perimeter-policy)
- Firewall instance (production-fw)

## Best Practices

1. **Use governance profiles.** Define organizational standards via `NetworkFirewallConfig` rather than repeating configuration on every resource.
2. **Separate stateless from stateful rules.** Stateless rules (L3/L4 inspection) are faster; use stateful only for protocol inspection.
3. **Organize rule groups by function.** Create focused rule groups (block-ssh, allow-https) rather than one monolithic group.
4. **Use retention for critical firewalls.** Set `spec.deletionPolicy: retain` for production firewalls to prevent accidental deletion.
5. **Log all traffic.** Enable alert, flow, and TLS logging via governance so you can inspect blocked traffic and tune rules.

## Further Reading

- [AWS Network Firewall User Guide](https://docs.aws.amazon.com/network-firewall/latest/userguide/)
- [Network Firewall Pricing](https://aws.amazon.com/network-firewall/pricing/)
- [ADR-010: Governance Cascade](https://github.com/kropath/kropath-core/blob/main/docs/adrs/010-governance-cascade.md)
