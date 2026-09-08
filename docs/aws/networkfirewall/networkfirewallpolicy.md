# NetworkFirewallPolicy — Firewall Policies

The `NetworkFirewallPolicy` resource creates and manages AWS Network Firewall policies. A firewall policy bundles rule groups and defines the evaluation order and default actions for traffic that matches no rule.

## What It Does

A `NetworkFirewallPolicy`:
- References stateless and stateful rule groups
- Defines default actions for packets matching no rule
- Controls rule evaluation order (strict or default)
- Applies governance via `NetworkFirewallConfig` profiles
- Is referenced by `NetworkFirewallFirewall` resources

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `NetworkFirewallConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the policy name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Policy Properties

| Field | Type | Required | Purpose |
|---|---|---|---|
| `description` | string | no | Human-readable description |

### Stateless Processing

| Field | Type | Required | Purpose |
|---|---|---|---|
| `statelessDefaultActions` | array | yes | Default actions for stateless packets: `aws:pass`, `aws:drop`, `aws:forward_to_sfe` |
| `statelessFragmentDefaultActions` | array | yes | Default actions for fragmented packets |
| `statelessRuleGroupReferences` | array | no | Ordered list of stateless rule groups to apply |
| `statelessCustomActions` | array | no | Custom publish-metric actions |

### Stateful Processing

| Field | Type | Purpose |
|---|---|---|
| `statefulDefaultActions` | array | Default actions for unmatched stateful packets (governance-driven) |
| `statefulEngineOptions` | object | Stateful engine configuration (rule order, stream exception policy) |
| `statefulRuleGroupReferences` | array | Ordered list of stateful rule groups to apply |
| `policyVariables` | object | Suricata variable overrides (e.g., `HOME_NET`) |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionType` | string | `""` | Encryption type (governance-driven) |
| `kmsKeyId` | string | `""` | KMS key ARN/ID |
| `kmsKeyRef` | string | `""` | Reference to a local KMSKey CR |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** 1–128 characters, alphanumeric and hyphens only
- **Predicted ARN:** `arn:aws:network-firewall:<region>:<account>:firewall-policy/<name>`

## Example: Production Firewall Policy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallPolicy
metadata:
  name: production-policy
  namespace: security-prod
spec:
  configRef: production
  description: "Production perimeter firewall policy"
  
  # Stateless processing — default forward to stateful
  statelessDefaultActions:
    - aws:forward_to_sfe
  statelessFragmentDefaultActions:
    - aws:forward_to_sfe
  statelessRuleGroupReferences:
    - ruleGroupRef: allow-https        # Reference by name (same namespace)
      priority: 100
    - ruleGroupRef: allow-http         # Higher priority = evaluated first
      priority: 110
  
  # Stateful processing
  statefulDefaultActions:
    - aws:drop_strict                  # Drop all unmatched stateful packets
  statefulEngineOptions:
    ruleOrder: STRICT_ORDER            # Governance can override this
  statefulRuleGroupReferences:
    - ruleGroupRef: block-ssh
      priority: 100
      overrideAction: ""               # Use default DROP action
    - ruleGroupRef: block-malicious-domains
      priority: 110
  
  policyVariables:
    ruleVariables:
      HOME_NET:
        definition:
          - "10.0.0.0/8"
          - "172.16.0.0/12"
  
  tags:
    environment: production
    policy-version: "1.0"
```

Result:
- Firewall policy named `security-prod-production-policy`
- Stateless traffic is forwarded to stateful inspection
- Stateful traffic is evaluated against rule groups in priority order
- Unmatched packets are dropped (default action)
- All governance from `production` profile applies

## Example: Policy with ARN References

For rule groups in different namespaces or accounts, reference by ARN:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallPolicy
metadata:
  name: cross-namespace-policy
  namespace: security-prod
spec:
  configRef: general-policy
  
  statelessDefaultActions:
    - aws:forward_to_sfe
  statelessFragmentDefaultActions:
    - aws:forward_to_sfe
  statelessRuleGroupReferences:
    - resourceArn: "arn:aws:network-firewall:us-east-1:123456789012:stateless-rulegroup/shared-allow-https"
      priority: 100
  
  statefulDefaultActions:
    - aws:drop_strict
  statefulRuleGroupReferences:
    - resourceArn: "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/shared-block-ssh"
      priority: 100
```

Use `resourceArn` when:
- Rule groups are in different AWS accounts
- Rule groups are managed outside of Kubernetes
- Rule groups are shared across many firewall policies

## Status Fields

After creation, the policy exposes status fields:

| Field | Type | Meaning |
|---|---|---|
| `status.resourceName` | string | The resolved policy name |
| `status.namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `status.predictedArn` | string | The predicted AWS ARN |

## Governance Fields

The following fields are governance-driven via `NetworkFirewallConfig`:

| Field | Governance Behavior |
|---|---|
| `statefulRuleOrder` | Falls through: mandatory → spec → defaults |
| `statefulDefaultActions` | Falls through: mandatory → spec → defaults |
| `streamExceptionPolicy` | Falls through: mandatory → spec → defaults |
| `encryptionType` | Falls through: mandatory → spec → defaults |
| `tags`, `syncedLabels`, `syncedAnnotations` | Merges governance + spec values |

If `statefulRuleOrder` is set in the mandatory tier of `NetworkFirewallConfig`, all policies use that rule order regardless of their `spec.statefulEngineOptions.ruleOrder`.

## Rule Group References

Rule groups can be referenced by **name** (same namespace) or by **ARN**:

### By Name (KRO Reference)

```yaml
statelessRuleGroupReferences:
  - ruleGroupRef: allow-https
    priority: 100
```

The RGD reads `status.predictedArn` from the referenced `NetworkFirewallRuleGroup` CR and resolves it to the ARN.

### By ARN (Direct Reference)

```yaml
statelessRuleGroupReferences:
  - resourceArn: "arn:aws:network-firewall:us-east-1:123456789012:stateless-rulegroup/allow-https"
    priority: 100
```

Use direct ARN references for rule groups outside your Kubernetes cluster.

## Rule Evaluation Order

Stateless and stateful rule groups are evaluated in priority order (**lower number = higher priority**):

```yaml
statelessRuleGroupReferences:
  - ruleGroupRef: whitelist          # Priority 1 - evaluated first
    priority: 1
  - ruleGroupRef: blacklist          # Priority 2 - evaluated second
    priority: 2
```

The default action applies to packets that match no rule.

## Override Actions

For stateful rule group references, you can override the default action:

```yaml
statefulRuleGroupReferences:
  - ruleGroupRef: block-ssh
    priority: 100
    overrideAction: "DROP_TO_ALERT"   # Downgrade DROP to ALERT for monitoring
```

Use `overrideAction: "DROP_TO_ALERT"` to alert instead of drop during testing or monitoring phases.

## Best Practices

1. **Use default forward-to-stateful.** Most policies should forward stateless traffic to stateful inspection.
2. **Organize rule groups by priority.** Order rule groups so more specific or higher-priority rules are evaluated first.
3. **Test policies before production.** Create a development policy with the same rule groups to verify behavior.
4. **Use governance defaults.** Let governance set default actions, rule order, and encryption when possible.
5. **Monitor with ALERT.** Use `overrideAction: "DROP_TO_ALERT"` to monitor rules before enforcing them.

## Cross-References

- Policies reference [`NetworkFirewallRuleGroup`](networkfirewallrulegroup.md) resources
- Policies are referenced by [`NetworkFirewallFirewall`](networkfirewallfirewall.md) resources
