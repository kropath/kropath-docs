---
title: CloudFrontOriginRequestPolicy — Origin Forwarding
description: "`CloudFrontOriginRequestPolicy` controls which cookies, headers, and query strings are forwarded to your origin."
doc_type: reference
---
# CloudFrontOriginRequestPolicy — Origin Forwarding

`CloudFrontOriginRequestPolicy` controls which cookies, headers, and query strings are forwarded to your origin. This is independent of the cache key — you can cache based on one set of parameters while forwarding a different set to the origin.

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects `CloudFrontConfig` governance profile |
| `name` | string | `""` | Human-readable policy name |
| `comment` | string | `""` | Free-text description |
| `deletionPolicy` | string | `"retain"` | `"retain"` or `"delete"` |
| `syncedLabels` | map | `{}` | Kubernetes labels only (no AWS tags) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Origin Forwarding Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `cookiesConfig.cookieBehavior` | string | `"none"` | `"none"` (don't forward), `"whitelist"`, `"allExcept"`, `"all"` |
| `cookiesConfig.cookies` | array | `[]` | Cookie names when behavior is `"whitelist"` or `"allExcept"` |
| `headersConfig.headerBehavior` | string | `"none"` | `"none"`, `"whitelist"`, `"allViewer"`, `"allViewerAndWhitelistCloudFront"` |
| `headersConfig.headers` | array | `[]` | Header names when behavior is `"whitelist"` |
| `queryStringsConfig.queryStringBehavior` | string | `"none"` | `"none"`, `"whitelist"`, `"allExcept"`, `"all"` |
| `queryStringsConfig.queryStrings` | array | `[]` | Query string names when behavior is `"whitelist"` or `"allExcept"` |
| `nameOverride` | string | `""` | Bypass naming template |

## Header Behavior Explained

| Behavior | Meaning |
|---|---|
| `"none"` | Don't forward any headers (CloudFront supplies Host and CloudFront-specific headers) |
| `"whitelist"` | Forward only the listed headers |
| `"allViewer"` | Forward all headers sent by the viewer |
| `"allViewerAndWhitelistCloudFront"` | Forward all viewer headers plus a CloudFront whitelist (e.g., CloudFront-Is-Desktop-Viewer, CloudFront-Viewer-Country) |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `id` | string | CloudFront-assigned policy ID (referenced by distributions) |
| `resourceName` | string | Effective policy name |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `conditions[]` | array | Reconciliation status |

## Examples

### Forward Authorization Headers

Preserve authentication for backend API:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: auth-forward
  namespace: api-team
spec:
  configRef: general-policy
  name: forward-auth-headers
  comment: "Forward auth headers to origin"
  headersConfig:
    headerBehavior: whitelist
    headers:
      - Authorization
      - Cookie
      - Host
  cookiesConfig:
    cookieBehavior: all
  queryStringsConfig:
    queryStringBehavior: all
```

### Forward All Viewer Headers

Pass through all headers as-is (useful for custom origin headers):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: passthrough
  namespace: web-team
spec:
  configRef: general-policy
  name: passthrough-all-headers
  comment: "Pass through all headers to origin"
  headersConfig:
    headerBehavior: allViewer
  cookiesConfig:
    cookieBehavior: all
  queryStringsConfig:
    queryStringBehavior: all
```

### Forward Query Strings Only

Forward query parameters but not headers or cookies:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: query-only
  namespace: app-team
spec:
  configRef: general-policy
  name: forward-query-strings
  comment: "Forward query strings only"
  queryStringsConfig:
    queryStringBehavior: all
  headersConfig:
    headerBehavior: none
  cookiesConfig:
    cookieBehavior: none
```

### Forward Specific Query Parameters

Only forward certain query params (e.g., for API filtering):

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: filtered-queries
  namespace: api-team
spec:
  configRef: general-policy
  name: forward-filter-queries
  comment: "Forward only filter-related query params"
  queryStringsConfig:
    queryStringBehavior: whitelist
    queryStrings:
      - filter
      - sort
      - page
      - limit
  headersConfig:
    headerBehavior: none
  cookiesConfig:
    cookieBehavior: none
```

### Forward CloudFront Geolocation Headers

Include CloudFront's geolocation and device detection headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: geo-aware
  namespace: web-team
spec:
  configRef: general-policy
  name: forward-geo-headers
  comment: "Forward geolocation and device headers"
  headersConfig:
    headerBehavior: allViewerAndWhitelistCloudFront
  cookiesConfig:
    cookieBehavior: none
  queryStringsConfig:
    queryStringBehavior: none
```

### Selective Header Forwarding

Forward specific headers needed by your backend:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontOriginRequestPolicy
metadata:
  name: custom-headers
  namespace: app-team
spec:
  configRef: general-policy
  name: forward-custom-headers
  comment: "Forward custom app headers"
  headersConfig:
    headerBehavior: whitelist
    headers:
      - X-Custom-Header
      - X-Request-ID
      - X-API-Version
      - User-Agent
      - Accept-Language
  cookiesConfig:
    cookieBehavior: none
  queryStringsConfig:
    queryStringBehavior: none
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
  name: api
  namespace: api-team
spec:
  # ...
  defaultCacheBehavior:
    targetOriginID: api-origin
    originRequestPolicyRef: auth-forward  # Resolves to local CloudFrontOriginRequestPolicy CR
```

## Common Patterns

### Static Site (S3)

Forward nothing — CloudFront only sends the Host header:

```yaml
headersConfig:
  headerBehavior: none
cookiesConfig:
  cookieBehavior: none
queryStringsConfig:
  queryStringBehavior: none
```

### API Gateway Backend

Forward authorization, all query strings:

```yaml
headersConfig:
  headerBehavior: whitelist
  headers:
    - Authorization
    - Content-Type
cookiesConfig:
  cookieBehavior: all
queryStringsConfig:
  queryStringBehavior: all
```

### Custom Web Server

Forward all viewer headers and query strings:

```yaml
headersConfig:
  headerBehavior: allViewer
queryStringsConfig:
  queryStringBehavior: all
cookiesConfig:
  cookieBehavior: all
```

## Relationship to Cache Policy

- **Cache Policy** — Defines what CloudFront caches (based on headers, cookies, query strings)
- **Origin Request Policy** — Defines what is forwarded to the origin

**Example:** You might cache by cookie (separate cache entries for different users) but forward all cookies to the origin.

## Troubleshooting

### Origin Returns 400 / Missing Data

Origin might need headers you're not forwarding:
- Add required headers via `headersConfig.headers`
- Use `allViewer` to pass through all headers as-is

### Authentication Not Working

If using auth headers:
- Include `Authorization` header in the whitelist
- Forward cookies if using session-based auth
- Ensure backend doesn't rely on undeclared headers

---

See [CloudFrontDistribution](./cloudfrontdistribution.md) for usage with distributions.
