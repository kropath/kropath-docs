# AWS WAF — Web Application Firewall

Amazon WAF provides application-layer protection for your web applications. The kropath platform provides managed Kubernetes resources for WAF governance, web ACLs, rule groups, and IP sets with built-in policy enforcement and environment-specific configuration profiles.

## Resources

- [WAFConfig](wafconfig.md) — Governance policies for WAF resources (scope, default action, visibility, naming)
- [WAFWebACL](wafwebacl.md) — Web Access Control Lists (the primary WAF policy resource)
- [WAFRuleGroup](wafrulegroup.md) — Reusable sets of WAF rules
- [WAFIPSet](wafipset.md) — IP address collections for rule conditions

## Quick Start

### 1. Create a governance profile

Deploy a `WAFConfig` CR to `kro-system` to define organization-wide policies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFConfig
metadata:
  name: general-policy
  namespace: kro-system
spec:
  defaults:
    scope: REGIONAL
    defaultAction: block
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
    namingTemplate: "{namespace}-{name}"
```

### 2. Create a web ACL

Deploy a `WAFWebACL` CR to protect your resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: main-acl
  namespace: production
spec:
  configRef: general-policy
  scope: REGIONAL
  rules:
    - name: rate-limit
      priority: 0
      statement:
        rateBasedStatement:
          limit: 2000
          aggregateKeyType: IP
      action:
        block: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: main-acl
    sampledRequestsEnabled: true
```

### 3. Create supporting resources (optional)

Define reusable rule groups and IP sets for complex policies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: block-ips
  namespace: production
spec:
  configRef: general-policy
  scope: REGIONAL
  capacity: 100
  rules:
    - name: block-malicious
      priority: 0
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/office-ips/a1b2c3d4
      action:
        block: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
```

## Key Concepts

### Governance Cascade

WAF resources use a **ten-level cascade** to resolve configuration, combining organization-wide (`KropathConfig`) and resource-type-specific (`WAFConfig`) policies with instance-level overrides:

```
KropathConfig.mandatory → WAFConfig.mandatory → Instance spec → WAFConfig.defaults → KropathConfig.defaults
```

This allows platform teams to enforce security policies while giving teams the flexibility to override when needed.

### Scope and Immutability

WAF resources operate at either `CLOUDFRONT` (global edge locations) or `REGIONAL` (AWS region) scope. The scope is **immutable after creation** — it cannot be changed without deleting and recreating the resource.

### Policy Enforcement

**Mandatory tier** fields override instance specifications — platform requirements that instances cannot bypass. Use the mandatory tier to enforce compliance requirements like "default action must be block" or "must log all requests."

**Defaults tier** fields apply only when an instance specification is empty, providing sensible defaults without blocking team overrides.

### ARN-Based References

WAF resources use Amazon Resource Names (ARNs) to reference each other:
- Rule groups and IP sets are referenced by ARN within web ACL rules
- Web ACLs are referenced by ARN when associating with AWS infrastructure (CloudFront distributions, ALBs, API Gateways)
- Read `status.ackResourceMetadata.arn` from the child Kubernetes resource to get the ARN for use in other resources

### Tag Format

WAFv2 uses an array-based tag format (`[{key: "x", value: "y"}]`) instead of maps. The kropath platform converts your map-style tags automatically — you write normal Kubernetes metadata and it's converted to the WAF format behind the scenes.

## Common Workflows

### Enforce Organization-Wide Policy

Platform teams deploy a `WAFConfig` profile in `kro-system` with mandatory fields:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFConfig
metadata:
  name: production
  namespace: kro-system
spec:
  mandatory:
    scope: REGIONAL
    defaultAction: block
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
    tags:
      environment: production
      managed-by: platform
  defaults:
    namingTemplate: "prod-{namespace}-{name}"
```

Application teams use `spec.configRef: production` to adopt the policy, and the platform's rules are automatically enforced.

### Define Reusable Rules

Create a `WAFRuleGroup` with common patterns, then reference it from multiple `WAFWebACL` resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: owasp-rules
  namespace: security
spec:
  scope: REGIONAL
  capacity: 200
  rules:
    - name: sqli-protection
      priority: 0
      statement:
        sqliMatchStatement:
          fieldToMatch:
            body: {}
          sensitivityLevel: HIGH
      action:
        block: {}
```

Reference it in web ACLs:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: app-acl
spec:
  rules:
    - name: use-owasp
      priority: 0
      statement:
        ruleGroupReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/rulegroup/owasp-rules/a1b2c3d4
      overrideAction:
        none: {}
```

### Manage IP Allowlists/Blocklists

Create an `WAFIPSet` to manage allowed or blocked IP ranges, then reference it in rules:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFIPSet
metadata:
  name: office-ips
  namespace: production
spec:
  scope: REGIONAL
  ipAddressVersion: IPV4
  addresses:
    - 203.0.113.0/24
    - 198.51.100.0/24
```

## Known Limitations (Phase 1)

- **Recursive statements** — Complex nested rule conditions (`andStatement`, `orStatement`, `notStatement`) are passed through as opaque JSON/YAML strings. Structured schema is planned for Phase 2.
- **Managed rule groups** — Top-level convenience references are not yet available; use ARN strings directly.
- **Structured statement types** — Full structured schema for all WAF statement types is deferred to Phase 2.

## Best Practices

1. **Use governance profiles** — Deploy a `WAFConfig` profile in `kro-system` to codify your organization's policies.
2. **Reference, don't duplicate** — Create reusable `WAFRuleGroup` and `WAFIPSet` resources instead of embedding rules in every web ACL.
3. **Immutability awareness** — Plan scope carefully before creating resources; changing scope later requires deletion and recreation.
4. **Tag consistently** — Use `syncedLabels` to ensure metadata is consistent across Kubernetes and AWS.
5. **Monitor and log** — Enable `cloudWatchMetricsEnabled` and `sampledRequestsEnabled` to gain visibility into traffic patterns.

## Related Documentation

- [WAFConfig](wafconfig.md) — Detailed governance configuration reference
- [WAFWebACL](wafwebacl.md) — Web ACL resource reference and examples
- [WAFRuleGroup](wafrulegroup.md) — Rule group reference
- [WAFIPSet](wafipset.md) — IP set reference
- [kropath Engineering Standards](../../engineering-standards.md) — Shared platform conventions
