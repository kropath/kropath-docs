# WAFRuleGroup — AWS WAF Rule Groups

The `WAFRuleGroup` resource creates and manages AWS WAF rule groups. A rule group is a reusable set of WAF rules that can be shared across multiple web ACLs. Each rule group has a fixed WCU (Web ACL Capacity Unit) capacity set at creation time. Rule groups contain rule statements defining web request inspection logic — byte match, geo match, IP set reference, rate-based, SQL injection, XSS detection, and logical operators.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `WAFConfig` governance profile |
| `nameOverride` | string | `""` | Bypasses naming template; sets a custom rule group name |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the rule group in AWS when the CR is deleted; `"delete"` removes it |

### Rule Group Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scope` | string | `""` | `"CLOUDFRONT"` or `"REGIONAL"`; empty falls through to governance. **Immutable after creation.** |
| `capacity` | integer | required | WCU (Web ACL Capacity Unit) capacity; immutable after creation; must be > 0. Each rule statement type consumes a fixed WCU cost. |
| `visibilityConfig` | object | required | CloudWatch metrics and sampled request logging configuration |
| `visibilityConfig.cloudWatchMetricsEnabled` | boolean | true | Enable CloudWatch metrics; pointer (`*bool`) semantics |
| `visibilityConfig.metricName` | string | derived | CloudWatch metric name; if empty, derived from `status.resourceName` |
| `visibilityConfig.sampledRequestsEnabled` | boolean | true | Enable sampled request logging |
| `rules[]` | array | optional | Rules within the rule group (empty rule group is valid) |

### Rule Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Rule name; unique within the rule group |
| `priority` | integer | required | Evaluation order (lower = higher priority); unique within rule group |
| `statement` | object | required | Rule statement (see Statement Types in WAFWebACL documentation) |
| `action` | object | required | Action: `allow`, `block`, `captcha`, `challenge`, or `count` |
| `visibilityConfig` | object | optional | Per-rule CloudWatch/sampling config |
| `ruleLabels[]` | object | optional | Labels to apply to matching requests |
| `captchaConfig` | object | optional | Per-rule CAPTCHA immunity time override |
| `challengeConfig` | object | optional | Per-rule challenge immunity time override |

### Custom Response Bodies

| Field | Type | Purpose |
|---|---|---|
| `customResponseBodies` | map | Map of custom response body keys to definitions; `additionalProperties: {content: string, contentType: string}` |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |
| `description` | string | `""` | Human-readable description |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `status.resourceName` | string | Effective name after naming template substitution |
| `status.namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `status.ackResourceMetadata.arn` | string | WAF RuleGroup ARN (includes WAF-assigned UUID); read this to get the ARN for use in web ACLs |

**Note:** WAF RuleGroup ARNs include a WAF-assigned UUID that is only known after creation. Read `status.ackResourceMetadata.arn` to get the full ARN for referencing from web ACLs.

## Governance Cascade

Rule groups use the ten-level cascade:

```
KropathConfig.mandatory → WAFConfig.mandatory → Instance spec → WAFConfig.defaults → KropathConfig.defaults
```

- **`scope`** — Immutable after creation; mandatory and instance values override defaults
- **`cloudWatchMetricsEnabled` / `sampledRequestsEnabled`** — Pointer semantics; nil means defer
- **Tags, labels, annotations** — Merged additively across tiers

## WCU Capacity

Each rule statement type consumes a specific number of WCUs. The `capacity` field sets the total WCU budget for the rule group. The AWS WAF API validates that rules don't exceed capacity and returns a clear error if they do; the RGD does not pre-validate.

## Complete Examples

### Simple Rate-Limiting Rule Group

A rule group that enforces rate limits:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: rate-limit
  namespace: security
spec:
  configRef: general-policy
  scope: REGIONAL
  capacity: 50
  rules:
    - name: enforce-rate-limit
      priority: 0
      statement:
        rateBasedStatement:
          limit: 2000
          aggregateKeyType: IP
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: rate-limit-group
    sampledRequestsEnabled: true
```

**Usage:**

Reference this rule group from a web ACL:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: app-acl
spec:
  rules:
    - name: apply-rate-limiting
      priority: 0
      statement:
        ruleGroupReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/rulegroup/rate-limit/a1b2c3d4
      overrideAction:
        none: {}
```

### OWASP-Inspired Protection Rules

A rule group with multiple layers of protection:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: owasp-rules
  namespace: security
spec:
  configRef: production
  scope: REGIONAL
  capacity: 200
  rules:
    - name: sql-injection
      priority: 0
      statement:
        sqliMatchStatement:
          fieldToMatch:
            body: {}
          sensitivityLevel: HIGH
          textTransformations:
            - priority: 0
              type: URL_DECODE
            - priority: 1
              type: HTML_ENTITY_DECODE
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: xss-attack
      priority: 1
      statement:
        xssMatchStatement:
          fieldToMatch:
            queryString: {}
          textTransformations:
            - priority: 0
              type: URL_DECODE
            - priority: 1
              type: HTML_ENTITY_DECODE
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: path-traversal
      priority: 2
      statement:
        byteMatchStatement:
          fieldToMatch:
            uriPath: {}
          positionalConstraint: CONTAINS
          searchString: ".."
          textTransformations:
            - priority: 0
              type: URL_DECODE
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: owasp-rules
    sampledRequestsEnabled: true
```

### Geo-Blocking Rules

A rule group that blocks traffic from specific countries:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: geo-block
  namespace: compliance
spec:
  configRef: general-policy
  scope: REGIONAL
  capacity: 100
  rules:
    - name: block-embargoed-countries
      priority: 0
      statement:
        geoMatchStatement:
          countryCodes:
            - KP  # North Korea
            - IR  # Iran
            - SY  # Syria
            - CU  # Cuba
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: block-unknown-origin
      priority: 1
      statement:
        geoMatchStatement:
          countryCodes:
            - ZZ  # Unknown location
      action:
        count: {}  # Monitor only
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: geo-block
    sampledRequestsEnabled: true
```

### IP-Based Filtering

A rule group that references IP sets:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: ip-filtering
  namespace: security
spec:
  configRef: general-policy
  scope: REGIONAL
  capacity: 50
  rules:
    - name: allow-vpn-only
      priority: 0
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/corporate-vpn/b2c3d4e5
      action:
        allow: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: block-known-bots
      priority: 1
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/malicious-ips/c3d4e5f6
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: ip-filtering
    sampledRequestsEnabled: true
```

### Complex Rules with Custom Responses

A rule group with multiple rules and custom block responses:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFRuleGroup
metadata:
  name: api-protection
  namespace: apis
spec:
  configRef: production
  scope: REGIONAL
  capacity: 300
  rules:
    - name: api-rate-limit
      priority: 0
      statement:
        rateBasedStatement:
          limit: 1000
          aggregateKeyType: IP
      action:
        block:
          customResponse:
            responseCode: 429
            customResponseBodyKey: rate-limited
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: auth-required
      priority: 1
      statement:
        byteMatchStatement:
          fieldToMatch:
            singleHeader:
              name: authorization
          positionalConstraint: EXACTLY
          searchString: ""
      action:
        block:
          customResponse:
            responseCode: 401
            customResponseBodyKey: auth-required
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: content-type-validation
      priority: 2
      statement:
        byteMatchStatement:
          fieldToMatch:
            singleHeader:
              name: content-type
          positionalConstraint: CONTAINS
          searchString: "application/json"
      action:
        allow: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  customResponseBodies:
    rate-limited:
      content: '{"error": "Too many requests. Please try again later."}'
      contentType: APPLICATION_JSON
    auth-required:
      content: '{"error": "Authorization header required"}'
      contentType: APPLICATION_JSON
  tags:
    team: api-platform
    component: protection
  syncedLabels:
    critical: "true"
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: api-protection
    sampledRequestsEnabled: true
```

## Naming Convention

Rule group names are AWS account+region scoped — they must be unique within your account.

**Default template:** `{namespace}-{name}` → e.g., `security-owasp-rules`

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
- **Capacity immutability** — Once set, capacity cannot be changed; capacity is validated server-side
- **WCU calculation** — Each statement type has a fixed WCU cost; AWS validates total doesn't exceed capacity
- **No standalone test** — The RGD does not validate WCU capacity; AWS WAF API provides this validation
- **Shared across ACLs** — Reference the same rule group from multiple web ACLs via ARN
- **Custom response bodies** — Define custom responses and reference them from rules
- **Recursive statements** — `rateBasedStatement.scopeDownStatement` and others are opaque strings (Phase 1)

## Known Limitations (Phase 1)

- **Recursive statements** — Nested conditions are opaque strings; structured schema planned for Phase 2
- **WCU pre-validation** — No client-side WCU calculation; rely on AWS server-side validation

## Best Practices

1. **Plan capacity carefully** — Allocate enough WCU for current and future rules
2. **Reuse rule groups** — Create general-purpose rule groups and reference them from multiple ACLs
3. **Name for clarity** — Use descriptive names that indicate the rule group's purpose
4. **Document rule intent** — Use rule names and descriptions to explain what each rule protects against
5. **Monitor and adjust** — Use CloudWatch metrics to understand which rules are triggering
6. **Version via namespacing** — Use Kubernetes namespaces to version rule groups if needed

## Related Resources

- [WAFConfig](wafconfig.md) — Governance configuration reference
- [WAFWebACL](wafwebacl.md) — Web ACL resources that reference rule groups
- [WAFIPSet](wafipset.md) — IP sets for IP-based rule conditions
