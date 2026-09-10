# WAFIPSet — AWS WAF IP Sets

The `WAFIPSet` resource creates and manages AWS WAF IP sets. An IP set is a collection of IPv4 or IPv6 CIDR ranges used in WAF rule statements to match web request source addresses. IP sets are standalone resources referenced by web ACLs and rule groups via their ARN in `ipSetReferenceStatement`.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `WAFConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets a custom IP set name |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the IP set in AWS when the CR is deleted; `"delete"` removes it |

### IP Set Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scope` | string | `""` | `"CLOUDFRONT"` or `"REGIONAL"`; empty falls through to governance. **Immutable after creation.** |
| `ipAddressVersion` | string | required | `"IPV4"` or `"IPV6"`; each IP set holds one version only |
| `addresses[]` | string | required | List of IP addresses or CIDR blocks; must contain at least one; WAF supports all CIDR ranges except /0 |
| `description` | string | `""` | Human-readable description |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags; converted to WAF array format |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `status.resourceName` | string | Effective name after naming template substitution |
| `status.namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `status.ackResourceMetadata.arn` | string | WAF IPSet ARN (includes WAF-assigned UUID); read this to get the ARN for use in rules |

**Note:** WAF IPSet ARNs include a WAF-assigned UUID that is only known after creation. Read `status.ackResourceMetadata.arn` to get the full ARN for referencing from rules and rule groups.

## Governance Cascade

IP sets use the ten-level cascade:

```
KropathConfig.mandatory → WAFConfig.mandatory → Instance spec → WAFConfig.defaults → KropathConfig.defaults
```

- **`scope`** — Immutable after creation; mandatory and instance values override defaults
- **Tags, labels, annotations** — Merged additively across tiers

## CIDR Notation

IP sets use CIDR notation for address ranges:

- **IPv4:** `203.0.113.0/24` represents 203.0.113.0 through 203.0.113.255
- **Single address:** `203.0.113.42/32` (IPv4) or `2001:db8::1/128` (IPv6)
- **IPv6:** `2001:db8::/32` for a large IPv6 range

**Constraint:** WAF does not accept `/0` ranges (all IPs). Use specific ranges instead.

## Complete Examples

### IPv4 Allowlist

An IP set allowing traffic from specific office networks:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: office-ips
  namespace: production
spec:
  configRef: general-policy
  scope: REGIONAL
  ipAddressVersion: IPV4
  addresses:
    - 203.0.113.0/24     # Office network 1
    - 198.51.100.0/24    # Office network 2
    - 192.0.2.50/32      # VPN gateway
  description: "Authorized office IP ranges"
  tags:
    type: allowlist
    managed-by: platform
```

### IPv6 Allowlist

An IP set for IPv6 traffic (e.g., for CDN or modern clients):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: ipv6-trusted
  namespace: production
spec:
  configRef: general-policy
  scope: REGIONAL
  ipAddressVersion: IPV6
  addresses:
    - 2001:db8::/32      # Trusted network
    - 2001:db9:1234::/48 # Partner network
  description: "Trusted IPv6 address ranges"
```

### Blocklist for Known Bad IPs

An IP set blocking traffic from known malicious sources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: malicious-ips
  namespace: security
spec:
  configRef: production
  scope: REGIONAL
  ipAddressVersion: IPV4
  addresses:
    - 192.0.2.100/32     # Known botnet C&C server
    - 198.51.100.50/32   # Identified scanner
    - 203.0.113.0/25     # Compromised datacenter
  description: "Known malicious IP addresses"
  tags:
    type: blocklist
    threat-level: high
  syncedLabels:
    security: "critical"
```

### CloudFront Allowlist

An IP set for CloudFront-protected APIs (CLOUDFRONT scope):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: cdn-cloudfront-ips
  namespace: security
spec:
  configRef: general-policy
  scope: CLOUDFRONT  # Must be CLOUDFRONT for CloudFront resources
  ipAddressVersion: IPV4
  addresses:
    - 76.223.100.0/23    # AWS CloudFront IP range (example)
    - 76.223.102.0/23    # AWS CloudFront IP range (example)
  description: "Allowed CloudFront edge locations"
```

### Geo-Distributed Partner Networks

An IP set with multiple regional partner networks:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: partner-networks
  namespace: integrations
spec:
  configRef: general-policy
  scope: REGIONAL
  ipAddressVersion: IPV4
  addresses:
    # US Partner - East
    - 198.51.100.0/24
    # US Partner - West
    - 203.0.113.0/24
    # EU Partner
    - 192.0.2.0/24
    # APAC Partner
    - 10.0.0.0/16
  description: "Authorized partner organization IP ranges"
  tags:
    type: allowlist
    purpose: b2b-integrations
  syncedLabels:
    partners: "trusted"
```

### Single IP Address

An IP set for a specific host or service:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: admin-access
  namespace: operations
spec:
  configRef: production
  scope: REGIONAL
  ipAddressVersion: IPV4
  addresses:
    - 203.0.113.42/32    # Admin workstation IP
    - 198.51.100.99/32   # Backup admin IP
  description: "Administrative access IPs"
  nameOverride: admin-ips  # Use custom naming
```

## Using IP Sets in Rules

Reference an IP set from a rule group or web ACL:

**In a WAFRuleGroup:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: allow-trusted
  namespace: security
spec:
  scope: REGIONAL
  capacity: 50
  rules:
    - name: allow-office-ips
      priority: 0
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/office-ips/a1b2c3d4
      action:
        allow: {}
```

**In a WAFWebACL:**

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: secure-app
  namespace: production
spec:
  scope: REGIONAL
  rules:
    - name: block-malicious
      priority: 0
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/malicious-ips/b2c3d4e5
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  defaultAction:
    allow: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: secure-app
    sampledRequestsEnabled: true
```

## Naming Convention

IP set names are AWS account+region scoped.

**Default template:** `{namespace}-{name}` → e.g., `security-malicious-ips`

**Available tokens:**
- `{namespace}` — Kubernetes namespace
- `{name}` — Kubernetes resource name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{configRef}` — WAFConfig profile name
- `{tag.<key>}` — Replace with tag value

**AWS constraints:** Alphanumeric characters and hyphens only.

## Key Behaviors

- **Scope immutability** — Once set, scope cannot be changed without deletion and recreation
- **Address version immutability** — IP address version cannot be changed; each IP set holds only IPv4 or IPv6
- **ARN-based references** — Read `status.ackResourceMetadata.arn` to get the full ARN for use in rules
- **Centralized management** — Define IP sets once, reference from multiple rules and ACLs
- **Efficient filtering** — IP set lookups are fast; use them for large allowlists/blocklists
- **Tag format conversion** — Maps are automatically converted to WAF's array format

## Best Practices

1. **Separate concerns** — Create distinct IP sets for allowlists, blocklists, and regional networks
2. **Version for tracking** — Use namespacing or naming conventions to track IP set versions
3. **Document purpose** — Use descriptions to explain when and why each IP set is used
4. **Regular reviews** — Periodically audit IP ranges to remove obsolete entries
5. **Monitor usage** — Reference the same IP set from multiple rules when possible
6. **Combine with other rules** — Use IP sets alongside other rule types for defense-in-depth

## Known Limitations

- **Single address version** — Each IP set holds either IPv4 or IPv6, not both
- **No inline CIDR validation** — AWS validates CIDR format server-side; invalid ranges cause deployment errors

## Related Resources

- [WAFWebACL](wafwebacl.md) — Web ACLs that reference IP sets
- [WAFRuleGroup](wafrulegroup.md) — Rule groups that reference IP sets
- [WAFConfig](wafconfig.md) — Governance configuration reference
