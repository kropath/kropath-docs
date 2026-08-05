# ELBTargetGroup — Target Groups and Health Checks

The `ELBTargetGroup` resource represents a target group in AWS. Target groups route traffic to registered targets — EC2 instances, IP addresses, Lambda functions, or other ALBs. They are created independently and referenced by listeners and routing rules.

## Target Types

| Type | Use Case | Protocols |
|---|---|---|
| **instance** | EC2 instances and on-premises servers | HTTP, HTTPS, TCP, TLS, UDP, TCP_UDP, GENEVE |
| **ip** | IP addresses (any network interface) | HTTP, HTTPS, TCP, TLS, UDP, TCP_UDP, GENEVE |
| **lambda** | Lambda functions | HTTP, HTTPS (no protocol field needed) |
| **alb** | Application Load Balancers (cross-LB routing) | HTTP, HTTPS |

**Important:** The target type is immutable after creation. Choose the correct type when creating the resource.

## Core Fields

### Target Group Identity

| Field | Type | Default | Purpose |
|---|---|---|---|
| `configRef` | string | `"general-policy"` | Selects which `ELBConfig` governance profile to apply |
| `targetType` | string | `"instance"` | `"instance"`, `"ip"`, `"lambda"`, or `"alb"` |
| `nameOverride` | string | `""` | Bypasses the naming template; sets the target group name directly |
| `deletionPolicy` | string | `"retain"` | Behavior when deleted: `"retain"` (keeps AWS TG) or `"delete"` (deletes AWS TG) |

### Protocol and Port

| Field | Type | Required | Purpose |
|---|---|---|---|
| `protocol` | string | for instance/ip/alb | `HTTP`, `HTTPS`, `TCP`, `TLS`, `UDP`, `TCP_UDP`, `GENEVE`. Omit for Lambda targets. |
| `protocolVersion` | string | `"HTTP1"` (HTTP/HTTPS) | `"HTTP1"`, `"HTTP2"`, or `"GRPC"` (HTTP/HTTPS targets only) |
| `port` | integer | for instance/ip/alb | Port targets receive traffic on (1–65535). GENEVE uses 6081. Omit for Lambda targets. |
| `vpcId` | string | for instance/ip/alb | VPC ID. Required unless target type is lambda. |

### Health Check Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `healthCheck.enabled` | boolean | `true` | Enable health checks (always enabled for instance/ip/alb; optional for lambda) |
| `healthCheck.protocol` | string | varies by LB | `HTTP`, `HTTPS`, `TCP`, `TLS`, `GENEVE`, `UDP` |
| `healthCheck.port` | string | `"traffic-port"` | Port for health checks (`"traffic-port"` or a specific port number) |
| `healthCheck.path` | string | `"/"` | Health check path (HTTP/HTTPS targets only) |
| `healthCheck.intervalSeconds` | integer | varies by LB | Seconds between checks (5–300) |
| `healthCheck.timeoutSeconds` | integer | varies by LB | Timeout in seconds (2–120) |
| `healthCheck.healthyThreshold` | integer | `3` (instance), `2` (ip/lambda) | Consecutive successes before healthy (2–10) |
| `healthCheck.unhealthyThreshold` | integer | `3` (instance), `2` (ip/lambda) | Consecutive failures before unhealthy (2–10) |
| `healthCheck.matcher.httpCode` | string | `"200"` | HTTP success codes (e.g. `"200-299"`, `"200,201"`) |
| `healthCheck.matcher.grpcCode` | string | `"0"` | gRPC success codes (e.g. `"0-99"`) |

### Advanced Configuration

| Field | Type | Default | Purpose |
|---|---|---|---|
| `ipAddressType` | string | `"ipv4"` | `"ipv4"` or `"ipv6"` (for ip target type) |
| `stickiness.enabled` | boolean | `false` | Enable session stickiness |
| `stickiness.type` | string | `"lb_cookie"` | `"lb_cookie"`, `"app_cookie"`, or `"source_ip"` |
| `stickiness.durationSeconds` | integer | varies | Cookie duration (1–604800 seconds) |
| `deregistrationDelay` | integer | `300` | Seconds before deregistering unhealthy targets (0–3600) |
| `slowStartDuration` | integer | `0` | Slow start ramp-up seconds (30–900, 0=disabled) |

### Target Registration

| Field | Type | Purpose |
|---|---|---|
| `targets` | array | Static target registration |
| `targets[].id` | string | Target ID (instance ID, IP address, Lambda ARN, or ALB ARN) |
| `targets[].port` | integer | Optional port override for this target |
| `targets[].availabilityZone` | string | Optional AZ for cross-zone targets; `"all"` for all AZs |

### Metadata and Tags

| Field | Type | Default | Purpose |
|---|---|---|---|
| `tags` | map | `{}` | AWS tags; merged with governance tags |
| `syncedLabels` | map | `{}` | Kubernetes labels and AWS tags (prefixed `aws.kropath.run/`) |
| `syncedAnnotations` | map | `{}` | Kubernetes annotations (prefixed `aws.kropath.run/`) |
| `additionalAttributes` | array | `[]` | Additional key-value attributes beyond typed fields |

## Status Outputs

After reconciliation, the target group's status contains:

| Field | Type | Purpose |
|---|---|---|
| `resourceName` | string | The effective target group name in AWS (derived from naming template or `nameOverride`) |
| `namingStatus` | string | `"valid"` if the name is ready, `"invalid-unresolved-tokens"` if template has unresolved tokens |
| `conditions` | array | Status conditions (ready, error, etc.) |

**Note:** There is no `status.predictedArn` because target group ARNs include a hash suffix assigned by AWS at creation time.

## Complete Examples

### HTTP Target Group with Instance Registration

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: web-targets
  namespace: web-team
spec:
  configRef: general-policy
  targetType: instance
  protocol: HTTP
  port: 80
  vpcId: vpc-0a1b2c3d4e5f6g7h8
  healthCheck:
    enabled: true
    protocol: HTTP
    path: /healthz
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThreshold: 2
    unhealthyThreshold: 2
    matcher:
      httpCode: "200-299"
  targets:
    - id: i-0abc1234def567890
      port: 8080
    - id: i-0def4567abc890123
      port: 8080
  tags:
    tier: web
```

### HTTPS Target Group with Sticky Sessions

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: api-targets
  namespace: api-team
spec:
  configRef: general-policy
  targetType: instance
  protocol: HTTPS
  port: 443
  vpcId: vpc-0a1b2c3d4e5f6g7h8
  protocolVersion: HTTP2
  healthCheck:
    enabled: true
    protocol: HTTPS
    path: /api/health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThreshold: 2
    unhealthyThreshold: 3
  stickiness:
    enabled: true
    type: lb_cookie
    durationSeconds: 86400
  deregistrationDelay: 30
  tags:
    tier: api
```

### Lambda Target Group

Lambda target group with gRPC protocol version:

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: grpc-targets
  namespace: functions-team
spec:
  configRef: general-policy
  targetType: lambda
  protocolVersion: GRPC
  healthCheck:
    enabled: true
    protocol: HTTPS
    path: /grpc.health.v1.Health/Check
    matcher:
      grpcCode: "0"
  targets:
    - id: "arn:aws:lambda:us-east-1:123456789012:function:my-grpc-handler"
  tags:
    runtime: lambda
```

### NLB Target Group with TCP

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: db-targets
  namespace: data-team
spec:
  configRef: general-policy
  targetType: instance
  protocol: TCP
  port: 5432
  vpcId: vpc-0a1b2c3d4e5f6g7h8
  healthCheck:
    enabled: true
    protocol: TCP
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThreshold: 3
    unhealthyThreshold: 3
  deregistrationDelay: 60
  tags:
    service: postgres
```

### IP Target Group for Kubernetes

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: k8s-targets
  namespace: cluster-team
spec:
  configRef: general-policy
  targetType: ip
  protocol: HTTP
  port: 8080
  vpcId: vpc-0a1b2c3d4e5f6g7h8
  ipAddressType: ipv4
  healthCheck:
    enabled: true
    protocol: HTTP
    path: /ready
    intervalSeconds: 15
    timeoutSeconds: 3
    healthyThreshold: 2
    unhealthyThreshold: 2
  targets:
    - id: 10.0.1.100
      port: 8080
      availabilityZone: us-east-1a
    - id: 10.0.2.100
      port: 8080
      availabilityZone: us-east-1b
  tags:
    orchestration: kubernetes
```

## Health Check Defaults

Default health check settings vary by load balancer type and target type:

| LB Type | Protocol | Interval | Timeout | Healthy | Unhealthy |
|---|---|---|---|---|---|
| ALB | HTTP | 30s | 5s | 5 | 2 |
| ALB | HTTPS | 30s | 5s | 5 | 2 |
| NLB | TCP | 30s | 3s | 3 | 3 |
| NLB | TLS | 30s | 3s | 3 | 3 |
| NLB (UDP) | UDP | 30s | 3s | 3 | 3 |
| GWLB | GENEVE | 30s | 3s | 3 | 3 |

## Session Stickiness

Session stickiness (affinity) keeps requests from the same client going to the same target:

```yaml
stickiness:
  enabled: true
  type: lb_cookie               # ALB/NLB
  durationSeconds: 86400        # 1 day
```

For application-controlled cookies:

```yaml
stickiness:
  enabled: true
  type: app_cookie
  cookieName: JSESSIONID        # Your app's session cookie name
  durationSeconds: 3600
```

## Deregistration Delay (Connection Draining)

Gracefully close connections to targets being removed:

```yaml
deregistrationDelay: 60  # 60 seconds to drain connections
```

During deregistration delay:
- No new requests are sent to the target
- Existing connections continue until closed or timeout expires
- If connections remain after delay expires, they are forcibly closed

## Slow Start

Ramp up traffic gradually to new targets:

```yaml
slowStartDuration: 120  # Gradually increase traffic over 2 minutes
```

New targets receive a percentage of traffic that increases over the slow start period, preventing overload on cold starts.

## Naming Convention

Target groups use the same naming template system as load balancers. The default template is `{namespace}-{name}`.

Available tokens:
- `{name}` — Resource's Kubernetes name
- `{namespace}` — Resource's Kubernetes namespace
- `{configRef}` — Governance profile name
- `{account_id}` — AWS account ID
- `{region}` — AWS region
- `{tag.KEY}` — Tag values

Example: With template `{namespace}-{configRef}-{name}`, a target group named `api-targets` in namespace `api-team` using `general-policy` profile becomes `api-team-general-policy-api-targets`.
