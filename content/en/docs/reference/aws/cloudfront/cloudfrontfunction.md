---
title: CloudFrontFunction — Edge Compute
description: "`CloudFrontFunction` is lightweight JavaScript code that runs at CloudFront edge locations."
doc_type: reference
---
# CloudFrontFunction — Edge Compute

`CloudFrontFunction` is lightweight JavaScript code that runs at CloudFront edge locations. Functions execute in under 1ms and are ideal for URL rewrites, header manipulation, A/B testing, and simple authentication checks. Functions are associated with distributions at the `viewer-request` or `viewer-response` stage.

## Core Fields

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects `CloudFrontConfig` governance profile |
| `name` | string | `""` | Human-readable function name |
| `functionCode` | string | required | Plain-text JavaScript code (Kropath base64-encodes it for CloudFront) |
| `nameOverride` | string | `""` | Bypass naming template |
| `deletionPolicy` | string | `"retain"` | `"retain"` or `"delete"` |
| `syncedLabels` | map | `{}` | Kubernetes labels only |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations |

## Status Outputs

| Field | Type | Purpose |
|---|---|---|
| `predictedArn` | string | CloudFront function ARN (e.g., `arn:aws:cloudfront::123456789012:function/my-function`) |
| `resourceName` | string | Effective function name (after naming template) |
| `namingStatus` | string | `"valid"` or `"invalid-unresolved-tokens"` |
| `conditions[]` | array | Reconciliation status |

## Naming

Default template: `{namespace}-{name}`.

**Available tokens:** `{name}`, `{namespace}`, `{configRef}`, `{account_id}`, `{region}`, `{tag.KEY}`

Example: Resource named `rewrite-fn` in namespace `web-team` produces function name `web-team-rewrite-fn`.

## JavaScript Runtime

- **CloudFront Functions runtime:** `cloudfront-js-2.0`
- **Max execution time:** <1ms
- **Event types:** `viewer-request`, `viewer-response`
- **Language:** ECMAScript 5.1 (modern JavaScript syntax not guaranteed)

## Function Structure

A CloudFront Function receives the event object and returns a request/response:

```javascript
// Viewer-request function
function handler(event) {
  var request = event.request;
  
  // Modify request
  request.headers['x-custom-header'] = { value: 'custom-value' };
  
  return request;  // Return the modified request
}
```

## Examples

### URL Rewrite

Rewrite `/old-path/` to `/new-path/`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: url-rewrite
  namespace: web-team
spec:
  configRef: general-policy
  name: legacy-path-rewrite
  functionCode: |
    function handler(event) {
      var request = event.request;
      var uri = request.uri;
      
      // Rewrite /old-path to /new-path
      if (uri.startsWith('/old-path/')) {
        request.uri = uri.replace('/old-path/', '/new-path/');
      }
      
      return request;
    }
```

### Add Custom Headers

Add tracing headers to requests:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: add-tracing
  namespace: platform
spec:
  configRef: general-policy
  name: request-tracing
  functionCode: |
    function handler(event) {
      var request = event.request;
      var headers = request.headers;
      
      // Add trace ID if not present
      if (!headers['x-trace-id']) {
        headers['x-trace-id'] = { value: 'trace-' + Date.now() };
      }
      
      // Add function execution marker
      headers['x-cf-function'] = { value: 'request-tracing' };
      
      return request;
    }
```

### Redirect Based on Headers

Redirect mobile users to a mobile version:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: mobile-redirect
  namespace: web-team
spec:
  configRef: general-policy
  name: mobile-version-redirect
  functionCode: |
    function handler(event) {
      var request = event.request;
      var headers = request.headers;
      
      // Check if CloudFront detected a mobile device
      if (headers['cloudfront-is-mobile-viewer'] && 
          headers['cloudfront-is-mobile-viewer'].value === 'true') {
        
        // Redirect to mobile subdomain
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: {
            'location': { value: 'https://mobile.example.com' + request.uri }
          }
        };
      }
      
      return request;
    }
```

### Basic Authentication

Check for Authorization header:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: basic-auth
  namespace: platform
spec:
  configRef: general-policy
  name: require-auth
  functionCode: |
    function handler(event) {
      var request = event.request;
      var headers = request.headers;
      
      // Simple authorization check
      if (!headers.authorization) {
        return {
          statusCode: 401,
          statusDescription: 'Unauthorized',
          headers: {
            'content-type': { value: 'text/plain' }
          },
          body: 'Authorization required'
        };
      }
      
      return request;
    }
```

### Cache-Busting with Query Strings

Normalize query string order for better caching:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: normalize-qs
  namespace: api-team
spec:
  configRef: general-policy
  name: query-string-normalizer
  functionCode: |
    function handler(event) {
      var request = event.request;
      var querystring = request.querystring;
      
      // Normalize query string by removing empty values
      var normalized = {};
      for (var key in querystring) {
        if (querystring[key].value) {
          normalized[key] = querystring[key];
        }
      }
      
      request.querystring = normalized;
      return request;
    }
```

### Response Header Manipulation

Add version info to response headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: add-version
  namespace: web-team
spec:
  configRef: general-policy
  name: add-app-version
  functionCode: |
    function handler(event) {
      var response = event.response;
      var headers = response.headers;
      
      // Add app version header
      headers['x-app-version'] = { value: '2.1.0' };
      headers['x-cf-id'] = { value: event.context.distributionDomainName };
      
      return response;
    }
```

### A/B Testing

Split traffic between variants:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: ab-test
  namespace: product
spec:
  configRef: general-policy
  name: ab-test-splitter
  functionCode: |
    function handler(event) {
      var request = event.request;
      var headers = request.headers;
      
      // Use cookie or header to determine variant
      var variant = headers['x-ab-variant'];
      
      if (!variant) {
        // Assign variant based on request time (for demo)
        // In production, use a cookie or user ID
        var assigned = (Date.now() % 2 === 0) ? 'A' : 'B';
        request.headers['x-ab-variant'] = { value: assigned };
      }
      
      return request;
    }
```

## Using Functions in Distributions

Reference the function by ARN in a distribution:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontFunction
metadata:
  name: my-rewrite
  namespace: web-team
spec:
  configRef: general-policy
  name: path-rewriter
  functionCode: |
    function handler(event) {
      // ... function code ...
    }
---
apiVersion: aws.kropath.run/v1alpha1
kind: CloudFrontDistribution
metadata:
  name: my-app
  namespace: web-team
spec:
  configRef: general-policy
  origins:
    - id: origin1
      domainName: example.com
  defaultCacheBehavior:
    targetOriginID: origin1
    viewerProtocolPolicy: https-only
    cachePolicyID: 658327ea-f89d-4fab-a63d-7e88639e58f6
    functionAssociations:
      - eventType: viewer-request
        functionARN: arn:aws:cloudfront::123456789012:function/web-team-path-rewriter
```

## Event Structure

### Viewer-Request Event

```javascript
event = {
  request: {
    method: "GET",
    uri: "/path/to/resource",
    querystring: {
      param1: { value: "value1" },
      param2: { value: "value2" }
    },
    headers: {
      host: { value: "example.com" },
      "user-agent": { value: "Mozilla/5.0..." },
      // ... other headers
    },
    clientIp: "192.0.2.1"
  },
  context: {
    distributionDomainName: "d123.cloudfront.net",
    // ... other context
  }
}
```

### Viewer-Response Event

```javascript
event = {
  request: {
    method: "GET",
    uri: "/path/to/resource",
    // ... (same as viewer-request)
  },
  response: {
    statusCode: 200,
    statusDescription: "OK",
    headers: {
      "content-type": { value: "text/html" },
      "cache-control": { value: "max-age=3600" },
      // ... other headers
    }
  },
  context: {
    // ... (same as viewer-request)
  }
}
```

## Common Operations

### Get Header Value

```javascript
var userAgent = event.request.headers['user-agent'];
var value = userAgent ? userAgent.value : '';
```

### Modify URI

```javascript
event.request.uri = '/new-path' + event.request.uri;
```

### Add Query String

```javascript
event.request.querystring['new-param'] = { value: 'new-value' };
```

### Return Error Response

```javascript
return {
  statusCode: 403,
  statusDescription: 'Forbidden',
  headers: {
    'content-type': { value: 'text/plain' }
  },
  body: 'Access denied'
};
```

## Limits

- **Code size:** Max 10 KB
- **Execution time:** <1 ms (hard limit)
- **Memory:** Not user-configurable
- **Events:** `viewer-request`, `viewer-response` only (no origin events)

## CloudFront Device Detection Headers

Functions receive CloudFront's device detection headers:

| Header | Values | Purpose |
|---|---|---|
| `CloudFront-Is-Mobile-Viewer` | `true`, `false` | Detect mobile devices |
| `CloudFront-Is-Desktop-Viewer` | `true`, `false` | Detect desktop browsers |
| `CloudFront-Is-SmartTV-Viewer` | `true`, `false` | Detect smart TV devices |
| `CloudFront-Is-Tablet-Viewer` | `true`, `false` | Detect tablets |
| `CloudFront-Viewer-Country` | ISO country code | User's country |

Example: Geo-blocking using `CloudFront-Viewer-Country`:

```javascript
var country = event.request.headers['cloudfront-viewer-country'];
var blocked = ['CN', 'RU'];
if (blocked.indexOf(country.value) >= 0) {
  return {
    statusCode: 403,
    statusDescription: 'Forbidden'
  };
}
```

## Naming

Default template: `{namespace}-{name}`.

## Troubleshooting

### Function Not Executing

- Verify function is associated in `defaultCacheBehavior.functionAssociations`
- Check `eventType` is `viewer-request` or `viewer-response`
- Ensure function ARN is correct

### Syntax Error

- Verify JavaScript syntax (CloudFront uses ECMAScript 5.1)
- Test code locally first
- Check `status.conditions` for detailed error messages

### Header Not Present

Headers are case-insensitive in the function event, but CloudFront normalizes them to lowercase. Use lowercase header names in your code.

### Performance Issues

Functions must return in <1ms. Avoid:
- Complex loops or recursion
- Heavy string operations
- External API calls (not supported)

---

See [CloudFrontDistribution](./cloudfrontdistribution.md) for usage with distributions.
