---
title: WAFWebACL — AWS WAF Web Access Control Lists
description: "The `WAFWebACL` resource creates and manages AWS WAF web access control lists (ACLs)."
doc_type: reference
---
# WAFWebACL — AWS WAF Web Access Control Lists

The `WAFWebACL` resource creates and manages AWS WAF web access control lists (ACLs). A web ACL defines a default action, a set of rules with custom and managed rule groups, visibility configuration, and optional logging. Web ACLs are associated with AWS infrastructure (CloudFront distributions, ALBs, API Gateways, AppSync, Cognito) to provide application-layer protection.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects the `WAFConfig` governance profile (e.g., `production`, `strict-security`) |
| `nameOverride` | string | `""` | Bypasses naming template; sets a custom web ACL name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` keeps the web ACL in AWS when the CR is deleted; `"delete"` removes it |

### Web ACL Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `scope` | string | `""` | `"CLOUDFRONT"` or `"REGIONAL"`; empty falls through to governance. **Immutable after creation.** |
| `defaultAction` | object | absent | Default action when no rule matches. Optional at the kropath level; when absent or empty, governance provides the value via cascade. `allow` and `block` are mutually exclusive (validated on child ACK CR). |
| `defaultAction.allow` | object | — | Allow the request; optional `customRequestHandling` |
| `defaultAction.block` | object | — | Block the request; optional `customResponse` |
| `visibilityConfig` | object | required | CloudWatch metrics and sampled request logging configuration |
| `visibilityConfig.cloudWatchMetricsEnabled` | boolean | true | Enable CloudWatch metrics; nil falls through to governance; pointer (`*bool`) semantics to distinguish "not set" from "explicitly false" |
| `visibilityConfig.metricName` | string | derived | CloudWatch metric name; if empty, derived from `status.resourceName` |
| `visibilityConfig.sampledRequestsEnabled` | boolean | true | Enable sampled request logging to CloudWatch Logs |
| `rules[]` | array | optional | Rules to evaluate before applying default action |

### Rule Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Rule name; unique within the web ACL |
| `priority` | integer | required | Evaluation order (lower = higher priority); unique within the web ACL |
| `statement` | object | required | Rule statement defining the match condition (see Statement Types below) |
| `action` | object | — | Action for custom rules: `allow`, `block`, `captcha`, `challenge`, or `count`. Mutually exclusive with `overrideAction`. |
| `overrideAction` | object | — | Override action for rule group references and managed rule groups: `count` or `none`. Mutually exclusive with `action`. |
| `visibilityConfig` | object | — | Per-rule CloudWatch/sampling config |
| `ruleLabels[]` | object | — | Labels to apply to matching requests; each has `name` (string) |
| `captchaConfig` | object | — | Per-rule CAPTCHA immunity time override |
| `challengeConfig` | object | — | Per-rule challenge immunity time override |

### Statement Types

All statement types from AWS WAFv2 are available. Non-recursive types are available as structured objects; recursive types are passed through as opaque strings (Phase 1):

| Statement Type | Structured? | Notes |
|---|---|---|
| `byteMatchStatement` | ✓ | Match request bytes against a value |
| `geoMatchStatement` | ✓ | Match country codes |
| `ipSetReferenceStatement` | ✓ | Reference an IP set by ARN |
| `labelMatchStatement` | ✓ | Match labels on requests |
| `rateBasedStatement` | ✓ | Rate limiting (with optional `scopeDownStatement` as opaque string) |
| `regexMatchStatement` | ✓ | Match regex patterns |
| `regexPatternSetReferenceStatement` | ✓ | Reference a regex pattern set by ARN |
| `sizeConstraintStatement` | ✓ | Match request size constraints |
| `sqliMatchStatement` | ✓ | SQL injection detection |
| `xssMatchStatement` | ✓ | Cross-site scripting detection |
| `managedRuleGroupStatement` | ✓ | AWS Managed Rules; includes `vendorName`, `name`, excluded rules, overrides, and `scopeDownStatement` (opaque) |
| `andStatement` | ✗ (opaque string, Phase 1) | Nested statements with AND logic |
| `notStatement` | ✗ (opaque string, Phase 1) | Negation of a nested statement |
| `orStatement` | ✗ (opaque string, Phase 1) | Nested statements with OR logic |
| `ruleGroupReferenceStatement` | ✓ | Reference a rule group by ARN |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags; converted to WAF array format automatically |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

### CAPTCHA and Challenge (WebACL-Level Config)

| Field | Type | Purpose |
|---|---|---|
| `captchaConfig` | object | WebACL-level default CAPTCHA immunity time |
| `captchaConfig.immunityTimeProperty.immunityTime` | integer | CAPTCHA immunity duration in seconds |
| `challengeConfig` | object | WebACL-level default challenge immunity time |
| `challengeConfig.immunityTimeProperty.immunityTime` | integer | Challenge immunity duration in seconds |

### Custom Response Bodies

| Field | Type | Purpose |
|---|---|---|
| `customResponseBodies` | map | Map of custom response body keys to definitions; `additionalProperties: {content: string, contentType: string}` |

### Logging Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `loggingConfiguration` | object | — | Logging destination and filter configuration (optional) |
| `loggingConfiguration.logDestinationConfigs[]` | string | — | ARNs of logging destinations (Kinesis/CloudWatch/S3); required if logging is enabled |
| `loggingConfiguration.loggingFilter` | object | — | Filters controlling which requests are logged; `defaultBehavior` is `"KEEP"` or `"DROP"`; `filters[]` array with behavior, conditions, requirement |
| `loggingConfiguration.redactedFields[]` | object | — | Request components redacted from logs (discriminated union); e.g., `singleHeader: {name: "authorization"}` |

### Association Configuration

| Field | Type | Purpose |
|---|---|---|
| `associationConfig` | object | Request body size inspection limits per resource type |
| `associationConfig.requestBody` | map | Map of resource type to `{defaultSizeInspectionLimit: string}` (KB_8, KB_16, KB_32, KB_48, KB_64) |

Valid resource types: `API_GATEWAY`, `APP_RUNNER_SERVICE`, `COGNITO_USER_POOL`, `VERIFIED_ACCESS_INSTANCE`, `APPLICATION_LOAD_BALANCER`

### Additional Configuration

| Field | Type | Purpose |
|---|---|---|
| `tokenDomains[]` | string | Additional domains for Application Integration SDK tokens |
| `description` | string | Human-readable description |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `status.resourceName` | string | Effective name after naming template substitution |
| `status.namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `status.ackResourceMetadata.arn` | string | WAF WebACL ARN (includes WAF-assigned UUID); read this to get the ARN for use in AWS infrastructure associations |

**Note:** WAF WebACL ARNs include a WAF-assigned UUID (`arn:aws:wafv2:<region>:<account_id>:regional/webacl/<name>/<id>`) that is only known after creation. Read `status.ackResourceMetadata.arn` at runtime to get the full ARN.

## Governance Cascade

Web ACLs use the ten-level cascade to resolve all governance fields:

```
KropathConfig.mandatory → WAFConfig.mandatory → Instance spec → WAFConfig.defaults → KropathConfig.defaults
```

- **`scope`** — Mandatory and instance values override defaults; immutable after creation
- **`defaultAction`** — When mandatory governance overrides, custom request/response handling is dropped
- **`cloudWatchMetricsEnabled` / `sampledRequestsEnabled`** — Pointer semantics; nil means "not set, defer to next tier"
- **Tags, labels, annotations** — Merged additively across all tiers

## Complete Examples

### Minimal Web ACL (Default Action Only)

A simple ACL that blocks all traffic by default:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: simple-acl
  namespace: production
spec:
  configRef: general-policy
  scope: REGIONAL
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    sampledRequestsEnabled: true
```

**Result:**
- Scope and default action inherited from governance
- No custom rules; all traffic evaluated against default action
- CloudWatch metrics and sampling enabled

### Web ACL with Custom Rules

A web ACL with multiple custom rules including rate limiting and SQL injection protection:

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
        sampledRequestsEnabled: true
    - name: protect-admin
      priority: 1
      statement:
        byteMatchStatement:
          fieldToMatch:
            uriPath: {}
          positionalConstraint: STARTS_WITH
          searchString: "/admin"
          textTransformations:
            - priority: 0
              type: LOWERCASE
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  defaultAction:
    allow: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: main-acl
    sampledRequestsEnabled: true
```

**Result:**
- Rate limiting at 2000 requests/IP
- Admin paths blocked
- All other traffic allowed
- Full visibility via CloudWatch

### Web ACL with Managed Rules

A web ACL using AWS Managed Rules for OWASP protection:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: owasp-acl
  namespace: production
spec:
  configRef: production
  scope: REGIONAL
  rules:
    - name: aws-managed-rules
      priority: 0
      statement:
        managedRuleGroupStatement:
          vendorName: AWS
          name: AWSManagedRulesCommonRuleSet
          excludedRules:
            - name: SizeRestrictions_BODY
            - name: GenericRFI_BODY
          ruleActionOverrides:
            - name: SQLi_BODY
              actionToUse:
                count: {}
      overrideAction:
        none: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  defaultAction:
    block: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: owasp-protection
    sampledRequestsEnabled: true
```

**Result:**
- AWS Managed Rules (OWASP Core Rule Set) applied
- Specific rules excluded to reduce false positives
- SQL injection rule set to count-only (monitoring mode)
- Block default for other traffic

### Web ACL with Rule Group References

A web ACL referencing reusable rule groups and IP sets:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: app-acl
  namespace: production
spec:
  configRef: production
  scope: REGIONAL
  rules:
    - name: block-malicious-ips
      priority: 0
      statement:
        ipSetReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/ipset/malicious-ips/a1b2c3d4
      action:
        block: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
    - name: custom-rules
      priority: 1
      statement:
        ruleGroupReferenceStatement:
          arn: arn:aws:wafv2:us-east-1:123456789012:regional/rulegroup/custom-rules/b2c3d4e5
      overrideAction:
        none: {}
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  defaultAction:
    allow: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: app-acl
    sampledRequestsEnabled: true
```

**Result:**
- IP sets and rule groups referenced by ARN
- Centralized rules updated once, applied everywhere
- Combined protection from IP lists and custom rules

### Web ACL with Logging and Custom Responses

A web ACL with detailed logging and custom block responses:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: WAFWebACL
metadata:
  name: secure-acl
  namespace: production
spec:
  configRef: strict-security
  scope: REGIONAL
  rules:
    - name: block-attack
      priority: 0
      statement:
        sqliMatchStatement:
          fieldToMatch:
            body: {}
          sensitivityLevel: HIGH
      action:
        block:
          customResponse:
            responseCode: 403
            customResponseBodyKey: blocked-body
      visibilityConfig:
        cloudWatchMetricsEnabled: true
        sampledRequestsEnabled: true
  customResponseBodies:
    blocked-body:
      content: "<html><body><h1>Access Denied</h1><p>Your request has been blocked by WAF.</p></body></html>"
      contentType: TEXT_HTML
  loggingConfiguration:
    logDestinationConfigs:
      - arn:aws:logs:us-east-1:123456789012:log-group:/aws/waf/production
    loggingFilter:
      defaultBehavior: KEEP
      filters:
        - behavior: KEEP
          conditions:
            - actionCondition:
                action: BLOCK
          requirement: MEETS_ANY
    redactedFields:
      - singleHeader:
          name: authorization
      - singleHeader:
          name: cookie
  defaultAction:
    allow: {}
  visibilityConfig:
    cloudWatchMetricsEnabled: true
    metricName: secure-acl
    sampledRequestsEnabled: true
  associationConfig:
    requestBody:
      API_GATEWAY:
        defaultSizeInspectionLimit: KB_64
```

**Result:**
- SQL injection attacks blocked with custom 403 response
- All requests logged to CloudWatch
- Authorization headers and cookies redacted from logs
- Request body inspection enabled for API Gateway

## Key Behaviors

- **Scope immutability** — Once set, scope cannot be changed without deleting and recreating the web ACL
- **Governance override** — When mandatory governance overrides `defaultAction`, custom request handling is dropped
- **Optional defaultAction** — When `spec.defaultAction` is absent or empty, the cascade resolves via governance; an empty object `{}` triggers the cascade, not a hard error
- **ARN-based references** — Rule groups and IP sets are referenced by ARN in statements; read `status.ackResourceMetadata.arn` from sibling resources
- **Tag format conversion** — Maps are automatically converted to WAF's array format (`[{key, value}]`)
- **Profile fallback** — If the referenced `WAFConfig` profile doesn't exist, falls back to `general-policy`

## Known Limitations (Phase 1)

- **Recursive statements** — Complex nested conditions (`andStatement`, `orStatement`, `notStatement`) are opaque strings; structured schema planned for Phase 2
- **Managed rule group convenience refs** — No top-level convenience references; use ARN strings directly
- **Structured recursive statements** — Full structured schema for nested statements deferred to Phase 2

## Best Practices

1. **Inherit from governance** — Use `configRef` to leverage organization policies instead of hardcoding scope and defaults
2. **Reference rules, don't embed** — Create reusable `WAFRuleGroup` resources and reference them by ARN
3. **Enable logging** — Use `loggingConfiguration` to capture detailed request data for troubleshooting
4. **Monitor metrics** — Enable `cloudWatchMetricsEnabled` and `sampledRequestsEnabled` for visibility
5. **Redact sensitive data** — Use `redactedFields` to prevent logging of passwords, tokens, and PII
6. **Test rule changes** — Use `overrideAction: count` to test new rules in monitor mode before enforcement

## Related Resources

- [WAFConfig](wafconfig.md) — Governance configuration reference
- [WAFRuleGroup](wafrulegroup.md) — Create and manage reusable rule groups
- [WAFIPSet](wafipset.md) — Create and manage IP sets
- AWS WAFv2 documentation for detailed statement type reference
