---
title: NetworkFirewallRuleGroup — Creating and Managing Rule Groups
description: "The `NetworkFirewallRuleGroup` resource creates and manages AWS Network Firewall rule groups."
doc_type: reference
---
# NetworkFirewallRuleGroup — Creating and Managing Rule Groups

The `NetworkFirewallRuleGroup` resource creates and manages AWS Network Firewall rule groups. A rule group is a reusable collection of stateless or stateful inspection rules that are referenced by firewall policies.

## What It Does

A `NetworkFirewallRuleGroup`:
- Defines inspection rules for traffic (stateless L3/L4 or stateful protocol inspection)
- Supports structured rule definitions or Suricata flat-format rule strings
- Can be referenced by multiple firewall policies
- Supports encryption via customer-managed KMS keys
- Applies governance via `NetworkFirewallConfig` profiles

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `NetworkFirewallConfig` governance profile to apply |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the rule group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (safe) or `"delete"` |

### Rule Group Properties

| Field | Type | Required | Purpose |
|---|---|---|---|
| `type` | string | yes | Rule group type: `STATELESS` or `STATEFUL` |
| `capacity` | integer | yes | Maximum capacity in Capacity Units (immutable after creation) |
| `description` | string | no | Human-readable description |
| `analyzeRuleGroup` | boolean | no | (Stateless only) Run asymmetric-routing analysis on the rule group; default `false` |

### Rule Definitions

Choose ONE of the following:

| Field | Type | Purpose |
|---|---|---|
| `ruleGroup` | object | Structured rule definition (stateless or stateful rules with variables) |
| `rules` | string | Suricata flat-format rules (mutually exclusive with `ruleGroup`) |

### Encryption

| Field | Type | Default | Purpose |
|---|---|---|---|
| `encryptionType` | string | `""` | Encryption type (governance-driven): `AWS_OWNED_KMS_KEY` or `CUSTOMER_KMS` |
| `kmsKeyId` | string | `""` | KMS key ARN/ID for CUSTOMER_KMS encryption |
| `kmsKeyRef` | string | `""` | Reference to a local KMSKey CR (mutually exclusive with `kmsKeyId`) |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Naming Convention

- **Default template:** `{namespace}-{name}`
- **Cloud resource name:** 1–128 characters, alphanumeric and hyphens only
- **Predicted ARN (stateful):** `arn:aws:network-firewall:<region>:<account>:stateful-rulegroup/<name>`
- **Predicted ARN (stateless):** `arn:aws:network-firewall:<region>:<account>:stateless-rulegroup/<name>`

Use `spec.nameOverride` to set a custom identifier if the default template doesn't fit your naming scheme.

## Example: Stateless Rule Group (Allow HTTPS)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: allow-https
  namespace: security-prod
spec:
  configRef: production
  type: STATELESS
  capacity: 100
  description: "Allow HTTPS traffic"
  
  ruleGroup:
    ruleVariables:
      ipSets:
        HOME_NET:
          definition:
            - "10.0.0.0/8"
            - "172.16.0.0/12"
    rulesSource:
      statelessRulesAndCustomActions:
        statelessRules:
          - priority: 100
            ruleDefinition:
              actions:
                - "aws:pass"
              matchAttributes:
                protocols:
                  - 6  # TCP
                destinations:
                  - addressDefinition: "0.0.0.0/0"
                destinationPorts:
                  - fromPort: 443
                    toPort: 443
                sources:
                  - addressDefinition: "0.0.0.0/0"
  
  tags:
    purpose: security
    rule-type: allowlist
```

Result:
- Stateless rule group named `security-prod-allow-https`
- Allows TCP port 443 (HTTPS) from anywhere to anywhere
- Governance profile (`production`) applies mandatory controls

## Example: Stateful Rule Group (Block SSH)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: block-ssh
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 100
  description: "Block SSH (port 22) inbound"
  
  ruleGroup:
    ruleVariables:
      ipSets:
        INTERNAL:
          definition:
            - "10.0.0.0/8"
    rulesSource:
      statefulRules:
        - action: DROP
          header:
            protocol: TCP
            source: "0.0.0.0/0"
            sourcePort: "ANY"
            destination: "ANY"
            destinationPort: "22"
            direction: FORWARD
          ruleOptions:
            - keyword: sid
              settings:
                - "1"
            - keyword: msg
              settings:
                - "Block SSH"
    statefulRuleOptions:
      ruleOrder: STRICT_ORDER
  
  tags:
    purpose: security
    rule-type: blocklist
```

Result:
- Stateful rule group named `security-prod-block-ssh`
- Drops all inbound TCP traffic on port 22 (SSH)
- Uses structured stateful rules with Suricata options

## Example: Domain List Rule Group (Blocklist)

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: block-malicious-domains
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 500
  description: "Block known malicious domains"
  
  ruleGroup:
    rulesSource:
      rulesSourceList:
        targets:
          - ".example-malware.com"
          - ".c2-server.net"
          - ".phishing-site.org"
        targetTypes:
          - HTTP_HOST
          - TLS_SNI
        generatedRulesType: DENYLIST
```

Result:
- Blocks HTTP and TLS traffic to specified malicious domains
- Traffic to listed domains is denied
- Much simpler than writing individual Suricata rules

## Status Fields

After creation, the rule group exposes status fields:

| Field | Type | Meaning |
|---|---|---|
| `status.resourceName` | string | The resolved rule group name (from naming template or override) |
| `status.namingStatus` | string | `"valid"` if all naming tokens resolved, `"invalid-unresolved-tokens"` otherwise |
| `status.predictedArn` | string | The predicted AWS ARN (available before creation) |

## Governance Fields

The following fields are governance-driven via `NetworkFirewallConfig`:

| Field | Governance Behavior |
|---|---|
| `encryptionType` | Falls through cascade: mandatory → spec → defaults |
| `tags`, `syncedLabels`, `syncedAnnotations` | Merges governance + spec values |

If `encryptionType` is set in the mandatory tier of `NetworkFirewallConfig`, all rule groups use that encryption type regardless of their `spec.encryptionType`.

## Advanced: Reference Sets (External IP Lists)

For stateless rules that reference external IP lists, use `referenceSets.ipSetReferences`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: allow-trusted-ips
  namespace: security-prod
spec:
  type: STATELESS
  capacity: 100
  
  ruleGroup:
    referenceSets:
      ipSetReferences:
        TRUSTED_PARTNERS:
          referenceArn: "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0"
    ruleVariables:
      ipSets:
        INTERNAL_NETS:
          definition:
            - "10.0.0.0/8"
    rulesSource:
      statelessRulesAndCustomActions:
        statelessRules:
          - priority: 100
            ruleDefinition:
              actions:
                - "aws:pass"
              matchAttributes:
                protocols:
                  - 6
                sources:
                  - addressDefinition: "$TRUSTED_PARTNERS"
```

Reference sets allow dynamic IP list lookups without hardcoding addresses in the rule group.

## Advanced: Suricata Flat-Format Rules

For complex stateful inspection, use raw Suricata rules in a single string:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: NetworkFirewallRuleGroup
metadata:
  name: suricata-rules
  namespace: security-prod
spec:
  configRef: production
  type: STATEFUL
  capacity: 1000
  
  # Mutually exclusive with ruleGroup
  rules: |
    pass tcp $HOME_NET any -> $EXTERNAL_NET 443 (msg:"Allow HTTPS"; sid:1; rev:1;)
    drop tcp $EXTERNAL_NET any -> $HOME_NET 22 (msg:"Block SSH"; sid:2; rev:1;)
    alert tcp any any -> any 25 (msg:"SMTP traffic"; sid:3; rev:1;)
```

Use this pattern when:
- You have complex Suricata rules from another firewall or IDS
- You need full Suricata syntax (sid, rev, threshold, etc.)
- Rules cannot be expressed in structured form

## Immutable Fields

After creation, these fields cannot be changed:

| Field | Reason |
|---|---|
| `type` | STATELESS and STATEFUL have different rule evaluation semantics |
| `capacity` | AWS requires capacity reservation at creation; changing it would require recreating the rule group |

To change these fields, delete and recreate the resource.

## Best Practices

1. **Organize rules by function.** Create focused rule groups (allow-https, block-ssh) rather than one monolithic group.
2. **Use stateless for L3/L4.** Stateless rules are faster for basic protocol inspection; use stateful only when you need protocol state.
3. **Set capacity appropriately.** Capacity units vary by rule type; allocate generously (unused capacity doesn't incur charges).
4. **Use variable references.** Define IP sets and port sets as variables for reuse and maintainability.
5. **Test rules locally.** Test firewall rules in a development cluster before promoting to production.
6. **Version your rule groups.** Consider tagging rule groups with version information (e.g., `v1`, `v2`).

## Cross-References

- Rule groups are referenced by [`NetworkFirewallPolicy`](networkfirewallpolicy.md) via ARN or reference
- Policies are referenced by [`NetworkFirewallFirewall`](networkfirewallfirewall.md)
