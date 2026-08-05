# ELBListener — Listener Configuration and Default Actions

The `ELBListener` resource defines how a load balancer listens for inbound connections. A listener checks for incoming requests using a configured protocol and port, then applies default actions when no routing rule matches (or for non-ALB load balancers with no rules).

## Listener Protocols

| LB Type | Protocols | TLS Support |
|---|---|---|
| **ALB** | HTTP, HTTPS | HTTPS only |
| **NLB** | TCP, TLS, UDP, TCP_UDP | TLS only |
| **GWLB** | GENEVE | No TLS |

**Note:** ALB listeners support rules (conditional routing). NLB and GWLB listeners use only default actions (all traffic takes the same path).

## Core Fields

### Listener Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ELBConfig` governance profile to apply |
| `loadBalancerRef` | string | required | Name of the `ELBLoadBalancer` CR in the same namespace |
| `port` | integer | required | Listening port (1–65535). Cannot be set for GWLB. |
| `protocol` | string | required | `HTTP`, `HTTPS` (ALB); `TCP`, `TLS`, `UDP`, `TCP_UDP` (NLB); `GENEVE` (GWLB) |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` or `"delete"` |

### TLS and Certificates

| Field | Type | Purpose |
|---|---|---|
| `certificateArn` | string | Default SSL certificate ARN (HTTPS/TLS only) |
| `sslPolicy` | string | TLS security policy name (HTTPS/TLS only). Governable by `ELBConfig`. |
| `alpnPolicy` | string | ALPN negotiation policy (NLB TLS only): `HTTP1Only`, `HTTP2Only`, `HTTP2Optional`, `HTTP2Preferred`, `None` |

### Default Actions

| Field | Type | Purpose |
|---|---|---|
| `defaultActions` | array | Actions to apply when no rule matches (ALB) or for all traffic (NLB/GWLB). At least one required. |
| `defaultActions[].type` | string | `forward`, `fixed-response`, `redirect`, `authenticate-cognito`, `authenticate-oidc` |
| `defaultActions[].order` | integer | Evaluation order when chaining multiple actions |
| `defaultActions[].targetGroupRef` | string | Target group for `forward` action (simple forward to one group) |
| `defaultActions[].forwardConfig` | object | Weighted forward to multiple target groups |
| `defaultActions[].redirectConfig` | object | Redirect to different protocol/host/path/port |
| `defaultActions[].fixedResponseConfig` | object | Return a fixed HTTP response |

### Mutual Authentication (mTLS)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `mutualAuthentication.mode` | string | `"off"` | `"off"`, `"verify"`, or `"passthrough"` |
| `mutualAuthentication.trustStoreArn` | string | required for verify | ARN of trust store (for mTLS verify mode) |
| `mutualAuthentication.ignoreClientCertificateExpiry` | boolean | `false` | Ignore expired client certificates |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |

## Status Outputs

After reconciliation, the listener's status contains:

| Field | Type | Purpose |
|---|---|---|
| `conditions` | array | Status conditions (ready, error, etc.) |

**Note:** Listeners have no `status.resourceName` or `status.predictedArn` because they lack a provider `name` field.

## Default Action Types

### Forward

Route traffic to a single target group:

```yaml
defaultActions:
  - type: forward
    targetGroupRef: api-targets
```

### Weighted Forward

Route traffic to multiple target groups with weights:

```yaml
defaultActions:
  - type: forward
    forwardConfig:
      targetGroups:
        - targetGroupRef: api-targets-v1
          weight: 80
        - targetGroupRef: api-targets-v2
          weight: 20
      targetGroupStickinessConfig:
        enabled: true
        durationSeconds: 3600
```

### Redirect

Redirect requests to a different protocol, host, or path:

```yaml
defaultActions:
  - type: redirect
    redirectConfig:
      protocol: HTTPS        # or #{protocol}
      host: api.example.com  # or #{host}
      path: /v2#{path}       # or #{path}
      port: "443"            # or #{port}
      query: "#{query}"
      statusCode: HTTP_301   # or HTTP_302
```

### Fixed Response

Return a fixed HTTP response:

```yaml
defaultActions:
  - type: fixed-response
    fixedResponseConfig:
      statusCode: "503"
      contentType: text/plain
      messageBody: "Service Unavailable"
```

## Complete Examples

### HTTP Listener with Simple Forward

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: http-listener
  namespace: web-team
spec:
  configRef: general-policy
  loadBalancerRef: web-alb
  protocol: HTTP
  port: 80
  defaultActions:
    - type: forward
      targetGroupRef: web-targets
```

### HTTPS Listener with TLS Policy

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: https-listener
  namespace: api-team
spec:
  configRef: general-policy
  loadBalancerRef: api-alb
  protocol: HTTPS
  port: 443
  certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345678"
  sslPolicy: "ELBSecurityPolicy-TLS13-1-2-2021-06"
  defaultActions:
    - type: forward
      targetGroupRef: api-targets
```

### Redirect HTTP to HTTPS

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: http-redirect
  namespace: web-team
spec:
  configRef: general-policy
  loadBalancerRef: web-alb
  protocol: HTTP
  port: 80
  defaultActions:
    - type: redirect
      redirectConfig:
        protocol: HTTPS
        statusCode: HTTP_301
```

### NLB Listener with Multiple Protocol Families

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: nlb-tcp-listener
  namespace: network-team
spec:
  configRef: general-policy
  loadBalancerRef: performance-nlb
  protocol: TCP
  port: 443
  defaultActions:
    - type: forward
      targetGroupRef: secure-targets
```

### TLS Listener with ALPN

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: tls-listener
  namespace: network-team
spec:
  configRef: general-policy
  loadBalancerRef: performance-nlb
  protocol: TLS
  port: 443
  certificateArn: "arn:aws:acm:us-east-1:123456789012:certificate/12345678"
  alpnPolicy: "HTTP2Preferred"
  defaultActions:
    - type: forward
      targetGroupRef: api-targets
```

### Weighted Canary Deployment

Route 90% of traffic to stable version, 10% to new version:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: canary-listener
  namespace: api-team
spec:
  configRef: general-policy
  loadBalancerRef: api-alb
  protocol: HTTP
  port: 80
  defaultActions:
    - type: forward
      forwardConfig:
        targetGroups:
          - targetGroupRef: api-v1-targets
            weight: 90
          - targetGroupRef: api-v2-targets
            weight: 10
        targetGroupStickinessConfig:
          enabled: true
          durationSeconds: 86400
```

## Protocol and Port Constraints

- **ALB:** HTTP (80), HTTPS (443), or any port 1–65535
- **NLB:** TCP (1–65535), TLS (1–65535), UDP (1–65535), TCP_UDP (1–65535)
- **GWLB:** GENEVE (6081)

Port numbers must be unique within a load balancer (no duplicate ports).

## TLS Security Policy

Use `sslPolicy` to enforce modern TLS versions and cipher suites:

```yaml
sslPolicy: "ELBSecurityPolicy-TLS13-1-2-2021-06"
```

AWS-managed policies include:
- `ELBSecurityPolicy-TLS13-1-2-2021-06` — TLS 1.3 and 1.2 only (recommended for most new applications)
- `ELBSecurityPolicy-TLS-1-2-2017-01` — TLS 1.2 only (legacy)
- `ELBSecurityPolicy-2016-08` — TLS 1.2 and 1.1 (deprecated)

Policy is governable via `ELBConfig.mandatory.sslPolicy` to enforce compliance.

## Mutual Authentication (mTLS)

Enable mTLS to verify client certificates:

```yaml
mutualAuthentication:
  mode: "verify"
  trustStoreArn: "arn:aws:elasticloadbalancing:us-east-1:123456789012:truststore/my-trust-store"
  ignoreClientCertificateExpiry: false
```

Modes:
- `"off"` (default) — No client certificate required
- `"verify"` — Client certificate required and verified
- `"passthrough"` — Client certificate passed to target but not verified

## ALPN Policy (NLB TLS)

Advertise supported protocols during TLS negotiation:

- `HTTP2Preferred` — Prefer HTTP/2; fall back to HTTP/1.1
- `HTTP2Only` — Accept only HTTP/2
- `HTTP1Only` — Accept only HTTP/1.1
- `HTTP2Optional` — Accept HTTP/2 or HTTP/1.1
- `None` — No protocol negotiation
