# CloudFrontCachePolicy — Cache Key and TTL

`CloudFrontCachePolicy` defines how CloudFront caches responses based on headers, cookies, and query strings. It also controls TTL (time-to-live) settings. Policies are referenced by distribution cache behaviors to control caching behavior independently of what is forwarded to the origin.

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects `CloudFrontConfig` governance profile |
| `name` | string | `""` | Human-readable cache policy name |
| `comment` | string | `""` | Free-text description |
| `defaultTTL` | integer | `86400` | Default cache duration in seconds (24 hours) |
| `minTTL` | integer | `0` | Minimum cache duration (overrides `Cache-Control: max-age` if origin value is lower) |
| `maxTTL` | integer | `31536000` | Maximum cache duration in seconds (1 year) |
| `deletionPolicy` | string | `"retain"` | `"retain"` or `"delete"` |
| `syncedLabels` | map | `{}` | Kubernetes labels only (no AWS tags for cache policies) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Cache Key Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `parametersInCacheKeyAndForwardedToOrigin.cookiesConfig.cookieBehavior` | string | `"none"` | `"none"` (don't cache by cookies), `"whitelist"` (specific cookies), `"allExcept"` (all except listed), `"all"` (all cookies) |
| `parametersInCacheKeyAndForwardedToOrigin.cookiesConfig.cookies` | array | `[]` | Cookie names when behavior is `"whitelist"` or `"allExcept"` |
| `parametersInCacheKeyAndForwardedToOrigin.headersConfig.headerBehavior` | string | `"none"` | `"none"` (ignore headers) or `"whitelist"` (specific headers) |
| `parametersInCacheKeyAndForwardedToOrigin.headersConfig.headers` | array | `[]` | Header names when behavior is `"whitelist"` |
| `parametersInCacheKeyAndForwardedToOrigin.queryStringsConfig.queryStringBehavior` | string | `"none"` | `"none"`, `"whitelist"`, `"allExcept"`, `"all"` |
| `parametersInCacheKeyAndForwardedToOrigin.queryStringsConfig.queryStrings` | array | `[]` | Query string parameter names |
| `parametersInCacheKeyAndForwardedToOrigin.enableAcceptEncodingGzip` | boolean | `true` | Include `Accept-Encoding: gzip` in cache key normalization |
| `parametersInCacheKeyAndForwardedToOrigin.enableAcceptEncodingBrotli` | boolean | `true` | Include `Accept-Encoding: br` (brotli) in cache key normalization |
| `nameOverride` | string | `""` | Bypass naming template |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `id` | string | CloudFront-assigned policy ID (referenced by distributions) |
| `resourceName` | string | Effective policy name after naming template |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `conditions[]` | array | Reconciliation status |

## Examples

### Aggressive Caching (Static Assets)

Cache everything based on path only (ignore cookies/headers):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: aggressive-cache
  namespace: app-team
spec:
  configRef: general-policy
  name: static-assets-cache
  comment: "Aggressive caching for static assets"
  defaultTTL: 2592000    # 30 days
  minTTL: 0
  maxTTL: 31536000       # 1 year
  parametersInCacheKeyAndForwardedToOrigin:
    cookiesConfig:
      cookieBehavior: none
    headersConfig:
      headerBehavior: none
    queryStringsConfig:
      queryStringBehavior: none
    enableAcceptEncodingGzip: true
    enableAcceptEncodingBrotli: true
```

### Query String Caching (API Responses)

Include query strings in cache key:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: api-query-cache
  namespace: api-team
spec:
  configRef: general-policy
  name: api-query-cache
  comment: "Cache API responses by query string"
  defaultTTL: 300       # 5 minutes
  minTTL: 0
  maxTTL: 3600
  parametersInCacheKeyAndForwardedToOrigin:
    queryStringsConfig:
      queryStringBehavior: all  # Include all query strings
    cookiesConfig:
      cookieBehavior: none
    headersConfig:
      headerBehavior: none
    enableAcceptEncodingGzip: true
    enableAcceptEncodingBrotli: true
```

### Cookie-Based Caching (User Sessions)

Cache separately for different users based on session cookie:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: session-aware-cache
  namespace: web-team
spec:
  configRef: general-policy
  name: session-cookie-cache
  comment: "Cache by session cookie"
  defaultTTL: 3600
  minTTL: 0
  maxTTL: 86400
  parametersInCacheKeyAndForwardedToOrigin:
    cookiesConfig:
      cookieBehavior: whitelist
      cookies:
        - session-id
        - user-token
    headersConfig:
      headerBehavior: none
    queryStringsConfig:
      queryStringBehavior: none
    enableAcceptEncodingGzip: true
```

### Header-Based Caching (Content Negotiation)

Cache by `Accept-Language` header (content negotiation):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: language-aware-cache
  namespace: web-team
spec:
  configRef: general-policy
  name: language-cache
  comment: "Cache by Accept-Language header"
  defaultTTL: 86400
  minTTL: 0
  maxTTL: 2592000
  parametersInCacheKeyAndForwardedToOrigin:
    headersConfig:
      headerBehavior: whitelist
      headers:
        - Accept-Language
        - Accept-Encoding
    cookiesConfig:
      cookieBehavior: none
    queryStringsConfig:
      queryStringBehavior: none
    enableAcceptEncodingGzip: true
    enableAcceptEncodingBrotli: true
```

### No Caching (Dynamic Content)

Disable caching entirely:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontCachePolicy
metadata:
  name: no-cache
  namespace: api-team
spec:
  configRef: general-policy
  name: dynamic-content-nocache
  comment: "No caching for dynamic content"
  defaultTTL: 0
  minTTL: 0
  maxTTL: 0
  parametersInCacheKeyAndForwardedToOrigin:
    cookiesConfig:
      cookieBehavior: all
    headersConfig:
      headerBehavior: none
    queryStringsConfig:
      queryStringBehavior: all
    enableAcceptEncodingGzip: false
    enableAcceptEncodingBrotli: false
```

## Naming

Default template: `{namespace}-{name}`.

**Available tokens:** `{name}`, `{namespace}`, `{configRef}`, `{account_id}`, `{region}`, `{tag.KEY}`

## Usage in Distributions

Reference the policy by name:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-app
  namespace: app-team
spec:
  # ...
  defaultCacheBehavior:
    targetOriginID: s3-origin
    cachePolicyRef: aggressive-cache  # Resolves to local CloudFrontCachePolicy CR
```

Or use CloudFront managed policies by ID:
- `658327ea-f89d-4fab-a63d-7e88639e58f6` — CachingOptimized (static assets)
- `4135ea3d-c35d-46eb-81d7-reeSJmXQQpQ` — CachingDisabled (no caching)
- Others available via AWS documentation

## TTL Precedence

CloudFront respects `Cache-Control` headers from the origin:
- If origin returns `Cache-Control: max-age=600`, CloudFront honors it up to `maxTTL`
- If origin returns `Cache-Control: max-age=10`, CloudFront enforces `minTTL` (so if `minTTL: 300`, it caches for 300 seconds anyway)
- If origin doesn't set `Cache-Control`, `defaultTTL` applies

## Compression Encoding

- `enableAcceptEncodingGzip: true` — Treat requests with different gzip encoding as same cache entry
- `enableAcceptEncodingBrotli: true` — Treat requests with different brotli encoding as same cache entry

Both should usually be `true` to maximize cache hit rates across browsers.

## Troubleshooting

### Low Cache Hit Rate

Check cache key configuration:
- If including cookies/query strings unnecessarily, cache hits drop
- If minTTL is very high, short-lived content expires

### Stale Content Served

Increase `minTTL` or adjust origin `Cache-Control` headers.

### Missing Compression

Ensure `enableAcceptEncodingGzip` and `enableAcceptEncodingBrotli` are `true`.

---

See [CloudFrontDistribution](./cloudfrontdistribution.md) for usage with distributions.
