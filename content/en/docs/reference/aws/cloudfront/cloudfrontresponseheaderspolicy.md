---
title: CloudFrontResponseHeadersPolicy — Response Headers
description: "`CloudFrontResponseHeadersPolicy` adds, removes, or overrides HTTP response headers sent to viewers."
doc_type: reference
---
# CloudFrontResponseHeadersPolicy — Response Headers

`CloudFrontResponseHeadersPolicy` adds, removes, or overrides HTTP response headers sent to viewers. Use this to enforce security headers (HSTS, CSP, X-Frame-Options), CORS headers, custom headers, and Server-Timing instrumentation.

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects `CloudFrontConfig` governance profile |
| `name` | string | `""` | Human-readable policy name |
| `comment` | string | `""` | Free-text description |
| `nameOverride` | string | `""` | Bypass naming template and set policy name directly |
| `deletionPolicy` | string | `"retain"` | `"retain"` or `"delete"` |
| `syncedLabels` | map | `{}` | Kubernetes labels only |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Security Headers Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `securityHeadersConfig.strictTransportSecurity.accessControlMaxAgeSec` | integer | `63072000` | HSTS max-age in seconds (2 years = 63,072,000) |
| `securityHeadersConfig.strictTransportSecurity.includeSubdomains` | boolean | `false` | Apply HSTS to subdomains |
| `securityHeadersConfig.strictTransportSecurity.preload` | boolean | `false` | Allow domain to be preloaded in browsers |
| `securityHeadersConfig.strictTransportSecurity.override` | boolean | `true` | Override origin `Strict-Transport-Security` headers |
| `securityHeadersConfig.frameOptions.frameOption` | string | `"DENY"` | `"DENY"` (no framing) or `"SAMEORIGIN"` |
| `securityHeadersConfig.frameOptions.override` | boolean | `true` | Override origin `X-Frame-Options` |
| `securityHeadersConfig.contentTypeOptions.override` | boolean | `true` | Set `X-Content-Type-Options: nosniff` |
| `securityHeadersConfig.xssProtection.protection` | boolean | `true` | Enable XSS protection header |
| `securityHeadersConfig.xssProtection.modeBlock` | boolean | `true` | Block rendering if XSS detected (vs. sanitize) |
| `securityHeadersConfig.xssProtection.reportURI` | string | `""` | Optional URI for XSS violation reports |
| `securityHeadersConfig.xssProtection.override` | boolean | `true` | Override origin `X-XSS-Protection` |
| `securityHeadersConfig.referrerPolicy.referrerPolicy` | string | `"strict-origin-when-cross-origin"` | Referrer policy value |
| `securityHeadersConfig.referrerPolicy.override` | boolean | `true` | Override origin `Referrer-Policy` |
| `securityHeadersConfig.contentSecurityPolicy.contentSecurityPolicy` | string | `""` | CSP header value (e.g., `"default-src 'self'; script-src 'self' 'unsafe-inline'"`) |
| `securityHeadersConfig.contentSecurityPolicy.override` | boolean | `true` | Override origin `Content-Security-Policy` |

## CORS Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `corsConfig.accessControlAllowOrigins` | array | `[]` | Allowed origins (e.g., `["https://example.com", "*"]`) |
| `corsConfig.accessControlAllowMethods` | array | `[]` | Allowed HTTP methods (e.g., `["GET", "POST", "PUT"]`) |
| `corsConfig.accessControlAllowHeaders` | array | `[]` | Allowed request headers (e.g., `["Content-Type", "Authorization"]`) |
| `corsConfig.accessControlExposeHeaders` | array | `[]` | Headers exposed to the browser (e.g., `["X-Total-Count"]`) |
| `corsConfig.accessControlMaxAgeSec` | integer | `600` | CORS preflight cache time (seconds) |
| `corsConfig.accessControlAllowCredentials` | boolean | `false` | Allow credentials in CORS requests |
| `corsConfig.originOverride` | boolean | `true` | Override origin CORS headers |

## Custom Headers Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `customHeadersConfig.items` | array | `[]` | Custom headers to add/override |
| `customHeadersConfig.items[].header` | string | required | Header name (e.g., `X-Custom-Header`) |
| `customHeadersConfig.items[].value` | string | required | Header value |
| `customHeadersConfig.items[].override` | boolean | `true` | Override if origin also sets this header |

## Header Removal Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `removeHeadersConfig.items` | array | `[]` | Headers to remove from origin response |
| `removeHeadersConfig.items[].header` | string | required | Header name to remove |

## Server-Timing Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `serverTimingHeadersConfig.enabled` | boolean | `false` | Enable Server-Timing header |
| `serverTimingHeadersConfig.samplingRate` | number | `0.0` | Sample rate (0.0-1.0) for Server-Timing header |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `id` | string | CloudFront-assigned policy ID |
| `resourceName` | string | Effective policy name |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `conditions[]` | array | Reconciliation status |

## Examples

### Basic Security Headers

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: security-headers
  namespace: web-team
spec:
  configRef: general-policy
  name: basic-security
  comment: "Basic security headers (HSTS, no-frame, nosniff)"
  securityHeadersConfig:
    strictTransportSecurity:
      accessControlMaxAgeSec: 31536000  # 1 year
      includeSubdomains: true
      preload: false
      override: true
    frameOptions:
      frameOption: DENY
      override: true
    contentTypeOptions:
      override: true
    xssProtection:
      protection: true
      modeBlock: true
      override: true
    referrerPolicy:
      referrerPolicy: strict-origin-when-cross-origin
      override: true
```

### Security + CORS Headers

Allow cross-origin API access with security headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: secure-cors
  namespace: api-team
spec:
  configRef: general-policy
  name: api-cors-security
  comment: "CORS with security headers"
  securityHeadersConfig:
    strictTransportSecurity:
      accessControlMaxAgeSec: 63072000
      includeSubdomains: true
      preload: true
      override: true
    frameOptions:
      frameOption: DENY
      override: true
    contentTypeOptions:
      override: true
  corsConfig:
    accessControlAllowOrigins:
      - "https://app.example.com"
      - "https://dashboard.example.com"
    accessControlAllowMethods:
      - GET
      - POST
      - PUT
      - DELETE
      - OPTIONS
    accessControlAllowHeaders:
      - Content-Type
      - Authorization
      - X-Requested-With
    accessControlExposeHeaders:
      - X-Total-Count
      - X-Page-Number
    accessControlMaxAgeSec: 3600
    accessControlAllowCredentials: true
    originOverride: true
```

### Content Security Policy

Enforce strict CSP:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: strict-csp
  namespace: web-team
spec:
  configRef: general-policy
  name: strict-content-security
  comment: "Strict CSP policy"
  securityHeadersConfig:
    contentSecurityPolicy:
      contentSecurityPolicy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https:; font-src 'self'; connect-src 'self' https://api.example.com"
      override: true
    strictTransportSecurity:
      accessControlMaxAgeSec: 31536000
      includeSubdomains: true
      preload: true
      override: true
```

### Remove Sensitive Headers

Strip server-identifying headers from origin:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: remove-server-headers
  namespace: security-team
spec:
  configRef: general-policy
  name: strip-server-headers
  comment: "Remove server-identifying headers"
  removeHeadersConfig:
    items:
      - header: Server
      - header: X-Powered-By
      - header: X-AspNet-Version
      - header: X-Runtime
```

### Custom Headers

Add custom business headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: custom-headers
  namespace: app-team
spec:
  configRef: general-policy
  name: app-custom-headers
  comment: "Add app-specific headers"
  customHeadersConfig:
    items:
      - header: X-App-Version
        value: "1.2.3"
        override: true
      - header: X-CDN-Provider
        value: CloudFront
        override: true
      - header: Cache-Control
        value: "public, max-age=3600"
        override: false  # Only add if origin didn't set it
```

### Server-Timing for Performance Monitoring

Enable Server-Timing header (sample 10% of requests):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: server-timing
  namespace: web-team
spec:
  configRef: general-policy
  name: server-timing-enabled
  comment: "Enable Server-Timing for performance monitoring"
  serverTimingHeadersConfig:
    enabled: true
    samplingRate: 0.1  # 10% of requests
```

## Naming

Default template: `{namespace}-{name}`.

**Available tokens:** `{name}`, `{namespace}`, `{configRef}`, `{account_id}`, `{region}`, `{tag.KEY}`

## Usage in Distributions

Reference by name:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-app
  namespace: web-team
spec:
  # ...
  defaultCacheBehavior:
    targetOriginID: s3-origin
    responseHeadersPolicyRef: security-headers
```

## Common Security Patterns

### Strict Security (OWASP Recommended)

```yaml
securityHeadersConfig:
  strictTransportSecurity:
    accessControlMaxAgeSec: 63072000  # 2 years
    includeSubdomains: true
    preload: true
  contentSecurityPolicy:
    contentSecurityPolicy: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https:; font-src 'self'"
  frameOptions:
    frameOption: DENY
  contentTypeOptions:
    override: true
  xssProtection:
    protection: true
    modeBlock: true
  referrerPolicy:
    referrerPolicy: strict-origin-when-cross-origin
```

### Moderate Security (Balance)

```yaml
securityHeadersConfig:
  strictTransportSecurity:
    accessControlMaxAgeSec: 31536000  # 1 year
    includeSubdomains: true
  frameOptions:
    frameOption: SAMEORIGIN
  contentTypeOptions:
    override: true
  referrerPolicy:
    referrerPolicy: strict-origin-when-cross-origin
```

## Troubleshooting

### Headers Not Showing in Response

Check:
- `override: true` — Ensures CloudFront adds the header even if origin provides a value
- Policy is actually referenced in the distribution
- Browser dev tools to verify headers are present

### CORS Not Working

Ensure:
- `corsConfig.accessControlAllowOrigins` includes your origin (exact match, including protocol/port)
- `corsConfig.accessControlAllowMethods` includes the HTTP method
- `corsConfig.accessControlAllowHeaders` includes request headers
- `corsConfig.originOverride: true` (to override origin CORS headers if they conflict)

---

See [CloudFrontDistribution](./cloudfrontdistribution.md) for usage with distributions.
