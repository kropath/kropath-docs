---
title: CloudFrontDistribution — CDN Distribution
description: "The `CloudFrontDistribution` resource represents a CloudFront content delivery network (CDN) distribution."
doc_type: reference
---
# CloudFrontDistribution — CDN Distribution

The `CloudFrontDistribution` resource represents a CloudFront content delivery network (CDN) distribution. A distribution serves content from origins (S3 buckets, web servers, custom domains) to viewers worldwide via CloudFront's global network of edge locations.

## Core Fields

### Governance and Selection

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `CloudFrontConfig` governance profile to apply |
| `deletionPolicy` | string | `"retain"` | When the resource is deleted: `"retain"` (keep AWS distribution) or `"delete"` (remove it) |

### Distribution Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `comment` | string | `""` | Human-readable description of the distribution |
| `enabled` | boolean | `true` | Whether the distribution is active and serving traffic |
| `defaultRootObject` | string | `""` | Object returned for root URL requests (e.g., `index.html`) |
| `isIPV6Enabled` | boolean | `true` | Enable IPv6 support for viewers |

### Viewer Protocol Policy & TLS

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaultCacheBehavior.viewerProtocolPolicy` | string | `""` | How viewers connect: `"allow-all"`, `"https-only"`, `"redirect-to-https"`, or `""` (use governance default) |
| `viewerCertificate.minimumProtocolVersion` | string | `""` | Minimum TLS version (e.g., `"TLSv1.2_2021"`) or `""` (use governance default) |
| `viewerCertificate.sslSupportMethod` | string | `""` | `"sni-only"` or `"vip"` (SNI is more cost-effective; VIP is legacy) |
| `viewerCertificate.acmCertificateArn` | string | `""` | ARN of an ACM certificate for custom domains (for HTTPS with custom domain names) |
| `viewerCertificate.cloudFrontDefaultCertificate` | boolean | `false` | Use CloudFront's default `*.cloudfront.net` certificate |

### HTTP Version

| Field | Type | Default | Purpose |
|---|---|---|---|
| `httpVersion` | string | `""` | HTTP protocol version: `"http1.1"`, `"http2"`, `"http2and3"`, `"http3"`, or `""` (use governance default) |

### Pricing & Performance

| Field | Type | Default | Purpose |
|---|---|---|---|
| `priceClass` | string | `""` | Edge location tier: `"PriceClass_100"` (fewest, cheapest), `"PriceClass_200"` (more), `"PriceClass_All"` (all), or `""` (use governance default) |

### WAF Integration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `webACLID` | string | `""` | ARN of a WAF WebACL to protect the distribution (required if governance sets `webACLRequired: true`) |

### Domain Names

| Field | Type | Default | Purpose |
|---|---|---|---|
| `aliases` | array | `[]` | Alternate domain names (CNAMEs) served by this distribution (max 100; requires corresponding DNS CNAME records) |

### Origins

| Field | Type | Default | Purpose |
|---|---|---|---|
| `origins` | array | required | At least one origin — the source of your content |
| `origins[].id` | string | required | Unique identifier for this origin (referenced by cache behaviors via `targetOriginID`) |
| `origins[].domainName` | string | required | Hostname of the origin (S3 bucket domain, web server DNS name, custom domain) |
| `origins[].originPath` | string | `""` | Optional path prefix (e.g., `/prod`) prepended to origin requests |
| `origins[].originAccessControlRef` | string | `""` | Name of a `CloudFrontOriginAccessControl` CR to restrict access (modern S3 approach) |
| `origins[].originAccessControlID` | string | `""` | CloudFront-assigned ID of an OAC (use `originAccessControlRef` instead) |
| `origins[].connectionAttempts` | integer | `3` | Number of connection retries (1–3) |
| `origins[].connectionTimeout` | integer | `10` | TCP connection timeout in seconds (1–10) |
| `origins[].customHeaders` | array | `[]` | Custom HTTP headers to add to origin requests |
| `origins[].s3OriginConfig` | object | optional | For S3 origins using legacy `originAccessIdentity` (deprecated; use OAC instead) |
| `origins[].customOriginConfig` | object | optional | For custom origins (web servers, ALBs, etc.) |
| `origins[].originShield` | object | optional | Enable Origin Shield — an additional caching layer between CloudFront and your origin |

### Cache Behaviors

| Field | Type | Default | Purpose |
|---|---|---|---|
| `defaultCacheBehavior` | object | required | The default cache behavior for all requests not matching a path pattern |
| `defaultCacheBehavior.targetOriginID` | string | required | Which origin to fetch from (references `origins[].id`) |
| `defaultCacheBehavior.cachePolicyID` | string | `""` | CloudFront-assigned ID of a cache policy defining cache key and TTL |
| `defaultCacheBehavior.cachePolicyRef` | string | `""` | Name of a local `CloudFrontCachePolicy` CR (takes precedence over `cachePolicyID`) |
| `defaultCacheBehavior.originRequestPolicyID` | string | `""` | CloudFront-assigned ID of an origin request policy |
| `defaultCacheBehavior.originRequestPolicyRef` | string | `""` | Name of a local `CloudFrontOriginRequestPolicy` CR |
| `defaultCacheBehavior.responseHeadersPolicyID` | string | `""` | CloudFront-assigned ID of a response headers policy |
| `defaultCacheBehavior.responseHeadersPolicyRef` | string | `""` | Name of a local `CloudFrontResponseHeadersPolicy` CR |
| `defaultCacheBehavior.compress` | boolean | `true` | Auto-compress responses (gzip, brotli) for smaller transfer size |
| `defaultCacheBehavior.allowedMethods` | object | optional | HTTP methods allowed (GET, POST, etc.) and which are cacheable |
| `defaultCacheBehavior.functionAssociations` | array | `[]` | CloudFront Functions to run at viewer-request or viewer-response events |
| `cacheBehaviors` | array | `[]` | Additional path-pattern-based cache behaviors (same structure as `defaultCacheBehavior` plus `pathPattern` and `targetOriginID`) |

### Logging

| Field | Type | Default | Purpose |
|---|---|---|---|
| `logging.enabled` | boolean | `false` | Enable access logging to S3 (or use governance default) |
| `logging.bucket` | string | `""` | S3 bucket domain for logs (e.g., `mybucket.s3.amazonaws.com`) or governance default |
| `logging.prefix` | string | `""` | S3 key prefix for log files (e.g., `cloudfront-logs/`) |
| `logging.includeCookies` | boolean | `false` | Include cookie data in access logs |

### Geographic Restriction

| Field | Type | Default | Purpose |
|---|---|---|---|
| `restrictions.geoRestriction.restrictionType` | string | `"none"` | `"none"` (no restriction), `"whitelist"` (allow only listed countries), `"blacklist"` (block listed countries) |
| `restrictions.geoRestriction.items` | array | `[]` | ISO 3166-1 alpha-2 country codes (e.g., `["US", "CA", "GB"]`) |

### Error Responses

| Field | Type | Default | Purpose |
|---|---|---|---|
| `customErrorResponses` | array | `[]` | Custom error pages for specific HTTP error codes |
| `customErrorResponses[].errorCode` | integer | required | HTTP status code (e.g., `404`, `500`) |
| `customErrorResponses[].responseCode` | integer | optional | HTTP status to return to viewer (e.g., return `200` for `404` errors) |
| `customErrorResponses[].responsePagePath` | string | optional | S3 object path for custom error page (e.g., `/error.html`) |
| `customErrorResponses[].errorCachingMinTTL` | integer | optional | Cache time for error responses in seconds |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation:

| Field | Type | Purpose |
|---|---|---|
| `id` | string | CloudFront's assigned distribution ID (e.g., `E1U5RQF7T870K0`) |
| `domainName` | string | CloudFront domain for the distribution (e.g., `d123.cloudfront.net`) |
| `conditions[]` | array | Reconciliation status (Ready, errors) |

**Note:** Distribution does not use naming (no `status.resourceName`, `status.predictedArn`). It is identified by the CloudFront-assigned distribution ID in `status.id`.

## Governance Cascade

All governance fields follow the same three-tier cascade:

1. **Governance mandatory** (if set) → overrides everything
2. **Resource spec** (if set by developer) → used
3. **Governance defaults** (fallback)

**Example:** If `CloudFrontConfig` has `mandatory.viewerProtocolPolicy: "https-only"` and the distribution specifies `spec.defaultCacheBehavior.viewerProtocolPolicy: "allow-all"`, the governance setting wins — the distribution uses HTTPS-only.

Governed fields:
- `viewerProtocolPolicy` (on `defaultCacheBehavior` and each `cacheBehaviors[]` entry)
- `minimumProtocolVersion` (on `viewerCertificate`)
- `httpVersion`
- `sslSupportMethod` (on `viewerCertificate`)
- `loggingEnabled` and `loggingBucket` (on `logging`)
- `priceClass`
- `webACLRequired` (gates creation if mandatory is true and `webACLID` is empty)
- `geoRestrictionType` (on `restrictions.geoRestriction`)

Non-governed fields (set directly on the distribution):
- Origins, custom headers, connection settings
- Cache behaviors, cache policies, origin policies, response header policies
- Error responses, default root object
- Tags (merged with governance tags)

## Complete Examples

### Basic S3-Backed Distribution

Serve a static website from an S3 bucket:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-website
  namespace: web-team
spec:
  configRef: general-policy
  comment: "Static website CDN"
  enabled: true
  defaultRootObject: index.html
  origins:
    - id: s3-origin
      domainName: my-website-bucket.s3.us-east-1.amazonaws.com
      s3OriginConfig: {}
  defaultCacheBehavior:
    targetOriginID: s3-origin
    viewerProtocolPolicy: redirect-to-https
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CloudFront Managed-CachingOptimized
  tags:
    application: website
    environment: production
```

### Custom Domain with ACM Certificate

Serve content with a custom domain name protected by an ACM certificate:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: api-cdn
  namespace: services
spec:
  configRef: general-policy
  comment: "API edge cache"
  enabled: true
  aliases:
    - api.example.com
    - api-eu.example.com
  origins:
    - id: api-origin
      domainName: api-backend.example.com
      customOriginConfig:
        httpPort: 80
        httpsPort: 443
        originProtocolPolicy: https-only
        originSSLProtocols:
          - TLSv1.2
  defaultCacheBehavior:
    targetOriginID: api-origin
    viewerProtocolPolicy: https-only
    cachePolicyID: 4135ea3d-c35d-46eb-81d7-reeSJmXQQpQ  # CloudFront Managed-CachingDisabled
  viewerCertificate:
    acmCertificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/abc123"
    sslSupportMethod: sni-only
    minimumProtocolVersion: TLSv1.2_2021
  logging:
    enabled: true
    bucket: api-logs.s3.us-east-1.amazonaws.com
    prefix: cloudfront/
  tags:
    service: api
    tier: backend
```

### Multi-Origin with Path-Based Routing

Route requests to different origins based on URL path:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: multi-app
  namespace: platform
spec:
  configRef: general-policy
  comment: "Multi-app CDN with path routing"
  enabled: true
  origins:
    - id: web-origin
      domainName: web.example.com
      customOriginConfig:
        originProtocolPolicy: https-only
    - id: api-origin
      domainName: api.example.com
      customOriginConfig:
        originProtocolPolicy: https-only
    - id: static-bucket
      domainName: static-assets.s3.us-east-1.amazonaws.com
  defaultCacheBehavior:
    targetOriginID: web-origin
    viewerProtocolPolicy: redirect-to-https
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6
  cacheBehaviors:
    - pathPattern: /api/*
      targetOriginID: api-origin
      viewerProtocolPolicy: https-only
      cachePolicyID: 4135ea3d-c35d-46eb-81d7-reeSJmXQQpQ  # No caching for API
    - pathPattern: /static/*
      targetOriginID: static-bucket
      viewerProtocolPolicy: https-only
      cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6  # Aggressive caching for static
```

### With OAC for Secure S3 Access

Restrict an S3 origin so only CloudFront can access it:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginAccessControl
metadata:
  name: s3-access
  namespace: app-team
spec:
  configRef: general-policy
  name: secure-s3-access
  description: "Restrict S3 to CloudFront only"
  originAccessControlOriginType: s3
  signingBehavior: always
---
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: secure-app
  namespace: app-team
spec:
  configRef: general-policy
  comment: "Secure S3 distribution"
  enabled: true
  defaultRootObject: index.html
  origins:
    - id: s3-origin
      domainName: app-bucket.s3.us-east-1.amazonaws.com
      originAccessControlRef: s3-access  # Reference the OAC
  defaultCacheBehavior:
    targetOriginID: s3-origin
    viewerProtocolPolicy: redirect-to-https
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6
```

### With Custom Policies and Functions

Reference local policy resources:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: premium-app
  namespace: premium
spec:
  configRef: strict-security
  comment: "Premium tier with custom policies"
  enabled: true
  webACLID: "arn:aws:wafv2:us-east-1:123456789012:global/webacl/name/abc"
  origins:
    - id: origin1
      domainName: premium-backend.example.com
  defaultCacheBehavior:
    targetOriginID: origin1
    viewerProtocolPolicy: https-only
    cachePolicyRef: premium-cache       # Local cache policy
    originRequestPolicyRef: auth-forward # Forward auth headers
    responseHeadersPolicyRef: sec-headers # Add security headers
    functionAssociations:
      - eventType: viewer-request
        functionARN: arn:aws:cloudfront::123456789012:function/url-rewrite
  logging:
    enabled: true
    bucket: premium-logs.s3.us-east-1.amazonaws.com
  restrictions:
    geoRestriction:
      restrictionType: whitelist
      items:
        - US
        - CA
        - GB
```

## Key Behaviors

### Governance Enforcement

Fields marked as mandatory in `CloudFrontConfig` cannot be overridden, even if specified in the distribution. Platform teams use this for compliance gates (e.g., forcing HTTPS-only, requiring WAF).

### Policy References vs IDs

Both ID-based and reference-based approaches are supported:
- `cachePolicyID: "xxx"` — Use a CloudFront managed policy or pre-created custom policy by its ID
- `cachePolicyRef: "my-policy"` — Reference a local `CloudFrontCachePolicy` CR; Kropath resolves it to the ID

Ref takes precedence over ID; if both are specified, the ref is used.

### Custom Domain Names (Aliases)

If you specify alternate domain names in `aliases`, you must:
1. Have an ACM certificate covering those domains
2. Create DNS CNAME records pointing those domains to the CloudFront domain name
3. Specify the ACM certificate ARN in `viewerCertificate.acmCertificateArn`

### Immutability After Creation

Once created, the distribution ID is permanent. Changing `metadata.name` does not rename the distribution.

### Deletion Policy

- `retain` (default) — Deleting the Kubernetes resource keeps the CloudFront distribution intact (safe default)
- `delete` — Deleting the Kubernetes resource also deletes the distribution in AWS (use with caution)

## Troubleshooting

### Distribution Not Creating

Check `status.conditions` for errors. Common issues:
- Missing `webACLID` when governance sets `webACLRequired: true`
- Invalid ACM certificate ARN
- Origin domain name not reachable
- IAM permissions insufficient

### Can't Override Governance Setting

If `CloudFrontConfig` marks a field as mandatory, you cannot override it. Only the defaults tier can be overridden. Contact your platform team if you need different settings.

### Custom Domain Not Working

Ensure:
1. `aliases` includes the custom domain
2. ACM certificate ARN is specified and covers the domain
3. DNS CNAME record points the domain to CloudFront's distribution domain

### Caching Not Working as Expected

Check your cache policy and origin response headers:
- `Cache-Control` headers from the origin may restrict caching
- `cachePolicyID` / `cachePolicyRef` defines what is cacheable based on headers/cookies/query strings
- Verify the selected CloudFront managed policy matches your expectations

---

For related resources and governance, see [CloudFront resources](./index.md) and [CloudFrontConfig](./cloudfrontconfig.md).
