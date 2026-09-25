---
title: AWS Elastic Load Balancing (ELB) Family
description: The AWS ELB family within kropath provides abstractions for managing Amazon Elastic Load Balancers and their routing components.
doc_type: reference
weight: 240
---
# AWS Elastic Load Balancing (ELB) Family

The AWS ELB family within kropath provides abstractions for managing Amazon Elastic Load Balancers and their routing components. It enables platform engineers to enforce organization-wide controls such as TLS security policies, deletion protection, and access logging, while allowing application teams to provision and configure load balancers, target groups, and routing rules for their workloads.

The ELB family supports all three ELBv2 load balancer types:
- **Application Load Balancer (ALB):** Layer 7 (application) load balancing for HTTP/HTTPS traffic
- **Network Load Balancer (NLB):** Layer 4 (transport) load balancing for TCP/UDP traffic
- **Gateway Load Balancer (GWLB):** Inline traffic inspection and modification via appliances

## Prerequisites and Setup

ELB resources require AWS networking infrastructure to be in place:

- **VPC and Subnets:** Specify the VPC ID and subnets where load balancers will listen for traffic. For ALBs, you must specify at least two subnets in different availability zones.
- **Security Groups:** Required for ALB and NLB; GWLB does not use security groups. Specify security group IDs that define inbound and outbound rules for traffic.
- **ACM Certificates:** Required for HTTPS and TLS listeners. Provide the ARN of an AWS Certificate Manager certificate.
- **KMS Keys (optional):** For managing encryption and access policies via the IAM family.

Integration with other kropath families:

- **IAM Family:** For specifying roles and policies that govern access to load balancer configurations.
- **Security Groups (future):** For referencing pre-created security groups by name via the network family.

## Configuration

Kropath's ELB configuration is managed through the following resources:

- `ELBConfig`: Governance profiles that enforce organization-wide policies across load balancers, target groups, and listeners.
- `ELBLoadBalancer`: Instances representing individual load balancers.
- `ELBTargetGroup`: Instances representing target groups that route traffic to backends.
- `ELBListener`: Instances representing listeners that accept incoming traffic on a specific protocol and port.
- `ELBRule`: Instances representing ALB routing rules for advanced traffic routing.

### Governance Model: ELBConfig

`ELBConfig` CRs define per-profile governance settings for the ELB family. Each profile is referenced by load balancer, target group, listener, and rule instances via `spec.configRef`.

#### Core Governance Fields

`ELBConfig` provides two governance tiers:

- **`mandatory`:** Policies that cannot be overridden at the instance level. When a field is mandatory, instance specifications are ignored or validated against the policy.
- **`defaults`:** Baseline configurations that instances can override. Defaults apply only when the instance does not explicitly set a value.

**Load Balancer Governance (applies to `ELBLoadBalancer` only):**

- `deletionProtection` (boolean): When mandatory, all load balancers must have deletion protection enabled, preventing accidental deletion.
- `accessLogsEnabled` (boolean): When mandatory, all load balancers must send access logs to an S3 bucket.
- `accessLogsS3Bucket` (string): The S3 bucket name for access logs (used with `accessLogsEnabled`).
- `crossZoneEnabled` (boolean): When mandatory on NLB/GWLB, load balancing across availability zones is enforced. ALB always has cross-zone enabled.
- `internalOnly` (boolean): When mandatory, load balancers are forced to be internal-facing; when default, they default to internal unless the instance specifies otherwise.
- `idleTimeoutSeconds` (integer): The idle timeout for ALB connections (1–4000 seconds). When mandatory on an ALB, this value overrides instance settings.
- `sslPolicy` (string): The TLS security policy for HTTPS/TLS listeners (e.g., `"ELBSecurityPolicy-TLS13-1-2-2021-06"`). When mandatory, all listeners must use this policy.

**Naming and Metadata:**

- `namingTemplate` (string): Template for cloud resource names using tokens like `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, and `{tag.<key>}`.
- `tags` (map): Organization-wide AWS tags applied to all resources in the family.
- `syncedLabels` and `syncedAnnotations` (maps): Kubernetes metadata synchronized as AWS tags with the `aws.kropath.run/` prefix.

#### Example Profiles

- `general-policy`: Conservative defaults suitable for most workloads (e.g., cross-zone enabled by default, deletion protection optional).
- `production`: Stricter profile mandatory deletion protection, mandatory access logging, mandatory TLS policy for listeners.
- `internal-only`: Forces all load balancers to be internal-facing.

#### Example ELBConfig

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBConfig
metadata:
  name: production
  namespace: platform-engineering
spec:
  mandatory:
    deletionProtection: true
    accessLogsEnabled: true
    accessLogsS3Bucket: org-lb-logs
    sslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
  defaults:
    internalOnly: false
    crossZoneEnabled: true
    idleTimeoutSeconds: 60
    namingTemplate: "{namespace}-{name}-{configRef}"
    tags:
      managed-by: platform-team
      cost-center: platform
    syncedLabels:
      governance: production
```

### Governance Cascade

Kropath uses a layered cascade to resolve effective configuration for ELB resources:

1. **KropathConfig org-wide mandatory** → Org-wide enforcement (applies to all resources)
2. **ELBConfig profile mandatory** → Profile-specific enforcement
3. **Instance spec** → Instance-level overrides
4. **ELBConfig profile defaults** → Profile-specific defaults
5. **KropathConfig org-wide defaults** → Org-wide defaults

The governance cascade is applied during resource reconciliation. All resources (load balancers, target groups, listeners, rules) read the effective configuration from the selected `ELBConfig` profile.

**When to use `KropathConfig.elb` vs. `ELBConfig`:**

- **`KropathConfig.elb`:** For blanket, organization-wide policies that apply across *all* ELBConfig profiles. For example, `KropathConfig.mandatory.elb.deletionProtection: true` forces deletion protection on every load balancer regardless of profile.
- **`ELBConfig`:** For per-profile governance. For instance, a `production` `ELBConfig` might mandate access logging only for production workloads, while allowing other profiles to skip it.

---

## ELBLoadBalancer

An `ELBLoadBalancer` instance represents the desired state of an AWS Elastic Load Balancer. You can provision ALB, NLB, or GWLB load balancers with this resource.

### Core Fields

- `configRef` (string, default: `"general-policy"`): Selects the `ELBConfig` governance profile.
- `type` (string, required, immutable): `"application"`, `"network"`, or `"gateway"`. Cannot be changed after creation.
- `scheme` (string, default: `"internet-facing"`): `"internet-facing"` or `"internal"`. Governable by `ELBConfig.mandatory.internalOnly`.
- `ipAddressType` (string, default: `"ipv4"`): `"ipv4"`, `"dualstack"`, or `"dualstack-without-public-ipv4"`. Internal LBs must use `"ipv4"`.
- `subnets` (array of strings): Subnet IDs where the LB listens. Mutually exclusive with `subnetMappings`.
- `subnetMappings` (array): Detailed subnet configurations with optional Elastic IP allocations or private IP addresses (for NLB).
- `securityGroups` (array): Security group IDs (ALB and NLB only).
- `deletionProtection` (boolean, default: `false`): Protects the load balancer from accidental deletion. Governable.
- `accessLogging` (object): S3 access log configuration.
  - `enabled` (boolean, default: `false`): Enable access logging.
  - `s3Bucket` (string): S3 bucket name for logs. Governable.
  - `s3Prefix` (string): S3 key prefix for logs.
- `crossZoneLoadBalancing` (boolean, default: `false` for NLB/GWLB): Enable cross-zone load balancing. Always enabled for ALB. Governable.
- `idleTimeoutSeconds` (integer, default: `0`): Idle timeout in seconds (ALB only; 1–4000). Governable.
- `nameOverride` (string): Bypass the naming template and specify a custom cloud resource name.
- `deletionPolicy` (string, default: `"retain"`): On CR deletion, `"retain"` keeps the AWS load balancer; `"delete"` removes it.
- `tags` and `syncedLabels` / `syncedAnnotations`: Metadata merged with governance configuration.

### Naming Convention

Load balancer names must be 1–32 characters, contain only alphanumeric characters and hyphens, and not start or end with a hyphen or the prefix `"internal-"`. The default naming template is `"{namespace}-{name}"`, which generates names like `"my-app-api-lb"` (with `.lowerAscii()` applied).

### Example ELBLoadBalancer

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBLoadBalancer
metadata:
  name: api-lb
  namespace: production
spec:
  configRef: production
  type: application
  scheme: internet-facing
  ipAddressType: ipv4
  subnets:
    - subnet-12345678
    - subnet-87654321
  securityGroups:
    - sg-abcdef01
  deletionProtection: true
  accessLogging:
    enabled: true
    s3Bucket: my-org-lb-logs
    s3Prefix: api/
  crossZoneLoadBalancing: true
  idleTimeoutSeconds: 60
  deletionPolicy: retain
  tags:
    environment: production
    team: platform
  syncedLabels:
    tier: frontend
```

---

## ELBTargetGroup

An `ELBTargetGroup` instance represents a target group that routes traffic to registered targets (EC2 instances, IP addresses, Lambda functions, or other ALBs).

### Core Fields

- `configRef` (string, default: `"general-policy"`): Selects the `ELBConfig` governance profile.
- `targetType` (string, required, immutable): `"instance"`, `"ip"`, `"lambda"`, or `"alb"`. Cannot be changed after creation.
- `protocol` (string): `"HTTP"`, `"HTTPS"`, `"TCP"`, `"TLS"`, `"UDP"`, `"TCP_UDP"`, or `"GENEVE"`.
- `protocolVersion` (string, default: `"HTTP1"`): `"HTTP1"`, `"HTTP2"`, or `"GRPC"` (HTTP/HTTPS targets only).
- `port` (integer): The port targets receive traffic on (omit for Lambda targets). GENEVE uses port 6081.
- `vpcId` (string): VPC ID (required unless target type is lambda).
- `ipAddressType` (string, default: `"ipv4"`): `"ipv4"` or `"ipv6"`.
- `healthCheck` (object): Health check configuration.
  - `enabled` (boolean, default: `true`): Enable health checks.
  - `protocol` (string): Health check protocol (default varies by target type).
  - `port` (string, default: `"traffic-port"`): Health check port.
  - `path` (string, default: `"/"`): HTTP/HTTPS health check path.
  - `intervalSeconds` (integer, default: 30): Interval between checks (5–300 seconds).
  - `timeoutSeconds` (integer, default: 5): Timeout per check (2–120 seconds).
  - `healthyThreshold` (integer, default: 5): Consecutive successes before healthy (2–10).
  - `unhealthyThreshold` (integer, default: 2): Consecutive failures before unhealthy (2–10).
  - `matcher` (object): Success codes for HTTP/HTTPS (e.g., `"200-299"`) or gRPC.
- `stickiness` (object): Session stickiness configuration.
  - `enabled` (boolean, default: `false`): Enable sticky sessions.
  - `type` (string): `"lb_cookie"`, `"app_cookie"`, or `"source_ip"` (varies by load balancer type).
  - `durationSeconds` (integer): Cookie duration (1–604800 seconds).
- `deregistrationDelay` (integer, default: 300): Seconds to wait before deregistering unhealthy targets (0–3600).
- `slowStartDuration` (integer, default: `0`): Slow-start ramp-up time (30–900 seconds, 0=disabled).
- `targets` (array): Static target registration.
  - `id` (string): Target ID (instance ID, IP, Lambda ARN, or ALB ARN).
  - `port` (integer): Override port for this target.
  - `availabilityZone` (string): Availability zone (or `"all"` for all AZs).
- `nameOverride`, `deletionPolicy`, `tags`, `syncedLabels`, `syncedAnnotations`: Same as load balancers.

### Naming Convention

Target group names must be 1–32 characters, contain only alphanumeric characters and hyphens, and not start or end with a hyphen. The default template is `"{namespace}-{name}"`.

### Example ELBTargetGroup

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBTargetGroup
metadata:
  name: api-tg
  namespace: production
spec:
  configRef: production
  targetType: instance
  protocol: HTTP
  port: 8080
  vpcId: vpc-12345678
  ipAddressType: ipv4
  healthCheck:
    enabled: true
    protocol: HTTP
    port: traffic-port
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThreshold: 3
    unhealthyThreshold: 2
    matcher:
      httpCode: "200-299"
  stickiness:
    enabled: true
    type: lb_cookie
    durationSeconds: 3600
  deregistrationDelay: 30
  targets:
    - id: i-1234567890abcdef0
      port: 8080
    - id: i-0987654321fedcba0
  deletionPolicy: retain
  tags:
    environment: production
    service: api
```

---

## ELBListener

An `ELBListener` instance represents a listener that accepts incoming traffic on a specific protocol and port of a load balancer, then applies default actions (forward, redirect, fixed-response, or authentication).

### Core Fields

- `configRef` (string, default: `"general-policy"`): Selects the `ELBConfig` governance profile.
- `loadBalancerRef` (string, required): Name of the `ELBLoadBalancer` CR in the same namespace to attach this listener.
- `port` (integer, required): Port the load balancer listens on (1–65535; omit for GWLB).
- `protocol` (string, required): `"HTTP"`, `"HTTPS"` (ALB); `"TCP"`, `"TLS"`, `"UDP"`, `"TCP_UDP"` (NLB); `"GENEVE"` (GWLB).
- `certificateArn` (string): ARN of the default SSL certificate (HTTPS/TLS only).
- `sslPolicy` (string): TLS security policy name (HTTPS/TLS only). Governable by `ELBConfig.mandatory.sslPolicy`.
- `alpnPolicy` (string): ALPN negotiation policy for NLB TLS: `"HTTP1Only"`, `"HTTP2Only"`, `"HTTP2Optional"`, `"HTTP2Preferred"`, or `"None"`.
- `mutualAuthentication` (object): mTLS configuration.
  - `mode` (string, default: `"off"`): `"off"`, `"verify"`, or `"passthrough"`.
  - `trustStoreArn` (string): Trust store ARN for verify mode.
  - `ignoreClientCertificateExpiry` (boolean, default: `false`): Ignore expired client certificates.
- `defaultActions` (array, required): At least one terminal action.
  - `type` (string): `"forward"`, `"fixed-response"`, `"redirect"`, `"authenticate-cognito"`, or `"authenticate-oidc"`.
  - `order` (integer): Evaluation order for chained actions.
  - `targetGroupRef` (string): Name of `ELBTargetGroup` CR (for simple forward).
  - `forwardConfig` (object): Weighted forward to multiple target groups.
    - `targetGroups` (array): Target group weight entries.
      - `targetGroupRef` (string): Name of `ELBTargetGroup` CR.
      - `weight` (integer): Weight (0–999).
    - `targetGroupStickinessConfig`: Sticky session options for weighted forward.
  - `redirectConfig` (object): Redirect action.
    - `host`, `path`, `port`, `protocol`, `query` (strings): Redirect components (default: preserve from request).
    - `statusCode` (string, required): `"HTTP_301"` or `"HTTP_302"`.
  - `fixedResponseConfig` (object): Fixed response action.
    - `statusCode` (string, required): HTTP status code (2XX, 4XX, or 5XX).
    - `contentType` (string): Response content type (e.g., `"text/plain"`, `"application/json"`).
    - `messageBody` (string): Response body (max 1024 bytes).
- `deletionPolicy` (string, default: `"retain"`): Retention policy on CR deletion.
- `tags`, `syncedLabels`, `syncedAnnotations`: Metadata merged with governance.

### Naming Convention

Listeners have no custom name in AWS (they are identified by their ARN). The naming convention does not apply.

### Example ELBListener

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBListener
metadata:
  name: api-listener-https
  namespace: production
spec:
  configRef: production
  loadBalancerRef: api-lb
  protocol: HTTPS
  port: 443
  certificateArn: arn:aws:acm:us-east-1:123456789012:certificate/abc12345
  sslPolicy: ELBSecurityPolicy-TLS13-1-2-2021-06
  defaultActions:
    - type: forward
      targetGroupRef: api-tg
  deletionPolicy: retain
  tags:
    environment: production
    protocol: https
```

---

## ELBRule

An `ELBRule` instance represents an ALB routing rule that matches requests based on conditions (host-header, path-pattern, HTTP headers, request methods, query strings, or source IP) and applies an action (forward, redirect, fixed-response, or authentication).

**Rules are ALB-only.** NLB and GWLB listeners do not support rules.

### Core Fields

- `configRef` (string, default: `"general-policy"`): Selects the `ELBConfig` governance profile.
- `listenerRef` (string, required): Name of the `ELBListener` CR in the same namespace to attach this rule.
- `priority` (integer, required): Rule priority (unique within a listener; lower numbers = higher precedence). Must be > 0.
- `conditions` (array, required): Match conditions.
  - `field` (string): `"host-header"`, `"http-header"`, `"http-request-method"`, `"path-pattern"`, `"query-string"`, or `"source-ip"`.
  - `hostHeaderConfig` (object): Host header patterns (wildcards * and ? supported).
  - `httpHeaderConfig` (object): HTTP header name and value patterns.
  - `httpRequestMethodConfig` (object): HTTP methods (GET, POST, etc.).
  - `pathPatternConfig` (object): URL path patterns (wildcards supported).
  - `queryStringConfig` (object): Query string key-value pairs.
  - `sourceIPConfig` (object): CIDR ranges for source IP matching.
- `actions` (array, required): Same action types as listener default actions (forward, redirect, fixed-response, authenticate-*).
- `deletionPolicy`, `tags`, `syncedLabels`, `syncedAnnotations`: Same as other resources.

### Example ELBRule

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: ELBRule
metadata:
  name: api-v2-rule
  namespace: production
spec:
  configRef: production
  listenerRef: api-listener-https
  priority: 10
  conditions:
    - field: path-pattern
      pathPatternConfig:
        values:
          - /api/v2/*
    - field: http-header
      httpHeaderConfig:
        httpHeaderName: X-API-Version
        values:
          - "2.0"
  actions:
    - type: forward
      targetGroupRef: api-v2-tg
  deletionPolicy: retain
  tags:
    api-version: v2
```

---

## Naming Conventions

Load balancers and target groups support dynamic naming templates with token substitution:

- **Tokens:** `{namespace}`, `{name}`, `{account_id}`, `{region}`, `{configRef}`, `{tag.<key>}`.
- **Default template:** `"{namespace}-{name}"`.
- **Naming constraints:** 1–32 characters, alphanumeric and hyphens only, no leading/trailing hyphens, no `"internal-"` prefix.
- **Post-processing:** `.lowerAscii()` applied automatically.

Listeners and rules have no provider name field and do not use naming templates.

**Dynamic tag fields in naming:**

```yaml
spec:
  tags:
    environment: production
    team: platform
  # With template: "{tag.environment}-{tag.team}-lb"
  # effectiveName = "production-platform-lb"
```

---

## Cross-Provider Notes

- **Load Balancer Types:** AWS ELBv2 provides ALB, NLB, and GWLB. GCP uses separate resources for HTTP(S) Load Balancer and Cloud Network Load Balancer. Azure uses Load Balancer (standard SKU) for both L4 and L7.
- **ARN Naming:** AWS load balancer and target group ARNs include a hash suffix assigned at creation time. The full ARN is available in the resource status once the load balancer or target group is created in AWS.
- **TLS Policies:** AWS TLS policies are AWS-specific (e.g., `"ELBSecurityPolicy-TLS13-1-2-2021-06"`). GCP and Azure use different SSL policy models.
- **Listener vs. Rules:** ALB supports routing rules for content-based routing. NLB and GWLB forward all traffic to a single target group.
- **Cross-Zone:** AWS allows toggling cross-zone load balancing. GCP built-in; Azure built-in.
