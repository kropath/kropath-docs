# AWS CloudFront — Global Content Delivery

CloudFront is AWS's global content delivery network (CDN). Kropath provides resources to create and manage CloudFront distributions, caching policies, security headers, edge functions, and access control — all with centralized governance through `CloudFrontConfig`.

## Resources

| Resource | Purpose |
|---|---|
| [`CloudFrontConfig`](./cloudfrontconfig.md) | Governance configuration for CloudFront resources (mandatory and default settings) |
| [`CloudFrontDistribution`](./cloudfrontdistribution.md) | A CloudFront CDN distribution delivering content from origins to viewers worldwide |
| [`CloudFrontVPCOrigin`](./cloudfrontvpcorigin.md) | Register a private AWS resource (ALB, NLB, EC2) as a CloudFront origin |
| [`CloudFrontConnectionGroup`](./cloudfrontconnectiongroup.md) | Shared routing endpoint and static IP configuration for multi-tenant distributions |
| [`CloudFrontDistributionTenant`](./cloudfrontdistributiontenant.md) | Attach a single customer (tenant) to a multi-tenant CloudFront distribution |
| [`CloudFrontOriginAccessControl`](./cloudfrontoriginaccesscontrol.md) | Restrict access to your origin (S3, MediaStore, Lambda) so only CloudFront can reach it |
| [`CloudFrontCachePolicy`](./cloudfrontcachepolicy.md) | Define cache key and TTL behavior for a distribution cache behavior |
| [`CloudFrontOriginRequestPolicy`](./cloudfrontoriginrequestpolicy.md) | Control which cookies, headers, and query strings are forwarded to your origin |
| [`CloudFrontResponseHeadersPolicy`](./cloudfrontresponseheaderspolicy.md) | Add, remove, or override HTTP response headers (security headers, CORS, custom headers) |
| [`CloudFrontFunction`](./cloudfrontfunction.md) | Lightweight JavaScript code that runs at CloudFront edge locations for URL rewrites and header manipulation |

## Quick Start

### Basic Distribution with Governance

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-app-cdn
  namespace: app-team
spec:
  configRef: general-policy  # Uses CloudFrontConfig governance
  comment: "CDN for my-app website"
  enabled: true
  defaultRootObject: index.html
  origins:
    - id: s3-origin
      domainName: my-app-bucket.s3.us-east-1.amazonaws.com
      originPath: /prod
      s3OriginConfig:
        originAccessIdentity: ""  # Use OAC instead (modern approach)
  defaultCacheBehavior:
    targetOriginID: s3-origin
    viewerProtocolPolicy: ""  # Governance default: redirect-to-https
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6  # CloudFront managed policy
  tags:
    environment: production
    app: my-app
```

Result: A CloudFront distribution with HTTPS redirect, caching, and governance-enforced security settings applied.

### Distribution with Custom Policies

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: api-cdn
  namespace: services
spec:
  configRef: general-policy
  comment: "API edge caching"
  enabled: true
  origins:
    - id: api-origin
      domainName: api.example.com
      customOriginConfig:
        httpPort: 80
        httpsPort: 443
        originProtocolPolicy: https-only
        originSSLProtocols:
          - TLSv1.2
  defaultCacheBehavior:
    targetOriginID: api-origin
    viewerProtocolPolicy: https-only
    cachePolicyRef: my-api-cache  # Reference to local CloudFrontCachePolicy CR
    originRequestPolicyRef: my-api-forward  # Reference to local OriginRequestPolicy CR
    responseHeadersPolicyRef: my-security-headers  # Reference to local ResponseHeadersPolicy CR
```

### Creating Supporting Policies

Create a cache policy that caches based on query strings:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: my-api-cache
  namespace: services
spec:
  configRef: general-policy
  name: api-cache-by-query
  comment: "Cache API responses based on query string"
  defaultTTL: 300  # 5 minutes
  minTTL: 0
  maxTTL: 3600
  parametersInCacheKeyAndForwardedToOrigin:
    queryStringsConfig:
      queryStringBehavior: all  # Include all query strings in cache key
    headersConfig:
      headerBehavior: none
    cookiesConfig:
      cookieBehavior: none
    enableAcceptEncodingGzip: true
    enableAcceptEncodingBrotli: true
```

Create an origin request policy to forward Authorization headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: my-api-forward
  namespace: services
spec:
  configRef: general-policy
  name: forward-auth-headers
  comment: "Forward Authorization header to origin"
  headersConfig:
    headerBehavior: whitelist
    headers:
      - Authorization
      - Host
  cookiesConfig:
    cookieBehavior: all
  queryStringsConfig:
    queryStringBehavior: all
```

Create a response headers policy for security:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontResponseHeadersPolicy
metadata:
  name: my-security-headers
  namespace: services
spec:
  configRef: general-policy
  name: security-headers
  comment: "Add security headers to all responses"
  securityHeadersConfig:
    strictTransportSecurity:
      accessControlMaxAgeSec: 63072000  # 2 years
      includeSubdomains: true
      preload: true
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
```

Restrict S3 origin with Origin Access Control:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginAccessControl
metadata:
  name: my-s3-oac
  namespace: app-team
spec:
  configRef: general-policy
  name: s3-access-control
  description: "Restrict S3 access to CloudFront only"
  originAccessControlOriginType: s3
  signingBehavior: always
  signingProtocol: sigv4
```

## Governance with CloudFrontConfig

Platform teams deploy `CloudFrontConfig` profiles to enforce policies across all distributions. See [`CloudFrontConfig`](./cloudfrontconfig.md) for details on governance fields and profiles.

Example: A `strict-security` profile that mandates HTTPS-only, enforces WAF, and requires HSTS:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontConfig
metadata:
  name: strict-security
  namespace: kro-system
spec:
  mandatory:
    viewerProtocolPolicy: https-only
    minimumProtocolVersion: TLSv1.2_2021
    webACLRequired: true  # Block distributions without WAF
    loggingEnabled: true
    loggingBucket: org-logs.s3.amazonaws.com
  defaults:
    # ... sensible defaults for other fields
```

When a distribution specifies `configRef: strict-security`, those mandatory settings apply automatically — developers cannot override them.

## Common Patterns

### S3 Website Behind CloudFront

- Create a `CloudFrontDistribution` pointing to your S3 bucket domain
- Use `CloudFrontOriginAccessControl` to restrict the bucket so only CloudFront can read it
- Set `defaultRootObject: index.html` for directory-style access
- Use the governance default for `viewerProtocolPolicy` (usually `redirect-to-https`)

### API Caching with Custom Logic

- Create `CloudFrontCachePolicy` to define cache key (query strings, headers)
- Create `CloudFrontOriginRequestPolicy` to forward authentication headers
- Create `CloudFrontResponseHeadersPolicy` to add `Cache-Control` and security headers
- Reference all three policies in your `CloudFrontDistribution` cache behavior

### Edge Function for URL Rewriting

- Create a `CloudFrontFunction` with JavaScript that rewrites `/old-path/` to `/new-path/`
- Associate the function in `defaultCacheBehavior.functionAssociations`
- CloudFront runs the function at viewer-request before cache lookup, enabling dynamic routing

### Multi-Region Failover

- Create two distributions (primary and secondary) pointing to different origins
- Use Route 53 health checks to failover DNS between CloudFront distribution domains
- Each distribution can have its own caching and header policies

## Naming

Most CloudFront policy resources (`CachePolicy`, `OriginRequestPolicy`, `ResponseHeadersPolicy`, `OriginAccessControl`, `Function`) support naming via a configurable template. The default template is `{namespace}-{name}`, producing names like `app-team-my-cache-policy`.

Distribution has no provider name field and therefore skips naming — it is identified by CloudFront's assigned distribution ID.

## Tag Support

- **Distribution:** Supports `tags`, `syncedLabels`, and `syncedAnnotations` — all flow to AWS tags and Kubernetes metadata
- **Policy resources** (`CachePolicy`, `OriginRequestPolicy`, `ResponseHeadersPolicy`): Support `syncedLabels` and `syncedAnnotations` only (no `tags`)
- **OriginAccessControl:** Supports `syncedLabels` and `syncedAnnotations` only (no `tags`)
- **Function:** Supports `syncedLabels` and `syncedAnnotations` only (no `tags`)

## Deletion Policy

Every CloudFront resource supports a `deletionPolicy` field:
- `retain` (default) — Deleting the Kubernetes resource keeps the AWS resource intact
- `delete` — Deleting the Kubernetes resource also deletes the AWS resource

For production distributions and shared policies, use `retain` to prevent accidental deletion.

---

## Resource Reference

- [CloudFrontConfig](./cloudfrontconfig.md) — Governance configuration
- [CloudFrontDistribution](./cloudfrontdistribution.md) — CDN distribution
- [CloudFrontVPCOrigin](./cloudfrontvpcorigin.md) — Private VPC origin
- [CloudFrontConnectionGroup](./cloudfrontconnectiongroup.md) — Multi-tenant routing endpoint
- [CloudFrontDistributionTenant](./cloudfrontdistributiontenant.md) — Multi-tenant subscriber
- [CloudFrontOriginAccessControl](./cloudfrontoriginaccesscontrol.md) — Origin access control
- [CloudFrontCachePolicy](./cloudfrontcachepolicy.md) — Cache key policy
- [CloudFrontOriginRequestPolicy](./cloudfrontoriginrequestpolicy.md) — Origin forwarding policy
- [CloudFrontResponseHeadersPolicy](./cloudfrontresponseheaderspolicy.md) — Response headers policy
- [CloudFrontFunction](./cloudfrontfunction.md) — Edge function

---

For ADRs and architectural details, see [kropath-core](https://github.com/kropath/kropath-core).
