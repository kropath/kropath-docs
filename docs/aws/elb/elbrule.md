# ELBRule — ALB Routing Rules

The `ELBRule` resource defines routing rules on an ALB listener. Rules evaluate match conditions in priority order and apply actions when conditions match.

**Important:** Rules are ALB-only. NLB and GWLB listeners do not support rules.

## Key Concepts

- **Priority:** Lower numbers evaluated first (1 is highest priority)
- **Conditions:** All conditions must match for the rule to trigger
- **Actions:** Same action types as listener default actions (forward, redirect, fixed-response)

## Core Fields

### Rule Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ELBConfig` governance profile to apply |
| `listenerRef` | string | required | Name of the `ELBListener` CR in the same namespace |
| `priority` | integer | required | Rule priority (unique within listener; lower = higher precedence) |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` or `"delete"` |

### Conditions

| Field | Type | Purpose |
|---|---|---|
| `conditions` | array | Match conditions (at least one required) |
| `conditions[].field` | string | `host-header`, `http-header`, `http-request-method`, `path-pattern`, `query-string`, `source-ip` |
| `conditions[].hostHeaderConfig.values` | array | Hostname patterns (wildcards * and ? supported) |
| `conditions[].httpHeaderConfig.httpHeaderName` | string | HTTP header name to match |
| `conditions[].httpHeaderConfig.values` | array | Header value patterns |
| `conditions[].httpRequestMethodConfig.values` | array | HTTP methods (GET, POST, PUT, DELETE, etc.) |
| `conditions[].pathPatternConfig.values` | array | URL path patterns (wildcards * and ? supported) |
| `conditions[].queryStringConfig.values` | array | Query string key-value pairs |
| `conditions[].sourceIPConfig.values` | array | CIDR ranges for source IP matching |

### Actions

| Field | Type | Purpose |
|---|---|---|
| `actions` | array | Actions to apply when rule matches (at least one required) |
| `actions[].type` | string | `forward`, `fixed-response`, `redirect`, `authenticate-cognito`, `authenticate-oidc` |
| `actions[].targetGroupRef` | string | Target group for `forward` action |
| `actions[].forwardConfig` | object | Weighted forward to multiple target groups |
| `actions[].redirectConfig` | object | Redirect to different protocol/host/path |
| `actions[].fixedResponseConfig` | object | Return a fixed HTTP response |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the rule's status contains:

| Field | Type | Purpose |
|---|---|---|
| `conditions` | array | Status conditions (ready, error, etc.) |

**Note:** Rules have no `status.resourceName` or `status.predictedArn` because they lack a provider `name` field.

## Complete Examples

### Path-Based Routing

Route `/api/*` to API target group, `/static/*` to static content:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: api-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/api/*"
  actions:
    - type: forward
      targetGroupRef: api-targets

---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: static-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 2
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/static/*"
  actions:
    - type: forward
      targetGroupRef: static-targets
```

### Host-Based Routing

Route `api.example.com` to API, `admin.example.com` to admin:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: api-host-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: host-header
      hostHeaderConfig:
        values:
          - "api.example.com"
  actions:
    - type: forward
      targetGroupRef: api-targets

---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: admin-host-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 2
  conditions:
    - field: host-header
      hostHeaderConfig:
        values:
          - "admin.example.com"
          - "*.admin.example.com"
  actions:
    - type: forward
      targetGroupRef: admin-targets
```

### HTTP Method Routing

Route POST/PUT/DELETE to API, GET to read-only targets:

```yaml
---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: write-methods-rule
  namespace: api-team
spec:
  configRef: general-policy
  listenerRef: api-listener
  priority: 1
  conditions:
    - field: http-request-method
      httpRequestMethodConfig:
        values:
          - "POST"
          - "PUT"
          - "DELETE"
          - "PATCH"
  actions:
    - type: forward
      targetGroupRef: api-write-targets

---
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: read-methods-rule
  namespace: api-team
spec:
  configRef: general-policy
  listenerRef: api-listener
  priority: 2
  conditions:
    - field: http-request-method
      httpRequestMethodConfig:
        values:
          - "GET"
          - "HEAD"
          - "OPTIONS"
  actions:
    - type: forward
      targetGroupRef: api-read-targets
```

### Custom Header Matching

Route requests with specific headers:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: beta-users-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: http-header
      httpHeaderConfig:
        httpHeaderName: "X-Beta-User"
        values:
          - "true"
  actions:
    - type: forward
      targetGroupRef: beta-targets
```

### Query String Matching

Route based on query parameters:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: version-query-rule
  namespace: api-team
spec:
  configRef: general-policy
  listenerRef: api-listener
  priority: 1
  conditions:
    - field: query-string
      queryStringConfig:
        values:
          - key: "version"
            value: "v2"
  actions:
    - type: forward
      targetGroupRef: api-v2-targets
```

### Source IP Matching

Route internal requests differently:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: internal-ips-rule
  namespace: operations-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: source-ip
      sourceIPConfig:
        values:
          - "10.0.0.0/8"
          - "172.16.0.0/12"
  actions:
    - type: forward
      targetGroupRef: internal-targets
```

### Multiple Conditions (AND)

Route only when all conditions match:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: api-v2-post-rule
  namespace: api-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/api/v2/*"
    - field: http-request-method
      httpRequestMethodConfig:
        values:
          - "POST"
  actions:
    - type: forward
      targetGroupRef: api-v2-write-targets
```

All conditions must match for the rule to apply.

### Weighted Canary Routing

Route 95% to stable, 5% to canary:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: canary-rule
  namespace: api-team
spec:
  configRef: general-policy
  listenerRef: api-listener
  priority: 1
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/api/*"
  actions:
    - type: forward
      forwardConfig:
        targetGroups:
          - targetGroupRef: api-stable-targets
            weight: 95
          - targetGroupRef: api-canary-targets
            weight: 5
        targetGroupStickinessConfig:
          enabled: true
          durationSeconds: 86400
```

### Redirect with Path Rewrite

Redirect `/old-path/*` to `/new-path`:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: path-redirect-rule
  namespace: web-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 1
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/old-path/*"
  actions:
    - type: redirect
      redirectConfig:
        protocol: "#{protocol}"
        host: "#{host}"
        path: "/new-path#{path}"
        port: "#{port}"
        query: "#{query}"
        statusCode: "HTTP_301"
```

### Fixed Response for Maintenance

Return maintenance page for specific paths:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: maintenance-rule
  namespace: ops-team
spec:
  configRef: general-policy
  listenerRef: https-listener
  priority: 99  # Low priority; evaluated last
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - "/maintenance-mode"
  actions:
    - type: fixed-response
      fixedResponseConfig:
        statusCode: "503"
        contentType: "text/html"
        messageBody: "<html><body><h1>Under Maintenance</h1><p>We'll be back soon!</p></body></html>"
```

## Priority and Evaluation Order

Rules are evaluated in priority order (lower number = higher priority):

- Priority 1 evaluated first
- Priority 2 evaluated next
- Priority 100 evaluated last
- Priorities must be unique within a listener

Assign priorities to control rule precedence:

```yaml
# High priority (specific rules)
priority: 1   # /api/health
priority: 2   # /api/*
priority: 10  # /admin/*

# Low priority (catch-all or fallback)
priority: 100  # Default forward
```

The listener's default actions apply if no rules match.

## Path Pattern Syntax

Path patterns support wildcards:

| Pattern | Matches |
|---|---|
| `/api/*` | `/api/`, `/api/users`, `/api/users/123`, etc. |
| `/images/*.jpg` | `/images/logo.jpg`, `/images/photo.jpg`, etc. |
| `/?.gif` | `/a.gif`, `/b.gif`, but not `/ab.gif` |
| `/api?` | `/api1`, `/api2`, but not `/api` or `/api/` |

## Hostname Pattern Syntax

Hostnames support wildcards:

| Pattern | Matches |
|---|---|
| `example.com` | Exact match: `example.com` |
| `*.example.com` | Subdomains: `api.example.com`, `admin.example.com` |
| `*.example.*` | Any domain like `example.com`, `example.co.uk` |

## Condition Matching Rules

- All conditions in a single rule must match (AND logic)
- Values within a condition use OR logic (e.g., `["/api/*", "/v2/*"]` matches either)
- Source IP matches against the client IP (not X-Forwarded-For)
